#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Napoleon — Datenpruefung (gezielte Stichprobe)

Liest direkt aus enriched_neu.json (Ausgabe des Enrichers), damit
vor dem Merge geprueft werden kann.
"""

import json
import random
import argparse
import os
import sys

SEP = "=" * 62
SUB = "-" * 62

QUOTA = {
    "verb_aspekt": 5,
    "nomen_betonung_plural": 5,
    "unregelmaessig": 3,
    "beliebig": 2,
}


def is_verb(e):
    return (e.get("word_type") or "").lower().startswith("verb")


def is_noun(e):
    return (e.get("word_type") or "").lower() in ("noun", "nomen", "substantiv")


def has_plural_stress_risk(e):
    decl = e.get("declension") or {}
    if not isinstance(decl, dict):
        return False
    if "plural" in decl:
        return True
    for v in decl.values():
        if isinstance(v, dict) and "plural" in v:
            return True
    return False


def looks_irregular(e):
    w = (e.get("word") or "").replace("\u0301", "")
    text = json.dumps(e, ensure_ascii=False).lower()
    markers = ("unregelm", "irregul", "ausnahme", "abweich", "besonder")
    if any(m in text for m in markers):
        return True
    return w.endswith(("мя", "ья", "ий", "ёнок", "анин", "ин"))


def stress_marked(e):
    s = e.get("stress") or ""
    w = e.get("word", "")
    # ё traegt im Russischen IMMER die Betonung - kein Akzent noetig.
    if "ё" in s or "Ё" in s:
        return True
    # Einsilbige Woerter werden nie markiert.
    vokale = sum(1 for c in s if c in "аеиоуыэюяАЕИОУЫЭЮЯ")
    if vokale <= 1:
        return True
    return ("́" in s) or (s != w)


def pick(pool, n, taken):
    out = []
    for e in pool:
        if len(out) >= n:
            break
        if e["id"] in taken:
            continue
        out.append(e)
        taken.add(e["id"])
    return out


def build_sample(entries, rng):
    rng.shuffle(entries)
    verbs = [e for e in entries if is_verb(e)]
    nouns_pl = [e for e in entries if is_noun(e) and has_plural_stress_risk(e)]
    irreg = [e for e in entries if looks_irregular(e)]

    taken = set()
    sample = []
    sample += [("Verbaspekt", e) for e in pick(verbs, QUOTA["verb_aspekt"], taken)]
    sample += [("Betonung Plural", e) for e in pick(nouns_pl, QUOTA["nomen_betonung_plural"], taken)]
    sample += [("Unregelmaessig", e) for e in pick(irreg, QUOTA["unregelmaessig"], taken)]

    fehlend = sum(QUOTA.values()) - len(sample)
    if fehlend > 0:
        sample += [("Beliebig", e) for e in pick(entries, fehlend, taken)]
    return sample


def flat(d, prefix=""):
    lines = []
    if isinstance(d, dict):
        for k, v in d.items():
            lines += flat(v, f"{prefix}{k}." if prefix else f"{k}.")
    elif isinstance(d, list):
        for i, v in enumerate(d):
            lines += flat(v, f"{prefix}{i}.")
    else:
        lines.append(f"    {prefix.rstrip('.')}: {d}")
    return lines


def render(sample):
    out = []
    a = out.append
    a(SEP)
    a("NAPOLEON — DATENPRUEFUNG (gezielte Stichprobe)")
    a(SEP)
    a("")
    a("Abbruchkriterium (vorher festgelegt):")
    a("  0-1 Fehler  -> Daten tragfaehig, weiter (mergen)")
    a("  2-3 Fehler  -> betroffene Wortart komplett nachpruefen")
    a("  >=4 Fehler  -> Enrichment-Prompt ueberarbeiten, neu generieren")
    a("")

    for i, (kat, e) in enumerate(sample, 1):
        a(SUB)
        a(f"[{i:2d}/{len(sample)}]  RISIKO: {kat}")
        a(SUB)
        a(f"  Wort         : {e.get('word', '?')}")
        a(f"  Betonung     : {e.get('stress', '(fehlt)')}"
          + ("" if stress_marked(e) else "   <-- KEINE Betonung markiert!"))
        a(f"  Phonetik     : {e.get('phonetic', '(fehlt)')}")
        a(f"  Uebersetzung : {e.get('translation', '(fehlt)')}")
        a(f"  Wortart      : {e.get('word_type', '(fehlt)')}")

        if e.get("conjugation"):
            a("  Konjugation:")
            out.extend(flat(e["conjugation"]))
        if e.get("declension"):
            a("  Deklination:")
            out.extend(flat(e["declension"]))
        if e.get("explanation"):
            a(f"  Erklaerung   : {str(e['explanation'])[:200]}")

        a("")
        a("  PRUEFEN gegen Woerterbuch:")
        if kat == "Verbaspekt":
            a("    [ ] Aspektpartner korrekt? (imperfektiv/perfektiv)")
            a("    [ ] Vergangenheitsform passt zum Aspekt?")
        elif kat == "Betonung Plural":
            a("    [ ] Betonung im Plural verschoben und korrekt markiert?")
            a("    [ ] Genitiv Plural korrekt?")
        elif kat == "Unregelmaessig":
            a("    [ ] Abweichende Formen vollstaendig?")
        a("    [ ] Betonung im Singular korrekt?")
        a("    [ ] Uebersetzung trifft die Hauptbedeutung?")
        a("")
        a("  Ergebnis:   [ ] OK    [ ] FEHLER  -> welcher: ______________")
        a("")

    a(SEP)
    a(f"Gepruefte Eintraege: {len(sample)}      Gefundene Fehler: ____")
    a(SEP)
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="enriched_neu.json")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", type=str, default=None)
    args = p.parse_args()

    if not os.path.isfile(args.input):
        print(f"FEHLER: {args.input} nicht gefunden.")
        sys.exit(1)

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    entries = []
    for k, v in data.items():
        e = dict(v)
        e.setdefault("id", k)
        entries.append(e)

    print(f"# Daten aus: {args.input}")
    print(f"# {len(entries)} Eintraege\n")

    rng = random.Random(args.seed)
    sample = build_sample(entries, rng)
    text = render(sample)
    print(text)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n# Gespeichert: {args.out}")


if __name__ == "__main__":
    main()
