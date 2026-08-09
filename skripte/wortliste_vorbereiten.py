#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import re
import sys
import unicodedata

SATZZEICHEN = re.compile(r"[!?.,:;»«\"()]")
KYRILLISCH = re.compile(r"[а-яА-ЯёЁ]")


def norm(s):
    s = s.replace("\u0301", "").replace("\u0300", "")
    return unicodedata.normalize("NFC", s).strip().lower()


def lade_zeilen(pfad):
    with open(pfad, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def bestand_laden(pfade):
    vorhanden = set()
    quellen = []
    for p in pfade:
        if not p or not os.path.isfile(p):
            continue
        if p.endswith(".json"):
            import json
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            for v in data.values():
                w = v.get("word") if isinstance(v, dict) else None
                if w:
                    vorhanden.add(norm(w))
            quellen.append(f"{p} ({len(data)} Eintraege)")
        else:
            zeilen = lade_zeilen(p)
            vorhanden.update(norm(z) for z in zeilen)
            quellen.append(f"{p} ({len(zeilen)} Zeilen)")
    return vorhanden, quellen


def ist_phrase(wort):
    return (" " in wort) or bool(SATZZEICHEN.search(wort))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("liste")
    p.add_argument("--bestand", nargs="*", default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--outdir", default=".")
    args = p.parse_args()

    if not os.path.isfile(args.liste):
        print(f"FEHLER: {args.liste} nicht gefunden.")
        sys.exit(1)

    bestand_pfade = args.bestand
    if bestand_pfade is None:
        bestand_pfade = []
        for kandidat in [
            os.path.expanduser("~/words_alt.txt"),
            os.path.expanduser("~/words.txt"),
            "words.txt",
            os.path.expanduser("~/vokabeltrainer/public/data/vocab_sm2.json"),
        ]:
            if os.path.isfile(kandidat):
                bestand_pfade.append(kandidat)

    vorhanden, quellen = bestand_laden(bestand_pfade)
    roh = lade_zeilen(args.liste)

    eindeutig = list(dict.fromkeys(roh))
    interne_dubletten = len(roh) - len(eindeutig)

    ohne_kyrillisch = [w for w in eindeutig if not KYRILLISCH.search(w)]
    eindeutig = [w for w in eindeutig if KYRILLISCH.search(w)]

    bereits_da = [w for w in eindeutig if norm(w) in vorhanden]
    neu = [w for w in eindeutig if norm(w) not in vorhanden]

    einzelwoerter = [w for w in neu if not ist_phrase(w)]
    phrasen = [w for w in neu if ist_phrase(w)]

    ausgabe_einzel = einzelwoerter[:args.limit] if args.limit else einzelwoerter

    os.makedirs(args.outdir, exist_ok=True)
    pw = os.path.join(args.outdir, "words_neu.txt")
    pp = os.path.join(args.outdir, "phrasen_neu.txt")

    with open(pw, "w", encoding="utf-8") as f:
        f.write("\n".join(ausgabe_einzel) + "\n")
    with open(pp, "w", encoding="utf-8") as f:
        f.write("\n".join(phrasen) + "\n")

    print("=" * 50)
    print(f"Zeilen gesamt        : {len(roh)}")
    print(f"Interne Dubletten    : {interne_dubletten}")
    print(f"Ohne Kyrillisch      : {len(ohne_kyrillisch)}")
    print("Bestandsquellen:")
    for q in (quellen or ["  (keine gefunden)"]):
        print(f"  {q}")
    print(f"Bereits vorhanden    : {len(bereits_da)}")
    print(f"ECHT NEU             : {len(neu)}")
    print(f"  Einzelwoerter      : {len(einzelwoerter)} -> {pw}")
    print(f"  Phrasen            : {len(phrasen)} -> {pp}")
    if args.limit:
        print(f"LIMIT aktiv: {len(ausgabe_einzel)} geschrieben")
    print("=" * 50)


if __name__ == "__main__":
    main()
