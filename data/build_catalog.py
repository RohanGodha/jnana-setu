"""Generate the master books.json catalog (600 entries).

- 50 canonical Digambar texts (full metadata; seed passages for well-known ones)
- 550 modern Acharya works (11 authors x 50)

Listed titles from 04-BOOK-CORPUS.md are used where available; remaining slots
for the "to catalog" authors are generated as numbered placeholders so the
catalog, pagination and filters work end-to-end. Seed passages are concise,
representative English renderings provided for demonstration/retrieval; replace
with parsed source text via ingest.py once the real corpus is collected.

Run:  python build_catalog.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "books.json"

# (title, title_hindi, author, anuyoga, language, century)
CANONICAL = [
    ("Shatkhandagama", "षट्खण्डागम", "Acharyas Pushpadanta & Bhutabali", "dravyanuyog", "prakrit", "2nd CE"),
    ("Dhavala", "धवला", "Acharya Virasena", "dravyanuyog", "prakrit", "9th CE"),
    ("Mahadhavala", "महाधवला", "Acharya Virasena", "dravyanuyog", "prakrit", "9th CE"),
    ("Kashayapahuda", "कषायपाहुड", "Acharya Gunadhara", "dravyanuyog", "prakrit", "2nd CE"),
    ("Jayadhavala", "जयधवला", "Acharya Virasena & Jinasena", "dravyanuyog", "prakrit", "9th CE"),
    ("Tattvartha Sutra", "तत्त्वार्थसूत्र", "Acharya Umasvati", "dravyanuyog", "sanskrit", "2nd CE"),
    ("Sarvarthasiddhi", "सर्वार्थसिद्धि", "Acharya Pujyapada", "dravyanuyog", "sanskrit", "5th CE"),
    ("Tattvartha Rajavartika", "तत्त्वार्थराजवार्तिक", "Acharya Akalankadeva", "dravyanuyog", "sanskrit", "8th CE"),
    ("Tattvartha Shlokavartika", "तत्त्वार्थश्लोकवार्तिक", "Acharya Vidyananda", "dravyanuyog", "sanskrit", "9th CE"),
    ("Gommatasara (Jiva-kanda)", "गोम्मटसार जीवकाण्ड", "Acharya Nemichandra", "dravyanuyog", "prakrit", "10th CE"),
    ("Gommatasara (Karma-kanda)", "गोम्मटसार कर्मकाण्ड", "Acharya Nemichandra", "dravyanuyog", "prakrit", "10th CE"),
    ("Samayasara", "समयसार", "Acharya Kundakunda", "dravyanuyog", "prakrit", "1st CE"),
    ("Pravachanasara", "प्रवचनसार", "Acharya Kundakunda", "dravyanuyog", "prakrit", "1st CE"),
    ("Niyamasara", "नियमसार", "Acharya Kundakunda", "dravyanuyog", "prakrit", "1st CE"),
    ("Panchastikaya-sara", "पञ्चास्तिकायसार", "Acharya Kundakunda", "dravyanuyog", "prakrit", "1st CE"),
    ("Ashtapahud", "अष्टपाहुड", "Acharya Kundakunda", "dravyanuyog", "prakrit", "1st CE"),
    ("Rayansara", "रयणसार", "Acharya Kundakunda", "charananuyog", "prakrit", "1st CE"),
    ("Dash Bhakti", "दशभक्ति", "Acharya Kundakunda", "charananuyog", "prakrit", "1st CE"),
    ("Baras-anuvekkha", "बारस अणुवेक्खा", "Acharya Kundakunda", "charananuyog", "prakrit", "1st CE"),
    ("Aptamimansa", "आप्तमीमांसा", "Acharya Samantabhadra", "dravyanuyog", "sanskrit", "2nd CE"),
    ("Nyayavinischaya", "न्यायविनिश्चय", "Acharya Akalankadeva", "dravyanuyog", "sanskrit", "8th CE"),
    ("Siddhivinischaya", "सिद्धिविनिश्चय", "Acharya Akalankadeva", "dravyanuyog", "sanskrit", "8th CE"),
    ("Praman Sangrah", "प्रमाणसंग्रह", "Acharya Akalankadeva", "dravyanuyog", "sanskrit", "8th CE"),
    ("Ashtashati", "अष्टशती", "Acharya Akalankadeva", "dravyanuyog", "sanskrit", "8th CE"),
    ("Ashtasahastri", "अष्टसहस्री", "Acharya Vidyananda", "dravyanuyog", "sanskrit", "9th CE"),
    ("Dravyasamgraha", "द्रव्यसंग्रह", "Acharya Nemichandra", "dravyanuyog", "prakrit", "10th CE"),
    ("Paramatma Prakash", "परमात्मप्रकाश", "Acharya Yogindu Dev", "dravyanuyog", "apabhramsha", "6th CE"),
    ("Yogasara", "योगसार", "Acharya Yogindu Dev", "dravyanuyog", "apabhramsha", "6th CE"),
    ("Tattvasara", "तत्त्वसार", "Acharya Devsena", "dravyanuyog", "prakrit", "10th CE"),
    ("Adi Purana", "आदिपुराण", "Acharya Jinasena", "prathamanuyoga", "sanskrit", "9th CE"),
    ("Uttara Purana", "उत्तरपुराण", "Acharya Gunabhadra", "prathamanuyoga", "sanskrit", "9th CE"),
    ("Padma-Purana", "पद्मपुराण", "Acharya Ravisena", "prathamanuyoga", "sanskrit", "7th CE"),
    ("Harivamsa Purana", "हरिवंशपुराण", "Acharya Jinasena (Punnata)", "prathamanuyoga", "sanskrit", "8th CE"),
    ("Mahapurana", "महापुराण", "Acharyas Jinasena & Gunabhadra", "prathamanuyoga", "sanskrit", "9th CE"),
    ("Pandava Purana", "पाण्डवपुराण", "Acharya Shubhachandra", "prathamanuyoga", "sanskrit", "16th CE"),
    ("Parshvanatha Purana", "पार्श्वनाथपुराण", "Acharya Vadiraja", "prathamanuyoga", "sanskrit", "11th CE"),
    ("Trishashti-Shalakapurusha Charitra", "त्रिषष्टिशलाकापुरुषचरित्र", "Acharya Hemachandra", "prathamanuyoga", "sanskrit", "12th CE"),
    ("Kalpa-sutra", "कल्पसूत्र", "Acharya Bhadrabahu", "prathamanuyoga", "prakrit", "4th BCE"),
    ("Ratnakaranda Shravakachara", "रत्नकरण्डश्रावकाचार", "Acharya Samantabhadra", "charananuyog", "sanskrit", "2nd CE"),
    ("Purushartha-siddhyupaya", "पुरुषार्थसिद्ध्युपाय", "Acharya Amritachandra", "charananuyog", "sanskrit", "10th CE"),
    ("Ishtopadesh", "इष्टोपदेश", "Acharya Pujyapada", "charananuyog", "sanskrit", "5th CE"),
    ("Samadhi Tantra", "समाधितन्त्र", "Acharya Pujyapada", "charananuyog", "sanskrit", "5th CE"),
    ("Atmanushasan", "आत्मानुशासन", "Acharya Gunabhadra", "charananuyog", "sanskrit", "9th CE"),
    ("Moksha Marg Prakashak", "मोक्षमार्गप्रकाशक", "Pandit Todarmal", "charananuyog", "hindi", "18th CE"),
    ("Mulachara", "मूलाचार", "Acharya Vattakera", "charananuyog", "prakrit", "2nd CE"),
    ("Triloksara", "त्रिलोकसार", "Acharya Nemichandra", "karnanuyoga", "prakrit", "10th CE"),
    ("Jambudveepa Pragnapti", "जम्बूद्वीपप्रज्ञप्ति", "Canonical", "karnanuyoga", "prakrit", "ancient"),
    ("Svayambhu Stotra", "स्वयम्भूस्तोत्र", "Acharya Samantabhadra", "karnanuyoga", "sanskrit", "2nd CE"),
    ("Bhaktamara Stotra", "भक्तामरस्तोत्र", "Acharya Manatunga", "karnanuyoga", "sanskrit", "7th CE"),
    ("Laghu Nayachakra", "लघुनयचक्र", "Acharya Devsena", "karnanuyoga", "prakrit", "10th CE"),
]

# Seed passages keyed by title (representative English renderings for demo).
SEED = {
    "Samayasara": (
        "The soul (jiva) is, by its very nature, pure consciousness and is forever "
        "distinct from karmic matter. Though bound in worldly existence, the soul "
        "never truly becomes the karma; it only appears so from the conventional "
        "standpoint (vyavahara naya). From the absolute standpoint (nishchaya naya), "
        "the soul is the knower and seer, untouched by the modifications of matter.",
        "जीव अपने स्वभाव से शुद्ध चैतन्यस्वरूप है और कर्म-पुद्गल से सर्वथा भिन्न है।",
        "Jiva Adhikar (Chapter 2)",
    ),
    "Tattvartha Sutra": (
        "Right faith, right knowledge, and right conduct together constitute the path "
        "to liberation (samyag-darshana-jnana-charitrani mokshamargah). The substances "
        "(dravya) are six: soul, matter, medium of motion, medium of rest, space, and "
        "time. The influx (asrava), bondage (bandha), stoppage (samvara), shedding "
        "(nirjara) and liberation (moksha) of karma define the spiritual journey.",
        "सम्यग्दर्शनज्ञानचारित्राणि मोक्षमार्गः।",
        "Chapter 1",
    ),
    "Pravachanasara": (
        "He who knows the soul as it truly is — pure, conscious, and self-luminous — "
        "attains equanimity. Knowledge and the knower are not separate; the soul is "
        "itself knowledge. By abandoning attachment and aversion (raga-dvesha) and "
        "resting in pure cognition, the practitioner moves toward liberation.",
        "जो आत्मा को शुद्ध चैतन्यरूप जानता है वही समता को प्राप्त करता है।",
        "Jnana-tattva-prajnapana",
    ),
    "Ratnakaranda Shravakachara": (
        "The conduct of a householder (shravaka) rests upon right faith and the twelve "
        "vows: five minor vows (anuvrata) of non-violence, truth, non-stealing, "
        "chastity and non-possession, together with the three guna-vratas and four "
        "shiksha-vratas. Non-violence (ahimsa) is the foremost, the root of all virtue.",
        "श्रावक का आचरण सम्यग्दर्शन और बारह व्रतों पर आधारित है; अहिंसा सर्वोपरि है।",
        "Shravakachara",
    ),
    "Purushartha-siddhyupaya": (
        "Non-violence is the supreme religion (ahimsa paramo dharmah). To injure any "
        "living being through carelessness (pramada) is himsa; to act with vigilance "
        "and compassion is ahimsa. True non-violence begins in the mind, before any "
        "outward act, for it is the intention that binds or frees the soul.",
        "प्रमादयोग से प्राणियों का घात ही हिंसा है; अप्रमत्त भाव ही अहिंसा है।",
        "Ahimsa Adhikar",
    ),
    "Dravyasamgraha": (
        "There are six substances (dravya): jiva (soul), pudgala (matter), dharma "
        "(medium of motion), adharma (medium of rest), akasha (space) and kala (time). "
        "The soul is characterized by consciousness (chetana) and is the only "
        "substance possessing upayoga — the active functions of knowing and perceiving.",
        "द्रव्य छह हैं: जीव, पुद्गल, धर्म, अधर्म, आकाश और काल।",
        "Jiva Dravya",
    ),
    "Bhaktamara Stotra": (
        "Having bowed at the feet of the first Tirthankara, whose radiance dispels the "
        "darkness of delusion, the devotee praises the Lord who is the refuge of all "
        "beings. As the morning sun reveals the lotus, so devotion to the Jina awakens "
        "the soul's innate purity.",
        "भक्तामर-प्रणत-मौलि-मणि-प्रभाणाम्...",
        "Verse 1",
    ),
    "Tattvartha Shlokavartika": (
        "Reality is many-sided (anekanta); every substance possesses infinite "
        "attributes and modes. Through the doctrine of conditional predication "
        "(syadvada) and the standpoints (naya), one apprehends truth without "
        "one-sided dogmatism. Valid knowledge (pramana) grasps the whole; a naya "
        "grasps a part.",
        "वस्तु अनेकान्तात्मक है; स्याद्वाद से ही उसका यथार्थ ज्ञान होता है।",
        "Pramana-naya Adhikar",
    ),
    "Baras-anuvekkha": (
        "Contemplate the twelve reflections (anuprekshas): the impermanence of all "
        "things (anitya), the helplessness of the soul (asharana), the cycle of "
        "rebirth (samsara), aloneness (ekatva), separateness (anyatva), the impurity "
        "of the body (ashuchi), and so on. Such contemplation loosens attachment and "
        "steadies the mind toward dispassion.",
        "बारह भावनाओं का चिंतन वैराग्य को दृढ़ करता है।",
        "Anupreksha",
    ),
    "Jambudveepa Pragnapti": (
        "At the center of the middle world lies Jambudvipa, a continent ringed by "
        "oceans, with the golden Mount Meru at its heart. The cosmos (loka) is "
        "uncreated and eternal, structured into the lower, middle and upper realms, "
        "each described in precise measure across vast cycles of time (kalpa).",
        "मध्यलोक के केंद्र में जम्बूद्वीप है, जिसके मध्य में सुमेरु पर्वत स्थित है।",
        "Kshetra-vinyasa",
    ),
    "Samadhi Tantra": (
        "You are not this body, nor these passing moods of anger, fear, or sorrow; you "
        "are the conscious knower who witnesses them all. When the mind is agitated, the "
        "wise one steps back and observes the disturbance as a cloud passing across an "
        "unchanging sky. Resting in this witnessing self (the knower), equanimity "
        "(samata) arises, and the grip of grief and craving loosens of its own accord.",
        "तू यह शरीर नहीं, न ये क्षणिक भाव; तू तो इन सबका साक्षी चैतन्य है।",
        "Self-Realization",
    ),
    "Ishtopadesh": (
        "Sorrow is born not from things themselves but from our clinging (raga) to what "
        "is other than the self. The one who looks outward for peace is like a person "
        "searching for a lamp in darkness while holding one in hand. Turn inward: the "
        "self is its own refuge. What is gained is lost, what is met is parted — knowing "
        "this, the wise neither grasp in gain nor break in loss.",
        "दुख वस्तुओं से नहीं, पर-पदार्थों के राग से उत्पन्न होता है।",
        "Inward Turning",
    ),
    "Atmanushasan": (
        "Anger (krodha) scorches first the one who holds it, before it ever touches "
        "another — as fire burns the vessel that carries it. Pride (maana) blinds, deceit "
        "(maya) entangles, and greed (lobha) is a thirst that drinking only deepens. "
        "These four passions (kasaya) are not enemies to be hated but habits to be "
        "gently unlearned through self-awareness and forgiveness (kshama). Govern the "
        "self with patience, not with violence toward the self.",
        "क्रोध पहले उसी को जलाता है जो उसे धारण करता है।",
        "On the Passions",
    ),
}

ACHARYA_TITLES: dict[str, tuple[str, str, str]] = {
    # slug: (display_name, default_anuyoga, era)
    "vidyasagar": ("Acharya Vidyasagar Ji Maharaj", "dravyanuyog", "contemporary"),
    "vidyananda": ("Acharya Vidyananda Ji Maharaj", "dravyanuyog", "contemporary"),
    "tarun_sagar": ("Muni Tarun Sagar Ji Maharaj", "charananuyog", "contemporary"),
    "gyanmati": ("Aryika Gyanmati Mataji", "karnanuyoga", "contemporary"),
    "pushpadant_sagar": ("Acharya Pushpadant Sagar Ji Maharaj", "dravyanuyog", "contemporary"),
    "deshbhushan": ("Acharya Deshbhushan Ji Maharaj", "charananuyog", "contemporary"),
    "gupti_sagar": ("Upadhyay Gupti Sagar Ji Maharaj", "charananuyog", "contemporary"),
    "vardhaman_sagar": ("Acharya Vardhaman Sagar Ji Maharaj", "prathamanuyoga", "contemporary"),
    "praman_sagar": ("Muni Praman Sagar Ji Maharaj", "dravyanuyog", "contemporary"),
    "nirbhay_sagar": ("Acharya Nirbhay Sagar Ji Maharaj", "prathamanuyoga", "contemporary"),
    "pulak_sagar": ("Pulak Sagar Ji Maharaj", "charananuyog", "contemporary"),
}

# Known titles per author (subset from 04-BOOK-CORPUS.md). Remaining slots are
# auto-filled to reach 50 each.
KNOWN: dict[str, list[str]] = {
    "vidyasagar": [
        "Muktadhara", "Mookmaati", "Kaavya Dhaaraa", "Chitraa Vichitra",
        "Prashnottar Manjari", "Tattva Sutra Vivechan", "Jeevan Vigyan",
        "Nischay aur Vyavahar", "Samta Darshan", "Atma Parichay",
    ],
    "vidyananda": [
        "Tattvartha Shlokavartika", "Ashtasahastri", "Pramana Pariksha",
        "Satyashasana Pariksha", "Jain Nyaya Darshan", "Anekant aur Syadvad",
        "Naya Sidhant", "Praman Mimansa", "Syadvad aur Saptbhangi",
    ],
    "tarun_sagar": [f"Kadve Pravachan - Part {i}" for i in range(1, 16)] + [
        "Jiyo to Aise Jiyo", "Jivan ke Moti", "Krodh se Mukti",
    ],
    "gyanmati": [
        "Jambudveepa Rachna aur Vikalpna", "Teen Lok ka Swaroop",
        "Trilok Prajnapti", "Jain Bhugol", "Jain Khagolshastra",
        "Meru Parvat ka Swaroop", "Anupreksha (12 contemplations)",
    ],
    "pushpadant_sagar": [f"Karma ka Rahasya - Vol {i}" for i in range(1, 5)] + [
        "Ashtakarma Vivechan", "Mohaniya Karma", "Karma Nirjara ke Upay",
        "Karma Sidhant Praveshika",
    ],
}


def build() -> list[dict]:
    books: list[dict] = []

    for i, (title, hi, author, anuyoga, lang, century) in enumerate(CANONICAL, 1):
        entry = {
            "id": f"canonical-{i:03d}",
            "title": title,
            "title_hindi": hi,
            "author": author,
            "author_slug": "canonical",
            "anuyoga": anuyoga,
            "language": lang,
            "century": century,
            "source_type": "scripture",
            "source_url": "https://jainebooks.org/",
            "file_path": "",
            "total_chunks": 0,
            "description": f"A foundational Digambar Jain text in the {anuyoga} tradition.",
        }
        if title in SEED:
            passage, translated, chapter = SEED[title]
            entry["sample_passage"] = passage
            entry["sample_passage_translated"] = translated
            entry["sample_chapter"] = chapter
        books.append(entry)

    for slug, (name, anuyoga, era) in ACHARYA_TITLES.items():
        known = KNOWN.get(slug, [])
        for n in range(1, 51):
            title = known[n - 1] if n <= len(known) else f"{name.split()[1]} Collected Works Vol. {n}"
            books.append(
                {
                    "id": f"{slug}-{n:03d}",
                    "title": title,
                    "title_hindi": "",
                    "author": name,
                    "author_slug": slug,
                    "anuyoga": anuyoga,
                    "language": "hindi",
                    "century": "21st",
                    "source_type": "discourse",
                    "source_url": "",
                    "file_path": "",
                    "total_chunks": 0,
                    "description": f"Work by {name} ({era}).",
                }
            )
    return books


if __name__ == "__main__":
    books = build()
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump(books, fh, ensure_ascii=False, indent=2)
    seeded = sum(1 for b in books if b.get("sample_passage"))
    print(f"Wrote {len(books)} books to {OUT} ({seeded} with seed passages).")
