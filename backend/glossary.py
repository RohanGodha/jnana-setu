"""Curated glossary of key Jain (Digambar) terms for the /glossary endpoint."""
from __future__ import annotations

GLOSSARY: list[dict] = [
    {"term": "Jiva", "hindi": "जीव", "meaning": "The living substance — the soul; characterized by consciousness (chetana) and the capacity to know and perceive."},
    {"term": "Ajiva", "hindi": "अजीव", "meaning": "Non-living substances: matter (pudgala), motion (dharma), rest (adharma), space (akasha) and time (kala)."},
    {"term": "Karma", "hindi": "कर्म", "meaning": "Subtle material particles that bind to the soul through action and intention, shaping future experience."},
    {"term": "Moksha", "hindi": "मोक्ष", "meaning": "Liberation — the soul's complete release from all karmic bondage and the cycle of rebirth."},
    {"term": "Ahimsa", "hindi": "अहिंसा", "meaning": "Non-violence in thought, word and deed — the foremost vow and root of Jain ethics."},
    {"term": "Anekantavada", "hindi": "अनेकान्तवाद", "meaning": "The doctrine of many-sidedness: reality has infinite aspects, grasped only from multiple viewpoints."},
    {"term": "Syadvada", "hindi": "स्याद्वाद", "meaning": "Conditional predication — qualifying every statement with 'in some respect' (syat) to express partial truth."},
    {"term": "Naya", "hindi": "नय", "meaning": "A standpoint or partial viewpoint that apprehends one aspect of a many-sided reality."},
    {"term": "Samyak Darshana", "hindi": "सम्यग्दर्शन", "meaning": "Right faith/insight — the first of the three jewels; rational perception of reality."},
    {"term": "Samyak Jnana", "hindi": "सम्यग्ज्ञान", "meaning": "Right knowledge — accurate, doubt-free understanding of the tattvas."},
    {"term": "Samyak Charitra", "hindi": "सम्यक्चारित्र", "meaning": "Right conduct — disciplined living in accordance with the vows."},
    {"term": "Ratnatraya", "hindi": "रत्नत्रय", "meaning": "The Three Jewels: right faith, right knowledge and right conduct — together the path to liberation."},
    {"term": "Tattva", "hindi": "तत्त्व", "meaning": "The seven (or nine) fundamental truths: jiva, ajiva, asrava, bandha, samvara, nirjara, moksha."},
    {"term": "Asrava", "hindi": "आस्रव", "meaning": "Influx — the inflow of karmic matter into the soul through activity and passion."},
    {"term": "Bandha", "hindi": "बन्ध", "meaning": "Bondage — the binding of karmic matter to the soul."},
    {"term": "Samvara", "hindi": "संवर", "meaning": "Stoppage — halting the influx of new karma through restraint and awareness."},
    {"term": "Nirjara", "hindi": "निर्जरा", "meaning": "Shedding — the dissociation and falling away of karma, especially through austerity (tapa)."},
    {"term": "Kashaya", "hindi": "कषाय", "meaning": "The four passions — anger (krodha), pride (mana), deceit (maya), greed (lobha) — that bind karma."},
    {"term": "Raga-Dvesha", "hindi": "राग-द्वेष", "meaning": "Attachment and aversion — the twin afflictions that drive karmic bondage."},
    {"term": "Anuvrata", "hindi": "अणुव्रत", "meaning": "The five minor vows observed by a householder (shravaka)."},
    {"term": "Mahavrata", "hindi": "महाव्रत", "meaning": "The five great vows fully observed by ascetics (muni)."},
    {"term": "Shravaka", "hindi": "श्रावक", "meaning": "A lay follower / householder who observes the minor vows."},
    {"term": "Tirthankara", "hindi": "तीर्थंकर", "meaning": "A 'ford-maker' — an enlightened teacher who shows the path across the ocean of rebirth; 24 in each age."},
    {"term": "Kevala Jnana", "hindi": "केवलज्ञान", "meaning": "Omniscience — infinite, perfect knowledge attained on destroying all knowledge-obscuring karma."},
    {"term": "Siddha", "hindi": "सिद्ध", "meaning": "A liberated soul that has attained moksha and dwells at the summit of the universe."},
    {"term": "Nishchaya Naya", "hindi": "निश्चयनय", "meaning": "The absolute standpoint — describing things as they are in their pure intrinsic nature."},
    {"term": "Vyavahara Naya", "hindi": "व्यवहारनय", "meaning": "The conventional standpoint — describing things in their everyday, relational aspect."},
    {"term": "Anupreksha", "hindi": "अनुप्रेक्षा", "meaning": "The twelve reflections (e.g. impermanence, aloneness) that foster detachment."},
    {"term": "Anitya", "hindi": "अनित्य", "meaning": "Impermanence — the contemplation that all worldly things are transient."},
    {"term": "Tapa", "hindi": "तप", "meaning": "Austerity — external and internal disciplines that shed accumulated karma."},
    {"term": "Samayika", "hindi": "सामायिक", "meaning": "A practice of periodic equanimity and meditation, withdrawing from worldly activity."},
    {"term": "Pudgala", "hindi": "पुद्गल", "meaning": "Matter — the physical substance that combines and divides, including karmic particles."},
    {"term": "Dravya", "hindi": "द्रव्य", "meaning": "Substance — that which persists through its changing modes (paryaya)."},
    {"term": "Paryaya", "hindi": "पर्याय", "meaning": "Mode or modification — the changing states a substance passes through."},
    {"term": "Guna", "hindi": "गुण", "meaning": "Quality — an inseparable attribute of a substance."},
    {"term": "Loka", "hindi": "लोक", "meaning": "The cosmos — the uncreated, eternal universe structured into lower, middle and upper realms."},
    {"term": "Jambudvipa", "hindi": "जम्बूद्वीप", "meaning": "The central continent of the middle world, with Mount Meru at its centre."},
    {"term": "Digambara", "hindi": "दिगम्बर", "meaning": "'Sky-clad' — the Jain tradition whose monks renounce clothing as a sign of total non-attachment."},
    {"term": "Samadhi-marana", "hindi": "समाधिमरण", "meaning": "A serene, voluntary death through fasting (sallekhana) with full equanimity."},
    {"term": "Namokar Mantra", "hindi": "णमोकार मंत्र", "meaning": "The foremost Jain prayer, bowing to the five supreme beings (Pancha Parameshthi)."},
]


def all_terms() -> list[dict]:
    return GLOSSARY


def search_terms(q: str) -> list[dict]:
    q = (q or "").lower().strip()
    if not q:
        return GLOSSARY
    return [
        t for t in GLOSSARY
        if q in t["term"].lower() or q in t["meaning"].lower() or q in t["hindi"]
    ]
