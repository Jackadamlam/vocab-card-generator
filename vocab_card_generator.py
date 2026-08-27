#!/usr/bin/env python3
"""
Vocabulary Card Generator for Obsidian
======================================

Generate bilingual-ready, Obsidian-formatted vocabulary cards from a free
dictionary API (https://dictionaryapi.dev).

Features
--------
* Looks up pronunciation, definitions, examples, synonyms and antonyms.
* Smart base-form detection: derived forms (past tense, -ing, plurals,
  comparatives, -tion/-ment/-ness ...) are traced back to their base word.
* Generates *verified* morphological word forms (plural / tenses /
  comparative ...) and writes them into the YAML frontmatter.
* Discovers derivationally related words (e.g. educate -> education,
  educator) and links them as Obsidian Wiki Links.
* Never silently overwrites an existing card. Existing cards are skipped by
  default; ``--force`` overwrites; ``--merge`` regenerates the dictionary
  fields while preserving your hand-written "My examples" bullets and the
  trailing "中文释义" section.

The generated card does NOT contain a Chinese translation automatically --
the free dictionary API is English-only. Add or translate the "中文释义"
section yourself after generation (the ``--merge`` flow preserves it).
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime with a clear message
    requests = None


# ---------------------------------------------------------------------------
# Irregular verbs: {base: (past_tense, past_participle)}
# ---------------------------------------------------------------------------
IRREGULAR_VERBS = {
    'arise': ('arose', 'arisen'),
    'awake': ('awoke', 'awoken'),
    'be': ('was/were', 'been'),
    'bear': ('bore', 'born/borne'),
    'beat': ('beat', 'beaten'),
    'become': ('became', 'become'),
    'begin': ('began', 'begun'),
    'bend': ('bent', 'bent'),
    'bet': ('bet', 'bet'),
    'bind': ('bound', 'bound'),
    'bite': ('bit', 'bitten'),
    'bleed': ('bled', 'bled'),
    'blow': ('blew', 'blown'),
    'break': ('broke', 'broken'),
    'breed': ('bred', 'bred'),
    'bring': ('brought', 'brought'),
    'build': ('built', 'built'),
    'burn': ('burnt/burned', 'burnt/burned'),
    'burst': ('burst', 'burst'),
    'buy': ('bought', 'bought'),
    'cast': ('cast', 'cast'),
    'catch': ('caught', 'caught'),
    'choose': ('chose', 'chosen'),
    'cling': ('clung', 'clung'),
    'come': ('came', 'come'),
    'cost': ('cost', 'cost'),
    'creep': ('crept', 'crept'),
    'cut': ('cut', 'cut'),
    'deal': ('dealt', 'dealt'),
    'dig': ('dug', 'dug'),
    'do': ('did', 'done'),
    'draw': ('drew', 'drawn'),
    'dream': ('dreamt/dreamed', 'dreamt/dreamed'),
    'drink': ('drank', 'drunk'),
    'drive': ('drove', 'driven'),
    'eat': ('ate', 'eaten'),
    'fall': ('fell', 'fallen'),
    'feed': ('fed', 'fed'),
    'feel': ('felt', 'felt'),
    'fight': ('fought', 'fought'),
    'find': ('found', 'found'),
    'flee': ('fled', 'fled'),
    'fly': ('flew', 'flown'),
    'forbid': ('forbade', 'forbidden'),
    'forget': ('forgot', 'forgotten'),
    'forgive': ('forgave', 'forgiven'),
    'freeze': ('froze', 'frozen'),
    'get': ('got', 'got/gotten'),
    'give': ('gave', 'given'),
    'go': ('went', 'gone'),
    'grind': ('ground', 'ground'),
    'grow': ('grew', 'grown'),
    'hang': ('hung', 'hung'),
    'have': ('had', 'had'),
    'hear': ('heard', 'heard'),
    'hide': ('hid', 'hidden'),
    'hit': ('hit', 'hit'),
    'hold': ('held', 'held'),
    'hurt': ('hurt', 'hurt'),
    'keep': ('kept', 'kept'),
    'kneel': ('knelt', 'knelt'),
    'know': ('knew', 'known'),
    'lay': ('laid', 'laid'),
    'lead': ('led', 'led'),
    'lean': ('leant/leaned', 'leant/leaned'),
    'leap': ('leapt/leaped', 'leapt/leaped'),
    'learn': ('learnt/learned', 'learnt/learned'),
    'leave': ('left', 'left'),
    'lend': ('lent', 'lent'),
    'let': ('let', 'let'),
    'lie': ('lay', 'lain'),
    'light': ('lit/lighted', 'lit/lighted'),
    'lose': ('lost', 'lost'),
    'make': ('made', 'made'),
    'mean': ('meant', 'meant'),
    'meet': ('met', 'met'),
    'mistake': ('mistook', 'mistaken'),
    'overcome': ('overcame', 'overcome'),
    'pay': ('paid', 'paid'),
    'put': ('put', 'put'),
    'quit': ('quit', 'quit'),
    'read': ('read', 'read'),
    'ride': ('rode', 'ridden'),
    'ring': ('rang', 'rung'),
    'rise': ('rose', 'risen'),
    'run': ('ran', 'run'),
    'say': ('said', 'said'),
    'see': ('saw', 'seen'),
    'seek': ('sought', 'sought'),
    'sell': ('sold', 'sold'),
    'send': ('sent', 'sent'),
    'set': ('set', 'set'),
    'sew': ('sewed', 'sewn/sewed'),
    'shake': ('shook', 'shaken'),
    'shine': ('shone', 'shone'),
    'shoot': ('shot', 'shot'),
    'show': ('showed', 'shown/showed'),
    'shut': ('shut', 'shut'),
    'sing': ('sang', 'sung'),
    'sink': ('sank', 'sunk'),
    'sit': ('sat', 'sat'),
    'sleep': ('slept', 'slept'),
    'slide': ('slid', 'slid'),
    'speak': ('spoke', 'spoken'),
    'spend': ('spent', 'spent'),
    'spin': ('spun', 'spun'),
    'spread': ('spread', 'spread'),
    'stand': ('stood', 'stood'),
    'steal': ('stole', 'stolen'),
    'stick': ('stuck', 'stuck'),
    'sting': ('stung', 'stung'),
    'strike': ('struck', 'struck/stricken'),
    'swear': ('swore', 'sworn'),
    'sweep': ('swept', 'swept'),
    'swim': ('swam', 'swum'),
    'swing': ('swung', 'swung'),
    'take': ('took', 'taken'),
    'teach': ('taught', 'taught'),
    'tear': ('tore', 'torn'),
    'tell': ('told', 'told'),
    'think': ('thought', 'thought'),
    'throw': ('threw', 'thrown'),
    'understand': ('understood', 'understood'),
    'undo': ('undid', 'undone'),
    'upset': ('upset', 'upset'),
    'wake': ('woke', 'woken'),
    'wear': ('wore', 'worn'),
    'weave': ('wove', 'woven'),
    'weep': ('wept', 'wept'),
    'win': ('won', 'won'),
    'withdraw': ('withdrew', 'withdrawn'),
    'wring': ('wrung', 'wrung'),
    'write': ('wrote', 'written'),
}

# Build reverse lookup: surface form -> [possible base forms].
# A list value is used because some surfaces belong to more than one verb
# (e.g. "lay" is both a base verb and the past tense of "lie").
IRREGULAR_REVERSE: dict[str, list[str]] = {}
for _base, (_past, _part) in IRREGULAR_VERBS.items():
    for _form in _past.split('/'):
        IRREGULAR_REVERSE.setdefault(_form.strip(), []).append(_base)
    for _form in _part.split('/'):
        IRREGULAR_REVERSE.setdefault(_form.strip(), []).append(_base)

# Suffixes that strongly suggest a multi-syllable adjective which normally
# forms its comparative/superlative analytically ("more/most ...") rather
# than with "-er/-est". Used to avoid generating nonsense like "neuraller".
_NON_GRADABLE_SUFFIXES = (
    'al', 'ous', 'ious', 'ful', 'less', 'ive', 'ant', 'ent', 'ic',
    'ate', 'ary', 'ory', 'ile', 'ine', 'ish', 'able', 'ible',
)

_PLACEHOLDER_EXAMPLE = "_Write your own sentence here:_"


def ensure_utf8_streams():
    """Force UTF-8 on stdout/stderr so status glyphs and IPA never crash the
    console on legacy Windows code pages (e.g. GBK/cp936)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable, no network)
# ---------------------------------------------------------------------------
def estimate_syllables(word: str) -> int:
    """Rough English syllable count via vowel-group counting."""
    word = re.sub(r'[^a-z]', '', word.lower())
    if not word:
        return 0
    groups = len(re.findall(r'[aeiouy]+', word))
    # Silent final "e" does not form a syllable -- unless it closes a
    # consonant+"le" ending (e.g. ta-ble), where it is pronounced.
    if word.endswith('e') and groups > 1:
        syllabic_le = len(word) >= 3 and word[-2] == 'l' and word[-3] not in 'aeiou'
        if not syllabic_le:
            groups -= 1
    return max(1, groups)


def is_likely_multisyllable_adjective(word: str) -> bool:
    """True when a word should use more/most instead of -er/-est."""
    w = word.lower()
    if w.endswith(_NON_GRADABLE_SUFFIXES):
        return True
    return estimate_syllables(w) >= 3


def extract_chinese_section(md: str) -> str:
    """Return the trailing '### 中文释义' block (heading included) or ''."""
    idx = md.find('### 中文释义')
    if idx == -1:
        return ''
    return md[idx:].rstrip() + '\n'


def extract_my_example_bullets(md: str) -> list[str]:
    """Return user-authored bullet texts under '**My examples:**'."""
    idx = md.find('**My examples:**')
    if idx == -1:
        return []
    tail = md[idx + len('**My examples:**'):]
    stop = re.search(r'\n(\*\*|---|###)', tail)
    if stop:
        tail = tail[:stop.start()]
    bullets = []
    for line in tail.splitlines():
        s = line.strip()
        if s.startswith('- '):
            text = s[2:].strip()
            if text and text != _PLACEHOLDER_EXAMPLE:
                bullets.append(text)
    return bullets


def merge_manual_into_generated(generated_md: str, old_md: str) -> str:
    """Splice hand-written content from ``old_md`` into fresh ``generated_md``."""
    out = generated_md

    bullets = extract_my_example_bullets(old_md)
    if bullets:
        placeholder_block = f"**My examples:**\n\n- {_PLACEHOLDER_EXAMPLE}\n"
        replacement = "**My examples:**\n\n" + "".join(f"- {b}\n" for b in bullets) + "\n"
        if placeholder_block in out:
            out = out.replace(placeholder_block, replacement)

    chinese = extract_chinese_section(old_md)
    if chinese and '### 中文释义' not in out:
        out = out.rstrip() + "\n\n---\n\n" + chinese

    return out


# ---------------------------------------------------------------------------
# Obsidian deep-link helper (pure + testable)
# ---------------------------------------------------------------------------
def build_obsidian_uri(abs_md_path, vault_root, vault_name):
    """Return an ``obsidian://open`` URI for a card, or None if not resolvable.

    The ``file`` parameter is the note path relative to the vault root, without
    the ``.md`` extension, using forward slashes. Returns ``None`` when either
    the vault info is missing or the file lives outside the vault.
    """
    if not vault_root or not vault_name:
        return None
    try:
        rel = Path(abs_md_path).resolve().with_suffix('').relative_to(
            Path(vault_root).resolve())
    except (ValueError, OSError):
        return None
    quote = urllib.parse.quote
    return (f"obsidian://open?vault={quote(str(vault_name))}"
            f"&file={quote(rel.as_posix())}")


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
class VocabCardGenerator:
    def __init__(self, output_dir=None, overwrite='skip', include_related=True,
                 vault_root=None, vault_name=None):
        if output_dir is None:
            output_dir = str(Path(__file__).parent)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_url = "https://api.dictionaryapi.dev/api/v2/entries/en"
        self.overwrite = overwrite          # 'skip' | 'force' | 'merge'
        self.include_related = include_related
        self.vault_root = vault_root or os.environ.get('VOCAB_OBSIDIAN_ROOT')
        self.vault_name = vault_name or os.environ.get('VOCAB_OBSIDIAN_VAULT')
        self.created_cards: set[str] = set()
        self._cache: dict[str, object] = {}
        self.timeout = 6                  # seconds per request; API is free/slow
        self.max_requests = 40            # hard safety budget per invocation
        self._request_count = 0

    # -- network ----------------------------------------------------------
    def fetch_word_data(self, word):
        key = word.lower()
        if key in self._cache:
            return self._cache[key]
        data = None
        if requests is not None and self._request_count < self.max_requests:
            self._request_count += 1
            try:
                response = requests.get(f"{self.api_url}/{key}", timeout=self.timeout)
                if response.status_code == 200:
                    payload = response.json()
                    if isinstance(payload, list) and payload:
                        data = payload
            except (requests.exceptions.RequestException, ValueError):
                data = None
        self._cache[key] = data
        return data

    @staticmethod
    def canonical_word(data, fallback):
        """Use the dictionary's canonical spelling (fixes Estimate -> estimate)."""
        if isinstance(data, list) and data:
            entry = data[0]
            if isinstance(entry, dict) and entry.get('word'):
                return str(entry['word']).strip()
        return fallback

    # -- morphology heuristics -------------------------------------------
    def find_base_forms(self, word):
        candidates: list[str] = []

        # 0. Irregular verb reverse lookup. Skipped when the word is itself a
        #    base verb (avoids mis-resolving "lay"/"read"/"put" to another head).
        if word in IRREGULAR_REVERSE and word not in IRREGULAR_VERBS:
            candidates.extend(IRREGULAR_REVERSE[word])

        # 1. Past tense / past participle (-ed)
        if word.endswith('ed') and len(word) > 3:
            if len(word) >= 5 and word[-3] == word[-4]:
                candidates.append(word[:-3])           # embedded -> embed
            candidates.append(word[:-2])               # walked -> walk
            candidates.append(word[:-1])               # loved -> love
            if word.endswith('ied'):
                candidates.append(word[:-3] + 'y')     # studied -> study

        # 2. Present participle (-ing)
        if word.endswith('ing') and len(word) > 4:
            if len(word) >= 6 and word[-4] == word[-5]:
                candidates.append(word[:-4])           # running -> run
            candidates.append(word[:-3])
            if word.endswith('ying'):
                candidates.append(word[:-4] + 'ie')    # lying -> lie
            if word.endswith('ving'):
                candidates.append(word[:-3] + 'e')     # having -> have

        # 3. Comparative / superlative (-er, -est)
        if word.endswith('er') and len(word) > 3:
            candidates.append(word[:-2])
            candidates.append(word[:-1])
            if word.endswith('ier'):
                candidates.append(word[:-3] + 'y')
        if word.endswith('est') and len(word) > 4:
            candidates.append(word[:-3])
            candidates.append(word[:-2])
            if word.endswith('iest'):
                candidates.append(word[:-4] + 'y')

        # 4/5. Third person singular & plural nouns
        if word.endswith('ies') and len(word) > 4:
            candidates.append(word[:-3] + 'y')
        elif word.endswith('ves') and len(word) > 4:
            candidates.append(word[:-3] + 'f')
            candidates.append(word[:-3] + 'fe')
        elif word.endswith(('ses', 'xes', 'zes', 'ches', 'shes')):
            candidates.append(word[:-2])
        elif word.endswith('es') and len(word) > 3:
            candidates.append(word[:-2])
            candidates.append(word[:-1])
        elif word.endswith('s') and len(word) > 2:
            candidates.append(word[:-1])

        # 6. Adverbs (-ly)
        if word.endswith('ly') and len(word) > 3:
            candidates.append(word[:-2])
            if word.endswith('ily'):
                candidates.append(word[:-3] + 'y')
            if word.endswith('ably'):
                candidates.append(word[:-4] + 'le')
            if word.endswith('ically'):
                candidates.append(word[:-6] + 'ic')
                candidates.append(word[:-6] + 'ical')

        # 7. Noun-form suffixes
        if word.endswith('tion') and len(word) > 4:
            candidates.append(word[:-4] + 'te')
            candidates.append(word[:-4] + 't')
        if word.endswith('sion') and len(word) > 4:
            candidates.append(word[:-4] + 'de')
            candidates.append(word[:-4] + 'd')
        if word.endswith('ation') and len(word) > 5:
            candidates.append(word[:-5] + 'e')
            candidates.append(word[:-5])
        if word.endswith('ment') and len(word) > 4:
            candidates.append(word[:-4])
            candidates.append(word[:-4] + 'e')
        if word.endswith('ness') and len(word) > 4:
            candidates.append(word[:-4])
            if word.endswith('iness'):
                candidates.append(word[:-5] + 'y')
        if word.endswith('ity') and len(word) > 4:
            candidates.append(word[:-3] + 'e')
            candidates.append(word[:-3] + 'y')

        # 8. Adjective-form suffixes
        if word.endswith('ful') and len(word) > 4:
            candidates.append(word[:-3])
        if word.endswith('less') and len(word) > 4:
            candidates.append(word[:-4])
        if word.endswith('ous') and len(word) > 4:
            candidates.append(word[:-3] + 'e')
        if word.endswith('ive') and len(word) > 4:
            candidates.append(word[:-3] + 'e')
            candidates.append(word[:-3])
        if word.endswith('able') and len(word) > 4:
            candidates.append(word[:-4])
            candidates.append(word[:-4] + 'e')
        if word.endswith('ible') and len(word) > 4:
            candidates.append(word[:-4])

        seen, unique = set(), []
        for c in candidates:
            if c and c != word and len(c) > 1 and c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    def try_base_forms(self, word):
        for candidate in self.find_base_forms(word):
            data = self.fetch_word_data(candidate)
            if data:
                return candidate, data
        return None, None

    def has_independent_meaning(self, word):
        data = self.fetch_word_data(word)
        if not data:
            return False, None
        return True, data

    def is_derived_word(self, word):
        for candidate in self.find_base_forms(word):
            if self.fetch_word_data(candidate):
                return True, candidate
        return False, None

    def parse_word_data(self, data, word):
        if not data or not isinstance(data, list):
            return None
        entry = data[0]
        result = {"word": word, "phonetics": [], "meanings": []}
        for phonetic in entry.get("phonetics", []):
            if phonetic.get("text"):
                result["phonetics"].append(phonetic["text"])
        for meaning in entry.get("meanings", []):
            pos = meaning.get("partOfSpeech", "")
            definitions = []
            for defn in meaning.get("definitions", []):
                definitions.append({
                    "definition": defn.get("definition", ""),
                    "example": defn.get("example", ""),
                    "synonyms": defn.get("synonyms", []),
                    "antonyms": defn.get("antonyms", []),
                })
            result["meanings"].append({"partOfSpeech": pos, "definitions": definitions})
        return result

    def generate_word_forms(self, word, pos_list):
        """Generate grammatical forms, verified against the dictionary."""
        forms: dict[str, str] = {}

        if 'noun' in pos_list:
            candidates = []
            if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
                candidates.append(word[:-1] + "ies")
            elif word.endswith(('s', 'sh', 'ch', 'x', 'z')):
                candidates.append(word + "es")
            elif word.endswith('f'):
                candidates.append(word[:-1] + "ves")
            elif word.endswith('fe'):
                candidates.append(word[:-2] + "ves")
            candidates.append(word + "s")
            for cand in candidates:
                if self.fetch_word_data(cand):
                    forms["plural"] = cand
                    break

        if 'verb' in pos_list:
            tp = []
            if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
                tp.append(word[:-1] + "ies")
            elif word.endswith(('s', 'sh', 'ch', 'x', 'z', 'o')):
                tp.append(word + "es")
            tp.append(word + "s")
            for cand in tp:
                if self.fetch_word_data(cand):
                    forms["third_person"] = cand
                    break

            ing = []
            if word.endswith('ie'):
                ing.append(word[:-2] + "ying")
            elif word.endswith('e') and not word.endswith('ee'):
                ing.append(word[:-1] + "ing")
            elif (len(word) >= 3 and word[-1] not in 'aeiouwxy'
                  and word[-2] in 'aeiou' and word[-3] not in 'aeiou'):
                ing.append(word + word[-1] + "ing")
            ing.append(word + "ing")
            for cand in ing:
                if self.fetch_word_data(cand):
                    forms["present_participle"] = cand
                    break

            if word in IRREGULAR_VERBS:
                forms["past_tense"] = IRREGULAR_VERBS[word][0]
                forms["past_participle"] = IRREGULAR_VERBS[word][1]
            else:
                past = []
                if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
                    past.append(word[:-1] + "ied")
                elif word.endswith('e'):
                    past.append(word + "d")
                elif (len(word) >= 3 and word[-1] not in 'aeiouwxy'
                      and word[-2] in 'aeiou' and word[-3] not in 'aeiou'):
                    past.append(word + word[-1] + "ed")
                past.append(word + "ed")
                for cand in past:
                    if self.fetch_word_data(cand):
                        forms["past_tense"] = cand
                        forms["past_participle"] = cand
                        break

        if 'adjective' in pos_list and not is_likely_multisyllable_adjective(word):
            comp = []
            if word.endswith('e'):
                comp.append(word + "r")
            elif word.endswith('y'):
                comp.append(word[:-1] + "ier")
            elif (len(word) >= 3 and word[-1] not in 'aeiouwy'
                  and word[-2] in 'aeiou' and word[-3] not in 'aeiou'):
                comp.append(word + word[-1] + "er")
            comp.append(word + "er")
            for cand in comp:
                if self.fetch_word_data(cand):
                    forms["comparative"] = cand
                    break

            sup = []
            if word.endswith('e'):
                sup.append(word + "st")
            elif word.endswith('y'):
                sup.append(word[:-1] + "iest")
            elif (len(word) >= 3 and word[-1] not in 'aeiouwy'
                  and word[-2] in 'aeiou' and word[-3] not in 'aeiou'):
                sup.append(word + word[-1] + "est")
            sup.append(word + "est")
            for cand in sup:
                if self.fetch_word_data(cand):
                    forms["superlative"] = cand
                    break

        return forms

    def _deriv_candidates(self, word, pos_list):
        """Best-effort derivational neighbours to probe for Wiki Links."""
        c: set[str] = set()
        if 'verb' in pos_list:
            c |= {word + "tion", word + "ment", word + "er", word + "or", word + "able"}
            if word.endswith('e'):
                c |= {word[:-1] + "ion", word[:-1] + "able", word[:-1] + "or", word[:-1] + "ment"}
            if word.endswith('te'):
                c |= {word[:-2] + "tion"}
        if 'adjective' in pos_list:
            c |= {word + "ly", word + "ness", word + "ity", word + "al"}
            if word.endswith('y'):
                c |= {word[:-1] + "iness", word[:-1] + "ily"}
            if word.endswith('e'):
                c |= {word[:-1] + "ly"}
        if 'noun' in pos_list:
            c |= {word + "al", word + "y", word + "ish"}
            if word.endswith('y'):
                c |= {word[:-1] + "ial"}
        return {x for x in c if x and x != word}

    def discover_related_forms(self, word, pos_list, exclude):
        found = []
        probes = sorted(self._deriv_candidates(word, pos_list))[:12]
        for cand in probes:
            if len(found) >= 6 or self._request_count >= self.max_requests:
                break
            if cand in exclude:
                continue
            if self.fetch_word_data(cand):
                found.append(cand)
        return sorted(set(found))

    # -- rendering --------------------------------------------------------
    def generate_markdown(self, word_data, tags=None, input_word=None):
        if not word_data:
            return None
        word = word_data["word"]
        date_added = datetime.now().strftime("%Y-%m-%d")
        phonetic = word_data["phonetics"][0] if word_data["phonetics"] else ""
        all_pos = [m["partOfSpeech"] for m in word_data["meanings"]]

        if tags is None:
            tags = []
        for pos in all_pos:
            if pos not in tags:
                tags.append(pos)

        is_derived, base_word = self.is_derived_word(word)
        forms = {} if is_derived else self.generate_word_forms(word, all_pos)

        yaml_lines = [
            "---",
            f"word: {word}",
            f"pronunciation: {phonetic}",
            f"part_of_speech: {', '.join(all_pos)}",
            f"date_added: {date_added}",
        ]
        if is_derived and base_word:
            yaml_lines.append(f"base_form: {self.canonical_word(self.fetch_word_data(base_word), base_word)}")
        if input_word and input_word != word:
            yaml_lines.append(f"input_form: {input_word}")
        for key, value in forms.items():
            if value:
                yaml_lines.append(f"{key}: {value}")
        yaml_lines.append(f"tags: [{', '.join(tags)}]")
        yaml_lines.append("---")

        md = "\n".join(yaml_lines) + "\n\n"

        md += "---\n\n### Definition\n\n"
        for meaning in word_data["meanings"]:
            md += f"#### {meaning['partOfSpeech'].capitalize()}\n\n"
            for i, defn in enumerate(meaning["definitions"][:3], 1):
                md += f"{i}. {defn['definition']}\n"
                if defn["example"]:
                    md += f"   - *Example: {defn['example']}*\n"
            md += "\n"

        all_synonyms, all_antonyms = [], []
        for meaning in word_data["meanings"]:
            for defn in meaning["definitions"]:
                all_synonyms.extend(defn.get("synonyms", []))
                all_antonyms.extend(defn.get("antonyms", []))
        if all_synonyms:
            md += "---\n\n### Synonyms\n\n"
            md += ", ".join(sorted(set(all_synonyms))[:10]) + "\n\n"
        if all_antonyms:
            md += "### Antonyms\n\n"
            md += ", ".join(sorted(set(all_antonyms))[:10]) + "\n\n"

        related = []
        if self.include_related and not is_derived:
            related = self.discover_related_forms(word, all_pos, set(forms.values()))
        if forms or related:
            md += "---\n\n### Word Forms\n\n"
            for label, form in forms.items():
                md += f"- `{form}` ({label})\n"
            if related:
                md += "\n### Related Forms\n\n"
                for r in related:
                    md += f"- [[{r}]]\n"
            md += "\n"

        all_examples = [
            d["example"] for m in word_data["meanings"] for d in m["definitions"] if d["example"]
        ]
        md += "---\n\n### Usage Notes\n\n"
        if all_examples:
            md += "**Examples:**\n\n"
            for ex in all_examples[:5]:
                md += f"- {ex}\n"
            md += "\n"
        md += f"**My examples:**\n\n- {_PLACEHOLDER_EXAMPLE}\n\n"
        return md

    def create_template_card(self, word, tags=None):
        date_added = datetime.now().strftime("%Y-%m-%d")
        display_word = word.replace("-", " ")
        tags = tags or []
        yaml_lines = [
            "---",
            f"word: {display_word}",
            "pronunciation: ",
            "part_of_speech: ",
            f"date_added: {date_added}",
            f"tags: [{', '.join(tags)}]",
            "---",
        ]
        md = "\n".join(yaml_lines) + "\n\n"
        md += "---\n\n### Definition\n\n_Add definition here:_\n\n"
        md += "---\n\n### Usage Notes\n\n**Examples:**\n\n- _Add examples here:_\n\n"
        md += f"**My examples:**\n\n- {_PLACEHOLDER_EXAMPLE}\n\n"
        return md

    # -- persistence ------------------------------------------------------
    def save_card(self, word, markdown_content):
        filepath = self.output_dir / f"{word}.md"
        if filepath.exists():
            if self.overwrite == 'force':
                pass
            elif self.overwrite == 'merge':
                merged = merge_manual_into_generated(markdown_content, filepath.read_text(encoding="utf-8"))
                filepath.write_text(merged, encoding="utf-8")
                self.created_cards.add(word)
                print(f"  ✓ Card merged: {filepath.name}")
                return filepath
            else:  # skip
                print(f"  ⚠ Exists, left untouched (use --force/--merge): {filepath.name}")
                return filepath
        filepath.write_text(markdown_content, encoding="utf-8")
        self.created_cards.add(word)
        print(f"  ✓ Card saved: {filepath.name}")
        return filepath

    def suggest_similar(self, word):
        names = {p.stem for p in self.output_dir.glob("*.md")}
        names |= set(IRREGULAR_VERBS.keys())
        matches = difflib.get_close_matches(word, sorted(names), n=3, cutoff=0.7)
        if matches:
            print(f"  💡 Did you mean: {', '.join(matches)}?")
        return matches

    def open_file(self, filepath):
        """Jump to a saved card: Obsidian deep link if configured, else OS default."""
        uri = build_obsidian_uri(filepath, self.vault_root, self.vault_name)
        target = uri or str(Path(filepath).resolve())
        try:
            if sys.platform.startswith('win'):
                os.startfile(target)  # noqa: S606 - opens registered handler
            elif sys.platform == 'darwin':
                subprocess.run(['open', target], check=False)
            else:
                subprocess.run(['xdg-open', target], check=False)
            print(f"  ↗ Opened in Obsidian: {Path(filepath).name}")
        except OSError as exc:
            print(f"  ! Could not auto-open ({exc}). Path: {filepath}")

    # -- orchestration ----------------------------------------------------
    def create_card(self, word, tags=None):
        word = word.strip()
        if not word or word in self.created_cards:
            return None

        print(f"Looking up '{word}'...")

        is_derived, base_word = self.is_derived_word(word)
        if is_derived and base_word:
            print(f"  Detected derived form: '{word}' → base form: '{base_word}'")
            base_filepath = self.create_card(base_word, tags)
            has_meaning, data = self.has_independent_meaning(word)
            if has_meaning:
                canon = self.canonical_word(data, word)
                print(f"  '{word}' also has independent meaning, creating separate card...")
                wd = self.parse_word_data(data, canon)
                md = self.generate_markdown(wd, tags, input_word=word)
                return self.save_card(canon, md)
            print(f"  '{word}' has no independent meaning, covered by base form card.")
            return base_filepath

        has_meaning, data = self.has_independent_meaning(word)
        if has_meaning:
            canon = self.canonical_word(data, word)
            print(f"  Found '{canon}' in dictionary")
            wd = self.parse_word_data(data, canon)
            md = self.generate_markdown(wd, tags, input_word=word)
            return self.save_card(canon, md)

        found_base, base_data = self.try_base_forms(word)
        if found_base:
            canon = self.canonical_word(base_data, found_base)
            print(f"  ✓ Found base form: '{canon}'")
            wd = self.parse_word_data(base_data, canon)
            md = self.generate_markdown(wd, tags, input_word=word)
            return self.save_card(canon, md)

        print(f"  No dictionary entry found, creating template card...")
        self.suggest_similar(word)
        md = self.create_template_card(word, tags)
        return self.save_card(word, md)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate Obsidian vocabulary cards with smart base-form detection.",
        epilog="Tags must be passed with -t/--tags. Multiple positional words are joined "
               "into a hyphenated phrase (e.g. `vocab hash map` -> hash-map.md).",
    )
    parser.add_argument("word", nargs="+", help="Word or phrase to look up")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: script dir)")
    parser.add_argument("-t", "--tags", nargs="+", help="Additional tags for the card")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--force", action="store_true", help="Overwrite an existing card")
    group.add_argument("--merge", action="store_true",
                       help="Regenerate dictionary fields but keep manual 'My examples' and '中文释义'")
    parser.add_argument("--no-related", action="store_true", help="Skip related-form Wiki Link discovery")
    parser.add_argument("--open", dest="open_card", action="store_true",
                        help="After saving, jump to the card (Obsidian deep link if configured)")
    parser.add_argument("--vault-root", default=None,
                        help="Vault root folder, used with --open (or env VOCAB_OBSIDIAN_ROOT)")
    parser.add_argument("--vault-name", default=None,
                        help="Vault display name, used with --open (or env VOCAB_OBSIDIAN_VAULT)")

    args = parser.parse_args(argv)

    ensure_utf8_streams()

    if requests is None:
        print("Error: the 'requests' package is required. Install it with: pip install -r requirements.txt",
              file=sys.stderr)
        sys.exit(2)

    word = "-".join(args.word)
    if len(args.word) > 1:
        print(f"Note: treating multiple arguments as the phrase '{word}'. Use -t/--tags for tags.")

    overwrite = 'force' if args.force else ('merge' if args.merge else 'skip')
    output = args.output or str(Path(__file__).parent)

    generator = VocabCardGenerator(output_dir=output, overwrite=overwrite,
                                   include_related=not args.no_related,
                                   vault_root=args.vault_root, vault_name=args.vault_name)
    filepath = generator.create_card(word=word, tags=args.tags)

    if filepath:
        print(f"\nDone! Card at: {filepath}")
        if args.open_card:
            generator.open_file(filepath)
    else:
        print("\nFailed to create vocabulary card.")
        sys.exit(1)


if __name__ == "__main__":
    main()
