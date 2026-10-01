#!/usr/bin/env python3
# MOVED to aikos-home/aikos services/transcriber (tag transcriber-v1.0.0). This copy is frozen: the Mac service
# runs it until it switches to that tag, then it is removed here. Changes only there (PR + RoomKey review).
"""
talk_identity.py — who is speaking? (WIP) Finds the self-introduction in an intercom transcript.

    "Hi, hier ist Jonas, ich komme gleich runter"      → speaker "Jonas",            message "Ich komme gleich runter"
    "Guten Tag, Paketdienst von DHL, ein Paket für Sie" → speaker "Paketdienst · DHL", message "Ein Paket für Sie"
    "Hallo, hier ist die Polizei, bitte öffnen Sie"     → speaker "Polizei",           message "Bitte öffnen Sie"

1. Rules (instant, deterministic): self-introductions ("hier ist …", "ich bin …", "mein Name ist …", "… hier",
   "ich komme von …", dialect and a few foreign forms) and roles/companies announced up front (parcel services,
   police, neighbours, …). The clearest introduction wins; a name and a role said separately are combined.
2. Only if the rules find nothing: a local LLM through Ollama on this computer (optional). Its answer is only
   accepted when the words are really in the transcript and are not somebody addressed, mentioned or talked about.

The side matters: at the DOOR anyone can be speaking (visitor, courier, police …). From a ROOM the speaker is a
resident: only a name counts there ("Lieferando ist da, kannst du runtergehen?" names nobody).
What people say about themselves is NOT verified: anyone can say "Polizei". Displays show it as said.

    python3 tools/talk_identity.py "Hallo, hier ist Anna"           # try one sentence (door side)
    python3 tools/talk_identity.py --room --llm "Wagner, hallo?"     # room side, with the local LLM
    python3 tools/talk_identity.py --selftest                        # rule tests (no LLM)
Standard library only.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import urllib.request
from dataclasses import asdict, dataclass

# ── roles: id → (label, keyword regexes). Case-insensitive unless the pattern starts with (?-i) ──
ROLES: dict[str, tuple[str, list[str]]] = {
    "parcel":    ("Paketdienst", [r"paket\w*", r"\w*zusteller\w*", r"kurier\w*", r"sendung\w*", r"parcel", r"delivery", r"courier"]),
    "mail":      ("Post", [r"(?-i:Post)", r"deutsche post", r"postbot\w*", r"briefträger\w*", r"postman", r"mailman"]),
    "food":      ("Lieferdienst", [r"lieferando", r"wolt", r"uber ?eats", r"pizza\w*", r"essenslieferung", r"lieferservice",
                                   r"lieferdienst", r"(?:ihr|dein|euer) essen", r"food delivery"]),
    "police":    ("Polizei", [r"polizei\w*", r"police", r"kommissar\w*"]),
    "fire":      ("Feuerwehr", [r"feuerwehr\w*", r"fire (?:department|brigade)"]),
    "ambulance": ("Rettungsdienst", [r"rettungs\w*", r"notarzt\w*", r"sanitäter\w*", r"krankenwagen", r"paramedic\w*", r"ambulance"]),
    "neighbour": ("Nachbar", [r"nachbar(?:in)?", r"von nebenan", r"neighbou?r"]),
    "trades":    ("Handwerker", [r"handwerker\w*", r"monteur\w*", r"installateur\w*", r"elektriker\w*", r"klempner\w*",
                                 r"techniker\w*", r"schlüsseldienst", r"dachdecker\w*", r"maler\w*", r"plumber", r"electrician",
                                 r"technician"]),
    "chimney":   ("Schornsteinfeger", [r"schornsteinfeger\w*", r"kaminkehrer\w*", r"bezirksschornsteinfeger\w*"]),
    "utility":   ("Stadtwerke", [r"stadtwerke\w*", r"wasserwerk\w*", r"zähler\w*", r"ablesung", r"netzbetreiber\w*",
                                 r"energieversorger\w*", r"\w*anbieter"]),
    "property":  ("Hausverwaltung", [r"hausverwaltung\w*", r"vermieter\w*", r"hausmeister\w*", r"landlord", r"caretaker"]),
    "care":      ("Pflegedienst", [r"pflegedienst\w*", r"pflegerin", r"pfleger", r"hebamme", r"physiotherap\w*", r"tierarzt\w*",
                                   r"ärztin", r"arzt"]),
    "taxi":      ("Taxi", [r"taxi\w*"]),
    "officials": ("Behörde", [r"ordnungsamt", r"zoll", r"gerichtsvollzieher\w*", r"(?-i:Amt)", r"behörde", r"\w+amt"]),
    "telecom":   ("Techniker", [r"glasfaser\w*", r"kabelanschluss"]),
    # voice v2 (R17.10): more visitor types; the RoomKey shows an icon per id
    "shopping":  ("Einkauf", [r"getränke\w*", r"einkäufe", r"einkaufs\w*", r"lebensmittel\w*"]),
    "pharmacy":  ("Apotheke", [r"apotheke\w*", r"botendienst", r"medikament\w*"]),
    "flowers":   ("Blumen", [r"blumen\w*", r"florist\w*", r"blumenlieferung"]),
    "freight":   ("Spedition", [r"spedition\w*", r"möbel\w*", r"umzugs\w*", r"umzug"]),
    "waste":     ("Müllabfuhr", [r"müll\w*", r"sperrmüll", r"stadtreinigung", r"abfall\w*"]),
    "household_help": ("Haushaltshilfe", [r"putzhilfe", r"putzfrau", r"reinigungskraft", r"haushaltshilfe", r"gärtner\w*",
                                          r"babysitter\w*", r"tagesmutter"]),
    "seasonal":  ("Sternsinger", [r"sternsinger\w*"]),
    "religion":  ("Glaubensgemeinschaft", []),       # only via ORGS ("Zeugen Jehovas") and content
    "campaign":  ("Wahlkampf", [r"kandidat\w*", r"wahlhelfer\w*", r"wahlkämpfer\w*"]),
}
# content → visitor type, for the icon only (not a speaker): door side, when nobody introduced themselves
CONTENT_TYPES: list[tuple[str, str]] = [
    ("kids_friend", r"\b(?:ein |eine )?(?:freund|freundin|kumpel) von\b|\baus (?:der|seiner|ihrer) klasse\b|\bzum spielen\b|\bkita\b"),
    ("sales", r"\b(?:spende\w*|sammeln für|umfrage|angebot|zeitungsabo|abonnement|energieberatung|stromvertrag|tarif\w*|"
              r"vertrag\w*|verkaufe\w*|lose)\b"),
    ("religion", r"\b(?:zeugen jehovas|bibel\w*|kirche\w*|gottes|glauben|gemeinde (?:christi|gottes))\b"),
    ("seasonal", r"\b(?:süßes oder saures|halloween|sankt martin|st\.? martin|nikolaus|sternsinger\w*|weihnachts\w*)\b"),
    ("campaign", r"\b(?:partei\w*|wahlkampf|wahlhelfer\w*|kandidat\w*|wahl\b|bundestagswahl|landtagswahl|kommunalwahl)\b"),
]
# somebody needs help — overrides quiet hours (R17.15); content, not an introduction
URGENT = (r"^\W*hilfe\b|\bhilfe\s*!|\b(?:brauche|brauchen) (?:dringend |sofort )?hilfe|\bhelfen sie mir\b|\bbitte helfen\b|"
          r"\bhilf mir\b|\bnotfall\b|\b(?:rufen sie|ruf|ruft) (?:bitte )?(?:einen |den |die )?(?:krankenwagen|notarzt|polizei|feuerwehr)\b|"
          r"\b(?:ist|bin|sind) (?:\w+ )?(?:gestürzt|bewusstlos|verletzt)\b|\bblutet\b|\bes brennt\b|\bfeuer\s*!|"
          r"\beinbrecher\w*|\beinbruch\b|\büberfall\w*|\bhelp\b|\bemergency\b|"
          r"\b(?:habe|hab|haben) (?:schon |bereits )?(?:die |den |einen )?(?:krankenwagen|notarzt|polizei|feuerwehr) "
          r"(?:schon |bereits )?(?:gerufen|angerufen|alarmiert)\b")
FAMILY_TYPE = {"mama", "papa", "mami", "papi", "mutti", "vati", "oma", "opa", "omi", "opi", "tante", "onkel"}
SELF_DECLARED = {"police", "officials", "utility", "trades"}   # "laut Besucher" (§2c): shown with a "?" badge
# companies → (display name, role id). Short acronyms are case-sensitive: "Ups!" is not UPS.
ORGS: list[tuple[str, str, str]] = [
    (r"(?-i:D\.?\s?H\.?\s?L\.?)", "DHL", "parcel"), (r"hermes", "Hermes", "parcel"), (r"(?-i:D\.?\s?P\.?\s?[DT]\.?)", "DPD", "parcel"),
    (r"(?-i:UPS)", "UPS", "parcel"), (r"(?-i:GLS)", "GLS", "parcel"), (r"fed ?ex", "FedEx", "parcel"),
    (r"amazon", "Amazon", "parcel"), (r"deutsche post", "Deutsche Post", "mail"),
    (r"lieferando", "Lieferando", "food"), (r"wolt", "Wolt", "food"), (r"uber ?eats", "Uber Eats", "food"),
    (r"flink", "Flink", "shopping"), (r"rewe", "Rewe", "shopping"), (r"hellofresh|hello fresh", "HelloFresh", "food"),
    (r"gorillas", "Gorillas", "shopping"), (r"picnic", "Picnic", "shopping"), (r"knuspr", "Knuspr", "shopping"),
    (r"fleurop", "Fleurop", "flowers"), (r"zeugen jehovas", "Zeugen Jehovas", "religion"),
    (r"essen auf rädern", "Essen auf Rädern", "food"),
    (r"telekom", "Telekom", "telecom"), (r"vodafone", "Vodafone", "telecom"),
    (r"vattenfall", "Vattenfall", "utility"), (r"(?-i:E\.ON|EnBW)", "E.ON", "utility"),
]

L = r"[^\W\d_]"                                   # a letter of any alphabet ("Zoë", "Nguyễn", "Yılmaz")
W = L                                             # (kept for callers)
WORD = rf"{L}+(?:['’-]{L}+)*"
UP = "A-ZÄÖÜÀ-ÖØ-ÞŁŚŹŻČĆĐŠŽĞŞİŐŰĂȘȚ"
CAP = rf"(?-i:[{UP}]){L}*(?:-(?-i:[{UP}]){L}+)?"   # a capitalised word, even under re.I
ORGNAME = rf"(?-i:[{UP}])[\w&.-]*"                 # "DHL", "Amazon", "Stadtwerke", "E.ON"
ARTICLE = r"(?:der|die|das|dem|den|de|da|ein|eine|einer|ihr|ihre|ihrem|dein|deine|euer|eure|mein|meine|unser|unsere|the|a|an|your)"
GREETING = (r"(?:hallo|hallöchen|huhu|juhu|hier(?=\s*,)|hi|hey|moin(?: moin)?|servus|grüß gott|grüezi|guten (?:tag|morgen|abend)|tag|hello|na|"
            r"good (?:morning|afternoon|evening)|ja|also|okay|ok|merhaba|selam|salam|buongiorno|ciao|bonjour|hola|"
            r"dzień dobry|dobryj den|dobry den|privet|entschuldigung|sorry|excuse me)")
LEAD = r"(?:(?:\b" + GREETING + r")\b[\s,.!?]*)*"     # optional greetings before the introduction
FILLERS = r"(?<!\w)(?:ä+h+m*|ö+h+m*|hm+|mhm|e+h+m+|em)(?!\w)[,.]?\s*"

# introduction phrases → strength (the clearest introduction wins)
PHRASES = [
    (r"meine?\s+name\s+(?:ist|is)|ich\s+hei(?:ß|ss)e|hier\s+spricht|my\s+name\s+is|je\s+m['’]appelle|me\s+llamo|"
     r"mi\s+chiamo|nazywam\s+się|benim\s+adım", 3),
    (r"(?<!das\s)hier\s+(?:ist|sind|is)|this\s+is|it['’]s|c['’]est", 2),     # "das hier ist Anna" presents someone else
    (r"(?:ich|i|isch|icke|ick)\s+bin(?:['’]?s|\s+es|\s+et)?|wir\s+sind(?:['’]?s|\s+es)?|(?:ich|wir)\s+(?:komme|kommen)(?=\s+(?:von|vom|aus)\b)|"
     r"i\s+am|i['’]m|we\s+are|sono|je\s+suis|soy|jestem", 1),
]
# capitalised words that are never a name (sentence starts, pronouns, fillers)
STOP = {w.lower() for w in """Ich Sie Ihr Ihre Wir Es Er Hier Da Dort Jetzt Gleich Nicht Kein Keine Mal Nur Auch Schon Noch
    Zuhause Unten Oben Draußen Drinnen Ja Nein Okay Hallo Also Ah Äh Ähm Bitte Danke Moment Sorry Entschuldigung Leider Gerade
    Kurz Wieder Wer Was Wo Wie Warum Heute Morgen Gestern I You We They He She The This That Just Coming Here
    Und Aber Oder Dann Doch So Na Nun Das Die Der Den Dem Ein Eine Neue Neu Alles Nichts Etwas Viel Guten Gute Schön
    Mein Meine Dein Deine Unser Unsere Euer Eure Man Jemand Niemand Keiner Tschüss Servus Moin Grüß Wohnt Ist Sind
    Hast Habt Haben Kannst Könnt Können Kann Machst Macht Mach Komm Kommt Kommst Gib Geh Geht Soll Sollen Will Wollen
    Bin Bist War Waren Wird Werden Hat Hätte Würde Würden Gibt Liegt Steht Wartet Klingelt Schau Guck Sag Sagt
    Raus Rein Weg Los Hoch Runter Rauf Achtung Vorsicht Hilfe""".split()}
TITLES = {"frau", "herr", "herrn", "dr", "doktor", "prof", "schwester", "pfarrer", "pastor"}
# capitalised nouns that follow "ich bin" / "hier ist" without being a name ("ich bin Vegetarier", "hier ist Wasser")
NOT_NAMES = {w.lower() for w in """Montag Dienstag Mittwoch Donnerstag Freitag Samstag Sonntag Wochenende Feierabend
    Vegetarier Vegetarierin Veganer Veganerin Homeoffice Urlaub Arbeit Schule Uni Hause Keller Garten Küche Bad Dusche
    Toilette Klo Wasser Strom Licht Feuer Rauch Gas Chaos Ruhe Stress Mittag Mittagspause Abend Nacht Besuch Klingel Tür
    Haustür Treppe Treppenhaus Aufzug Wohnung Haus Auto Straße Bus Bahn Zug Weg Termin Meeting Telefon Handy Computer
    Essen Frühstück Kaffee Tee Geburtstag Party Feier Kind Baby Hund Katze Brief Rechnung Problem Notfall Fehler Unfall
    Einbruch Schluss Ende Anfang Glück Pech Spaß Ernst Sorge Angst Hunger Durst Fieber Krank Müde Fertig Allein Alleine
    Unterwegs Leute Menschen Männer Frauen Kinder Besucher Gast Gäste Bescheid Schuld Ordnung Platz Raum Zimmer Balkon
    Dach Hof Eingang Ausgang Stau Verspätung Pause Dienst Schicht Nachtschicht Spätschicht Frühschicht Training Sport
    Wetter Regen Schnee Sonne Winter Sommer Herbst Frühling Weihnachten Ostern Silvester Schnitt
    Schatz Schatzi Liebling Süße Süßer Mausi Hase Häschen Spatz Baby Darling Honey Meinung Ansicht Auffassung
    Überzeugung Hoffnung Ansicht Mieter Mieterin Vermieterin Eigentümer Eigentümerin Besitzer Kunde Kundin
    Nächste Nächster Erste Erster Letzte Letzter Einzige Einziger Richtige Falsche Pass Ausweis Schlüssel
    Deutscher Deutsche Türke Türkin Italiener Italienerin Spanier Spanierin Franzose Französin Pole Polin Russe Russin
    Ukrainer Ukrainerin Amerikaner Amerikanerin Kanadier Kanadierin Engländer Engländerin Brite Britin Österreicher
    Österreicherin Schweizer Schweizerin Grieche Griechin Rumäne Rumänin Syrer Syrerin Iraker Irakerin Afghane Afghanin
    Vietnamese Vietnamesin Chinese Chinesin Japaner Japanerin Inder Inderin Araber Araberin Kurde Kurdin
    Rentner Rentnerin Single""".split()}
# "ich bin (dein) Bruder / ein Freund von … / Student": not a name, but a fine self-description, shown as said
RELATION = {w.lower() for w in """Bruder Schwester Enkel Enkelin Sohn Tochter Cousin Cousine Neffe Nichte Schwager Schwägerin
    Schwiegersohn Schwiegertochter Patenkind Freund Freundin Kumpel Kollege Kollegin Mitbewohner Mitbewohnerin Student
    Studentin Schüler Schülerin Azubi Praktikant Praktikantin Vater Mutter Lieblingsnachbar Lieblingsnachbarin""".split()}
FAMILY_REL = {"bruder", "schwester", "enkel", "enkelin", "sohn", "tochter", "cousin", "cousine", "neffe", "nichte", "schwager",
              "schwägerin", "schwiegersohn", "schwiegertochter", "patenkind", "vater", "mutter"}
FAMILY = {"mama", "papa", "mami", "papi", "mutti", "vati", "oma", "opa", "omi", "opi", "tante", "onkel"}

# Whisper "hears" these in silence or noise (training-data subtitles). They are removed, never shown.
HALLUCINATIONS = [r"untertitel", r"amara\.org", r"(?:dank|danke)\w* (?:fürs|für's|für das) zu(?:schauen|sehen|hören)",
                  r"copyright", r"swr \d{4}", r"wdr \d{4}", r"thanks for watching", r"subtitles? by", r"in die kommentare",
                  r"abonnier", r"bis zum nächsten (?:mal|video)", r"(?:like|daumen) (?:da|hoch)", r"^tschüss\.?$",
                  r"^(?:musik|applaus|lachen|stille|gelächter|klingeln|piepen|rauschen|music|applause|silence)[.!]?$"]
# Vocabulary hint for Whisper (initial prompt): the words people say at a German front door.
# A word list, not sentences: then a real "Hier ist die Polizei" never looks like an echo of the hint.
WHISPER_PROMPT = ("Haustür-Sprechanlage. Paketdienst, DHL, Hermes, DPD, UPS, GLS, FedEx, Amazon, Deutsche Post, "
                  "Lieferando, Wolt, Uber Eats, Flink, Rewe, Polizei, Feuerwehr, Rettungsdienst, Schornsteinfeger, "
                  "Stadtwerke, Telekom, Vodafone, Hausmeister, Hausverwaltung, Pflegedienst, Nachbarin.")
PROMPT_WORDS = {w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", WHISPER_PROMPT)} - {"deutsche", "post"}


def prompt_echo(text: str, prompt: str = WHISPER_PROMPT) -> bool:
    """Whisper sometimes answers unclear audio with (a piece of) its own prompt ("Hier ist die Polizei, die Feuerwehr,
    die Nachbarin."): 4+ words in the same order as in the prompt, or 4+ of the prompt's brand/role words."""
    ws = [w.lower() for w in re.findall(rf"{WORD}", text)]
    ps = [w.lower() for w in re.findall(rf"{WORD}", prompt)]
    if len(set(ws) & PROMPT_WORDS) >= 4 or "sprechanlage" in text.lower():
        return True
    if len(ws) >= 2 and " ".join(ws) in " ".join(ps):  # the whole "transcript" is a piece of the hint ("Jonas, Anna.")
        return True
    grams = {tuple(ps[i:i + 4]) for i in range(len(ps) - 3)}
    return any(tuple(ws[i:i + 4]) in grams for i in range(len(ws) - 3))


@dataclass
class Identity:
    speaker: str = ""   # display text: "Jonas", "Paketdienst · DHL", "Polizei", "" = nobody introduced themselves
    kind: str = ""      # "name" | "role" | ""
    name: str = ""      # personal name as said, or ""
    role: str = ""      # role id from ROLES, or ""
    org: str = ""       # company, or ""
    message: str = ""   # transcript without greeting + self-introduction ("" if nothing else was said)
    method: str = ""    # "rules" | "llm" | ""
    urgent: bool = False  # somebody needs help (R17.15)
    vtype: str = ""     # visitor type id for the RoomKey icon (role, "family", "name", content type, "emergency", "")


def _find(pattern: str, text: str):
    return re.search(r"(?<!\w)(?:" + pattern + r")(?!\w)", text, re.I)


VOCAB = ["paketdienst", "paketbote", "paketzusteller", "zusteller", "kurier", "sendung", "postbote", "briefträger",
         "lieferando", "lieferdienst", "lieferservice", "polizei", "feuerwehr", "rettungsdienst", "notarzt", "sanitäter",
         "krankenwagen", "nachbar", "nachbarin", "handwerker", "monteur", "installateur", "elektriker", "klempner",
         "techniker", "schlüsseldienst", "schornsteinfeger", "kaminkehrer", "stadtwerke", "ablesung", "hausverwaltung",
         "vermieter", "hausmeister", "pflegedienst", "hebamme", "physiotherapie", "ordnungsamt", "gerichtsvollzieher",
         "hermes", "amazon", "telekom", "vodafone", "vattenfall", "hellofresh"]


def canon(word: str) -> str:
    """Whisper's near-misses of doorstep words ("Stadttwerke", "Klemmer") → the word itself. Long words only."""
    if len(word) < 6 or not re.fullmatch(L + r"+", word):
        return word
    if any(re.fullmatch(p, word, re.I) for _, pats in ROLES.values() for p in pats):
        return word                                              # already a known word ("Gerichtsvollzieherin")
    m = difflib.get_close_matches(word.lower(), VOCAB, n=1, cutoff=0.84)
    return m[0].capitalize() if m and m[0] != word.lower() else word


def role_of(word: str) -> str:
    word = canon(word)
    for rid, (_, pats) in ROLES.items():
        if any(re.fullmatch(p, word, re.I) for p in pats):
            return rid
    for pat, _, rid in ORGS:
        if re.fullmatch(pat, word, re.I):
            return rid
    return ""


def org_in(text: str) -> tuple[str, str]:
    for pat, name, rid in ORGS:
        if _find(pat, text):
            return name, rid
    return "", ""


def org_of(phrase: str) -> tuple[str, str]:
    phrase = canon(phrase)
    for pat, name, rid in ORGS:
        if re.fullmatch(pat, phrase, re.I):
            return name, rid
    return "", ""


# what may follow a role word at the start for it to be an announcement ("Polizei!", "Paket für …",
# "Die Handwerker sind da", "Gerichtsvollzieher Braun, …") rather than the subject of a sentence ("Das Paket ist kaputt")
AFTER_ROLE = (rf"(?:\s+(?:von|vom|from)\s+(?:(?:der|dem|den|the)\s+)?(?P<org>{ORGNAME}(?:\s+{ORGNAME})?))?"
              rf"(?:,?\s+(?!{ARTICLE}\s)(?P<name>{CAP}(?:\s+{CAP})?))?"
              r"(?=\s*(?:$|[,.!?;:–-]|für\b|hier\b|ist da\b|sind da\b|mit\b|for\b|here\b|is here\b))")
# a courier saying what they bring, anywhere in the utterance ("ich habe ein Paket für Sie", "isch habe Paket für Nachbar")
BRING = (r"\b(?:ich|isch|wir)\s+(?:habe|hab|hätte|bringe|bring|haben|bringen)\s+(?:(?:ein|eine|einen|zwei|drei|vier|\d+)\s+)?"
         r"(?P<what>pakete?|päckchen|sendung(?:en)?|lieferung|einschreiben)\w*\s+(?:für|abzugeben|bringen)\b"
         r"(?![^,.!?]*\b(?:angenommen|bekommen|abgeholt|verloren)\b)"
         r"|\b(?:ich|isch)\s+(?:pakete?|päckchen)\s+(?:bringen|bringe|abgeben|liefern)\b")


def lead(text: str) -> tuple[str, str, str, str]:
    """(role id, company, matched word, name) announced at the very start: "Amazon, ich stelle …",
    "Hallo, Paket für …", "Polizei, bitte öffnen", ", Ihre Nachbarin", "Paket von Amazon", "Gerichtsvollzieher Braun, …".
    A role word or company later in a sentence is only a topic ("beim Nachbarn abgeben", "die Polizei rufen",
    "mein Paket von Amazon", "Das Paket von Amazon ist beschädigt")."""
    m = re.match(r"\s*[,.!?;:–-]*\s*" + LEAD + rf"(?:{ARTICLE}\s+)?(?P<w1>{WORD})(?:\s+(?P<w2>{WORD})(?:\s+(?P<w3>{WORD}))?)?",
                 text, re.I)
    if not m:
        return "", "", "", ""
    w1, w2, w3 = m.group("w1"), m.group("w2") or "", m.group("w3") or ""
    for cand in (f"{w1} {w2} {w3}", f"{w1} {w2}", w1, w1.split("-")[0]):   # "Essen auf Rädern"   # a company up front is an announcement ("Amazon-Lieferung")
        org, rid = org_of(cand)
        if org:
            return rid, org, cand, ""
    rid = role_of(w1)
    if not rid:
        return "", "", "", ""
    after = re.match(AFTER_ROLE, text[m.start("w1") + len(w1):], re.I)
    if not after:
        return "", "", "", ""
    org = ""
    if after.group("org"):
        org, _ = org_of(after.group("org"))
        org = org or after.group("org")
    name = after.group("name") or ""
    if name and (name.split()[0].lower() in STOP | NOT_NAMES or role_of(name.split()[0]) or org_of(name)[0]):
        org = org or org_of(name)[0]
        name = ""
    return rid, org, w1, name


def brings(text: str) -> tuple[str, str]:
    """A courier describing the delivery anywhere: (role id, company said in the first words)."""
    m = re.search(BRING, text, re.I)
    if not m:
        return "", ""
    what = (m.group("what") or "").lower()
    rid = "mail" if what in ("einschreiben", "brief") else "parcel"
    for w in re.findall(WORD, text)[:14]:
        org, org_rid = org_of(w)
        if org:
            return org_rid, org
    return rid, ""


AS_SAID = {"trades", "care", "property", "officials", "ambulance", "chimney", "utility", "telecom", "mail", "fire", "freight"}   # "Hausmeister", "Gerichtsvollzieher", "Notarzt"


def role_label(rid: str, matched: str = "") -> str:
    if rid == "relation":
        return matched[:1].upper() + matched[1:]
    label = ROLES[rid][0]
    if rid == "neighbour" and matched.lower().endswith("in"):
        return "Nachbarin"
    matched = canon(matched) if matched else matched
    if rid in AS_SAID and matched and " " not in matched and not re.search(r"(?:en|ern)$", matched) or (
            rid in AS_SAID and matched.lower() in ("hausmeister", "handwerker", "techniker", "elektriker", "klempner")):
        return matched[0].upper() + matched[1:]
    return label


# ── cleaning ──────────────────────────────────────────────────────────────────
def strip_captions(text: str) -> str:
    """Remove Whisper's sound captions ("[Musik]", "(Glocken läuten)", "*Klingeln*", "BELLS CHIMING") and its
    subtitle hallucinations ("Untertitel im Auftrag des ZDF"), sentence by sentence — the rest is kept."""
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*|♪[^♪]*♪", " ", text)
    cased = [c for c in text if c.isupper() or c.islower()]
    if cased and not any(c.islower() for c in cased):   # all capitals = a caption ("BELLS CHIMING"); 汉字 has no case
        return ""
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return " ".join(p for p in parts if not any(re.search(h, p, re.I) for h in HALLUCINATIONS)).strip()


def is_noise(text: str) -> bool:
    """True if the transcript has no spoken words: only captions, symbols or Whisper hallucinations."""
    return not re.search(L + r"{2,}", strip_captions(text))


def clean(text: str) -> str:
    """Captions, hallucinations and fillers out ("hier ist, äh, der Jonas" → "hier ist, der Jonas")."""
    text = strip_captions(text)
    text = re.sub(FILLERS, "", text, flags=re.I)
    text = re.sub(r"(?<!\w)d['’](?=[" + UP + "])", "", text)          # Swiss/Alemannic "d'Frau Huber"
    text = re.sub(r"\b(und|oder)\s*,\s*", r"\1 ", text, flags=re.I)  # "Yusuf und, äh, Can" → "Yusuf und Can"
    return re.sub(r"\s+([,.!?])", r"\1", " ".join(text.split()))


# a speaker correcting themselves: "DPD, äh, nee, GLS", "Mar... Marion", "Jens hier, Jan! Jan, sorry"
CORRECTION = r"(?:\.\.\.|…|\b(?:nee|nein|quatsch|sorry|ich meine|also|pardon)\b)[\s,.!]*"


def corrected(text: str) -> str:
    """If the speaker corrects a name/company right at the start, keep only the correction."""
    m = re.match(rf"(?P<pre>.{{0,60}}?)(?:{CORRECTION})+(?P<rest>(?!(?:nee|nein|quatsch|sorry|also|pardon)\b)\S.*)",
                 text, re.I | re.S)
    if m and re.search(rf"(?-i:[{UP}])\w*", m.group("pre")) and len(re.findall(WORD, m.group("pre"))) <= 6:
        lead_words = re.findall(WORD, m.group("rest"))[:1]
        if re.match(r"(?:hier ist|hier sind|ich bin|mein name ist|ich heiße)\b", m.group("rest"), re.I):
            return (re.match(r"\s*" + LEAD, m.group("pre"), re.I).group(0) + m.group("rest")).strip()   # "Nein, ich bin's, Jonas"
        if lead_words and (org_of(lead_words[0])[0] or role_of(lead_words[0]) or lead_words[0][0].isupper()):
            greet = re.match(r"\s*" + LEAD, m.group("pre"), re.I).group(0)
            intro = re.search(r"\b(?:hier ist|hier sind|ich bin|mein name ist|ich heiße)\b", m.group("pre"), re.I)
            return (greet + (intro.group(0) + " " if intro else "") + m.group("rest")).strip()
    return text


def _message(text: str, span: tuple[int, int] | None) -> str:
    if span is None:
        rest = text
    else:
        rest = text[: span[0]] + " " + text[span[1]:]
        rest = re.sub(r"^\s*" + LEAD, "", rest, flags=re.I)         # greeting left in front
    rest = re.sub(r"\s+([,.!?])", r"\1", rest)
    rest = re.sub(r"([,.!?])(?:\s*[,])+", r"\1", rest)              # "Oma,, ich" → "Oma, ich"
    rest = re.sub(r",\s*([.!?])", r"\1", rest)                        # "Hilfe,!" → "Hilfe!"
    rest = re.sub(r"\b(und|oder|aber),", r"\1", rest)                  # "Anna, und, wir" → "Anna, und wir"
    rest = re.sub(r"^[\s,.!?;:–-]+|[\s,;:–-]+$", "", " ".join(rest.split())).strip()
    rest = re.sub(r"^" + LEAD + r"$", "", rest, flags=re.I).strip()  # only a greeting left
    if not re.search(L + r"{2,}", rest):
        return ""
    return rest[0].upper() + rest[1:]


def _compose(name: str, rid: str, org: str, matched: str = "") -> str:
    if rid == "relation":
        return role_label(rid, matched) + (f" von {org}" if org else "")
    tail = org or (role_label(rid, matched) if rid else "")
    if name:
        return f"{name} · {tail}" if tail else name
    if rid and org and org != role_label(rid):
        return org if rid in ("telecom", "utility") else f"{role_label(rid, matched)} · {org}"
    return tail


# ── rules ─────────────────────────────────────────────────────────────────────
TOKEN = re.compile(rf"{WORD}|[,.!?;:…–]")


@dataclass
class _Who:
    name: str
    rid: str
    org: str
    matched: str
    end: int


def parse_who(text: str, pos: int, known: dict) -> _Who | None:
    """Read who is named at text[pos:]: [article] [titles] Name(s) [und Name(s)] | Role [Name] [von Org|nebenan]."""
    toks = [(m.group(0), pos + m.start(), pos + m.end()) for m in TOKEN.finditer(text[pos:pos + 160])]
    i, n = 0, len(toks)

    def word(k):
        return k < n and re.fullmatch(WORD, toks[k][0]) is not None

    def cap(k):
        return word(k) and toks[k][0][0].isupper() and toks[k][0].lower() not in STOP

    possessive = word(i) and re.fullmatch(r"mein|meine|dein|deine|ihr|ihre|euer|eure|unser|unsere|your|my", toks[i][0], re.I)
    if word(i) and re.fullmatch(ARTICLE, toks[i][0], re.I):
        i += 1
    for _ in range(2):                                       # "der neue Vermieter", "die zuständige Hebamme"
        if word(i) and re.fullmatch(r"(?-i:[a-zäöüß])+(?:e|en|er|es)", toks[i][0]) and cap(i + 1):
            i += 1
    start_i = i
    titles, names, rid, org, matched, end = [], [], "", "", "", None
    while word(i) and toks[i][0].lower().rstrip(".") in TITLES:
        titles.append(toks[i][0]); end = toks[i][2]; i += 1
        if i < n and toks[i][0] == "." and titles[-1].lower() in ("dr", "prof"):
            titles[-1] += "."; i += 1
    if cap(i) and not titles and (role_of(toks[i][0]) or org_of(toks[i][0])[0]):
        matched = toks[i][0]
        org, org_rid = org_of(matched)
        if i + 1 < n and word(i + 1) and org_of(f"{matched} {toks[i + 1][0]}")[0]:       # "Deutsche Post", "Uber Eats"
            org, org_rid = org_of(f"{matched} {toks[i + 1][0]}"); i += 1
        rid = role_of(matched) or org_rid
        end = toks[i][2]; i += 1
        if not org and i + 1 < n and toks[i][0] == "," and word(i + 1) and org_of(toks[i + 1][0])[0]:
            org = org_of(toks[i + 1][0])[0]; end = toks[i + 1][2]; i += 2            # "Paketbote, Hermes"
        k = i + 1 if i < n and toks[i][0] == "," else i                                    # "Nachbar, Klaus"
        while cap(k) and len(names) < 2 and not role_of(toks[k][0]) and toks[k][0].lower() not in NOT_NAMES:
            names.append(toks[k][0]); end = toks[k][2]; k += 1
        if names:
            i = k
    else:
        while cap(i) and len(names) < 3 and not role_of(toks[i][0]) and not org_of(toks[i][0])[0]:
            names.append(toks[i][0]); end = toks[i][2]; i += 1
        if names and word(i) and toks[i][0].lower() == "und" and cap(i + 1):                # "Anna und Jonas"
            more = []
            k = i + 1
            while cap(k) and len(more) < 3 and not role_of(toks[k][0]):
                more.append(toks[k][0]); k += 1
            if more:
                names += ["und"] + more; end = toks[k - 1][2]; i = k
        if names and names[0].lower() in NOT_NAMES and not titles:
            return None
        if names and names[0].lower() in RELATION and not titles:
            rid, matched, names = "relation", names[0], []   # shown as said: "Bruder", "Freund von Tom", "Student"
        if names and len(names) == 1 and not titles and re.search(r"(?:ung|heit|keit|schaft|tion|tät|ismus)$", names[0]):
            return None                                      # "ich bin der Meinung": an abstract noun, not a name
        if names and possessive and names[0].lower() not in FAMILY and names[0].lower() not in RELATION:
            return None                                      # "Hier ist mein Pass" (but "Hier ist dein Papa", "dein Bruder")
        if names and len(names) == 1 and len(names[0]) < 2:
            return None                                      # "ich bin M, …": a stray letter is no name
        if not names and titles:
            return None
    # "… von DHL", "… vom Pflegedienst", "… von nebenan", "… von den Zeugen Jehovas"
    if word(i) and toks[i][0].lower() in ("von", "vom", "aus", "from"):
        k = i + 1
        if word(k) and toks[k][0].lower() in ("der", "dem", "den", "the"):
            k += 1
        if word(k) and toks[k][0].lower() in ("nebenan", "oben", "unten", "gegenüber", "drüben"):
            rid = rid or "neighbour"; end = toks[k][2]
        elif cap(k):
            words = [toks[k][0]]
            while cap(k + len(words)) and len(words) < 3 and not org_of(toks[k][0])[0]:
                words.append(toks[k + len(words)][0])
            phrase = " ".join(words)
            o, orid = org_of(phrase)
            if not o and len(words) > 1:
                o, orid = org_of(words[0])
                words = words[:1] if o else words
            if o:
                org, rid = o, rid or orid
            elif role_of(words[0]):
                rid = rid or role_of(words[0])                   # "von den Stadtwerken"
            elif names or rid or i == start_i:
                org = org or " ".join(words)                     # an unknown company, as said
                rid = rid or role_of(words[-1])
            end = toks[k + len(words) - 1][2]
            matched = matched or words[0]
    if not names and not rid and not org:
        return None
    name = " ".join(titles + names)
    return _Who(known.get(name.lower(), name), rid, org, matched, end)


def by_rules(text: str, known_names=(), side: str = "door") -> Identity:
    text = clean(text)
    fixed = corrected(text)
    if fixed != text:                                  # the speaker corrected themselves: try the correction first
        ident = _rules(fixed, known_names, side)
        if ident.speaker:
            return ident
    return _rules(text, known_names, side)


def _rules(text: str, known_names=(), side: str = "door") -> Identity:
    known = {n.lower(): n for n in known_names}
    found = []                                                   # (strength, -start, _Who, start)
    for pat, strength in PHRASES:
        for m in re.finditer(rf"(?<!\w)(?:{pat})(?!\w)[\s,]*", text, re.I):
            who = parse_who(text, m.end(), known)
            if who and strength == 1 and re.match(rf"\s+(?-i:[a-zäöüß]){L}*en\b", text[who.end:]) and \
                    not re.match(r"\s+(?:und|oder|aber|von|vom|aus|wegen|hier|gleich|jetzt)\b", text[who.end:], re.I):
                who = None                                       # "ich bin Oma besuchen" = I'm off visiting Oma
            if who:
                found.append((strength, -m.start(), who, m.start()))
    # Bavarian/Austrian "der Huber Franz, …" and family "die Omi ist da!" at the very start (door)
    m = re.match(r"\s*(?:hoho|haha|juhu|hey)?[\s,!]*" + LEAD + rf"(?:der|die|de|da)\s+(?P<w>{CAP}(?:\s+{CAP})?)(?=\s*(?:[,.!]|ist da\b|is da\b))",
                 text, re.I)
    if m and side == "door":
        who = parse_who(text, m.start("w"), known)
        if who and who.name and not who.rid and not who.org and \
                (len(who.name.split()) == 2 or who.name.lower() in FAMILY or re.match(r"\s+ist da\b", text[who.end:], re.I)
                 or len(re.findall(WORD, text)) <= 3):
            if re.match(r"\s+i?st da\b", text[who.end:], re.I):
                who.end = m.start("w")                           # keep "Omi ist da!" as the message
            found.append((1, -m.start(), who, m.start()))
    # "von Bülow hier" (name particles)
    for m in re.finditer(rf"(?:^|(?<=[,.!?]\s)|(?<=^\w{{0}}))(?:{GREETING}[\s,]+)?(?P<w>(?:von|van|de|zu)\s+{CAP})\s+hier(?!\w)", text, re.I):
        found.append((2, -m.start(), _Who(m.group("w"), "", "", "", m.end()), m.start("w")))
    # "Anna hier", "DHL hier" — not in a question ("Wohnt hier Herr Özdemir?")
    for m in re.finditer(rf"(?:^|(?<=[,.!?]\s))(?P<w>(?:{ARTICLE}\s+)?{WORD}(?:\s+{WORD}){{0,2}})\s+hier(?=\s*(?:[,.!:;–-]|$))", text, re.I):
        clause_end = re.search(r"[.!?]|$", text[m.end():])
        if text[m.end() + clause_end.start():m.end() + clause_end.end()] == "?":
            continue
        if re.match(r"(?:von|van|zu|de)\s", m.group("w")):
            continue                                             # "von Bülow hier": see name particles below
        who = parse_who(text, m.start("w"), known)
        if who and who.end == m.end("w"):
            who.end = m.end()
            found.append((2, -m.start(), who, m.start()))
    # "Kowalski mein Name", "Weber ist mein Name"
    for m in re.finditer(rf"(?:^|(?<=[,.!?]\s))(?P<w>{WORD}(?:\s+(?!ist\b){WORD})?),?\s+(?:ist\s+)?mein\s+name(?!\w)", text, re.I):
        who = parse_who(text, m.start("w"), known)
        if who and who.end == m.end("w"):
            who.end = m.end()
            found.append((3, -m.start(), who, m.start()))
    # from a room, a resident answers with the surname: "Wagner, hallo?", "Ja, Schmidt?"
    if side == "room" and len(re.findall(WORD, text)) <= 4:
        m = re.fullmatch(rf"\s*(?:ja,?\s*)?(?P<w>{CAP})\s*(?:,\s*(?:hallo|ja|guten tag))?\s*[?!.]*\s*", text, re.I)
        if m and m.group("w").lower() not in STOP | NOT_NAMES and not role_of(m.group("w")):
            found.append((2, 0, _Who(m.group("w"), "", "", "", m.end()), 0))

    if side == "room":                               # a resident: only a name counts, never a role or company
        found = [(s, p, w if w.rid == "relation" and not w.name else _Who(w.name, "", "", "", w.end), st)
                 for s, p, w, st in found if w.name or w.rid == "relation"]          # "Ich bin der Sohn" is fine too
    if found:
        strength, _, best, start = max(found, key=lambda f: (f[0], f[1]))
        name, rid, org, matched = best.name, best.rid, best.org, best.matched
        if not name and rid and side == "door":      # "Ihre Nachbarin hier, die Frau Schmitz"
            ap = re.match(r"\s*,\s*", text[best.end:])
            w = parse_who(text, best.end + ap.end(), known) if ap else None
            if w and w.name and not w.rid and not w.org and w.name.split()[-1].lower() not in NOT_NAMES:
                name = w.name
                best.end = w.end
        if side == "door":                           # a name and a role said separately belong together
            for _, _, w, _ in sorted(found, key=lambda f: -f[1]):
                if w is best:
                    continue
                if name and not (rid or org) and (w.rid or w.org) and not w.name:
                    rid, org, matched = w.rid, w.org, w.matched
                elif not name and w.name and (not w.rid or w.rid == rid):
                    name = w.name
            if name and not (rid or org):
                rid, org, matched, _ = lead(text[best.end:])                # "hier ist Anna, Ihre Nachbarin"
            if name and not (rid or org) and start > 0:
                rid, org, matched, _ = lead(text[:start])                   # "Physiotherapie, ich bin Tim"
        kind = "name" if name else "role"
        return Identity(speaker=_compose(name, rid, org, canon(matched)), kind=kind, name=name, role=rid, org=org,
                        message=_message(text, (start, best.end)), method="rules")
    if side == "room":
        return Identity(message=_message(text, None))
    # no introduction: a company or role word up front ("Amazon, ich stelle es …", "Paket für Schmidt")
    rid, org, matched, name = lead(text)
    if rid and not org and rid in ("parcel", "food", "mail"):
        org = brings(text)[1]
        if not org:
            for w in re.findall(WORD, text)[:8]:
                org = org_of(w)[0] or org
    if rid:
        return Identity(speaker=_compose(name, rid, org, matched), kind="name" if name else "role", name=name, role=rid,
                        org=org, message=_message(text, None), method="rules")
    rid, org = brings(text)                                                 # "isch habe Paket für Nachbar"
    if rid:
        return Identity(speaker=_compose("", rid, org), kind="role", role=rid, org=org,
                        message=_message(text, None), method="rules")
    return Identity(message=_message(text, None))


# ── optional: local LLM (Ollama) when the rules find nothing ──────────────────
LLM_PROMPT = """Du bekommst das Transkript EINER Äußerung an einer Haustür-Sprechanlage (meist Deutsch, oft mit Akzent,
Dialekt oder Fehlern der Spracherkennung). %s
Frage: Sagt die SPRECHENDE Person, wer SIE SELBST ist – ihren Namen, ihre Firma, Behörde oder Funktion?
Regeln:
- Nur Selbstvorstellungen zählen. Angesprochene, gesuchte oder erwähnte Personen zählen NICHT ("Mama, mach auf",
  "Mia, da ist jemand", "Ist Anna da?", "Ich suche Herrn Müller", "Guten Tag, Frau Doktor Weber", "Tom hat gesagt …",
  "Grüße von Tom", "Die Hebamme kommt um zehn").
- Empfänger zählen nicht: bei "Paket für Schmidt" ist der Sprecher der Paketdienst, nicht Schmidt.
- Themen zählen nicht: "Soll ich die Polizei rufen?", "beim Nachbarn abgeben", "das Paket von Amazon ist kaputt".
- Pronomen ("ich", "wir") sind keine Antwort. Im Zweifel: niemand.
- "speaker" wörtlich aus dem Transkript übernehmen (Name, Firma oder Funktion), nichts erfinden, nichts übersetzen.
Beispiele:
"Merhaba, ich Mehmet von oben, haben Sie Salz?" → {"speaker": "Mehmet", "kind": "name", "role": "neighbour"}
"Guten Tag, Stadtreinigung, wir müssen an die Mülltonnen." → {"speaker": "Stadtreinigung", "kind": "role", "role": ""}
"Habt ihr ein Paket für die Nachbarn angenommen?" → {"speaker": "", "kind": "none", "role": ""}
"Guten Tag, eine kurze Umfrage zur Bundestagswahl." → {"speaker": "", "kind": "none", "role": ""}
"Mama, mach auf, ich bin's!" → {"speaker": "", "kind": "none", "role": ""}
"Mia, da ist jemand an der Tür für dich." → {"speaker": "", "kind": "none", "role": ""}
"Guten Tag, Frau Doktor Weber, ich habe einen Termin." → {"speaker": "", "kind": "none", "role": ""}
"Icke bin's, der Kalle, mach ma uff." → {"speaker": "Kalle", "kind": "name", "role": ""}
"Das ist Anna, sie ist neu in der Klasse." → {"speaker": "", "kind": "none", "role": ""}
"I'm here for the apartment viewing." → {"speaker": "", "kind": "none", "role": ""}
Antworte nur mit JSON: {"speaker": "...", "kind": "name"|"role"|"none", "role": "<eine von: %s oder leer>"}"""
SIDE_HINT = {"door": "Sie kommt von der HAUSTÜR (Besuch, Lieferdienst, Behörde …).",
             "room": "Sie kommt aus einem ZIMMER: Es spricht jemand, der hier wohnt. Nur ein Name kann zählen; "
                     "Lieferdienste, Handwerker usw. sind dann nur Thema."}
THIRD_PERSON = (r"hat|hatte|ist|war|sagt|sagte|meinte|erzählte|kommt|kam|wird|will|möchte|lässt|grüßt|wartet|schläft|arbeitet|braucht|"
                r"steht|sitzt|holt|bringt|ruft|meint|weiß|kann|muss|soll|darf|wohnt")


def by_llm(text: str, url: str, model: str, timeout: float = 8.0, side: str = "door") -> Identity | None:
    body = {"model": model, "stream": False, "think": False, "keep_alive": -1, "format": "json",   # stays loaded: no cold start
            "options": {"temperature": 0},
            "messages": [{"role": "system", "content": LLM_PROMPT % (SIDE_HINT.get(side, ""), ", ".join(ROLES))},
                         {"role": "user", "content": text}]}
    req = urllib.request.Request(url.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ans = json.loads(json.loads(r.read())["message"]["content"])
    speaker = str(ans.get("speaker") or "").strip().strip(",.!?")
    kind = ans.get("kind")
    if not speaker or kind not in ("name", "role") or (side == "room" and kind != "name"):
        return None
    # guards: the LLM may only point at words that are really in the transcript, and never at somebody addressed,
    # mentioned or talked about, or at a thing ("Paket", "… zur Bundestagswahl", "Spenden für das Tierheim")
    i = text.lower().find(speaker.lower())
    if i < 0 or re.fullmatch(r"(?:pakete?|päckchen|sendung|lieferung|einschreiben|briefe?|post)", speaker, re.I):
        return None
    before, after = text[:i], text[i + len(speaker):]
    if speaker.split()[0].lower() in STOP or speaker.lower() in NOT_NAMES:
        return None                                                   # a pronoun or a thing is nobody
    if re.fullmatch(r"\s*" + LEAD + rf"(?:{ARTICLE}\s+)?", before, re.I) and re.match(r"\s*,", after) and \
            (re.fullmatch(r"(?:frau|herr|herrn|dr\.?|doktor)\b.*", speaker, re.I) or
             re.match(r"\s*,\s*(?:\w+\s+){0,3}?(?:du|dich|dir|ihr|euch|mach|komm|kannst|hast|bist|schau|guck|da ist|"
                      r"es hat|es klingelt|jemand)\b", after, re.I)):
        return None                                                   # "Guten Tag, Frau Weber, …", "Mia, da ist jemand"
    if re.match(rf"\s+(?:{THIRD_PERSON})\b", after, re.I) and not re.search(r"(?:hier ist|ich bin|hier spricht)\s+(?:\w+\s+)?$",
                                                                            before, re.I):
        return None                                                   # "Tom hat gesagt", "Die Hebamme kommt um zehn"
    clause_end = re.search(r"[,.!?]|$", after)
    clause = before[max(before.rfind(c) for c in ",.!?") + 1:] + speaker + after[:clause_end.end()]
    intro_here = re.search(r"\b(?:ich bin|hier ist|hier sind|wir sind|mein name|ich heiße|ich komme)\b", clause, re.I)
    if clause.rstrip().endswith("?") and not intro_here:
        return None                                                   # "Haben Sie Internet von der Telekom?"
    if re.search(r"\b(?:ob|dass|weil|wenn|falls)\b[^,.!?]*$", before, re.I):
        return None                                                   # "…, ob das Ordnungsamt bei Ihnen war"
    if re.search(r"\b(?:habe|hab|haben|hat|rufe|rufen|ruf|hole|holen|frage|fragen|suche|suchen|kenne|kennen)\s+"
                 r"(?:(?:die|den|der|das|ein|eine|einen)\s+)?(?:\w+\s+)?$", before, re.I):
        return None                                                   # "Ich habe die Polizei schon gerufen" (an object)
    if re.search(r"\bnicht\s+(?:(?:der|die|das|ein|eine|ihr|ihre)\s+)?$", before, re.I):
        return None                                                   # "Ich bin nicht der Postbote"
    if re.search(r"\bbin\s+$", before, re.I) and re.match(r"\s+(?-i:[a-zäöüß])\w*en\b", after):
        return None                                                   # "Ich bin Oma besuchen" = I'm off visiting Oma
    sentence_start = before[max(before.rfind(c) for c in ".!?") + 1:]
    if not intro_here and re.fullmatch(r"\s*" + LEAD + r"(?:\w+\?\s*)?", sentence_start, re.I) and re.match(r"\s*[,?!]", after) and (
            side == "room" or re.search(r"\b(?:du|dich|dir|ihr|euch|mach|komm|kannst|hast|bist|schau|guck|you|me in|open|let me)\b",
                                        after, re.I)):
        return None                                                   # "Lukas? Lukas, mach auf", "Sophie, welchen Knopf…"
    if (speaker.lower() in FAMILY or re.match(r"(?:frau|herr|herrn)\s", speaker, re.I)) and \
            not re.search(r"\b(?:ich bin|hier ist|mein name|ich heiße)\b[^.!?]*$", before, re.I) and \
            (side == "room" or (re.search(r",\s*$", before) and re.match(r"\s*,", after))):
        return None                                                   # "Post ist da, Mama, für dich …", "…, Herr Böck, …"
    if re.search(r"\bdas\s+(?:hier\s+)?ist\s+$", before, re.I) and \
            re.search(r"^[^.!?]*[.!?,]\s*(?:sie|er)\s+(?:ist|hat|will|möchte|kommt|wohnt|darf|kann)\b", after, re.I):
        return None                                                   # "Das ist Anna. Sie ist neu in der Klasse."
    if re.search(r"\bist\s+$", before, re.I) and re.match(r"\s+(?:da|zu hause|daheim|dahoam|zuhause)\b", after, re.I) or \
            re.match(r"\s+da\s+m[ıi]\b", after, re.I):
        return None                                                   # "Ist Ayşe zu Hause?", "Ayşe da mı?"
    if re.search(r",\s*$", before) and re.fullmatch(r"\s*[.!?]*\s*", after[:3]) and \
            not re.search(r"(?:ich bin['’]?s|ich bin es|hier ist|hier spricht|das ist|it['’]s|this is)\s*,\s*$", before, re.I):
        return None                                                   # "Ich bin zu Hause, Tom." addresses Tom
    if re.search(r"\b(?:für|zur|zum|wegen|über|an|auf|beim|bei|nach|mit|um|statt|anstatt|ohne|grüße von|gruß von|for|about|to|at)\s+"
                 r"(?:(?:der|die|das|den|dem|ein|eine|einen|einem)\s+)?$", before, re.I):
        return None
    if kind == "name" and re.search(r"\bvon\s+$", before, re.I) and not re.search(r"(?:ich bin|wir sind|komme)\b", before, re.I):
        return None                                                   # "Grüße von Tom"
    rid = ans.get("role") if ans.get("role") in ROLES else ""
    org, org_rid = org_in(speaker)
    if kind == "role" and (role_of(speaker) or org_rid):              # a known role word: same label as the rules
        rid = role_of(speaker) or org_rid
        if not org and rid in ("parcel", "food", "mail"):
            org = brings(text)[1]
        speaker = _compose("", rid, org, speaker)
    # shown as said: the LLM is only asked when the lists above know nothing about this visitor
    ident = Identity(speaker=speaker, kind=kind, name=speaker if kind == "name" else "", role=rid or org_rid, org=org,
                     method="llm")
    ident.message = _message(text, _clause_span(text, speaker))
    return ident


def _clause_span(text: str, speaker: str):
    """Span of the short clause that holds the introduction ("…, Stadtreinigung, …"); None if it is a long sentence."""
    for m in re.finditer(r"[^,.!?;]+[,.!?;]*", text):
        clause = m.group(0)
        if speaker.lower() in clause.lower():
            return m.span() if len(re.findall(WORD, clause)) <= 6 else None
    return None


def strip_echo(text: str, said: str) -> str:
    """Drop the sentences of a door transcript that mostly repeat what the resident said (the door mic hears the door
    speaker). Short sentences (< 3 words) stay: "Ja", "Danke" are too common to call an echo."""
    ref = {w.lower() for w in re.findall(r"\w+", said)}
    if not ref:
        return text
    keep = []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        ws = [w.lower() for w in re.findall(r"\w+", sent)]
        if len(ws) >= 3 and sum(1 for w in ws if w in ref) / len(ws) >= 0.7:
            continue
        keep.append(sent)
    return " ".join(keep).strip()


def classify(ident: Identity, text: str, side: str = "door") -> Identity:
    """Visitor type for the icon and the emergency flag (voice v2, R17.10 / R17.15)."""
    ident.urgent = re.search(URGENT, text, re.I) is not None
    if side == "room":
        ident.vtype = "name" if ident.name else ""
        return ident
    if ident.role == "relation":
        word = ident.speaker.split()[0].lower() if ident.speaker else ""
        ident.vtype = "family" if word in FAMILY_REL else ("kids_friend" if word in ("freund", "freundin", "kumpel")
                                                            and re.search(CONTENT_TYPES[0][1], text, re.I) else "name")
    elif ident.role:
        ident.vtype = ident.role
    elif ident.name:
        ident.vtype = "family" if ident.name.split()[-1].lower() in FAMILY_TYPE else "name"
    else:
        ident.vtype = next((t for t, pat in CONTENT_TYPES if re.search(pat, text, re.I)), "")
    if ident.urgent and ident.vtype in ("", "name", "family", "neighbour"):
        ident.vtype = "emergency" if not ident.vtype else ident.vtype
    return ident


def identify(text: str, known_names=(), llm_url: str = "", llm_model: str = "qwen3:8b", side: str = "door") -> Identity:
    text = clean(text)
    ident = by_rules(text, known_names, side)
    if ident.speaker or not llm_url or len(re.findall(L + r"{2,}", text)) < 3:
        return classify(ident, text, side)
    try:
        return classify(by_llm(text, llm_url, llm_model, side=side) or ident, text, side)
    except Exception as exc:  # LLM down or slow: the rules' answer stands
        print(f"talk_identity: LLM skipped ({exc})", file=sys.stderr)
        return classify(ident, text, side)


# ── self-test ─────────────────────────────────────────────────────────────────
CASES = [  # text, speaker, message   (door side unless the text starts with "room:")
    ("Hi, hier ist Jonas, ich komme gleich runter.", "Jonas", "Ich komme gleich runter."),
    ("Hallo, ich bin's, Anna. Machst du auf?", "Anna", "Machst du auf?"),
    ("Anna hier, ich hab meinen Schlüssel vergessen.", "Anna", "Ich hab meinen Schlüssel vergessen."),
    ("Guten Tag, Paketdienst von DHL, ich habe ein Paket für Sie.", "Paketdienst · DHL", "Guten Tag, Paketdienst von DHL, ich habe ein Paket für Sie."),
    ("Hallo, hier ist die Polizei, bitte öffnen Sie die Tür.", "Polizei", "Bitte öffnen Sie die Tür."),
    ("Hallo, Paket für Schmidt.", "Paketdienst", "Hallo, Paket für Schmidt."),
    ("Amazon, ich stelle es vor die Tür.", "Paketdienst · Amazon", "Amazon, ich stelle es vor die Tür."),
    ("Hier ist Anna, Ihre Nachbarin. Haben Sie kurz Zeit?", "Anna · Nachbarin", "Ihre Nachbarin. Haben Sie kurz Zeit?"),
    ("Ich bin der Schornsteinfeger, ich muss kurz in den Keller.", "Schornsteinfeger", "Ich muss kurz in den Keller."),
    ("Mein Name ist Thomas Weber von den Stadtwerken, es geht um den Zähler.", "Thomas Weber · Stadtwerke", "Es geht um den Zähler."),
    ("Ich bin gleich da.", "", "Ich bin gleich da."),
    ("Ist Anna da?", "", "Ist Anna da?"),
    ("Ups, falsche Klingel, Entschuldigung.", "", "Ups, falsche Klingel, Entschuldigung."),
    ("Hi, it's Anna, can you open the door?", "Anna", "Can you open the door?"),
    ("Hallo, ich bin Ihr Nachbar von nebenan.", "Nachbar", ""),
    ("Hier ist die Feuerwehr!", "Feuerwehr", ""),
    ("Ich komme gleich runter.", "", "Ich komme gleich runter."),
    ("Guten Tag, Kowalski mein Name, ich komme wegen der Besichtigung.", "Kowalski", "Ich komme wegen der Besichtigung."),
    ("Soll ich es sonst beim Nachbarn abgeben?", "", "Soll ich es sonst beim Nachbarn abgeben?"),
    ("Hier ist Anna, soll ich die Polizei rufen?", "Anna", "Soll ich die Polizei rufen?"),
    ("Polizei, bitte öffnen Sie!", "Polizei", "Polizei, bitte öffnen Sie!"),
    ("Ich hab dir ein Taxi gerufen, es kommt in fünf Minuten.", "", "Ich hab dir ein Taxi gerufen, es kommt in fünf Minuten."),
    ("Hast du mein Paket von Amazon angenommen?", "", "Hast du mein Paket von Amazon angenommen?"),
    ("Hier ist Anna, hast du mein Paket von Amazon?", "Anna", "Hast du mein Paket von Amazon?"),
    ("Hallo, Paket von Hermes für Schmidt.", "Paketdienst · Hermes", "Hallo, Paket von Hermes für Schmidt."),
    ("Guten Tag, hier ist DHL.", "Paketdienst · DHL", ""),
    ("Ich habe Ihre Katze gefunden, die saß bei uns im Garten.", "", "Ich habe Ihre Katze gefunden, die saß bei uns im Garten."),
    ("Hallo, Paket. DHL.", "Paketdienst · DHL", "Hallo, Paket. DHL."),
    ("Gerichtsvollzieher Braun, ich muss Ihnen etwas zustellen.", "Braun · Gerichtsvollzieher", "Gerichtsvollzieher Braun, ich muss Ihnen etwas zustellen."),
    ("Moin, der Hausmeister. Ich muss mal an die Heizung.", "Hausmeister", "Moin, der Hausmeister. Ich muss mal an die Heizung."),
    ("Das Paket von Amazon ist leider beschädigt angekommen.", "", "Das Paket von Amazon ist leider beschädigt angekommen."),
    ("Hallo, isch habe Paket für Nachbar. Sie nehmen?", "Paketdienst", "Hallo, isch habe Paket für Nachbar. Sie nehmen?"),
    ("Die Handwerker sind da, wo sollen wir anfangen?", "Handwerker", "Die Handwerker sind da, wo sollen wir anfangen?"),
    ("Ich habe ein Paket für dich angenommen.", "", "Ich habe ein Paket für dich angenommen."),
    ("Ihr Nachbar, Klaus. Kann ich mir kurz die Leiter ausleihen?", "Klaus · Nachbar", "Ihr Nachbar, Klaus. Kann ich mir kurz die Leiter ausleihen?"),
    ("Hier ist Frau Weber von nebenan, ich habe Ihre Post.", "Frau Weber · Nachbar", "Ich habe Ihre Post."),
    ("Hier sind Anna und Jonas, wir wollten euch abholen.", "Anna und Jonas", "Wir wollten euch abholen."),
    ("Hallo, ich bin Zoë, die neue Babysitterin.", "Zoë", "Die neue Babysitterin."),
    ("Mein Name ist Nguyễn Văn Minh, ich wohne im dritten Stock.", "Nguyễn Văn Minh", "Ich wohne im dritten Stock."),
    ("Hier ist, äh, der Jonas.", "Jonas", ""),
    ("Ich bin Vegetarier, bring bitte nichts mit Fleisch mit.", "", "Ich bin Vegetarier, bring bitte nichts mit Fleisch mit."),
    ("Hier ist Wasser im Keller!", "", "Hier ist Wasser im Keller!"),
    ("Wohnt hier Herr Özdemir?", "", "Wohnt hier Herr Özdemir?"),
    ("Guten Tag, ich komme von der Telekom wegen dem Glasfaseranschluss.", "Telekom", "Wegen dem Glasfaseranschluss."),
    ("Mein Name ist Weber, ich bin Gerichtsvollzieherin.", "Weber · Gerichtsvollzieherin", "Ich bin Gerichtsvollzieherin."),
    ("Servus, i bin da Sepp, is da Jonas dahoam?", "Sepp", "Is da Jonas dahoam?"),
    ("Hilfe, hier ist die Polizei! Untertitel im Auftrag des ZDF, 2021.", "Polizei", "Hilfe!"),
    ("room:Lieferando ist da, kannst du runtergehen?", "", "Lieferando ist da, kannst du runtergehen?"),
    ("room:Wagner, hallo?", "Wagner", ""),
    ("room:Hier ist Papa, stell es vor die Tür.", "Papa", "Stell es vor die Tür."),
    ("Ich bin's, Schatz, machst du auf?", "", "Ich bin's, Schatz, machst du auf?"),
    ("Hallo, das hier ist Anna, und ich bin Paul, wir wollen zu Jonas.", "Paul", "Das hier ist Anna, und wir wollen zu Jonas."),
    ("Guten Tag, ich bin von der Deutschen Glasfaser, wir bauen hier gerade aus.", "Deutschen Glasfaser", "Wir bauen hier gerade aus."),
    ("Hallo, Ihre Nachbarin hier, die Frau Schmitz, Sie haben das Licht am Auto angelassen.", "Frau Schmitz · Nachbarin", "Sie haben das Licht am Auto angelassen."),
    ("Guten Tag, ich bin vom Wasserwerk, bei Ihnen ist ein Rohrbruch.", "Wasserwerk", "Bei Ihnen ist ein Rohrbruch."),
    ("Servus, der Huber Franz, ich hätte ein Paket für euch.", "Huber Franz", "Ich hätte ein Paket für euch."),
    ("Hallo, von Bülow hier, wir hatten telefoniert.", "von Bülow", "Wir hatten telefoniert."),
    ("Huhu, die Omi ist da!", "Omi", "Omi ist da!"),
    ("room:Ich bin Oma besuchen, bin um sechs zurück.", "", "Ich bin Oma besuchen, bin um sechs zurück."),
    ("Guten Tag, Physiotherapie Hausbesuch, ich bin Tim.", "Tim · Physiotherapie", "Physiotherapie Hausbesuch."),
    ("Hier, delivery for Schmidt.", "Paketdienst", "Hier, delivery for Schmidt."),
    ("Hallo, ich bin der neue Vermieter, Herr Schäfer, ich wollte mich kurz vorstellen.", "Herr Schäfer · Vermieter", "Ich wollte mich kurz vorstellen."),
    ("Hallo, DPD, äh, nee, Quatsch, GLS. Paket für Sie.", "Paketdienst · GLS", "Hallo, GLS. Paket für Sie."),
    ("Hier ist Mar... äh, Marion. Entschuldigung, ich bin total erkältet.", "Marion", "Entschuldigung, ich bin total erkältet."),
    ("Amazon-Lieferung, ich lege es vor die Tür, okay?", "Paketdienst · Amazon", "Amazon-Lieferung, ich lege es vor die Tür, okay?"),
    ("Guten Tag, wir sind vom Deutschen Roten Kreuz und sammeln Spenden.", "Deutschen Roten Kreuz", "Und sammeln Spenden."),
    ("Jen dobry, guten Tag, ich bin Paketbote, Hermes, bitte aufmachen.", "Paketdienst · Hermes", "Jen dobry, guten Tag, bitte aufmachen."),
    ("Hier sind Yusuf und, äh, Can. Wir holen die Umzugskartons ab.", "Yusuf und Can", "Wir holen die Umzugskartons ab."),
    ("Hallo, also meine Frau hat gesagt, dass der Herr Dr. Lang hier irgendwo wohnen soll.", "", "Hallo, also meine Frau hat gesagt, dass der Herr Dr. Lang hier irgendwo wohnen soll."),
    ("Die Tanja.", "Tanja", ""),
    ("room:Ich bin der Meinung, dass Sie hier falsch sind.", "", "Ich bin der Meinung, dass Sie hier falsch sind."),
    ("Wohnt hier ein Herr Schulz? Ich hab einen Brief für ihn, der lag bei mir.", "", "Wohnt hier ein Herr Schulz? Ich hab einen Brief für ihn, der lag bei mir."),
    ("Tom ist mein Name.", "Tom", ""),
    ("Hier ist mein Pass.", "", "Hier ist mein Pass."),
    ("Hier ist dein Papa!", "Papa", ""),
    ("Ich bin Kanadier.", "", "Ich bin Kanadier."),
    ("Ich bin der Nächste.", "", "Ich bin der Nächste."),
    ("Raus hier, oder ich rufe die Polizei!", "", "Raus hier, oder ich rufe die Polizei!"),
]


TYPE_CASES = [  # text, side, vtype, urgent
    ("Guten Tag, Paketdienst von DHL, ich habe ein Paket für Sie.", "door", "parcel", False),
    ("Hallo, die Apotheke, ich bringe Ihre Medikamente.", "door", "pharmacy", False),
    ("Blumen für Frau Schmidt!", "door", "flowers", False),
    ("Hallo, Flink, Ihre Einkäufe.", "door", "shopping", False),
    ("Guten Tag, wir sammeln Spenden für das Tierheim.", "door", "sales", False),
    ("Guten Tag, wir sind von den Zeugen Jehovas.", "door", "religion", False),
    ("Süßes oder Saures!", "door", "seasonal", False),
    ("Wir sind die Sternsinger und bringen den Segen.", "door", "seasonal", False),
    ("Guten Tag, ich bin Kandidat für den Stadtrat und wollte mich vorstellen.", "door", "campaign", False),
    ("Hallo, ich bin ein Freund von Jonas, darf er raus zum Spielen?", "door", "kids_friend", False),
    ("Ich bin's, Oma!", "door", "family", False),
    ("Hallo, ich bin Susanne Maier.", "door", "name", False),
    ("Hallo, hier ist die Polizei.", "door", "police", False),
    ("Hilfe! Mein Mann ist gestürzt, bitte rufen Sie einen Krankenwagen!", "door", "emergency", True),
    ("Hier ist Anna von nebenan, bitte helfen Sie mir, es brennt!", "door", "neighbour", True),
    ("Kann ich Ihnen helfen?", "door", "", False),
    ("Soll ich die Polizei rufen?", "door", "", False),
    ("Danke für die Hilfe gestern.", "door", "", False),
    ("Hier ist Papa, ich komme gleich.", "room", "name", False),
]


def selftest() -> bool:
    ok = True
    for text, side, vtype, urgent in TYPE_CASES:
        got = classify(by_rules(text, side=side), clean(text), side)
        good = got.vtype == vtype and got.urgent == urgent
        ok &= good
        print(f"{'✓' if good else '✗'} type {side} {text!r} → {got.vtype!r}{' URGENT' if got.urgent else ''}"
              + ("" if good else f"   expected {vtype!r}{' URGENT' if urgent else ''}"))
    for text, speaker, message in CASES:
        side = "room" if text.startswith("room:") else "door"
        text = text.removeprefix("room:")
        got = by_rules(text, known_names=("Jonas", "Anna"), side=side)
        good = got.speaker == speaker and got.message == message
        ok &= good
        print(f"{'✓' if good else '✗'} {side} {text!r}\n    → speaker {got.speaker!r}, message {got.message!r}"
              + ("" if good else f"\n    expected {speaker!r}, {message!r}"))
    for noise in ["♪♪", "¶¶", "Untertitel im Auftrag des ZDF, 2020", " ", "Vielen Dank fürs Zuschauen!", "BELLS CHIMING", "Musik",
                  "[Musik]", "(Glocken läuten)", "*Klingeln*"]:
        good = is_noise(noise)
        ok &= good
        print(f"{'✓' if good else '✗'} noise {noise!r}")
    for echo in ["Polizei, Feuerwehr, Rettungsdienst, Schornsteinfeger.", "Hermes, DPD, UPS, GLS, FedEx", "Haustür-Sprechanlage.",
                 "Telekom, Vodafone."]:
        good = prompt_echo(echo)
        ok &= good
        print(f"{'✓' if good else '✗'} prompt echo {echo!r}")
    for real in ["Hallo, hier ist die Polizei, bitte öffnen Sie.", "Guten Tag, hier ist der Paketdienst von DHL.", "Polizei!",
                 "Hier ist die Nachbarin von oben."]:
        good = not prompt_echo(real)
        ok &= good
        print(f"{'✓' if good else '✗'} not an echo {real!r}")
    for speech in ["Hallo? [Musik] Ist da jemand?", "DHL, Paket!", "Polizei! Vielen Dank fürs Zuschauen!", "您好,我是沙利沃。"]:
        good = not is_noise(speech)
        ok &= good
        print(f"{'✓' if good else '✗'} speech {speech!r}")
    print("ALL OK" if ok else "FAILURES")
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    llm = "http://127.0.0.1:11434" if "--llm" in args else ""
    side = "room" if "--room" in args else "door"
    for t in [a for a in args if a not in ("--llm", "--room")]:
        print(json.dumps(asdict(identify(t, llm_url=llm, side=side)), ensure_ascii=False))
