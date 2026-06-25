"""Life-problem -> Jain-psychology mapping.

This is what lets Jnana Setu act as a guru rather than a search box. A person
rarely says "explain krodha"; they say "my partner betrayed me and I can't stop
seething." This module:

1. Detects whether a message is a *personal life problem* (guidance) vs a
   *scholarly question*.
2. Maps the felt experience to the underlying Jain concepts (kasaya, raga-dvesha,
   anekanta, anupreksha, samata ...), so retrieval can find the relevant teaching
   even when the user's words never match the scripture's words (query expansion).
3. Flags acute crisis language so we can respond with care and a safety net
   instead of philosophy.

Everything here is deterministic and dependency-free; it works in mock mode and
also sharpens retrieval when the real LLM + corpus are enabled.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Concept:
    key: str
    label: str  # Jain term + gloss
    triggers: list[str]  # words/phrases in everyday language
    search_terms: list[str] = field(default_factory=list)  # expand retrieval
    anuyoga: str = "all_texts"


# Ordered roughly by how often people bring these to a mentor.
CONCEPTS: list[Concept] = [
    Concept(
        "anger",
        "krodha (anger) — one of the four kasayas (passions) that bind karma",
        ["angry", "anger", "furious", "rage", "resentment", "betrayed", "hate",
         "irritated", "frustrat", "gussa", "krodh"],
        ["krodha anger kasaya passion", "forgiveness kshama", "equanimity samata",
         "raga dvesha attachment aversion"],
        "charananuyog",
    ),
    Concept(
        "pride",
        "maana (pride/ego) — the kasaya of self-importance",
        ["ego", "arrogant", "pride", "insulted", "disrespected", "humiliat",
         "superior", "inferior", "ahankar", "maan"],
        ["maana pride ego kasaya", "humility softness", "self soul jiva nature"],
        "charananuyog",
    ),
    Concept(
        "greed_materialism",
        "lobha (greed) & parigraha (possessiveness) — craving for more",
        ["greed", "money", "rich", "wealth", "materialis", "possess", "career success",
         "ambitio", "never enough", "lobh", "paisa"],
        ["lobha greed parigraha possession non-attachment aparigraha",
         "contentment santosh desire"],
        "charananuyog",
    ),
    Concept(
        "attachment_relationship",
        "raga (attachment) — clinging that becomes the root of sorrow",
        ["love", "relationship", "breakup", "partner", "spouse", "marriage",
         "clingy", "can't let go", "obsess", "miss them", "rishta", "moh"],
        ["raga attachment aversion dvesha", "equanimity detachment vairagya",
         "soul distinct from other"],
        "dravyanuyog",
    ),
    Concept(
        "fear_anxiety",
        "bhaya (fear) & the restless mind seeking refuge",
        ["anxious", "anxiety", "worried", "worry", "fear", "scared", "panic",
         "stress", "overwhelm", "restless", "chinta", "dar", "tension"],
        ["fear bhaya refuge asharana", "impermanence anitya contemplation",
         "equanimity samata steadiness of mind"],
        "charananuyog",
    ),
    Concept(
        "failure_selfworth",
        "the soul's intrinsic worth, independent of outcomes (jiva svabhava)",
        ["failure", "failed", "worthless", "not good enough", "useless", "loser",
         "ashamed", "self-doubt", "compare myself", "inadequate", "asphal"],
        ["soul jiva pure consciousness intrinsic nature", "karma fruits effort",
         "equanimity in success and failure samata"],
        "dravyanuyog",
    ),
    Concept(
        "grief_loss_death",
        "anitya (impermanence) & the deathless nature of the soul",
        ["grief", "died", "death", "loss", "lost my", "passed away", "mourning",
         "bereave", "funeral", "mrityu", "shok"],
        ["impermanence anitya transient", "soul eternal deathless immortal jiva",
         "twelve contemplations anupreksha"],
        "karnanuyoga",
    ),
    Concept(
        "jealousy_comparison",
        "irshya/maya — comparison and the distortions of the restless self",
        ["jealous", "jealousy", "envy", "compare", "comparison", "they have",
         "behind in life", "left behind", "irshya"],
        ["envy comparison maya deceit", "contentment santosh", "soul's own nature"],
        "charananuyog",
    ),
    Concept(
        "conflict_perspective",
        "anekanta (many-sidedness) — every truth has many standpoints",
        ["argument", "fight", "disagree", "conflict", "misunderstood", "they don't get",
         "stubborn", "who is right", "vivaad"],
        ["anekanta many-sided syadvada naya standpoints", "non-violence in speech"],
        "dravyanuyog",
    ),
    Concept(
        "desire_craving",
        "trishna (craving) — the thirst that the senses can never quench",
        ["addict", "craving", "can't stop", "temptation", "desire", "lust", "indulg",
         "habit i hate", "trishna", "vasana"],
        ["craving desire senses restraint sanyam", "non-attachment vairagya",
         "contentment santosh"],
        "charananuyog",
    ),
    Concept(
        "purpose_meaning",
        "moksha-marga (the path) — orienting life toward the soul's liberation",
        ["meaningless", "purpose", "point of life", "lost in life", "direction",
         "what should i do with my life", "empty inside", "jeevan ka uddeshya"],
        ["path to liberation moksha marga right faith knowledge conduct",
         "three jewels ratnatraya"],
        "dravyanuyog",
    ),
    Concept(
        "guilt_regret",
        "pratikramana (repentance) & shedding past karma (nirjara)",
        ["guilt", "regret", "i did something wrong", "can't forgive myself", "mistake",
         "sin", "shame about my past", "pashchatap", "galti"],
        ["repentance pratikramana confession", "shedding karma nirjara",
         "forgiveness kshamavani"],
        "charananuyog",
    ),
]

# First-person emotional signals that mark a message as a *life problem*.
GUIDANCE_SIGNALS = [
    r"\bi\s*('?m| am| feel| felt| can'?t| cannot| don'?t| keep| have been| was)\b",
    r"\bmy\s+(life|wife|husband|partner|boss|father|mother|son|daughter|friend|mind|heart)\b",
    r"\bme\b.*\b(sad|angry|lost|alone|stuck|broken|tired|hurt)\b",
    r"\b(should i|how do i cope|help me|what do i do|i need)\b",
    r"\b(मैं|मुझे|मेरा|मेरी|मेरे)\b",
]

# Acute-risk language. Intentionally conservative; better to over-care.
CRISIS_SIGNALS = [
    r"\b(kill myself|end my life|suicid|don'?t want to live|want to die|"
    r"no reason to live|hurt myself|harm myself|self harm)\b",
    r"\b(आत्महत्या|खुद को खत्म|जीना नहीं चाहता)\b",
]


def detect_crisis(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in CRISIS_SIGNALS)


def is_guidance(text: str) -> bool:
    t = text.lower()
    if detect_crisis(t):
        return True
    return any(re.search(p, t) for p in GUIDANCE_SIGNALS)


def match_concepts(text: str, limit: int = 3) -> list[Concept]:
    t = text.lower()
    scored: list[tuple[int, Concept]] = []
    for c in CONCEPTS:
        hits = sum(1 for trig in c.triggers if trig in t)
        if hits:
            scored.append((hits, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:limit]]


def expand_query(text: str, concepts: list[Concept]) -> str:
    """Original message + mapped Jain search terms -> better retrieval recall."""
    terms = []
    for c in concepts:
        terms.extend(c.search_terms)
    return (text + " " + " ".join(terms)).strip()


def primary_anuyoga(concepts: list[Concept]) -> str:
    return concepts[0].anuyoga if concepts else "all_texts"


def concept_brief(concepts: list[Concept]) -> str:
    """A short note handed to the LLM so it frames the reply through these lenses."""
    if not concepts:
        return ""
    lines = [f"- {c.label}" for c in concepts]
    return "RELEVANT JAIN LENSES FOR THIS PERSON'S SITUATION:\n" + "\n".join(lines)
