#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Napoleon - Merge in die App-JSONs

Haengt neue Woerter an vocab_sm2.json und grammar_db.json an, OHNE
den vorhandenen Lernfortschritt (sm2-Bloecke) zu ueberschreiben.
"""

import argparse
import json
import os
import shutil
import sys
import unicodedata
from datetime import datetime

SM2_START = {
    "easiness": 2.5,
    "interval": 1,
    "repetitions": 0,
    "next_review": None,
    "last_review": None,
}

GRAMMAR_FELDER = [
    "explanation", "conjugation", "declension", "common_mistakes",
    "tips_pronunciation", "etymology", "example_sentence", "example_translation",
    "aspect_partner",
]

VOCAB_FELDER = [
    "id", "word", "stress", "translation", "phonetic",
    "word_type", "category", "level", "aspect", "gender",
]


def norm(s):
    return unicodedata.normalize("NFC", (s or "").replace("\u0301", "")).strip().lower()


def lade(pfad, standard=None):
    if not os.path.isfile(pfad):
        return standard if standard is not None else {}
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def backup(pfad):
    if not os.path.isfile(pfad):
        return None
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    ziel = f"{pfad}.{stempel}.bak"
    shutil.copy2(pfad, ziel)
    return ziel


def schreiben(pfad, daten):
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)
    os.replace(tmp, pfad)


def finde_ziel():
    for k in [
        os.path.expanduser("~/vokabeltrainer/public/data"),
        os.path.expanduser("~/vokabeltrainer/src/data"),
        os.path.expanduser("~"),
        ".",
    ]:
        if os.path.isfile(os.path.join(k, "vocab_sm2.json")):
            return k
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--neu", default="enriched_data.json")
    p.add_argument("--ziel", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not os.path.isfile(args.neu):
        print(f"[-] {args.neu} nicht gefunden.")
        sys.exit(1)

    ziel = args.ziel or finde_ziel()
    if not ziel:
        print("[-] vocab_sm2.json nicht gefunden. Mit --ziel angeben.")
        sys.exit(1)

    p_vocab = os.path.join(ziel, "vocab_sm2.json")
    p_gram = os.path.join(ziel, "grammar_db.json")

    neu = lade(args.neu)
    vocab = lade(p_vocab)
    gram = lade(p_gram)

    print(f"[+] Ziel        : {ziel}")
    print(f"[+] Bestand     : {len(vocab)} Vokabeln, {len(gram)} Grammatik")
    print(f"[+] Neue Datei  : {len(neu)} Eintraege")
    print("=" * 58)

    nach_wort = {}
    for k, v in vocab.items():
        if isinstance(v, dict) and v.get("word"):
            nach_wort[norm(v["word"])] = k

    hinzugefuegt = aktualisiert = fortschritt_bewahrt = 0

    for roh_id, daten in neu.items():
        wort = daten.get("word")
        if not wort:
            continue

        vorhandene_id = nach_wort.get(norm(wort))
        ziel_id = vorhandene_id or roh_id

        vocab_eintrag = {k: daten[k] for k in VOCAB_FELDER if k in daten}
        vocab_eintrag["id"] = ziel_id
        vocab_eintrag.setdefault("word", wort)

        if vorhandene_id:
            alt = vocab[vorhandene_id]
            vocab_eintrag["sm2"] = alt.get("sm2", dict(SM2_START))
            if alt.get("sm2", {}).get("repetitions", 0) > 0:
                fortschritt_bewahrt += 1
            vocab[vorhandene_id] = {**alt, **vocab_eintrag}
            aktualisiert += 1
        else:
            vocab_eintrag["sm2"] = dict(SM2_START)
            vocab[ziel_id] = vocab_eintrag
            hinzugefuegt += 1

        gram_eintrag = {k: daten[k] for k in GRAMMAR_FELDER if k in daten}
        if gram_eintrag:
            gram_eintrag["id"] = ziel_id
            gram_eintrag["word"] = wort
            gram_eintrag["word_type"] = daten.get("word_type", "")
            gram[f"{ziel_id}_grammar"] = gram_eintrag

    print(f"    Neu hinzugefuegt      : {hinzugefuegt}")
    print(f"    Aktualisiert          : {aktualisiert}")
    print(f"    davon mit Fortschritt : {fortschritt_bewahrt}  (sm2 bewahrt)")
    print(f"    Neuer Bestand         : {len(vocab)} Vokabeln, {len(gram)} Grammatik")
    print("=" * 58)

    if args.dry_run:
        print("[i] --dry-run: nichts geschrieben.")
        return

    b1 = backup(p_vocab)
    b2 = backup(p_gram)
    if b1:
        print(f"[*] Backup: {os.path.basename(b1)}")
    if b2:
        print(f"[*] Backup: {os.path.basename(b2)}")

    schreiben(p_vocab, vocab)
    schreiben(p_gram, gram)
    print("[✓] Geschrieben.")
    print()
    print("[→] Browser neu laden (F5)")


if __name__ == "__main__":
    main()
