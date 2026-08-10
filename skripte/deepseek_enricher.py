#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Napoleon - Enricher (DeepSeek-Version)"""

import argparse
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    print("FEHLER: requests fehlt.  pip install requests")
    sys.exit(1)

API_URL = "https://api.deepseek.com/chat/completions"

MODELLE = {
    "chat":     "deepseek-chat",
    "reasoner": "deepseek-reasoner",
}

PREIS = {
    "chat":     (0.27, 1.10),
    "reasoner": (0.55, 2.19),
}

LEER = {
    "translation": "—",
    "word_type": "unbekannt",
    "gender": None,
    "aspect": None,
    "explanation": "—",
    "common_mistakes": [],
    "tips_pronunciation": "—",
    "etymology": "—",
}

CYR = re.compile(r"[а-яА-ЯёЁ]")


def deutsch_ok(text, schwelle=0.15):
    if not text:
        return True
    bereinigt = re.sub(r"\*[^*]+\*", "", text)
    buchstaben = [c for c in bereinigt if c.isalpha()]
    if not buchstaben:
        return True
    kyr = sum(1 for c in buchstaben if CYR.match(c))
    return (kyr / len(buchstaben)) <= schwelle


def eintrag_ok(eintrag):
    if not eintrag:
        return False
    if eintrag.get("translation") in (None, "—"):
        return False
    for feld in ("explanation", "tips_pronunciation", "etymology"):
        if not deutsch_ok(eintrag.get(feld, "")):
            return False
    return True


def prompt_bauen(word_data, verschaerft=False):
    word = word_data.get("word", "")

    hinweis = ""
    if word_data.get("conjugation"):
        hinweis += "\n(Hinweis: Konjugationstabelle gefunden - moeglicherweise ein Verb.)"
    if word_data.get("declension"):
        hinweis += "\n(Hinweis: Deklinationstabelle gefunden - moeglicherweise Nomen/Adjektiv.)"
    if word_data.get("aspect"):
        hinweis += f"\n(Hinweis aus dem Woerterbuch - Aspekt: {word_data['aspect']}"
        if word_data.get("aspect_partner"):
            hinweis += f", Partnerverb: {word_data['aspect_partner']}"
        hinweis += ")"

    warnung = ""
    if verschaerft:
        warnung = ("\n\nACHTUNG - WIEDERHOLUNG: Deine vorherige Antwort war auf Russisch "
                   "geschrieben. Das ist falsch. Schreibe JEDEN Fliesstext auf DEUTSCH. "
                   "Russische Woerter nur als einzelne Beispiele in *Sternchen*.\n")

    return f"""Du bist ein erfahrener Russisch-Lehrer fuer deutschsprachige Lernende (A1-B1).

Bestimme fuer dieses russische Wort alle folgenden Angaben aus eigenem Wissen.

**Wort:** {word}{hinweis}

Wichtig:
- ALLE Fliesstext-Felder MUESSEN vollstaendig auf DEUTSCH sein. Russische Woerter nur als einzelne Beispiele in *Sternchen*, nie als ganze Saetze.
- "word_type" muss einer dieser Werte sein: verb, noun, adjective, adverb, preposition, pronoun, conjunction, particle, numeral
- "gender" nur ausfuellen wenn word_type == noun (masculine/feminine/neuter), sonst null
- "aspect" nur ausfuellen wenn word_type == verb (perfektiv/imperfektiv), sonst null
- Wenn du bei Aspekt oder Genus unsicher bist, schreibe "unsicher" statt zu raten.
- Zeige in Beispielen ausschliesslich KORREKTE russische Saetze.{warnung}

Antworte als JSON-Objekt mit exakt diesen Feldern:
{{
  "translation": "Hauptuebersetzung ins Deutsche (kurz, 1-4 Woerter)",
  "word_type": "verb|noun|adjective|adverb|preposition|pronoun|conjunction|particle|numeral",
  "gender": "masculine|feminine|neuter oder null",
  "aspect": "perfektiv|imperfektiv oder null",
  "explanation": "Kurze Erklaerung auf DEUTSCH (2-3 Saetze) fuer A1-A2",
  "common_mistakes": ["Haeufiger Fehler 1 auf Deutsch", "Haeufiger Fehler 2 auf Deutsch"],
  "tips_pronunciation": "Tipps zu Aussprache und Betonung auf Deutsch (1-2 Saetze)",
  "etymology": "Kurze Herkunft oder verwandte Woerter auf Deutsch (1 Satz)"
}}"""


def api_call(api_key, model_id, prompt, max_retries=5):
    wartezeit = 4
    for versuch in range(1, max_retries + 1):
        try:
            r = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_id,
                    "max_tokens": 700,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=90,
            )
        except requests.exceptions.RequestException as e:
            print(f"    [!] Netzwerkfehler ({versuch}/{max_retries}): {e}")
            time.sleep(wartezeit)
            wartezeit = min(wartezeit * 2, 60)
            continue

        if r.status_code == 200:
            d = r.json()
            try:
                text = d["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                print(f"    [!] Unerwartetes Antwortformat: {str(d)[:200]}")
                return None, None
            return text, d.get("usage", {})

        if r.status_code in (401, 403):
            print("    [!] API-Key ungueltig oder keine Berechtigung - Abbruch.")
            sys.exit(1)

        if r.status_code == 402:
            print("    [!] Guthaben aufgebraucht (HTTP 402) - Abbruch.")
            sys.exit(1)

        if r.status_code in (429, 500, 502, 503):
            print(f"    [!] HTTP {r.status_code}, warte {wartezeit}s ({versuch}/{max_retries})")
            time.sleep(wartezeit)
            wartezeit = min(wartezeit * 2, 60)
            continue

        print(f"    [!] HTTP {r.status_code}: {r.text[:200]}")
        return None, None

    return None, None


def saeubern(t):
    ersatz = {
        "\u201e": "'", "\u201c": "'", "\u201d": "'",
        "\u2018": "'", "\u2019": "'",
        "\u00ab": "'", "\u00bb": "'",
    }
    for alt, neu in ersatz.items():
        t = t.replace(alt, neu)
    return t


def json_aus_text(text):
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    t2 = saeubern(t)
    try:
        return json.loads(t2)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", t2, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


def speichern(pfad, daten):
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)
    os.replace(tmp, pfad)


def verarbeite_wort(api_key, model_id, word_data):
    text, usage = api_call(api_key, model_id, prompt_bauen(word_data))
    tok_in = usage.get("prompt_tokens", 0) if usage else 0
    tok_out = usage.get("completion_tokens", 0) if usage else 0

    if text is None:
        return dict(LEER), tok_in, tok_out, "netzwerkfehler"

    enriched = json_aus_text(text)
    if enriched is None:
        return dict(LEER), tok_in, tok_out, "json_fehler"

    if not eintrag_ok(enriched):
        print("    [~] Sprache/Feld unvollstaendig, versuche verschaerft nach...")
        text2, usage2 = api_call(api_key, model_id, prompt_bauen(word_data, verschaerft=True))
        if usage2:
            tok_in += usage2.get("prompt_tokens", 0)
            tok_out += usage2.get("completion_tokens", 0)
        if text2 is not None:
            enriched2 = json_aus_text(text2)
            if enriched2 is not None and eintrag_ok(enriched2):
                return enriched2, tok_in, tok_out, "ok_nach_retry"
            elif enriched2 is not None:
                return enriched2, tok_in, tok_out, "sprachproblem_bleibt"
        return enriched, tok_in, tok_out, "sprachproblem_bleibt"

    return enriched, tok_in, tok_out, "ok"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="raw_data.json")
    p.add_argument("--output", default="enriched_data.json")
    p.add_argument("--model", default="chat", choices=list(MODELLE))
    p.add_argument("--every", type=int, default=10)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--pause", type=float, default=0.5)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[-] Kein API-Key gefunden.")
        print("    export DEEPSEEK_API_KEY='sk-...'")
        sys.exit(1)

    if not os.path.isfile(args.input):
        print(f"[-] {args.input} fehlt. Erst den Scraper laufen lassen.")
        sys.exit(1)

    with open(args.input, encoding="utf-8") as f:
        raw = json.load(f)

    fertig = {}
    if os.path.isfile(args.output) and not args.force:
        try:
            with open(args.output, encoding="utf-8") as f:
                fertig = json.load(f)
            print(f"[+] Fortsetzung: {len(fertig)} Eintraege bereits vorhanden")
        except json.JSONDecodeError:
            print("[!] Vorhandene Ausgabedatei unlesbar - starte neu")
            fertig = {}

    if args.force:
        offen = list(raw.items())
    else:
        offen = [(k, v) for k, v in raw.items()
                 if k not in fertig or not eintrag_ok(fertig.get(k))]
    if args.limit:
        offen = offen[:args.limit]

    model_id = MODELLE[args.model]
    ein_preis, aus_preis = PREIS[args.model]

    print("[+] Anbieter   : DeepSeek")
    print(f"[+] Modell     : {args.model} ({model_id})")
    print(f"[+] Gesamt     : {len(raw)}")
    print(f"[+] Zu tun     : {len(offen)}  (neu oder Sprachproblem)")
    print(f"[+] Checkpoint : alle {args.every} Eintraege -> {args.output}")
    print("=" * 60)

    if not offen:
        print("[✓] Nichts zu tun - alles vollstaendig und deutsch.")
        return

    tok_in = tok_out = 0
    fehler = 0
    sprachfehler_final = 0
    retries_erfolgreich = 0
    start = time.time()

    for i, (word_id, word_data) in enumerate(offen, 1):
        word = word_data.get("word", word_id)
        rest = len(offen) - i
        eta = (time.time() - start) / i * rest if i > 1 else 0
        print(f"[{i}/{len(offen)}] {word}  (Rest ~{eta/60:.0f} Min)")

        enriched, ti, to, status = verarbeite_wort(api_key, model_id, word_data)
        tok_in += ti
        tok_out += to

        if status in ("netzwerkfehler", "json_fehler"):
            fehler += 1
        elif status == "ok_nach_retry":
            retries_erfolgreich += 1
        elif status == "sprachproblem_bleibt":
            sprachfehler_final += 1
            print("    [!] Sprachproblem bleibt auch nach Nachversuch bestehen")

        # Scraper-Felder haben Vorrang - das LLM darf Betonung,
        # Konjugation und Deklination nicht ueberschreiben.
        for geschuetzt in ('stress','conjugation','declension','aspect_partner','phonetic'):
            enriched.pop(geschuetzt, None)
        fertig[word_id] = {**word_data, **enriched}

        if i % args.every == 0:
            speichern(args.output, fertig)
            kosten = tok_in / 1e6 * ein_preis + tok_out / 1e6 * aus_preis
            print(f"    [*] gespeichert ({len(fertig)} gesamt, ~{kosten:.2f} USD bisher)")

        if args.pause:
            time.sleep(args.pause)

    speichern(args.output, fertig)

    kosten = tok_in / 1e6 * ein_preis + tok_out / 1e6 * aus_preis
    dauer = (time.time() - start) / 60
    print("=" * 60)
    print(f"[✓] Fertig: {len(fertig)} Eintraege in {args.output}")
    print(f"    Fehler (Netzwerk/JSON) : {fehler}")
    print(f"    Sprachproblem behoben  : {retries_erfolgreich}")
    print(f"    Sprachproblem bleibt   : {sprachfehler_final}")
    print(f"    Token ein/aus          : {tok_in} / {tok_out}")
    print(f"    Kosten (ca.)           : {kosten:.2f} USD")
    print(f"    Dauer                  : {dauer:.0f} Min")
    print()
    print("[→] Naechster Schritt: enriched_neu.json extrahieren + pruefskript.py")


if __name__ == "__main__":
    main()
