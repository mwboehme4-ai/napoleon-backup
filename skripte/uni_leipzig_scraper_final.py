#!/usr/bin/env python3
"""
Uni Leipzig Online-Woerterbuch Scraper (FINAL v2)
URL: https://russisch.urz.uni-leipzig.de/online-woerterbuch/ruw.htm

v2-Aenderungen (08.08.2026):
- Betonung: Suchmuster korrigiert (Akzent sitzt MITTEN im Wort, nicht dahinter)
- Aspekt + Partnerverb: neu, ueber expliziten Seitentext "X, Y-er Partner ist Z"
- Konjugation: Label-basiert (Pronomen im Text selbst), nicht mehr Zeilenindex-basiert
- translation/word_type/gender werden NICHT mehr hier bestimmt (unzuverlaessig,
  da Uebersetzung fuer anonyme Nutzer gar nicht ausgeliefert wird) -
  das macht jetzt der Claude-Enricher.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import Dict, List, Optional
import sys
from urllib.parse import quote
import random

PRESENT_LABELS = ["я", "ты", "он/она", "мы", "вы", "они"]
PRESENT_KEYS   = ["1p_sg", "2p_sg", "3p_sg", "1p_pl", "2p_pl", "3p_pl"]
PAST_LABELS = ["я/ты/он", "я/ты/она", "оно", "мы/вы/они"]
PAST_KEYS   = ["masculine", "feminine", "neuter", "plural"]
CASES = ["nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"]
S_LABELS = [f"S{i}:" for i in range(1, 7)]
P_LABELS = [f"P{i}:" for i in range(1, 7)]
M_LABELS = [f"M{i}:" for i in range(1, 7)]
F_LABELS = [f"F{i}:" for i in range(1, 7)]
N_LABELS = [f"N{i}:" for i in range(1, 7)]
K_LABELS = ["KM:", "KF:", "KN:", "KP:", "Kmp:", "Sup:"]
ALL_DECL_LABELS = S_LABELS + P_LABELS + M_LABELS + F_LABELS + N_LABELS + K_LABELS

PARTICIPLE_LABELS = {
    "present_active":   "Partizip Präsens Aktiv",
    "present_passive":  "Partizip Präsens Passiv",
    "past_active":      "Partizip Präteritum Aktiv",
    "past_passive":     "Partizip Präteritum Passiv",
    "adverbial_impf":   "Adverbialpartizip imperfektiv",
    "adverbial_perf":   "Adverbialpartizip perfektiv",
}


class UniLeipzigScraperFinal:
    def __init__(self):
        self.base_url = "https://russisch.urz.uni-leipzig.de/online-woerterbuch/ruw.htm"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def search_word(self, word: str) -> Optional[Dict]:
        print(f"[*] Searching: {word}")
        try:
            rnd = random.randint(10000, 99999)
            word_encoded = quote(word.encode('utf-8'))
            url = f"{self.base_url}?ru={word_encoded}&rnd={rnd}"

            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"[-] Search failed for {word} (status {response.status_code})")
                return None

            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            text_voll = soup.get_text(separator=" ", strip=True)
            # Alles ab der Nachbarwoerter-Liste abschneiden -
            # das ist immer Seiten-Navigation, kein Wortinhalt.
            text = text_voll.split("Alphabetisch benachbarte")[0]

            if "nicht gefunden" in text.lower():
                print(f"[-] Word not found: {word}")
                return None

            aspect, aspect_partner = self._extract_aspect_partner(text)

            data = {
                "word": word,
                "url": url,
                "stress": self._extract_stress(text, word),
                "phonetic": self._extract_phonetic(text),
                "aspect": aspect,
                "aspect_partner": aspect_partner,
                "conjugation": self._extract_conjugation(text),
                "declension": self._extract_declension(text),
                "example_sentences": self._extract_examples(soup),
            }

            print(f"[+] Success: {word}")
            time.sleep(0.5)
            return data

        except Exception as e:
            print(f"[-] Error for {word}: {str(e)}")
            return None

    def _extract_stress(self, text: str, word: str) -> str:
        # Die Seite nutzt BEIDE Betonungszeichen: U+0301 (Akut) und
        # U+0300 (Gravis). Beide akzeptieren.
        parts = [re.escape(ch) + '[\u0300\u0301]?' for ch in word]
        pattern = ''.join(parts)
        matches = re.findall(pattern, text)
        for m in matches:
            if '\u0301' in m or '\u0300' in m:
                return m
        return word

    def _extract_phonetic(self, text: str) -> str:
        match = re.search(r'\[([ˈˌæəɪɔɛœɑaeiouɯʊʌ][^\]]{2,30})\]', text)
        if match:
            return f"[{match.group(1)}]"
        return ""

    def _extract_aspect_partner(self, text: str):
        m = re.search(
            r'(imperfektiv|perfektiv)\s*,\s*(?:imperfektiver|perfektiver)'
            r'\s*Partner\s*ist\s*([а-яА-ЯёЁ\u0301]+)',
            text
        )
        if m:
            return m.group(1), m.group(2)
        return None, None

    def _extract_conjugation(self, text: str) -> Optional[Dict]:
        t = re.sub(r'[ \t]+', ' ', text)
        result = {"present": {}, "past": {}, "imperative": {}, "participles": {}, "adverbial": {}}

        for label, key in zip(PRESENT_LABELS, PRESENT_KEYS):
            m = re.search(re.escape(label) + r'\s+(\S+)', t)
            if m:
                result["present"][key] = m.group(1)

        for label, key in zip(PAST_LABELS, PAST_KEYS):
            m = re.search(re.escape(label) + r'\s+(\S+)', t)
            if m:
                result["past"][key] = m.group(1)

        for im in re.findall(r'(\S+!)', t):
            if im.endswith('те!'):
                result["imperative"]["2p_pl"] = im
            elif "2p_sg" not in result["imperative"]:
                result["imperative"]["2p_sg"] = im

        alle_labels = list(PARTICIPLE_LABELS.values())
        for key, label in PARTICIPLE_LABELS.items():
            idx = t.find(label)
            if idx == -1:
                continue
            rest = t[idx + len(label):].strip()
            naechstes = len(rest)
            for other in alle_labels:
                if other == label:
                    continue
                p = rest.find(other)
                if p != -1 and p < naechstes:
                    naechstes = p
            form = rest[:naechstes].strip(" :-")
            if key.startswith("adverbial"):
                result["adverbial"][key.replace("adverbial_", "")] = form[:120]
            else:
                result["participles"][key] = form[:120]

        result = {k: v for k, v in result.items() if v}
        return result if result else None

    CASES = ["nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"]

    def _feld(self, t, label):
        idx = t.find(label)
        if idx == -1:
            return None
        rest = t[idx + len(label):]
        end = len(rest)
        for other in ALL_DECL_LABELS:
            if other == label:
                continue
            p = rest.find(other)
            if p != -1 and p < end:
                end = p
        tokens = rest[:end].strip().split()
        return tokens[-1] if tokens else None

    def _extract_declension(self, text):
        # Nomen : S1-S6 / P1-P6
        # Adjektiv: M/F/N/P 1-6 + Kurzformen KM/KF/KN/KP + Kmp/Sup
        # Seite kann MEHRERE Eintraege haben - nur den ersten nehmen.
        t = re.sub(r"[ 	]+", " ", text)
        t = t.split("Angemeldete Nutzer")[0]

        if all(lbl in t for lbl in ("M1:", "F1:", "N1:")):
            res = {"type": "adjective", "masculine": {}, "feminine": {},
                   "neuter": {}, "plural": {}}
            for labels, key in [(M_LABELS, "masculine"), (F_LABELS, "feminine"),
                                (N_LABELS, "neuter"), (P_LABELS, "plural")]:
                for i, lbl in enumerate(labels):
                    v = self._feld(t, lbl)
                    if v:
                        res[key][CASES[i]] = v
            kurz = {}
            for lbl, name in [("KM:", "masculine"), ("KF:", "feminine"),
                              ("KN:", "neuter"), ("KP:", "plural")]:
                v = self._feld(t, lbl)
                if v and v != "−":
                    kurz[name] = v
            if kurz:
                res["short_form"] = kurz
            for lbl, name in [("Kmp:", "comparative"), ("Sup:", "superlative")]:
                v = self._feld(t, lbl)
                if v and v != "−":
                    res[name] = v
            return res

        if "S1:" in t:
            res = {"type": "noun", "singular": {}, "plural": {}}
            for labels, key in [(S_LABELS, "singular"), (P_LABELS, "plural")]:
                for i, lbl in enumerate(labels):
                    v = self._feld(t, lbl)
                    if v:
                        res[key][CASES[i]] = v
            return res

        return None

    def _extract_examples(self, soup: BeautifulSoup) -> List[Dict]:
        examples = []
        text = soup.get_text()
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if re.search(r'[А-Яа-яЁё]{10,}', line) and len(line) > 15:
                example = {"russian": line.strip(), "german": ""}
                examples.append(example)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if len(next_line) > 5 and not any(c in next_line for c in 'ёЁ'):
                        example["german"] = next_line
        return examples[:5]


def main():
    try:
        with open('words.txt', 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print("[-] words.txt not found!")
        sys.exit(1)

    print(f"[+] Loaded {len(words)} words")
    print("=" * 60)

    scraper = UniLeipzigScraperFinal()
    all_data = {}
    for i, word in enumerate(words, 1):
        data = scraper.search_word(word)
        if data:
            word_id = f"{word}_{str(i).zfill(3)}"
            all_data[word_id] = data
        else:
            print(f"[!] Skipped: {word}")

    print("=" * 60)
    print(f"[+] Successfully scraped {len(all_data)} words")

    with open('raw_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"[+] Saved raw_data.json ({len(all_data)} entries)")
    print("\n[✓] Next step: python3 claude_enricher_v2.py")


if __name__ == "__main__":
    main()
