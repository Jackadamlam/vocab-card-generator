#!/usr/bin/env python3
"""Offline unit tests for vocab_card_generator.

These tests never touch the network: they exercise the pure helpers and use a
stubbed ``fetch_word_data`` to drive morphology/related-form logic.

Run with:  python -m unittest test_vocab_card_generator -v
"""

import os
import tempfile
import unittest
from pathlib import Path

import vocab_card_generator as v


class TestSyllables(unittest.TestCase):
    def test_basic_counts(self):
        self.assertEqual(v.estimate_syllables("cat"), 1)
        self.assertEqual(v.estimate_syllables("table"), 2)   # ta-ble, silent e
        self.assertEqual(v.estimate_syllables("neural"), 2)
        self.assertEqual(v.estimate_syllables("beautiful"), 3)

    def test_multisyllable_adjective_guard(self):
        # "neural" ends in -al -> should NOT take -er/-est (avoids "neuraller")
        self.assertTrue(v.is_likely_multisyllable_adjective("neural"))
        self.assertTrue(v.is_likely_multisyllable_adjective("explicit"))
        # short gradable adjectives still allowed
        self.assertFalse(v.is_likely_multisyllable_adjective("big"))
        self.assertFalse(v.is_likely_multisyllable_adjective("happy"))


class TestIrregularReverse(unittest.TestCase):
    def test_values_are_lists(self):
        for surface, bases in v.IRREGULAR_REVERSE.items():
            self.assertIsInstance(bases, list, msg=surface)

    def test_lay_is_a_base_verb_not_resolved_to_lie(self):
        # "lay" is itself a base verb AND the past tense of "lie".
        # find_base_forms must not offer "lie" as its base.
        gen = v.VocabCardGenerator(output_dir=tempfile.mkdtemp())
        self.assertNotIn("lie", gen.find_base_forms("lay"))

    def test_past_participle_resolves(self):
        gen = v.VocabCardGenerator(output_dir=tempfile.mkdtemp())
        self.assertIn("arise", gen.find_base_forms("arisen"))
        self.assertIn("write", gen.find_base_forms("written"))


class TestFindBaseForms(unittest.TestCase):
    def setUp(self):
        self.gen = v.VocabCardGenerator(output_dir=tempfile.mkdtemp())

    def test_ed_double_consonant(self):
        self.assertIn("embed", self.gen.find_base_forms("embedded"))

    def test_ing_double_consonant(self):
        self.assertIn("run", self.gen.find_base_forms("running"))

    def test_plural_y(self):
        self.assertIn("city", self.gen.find_base_forms("cities"))

    def test_no_self_candidate(self):
        for cand in self.gen.find_base_forms("walked"):
            self.assertNotEqual(cand, "walked")


class TestCanonicalWord(unittest.TestCase):
    def test_prefers_dictionary_headword(self):
        data = [{"word": "estimate", "meanings": []}]
        self.assertEqual(v.VocabCardGenerator.canonical_word(data, "Estimate"), "estimate")

    def test_fallback_when_missing(self):
        self.assertEqual(v.VocabCardGenerator.canonical_word(None, "Foo"), "Foo")


class TestMergeHelpers(unittest.TestCase):
    def test_extract_chinese_section(self):
        md = "---\nword: x\n---\n\n### Usage Notes\n\nbody\n\n---\n\n### 中文释义\n\n动词：嵌入\n"
        tail = v.extract_chinese_section(md)
        self.assertTrue(tail.startswith("### 中文释义"))
        self.assertIn("嵌入", tail)

    def test_extract_my_examples_skips_placeholder(self):
        md = "**My examples:**\n\n- _Write your own sentence here:_\n\n---\n"
        self.assertEqual(v.extract_my_example_bullets(md), [])
        md2 = "**My examples:**\n\n- I embedded the chart.\n- second line\n\n---\n"
        self.assertEqual(v.extract_my_example_bullets(md2),
                         ["I embedded the chart.", "second line"])

    def test_merge_preserves_manual_content(self):
        generated = ("---\nword: embed\n---\n\n### Usage Notes\n\n"
                     "**My examples:**\n\n- _Write your own sentence here:_\n\n")
        old = ("---\nword: embed\n---\n\n**My examples:**\n\n- my sentence\n\n"
               "---\n\n### 中文释义\n\n嵌入\n")
        merged = v.merge_manual_into_generated(generated, old)
        self.assertIn("- my sentence", merged)
        self.assertIn("### 中文释义", merged)
        self.assertNotIn("_Write your own sentence here:_", merged)


class TestFormGenerationStubbed(unittest.TestCase):
    """Drive generate_word_forms / discover_related via a fake dictionary."""

    def make_gen(self, known_words):
        gen = v.VocabCardGenerator(output_dir=tempfile.mkdtemp(), include_related=True)
        known = {w.lower() for w in known_words}
        gen.fetch_word_data = lambda w: ([{"word": w, "meanings": []}] if w.lower() in known else None)
        return gen

    def test_neural_gets_no_bad_comparative(self):
        gen = self.make_gen({"neural"})
        forms = gen.generate_word_forms("neural", ["adjective"])
        self.assertNotIn("comparative", forms)
        self.assertNotIn("superlative", forms)

    def test_big_gets_comparative(self):
        gen = self.make_gen({"bigger", "biggest"})
        forms = gen.generate_word_forms("big", ["adjective"])
        self.assertEqual(forms.get("comparative"), "bigger")
        self.assertEqual(forms.get("superlative"), "biggest")

    def test_related_forms_discovered_and_linked(self):
        gen = self.make_gen({"educate", "education", "educator", "educational"})
        related = gen.discover_related_forms("educate", ["verb"], exclude=set())
        self.assertIn("education", related)
        self.assertIn("educator", related)

    def test_markdown_contains_wiki_links(self):
        gen = self.make_gen({"host", "hosts", "hosting", "hosted", "hostel"})
        wd = {"word": "host", "phonetics": ["/həʊst/"],
              "meanings": [{"partOfSpeech": "noun",
                            "definitions": [{"definition": "a host", "example": "",
                                             "synonyms": [], "antonyms": []}]}]}
        md = gen.generate_markdown(wd, tags=None, input_word="host")
        self.assertIn("### Word Forms", md)
        self.assertIn("plural: hosts", md)  # YAML field present


class TestObsidianUri(unittest.TestCase):
    def test_relative_path_and_encoding(self):
        root = Path(tempfile.mkdtemp())
        card = (root / "EN_Learning" / "EN_Words" / "embed.md")
        card.parent.mkdir(parents=True)
        card.write_text("---\nword: embed\n---\n", encoding="utf-8")
        uri = v.build_obsidian_uri(card, root, "My Vault")
        self.assertTrue(uri.startswith("obsidian://open?vault=My%20Vault&file="))
        self.assertIn("EN_Learning/EN_Words/embed", uri)
        self.assertNotIn(".md", uri.split("file=", 1)[1])

    def test_returns_none_without_vault_info(self):
        self.assertIsNone(v.build_obsidian_uri("/tmp/x.md", None, "V"))
        self.assertIsNone(v.build_obsidian_uri("/tmp/x.md", "/tmp", None))

    def test_returns_none_when_outside_vault(self):
        root = Path(tempfile.mkdtemp())
        outside = Path(tempfile.mkdtemp()) / "elsewhere.md"
        outside.write_text("x", encoding="utf-8")
        self.assertIsNone(v.build_obsidian_uri(outside, root, "Vault"))


class TestDelayedOpen(unittest.TestCase):
    """VOCAB_OBSIDIAN_DELAY must hand the launch to a detached helper and return fast."""

    def setUp(self):
        import unittest.mock as m
        self._env = m.patch.dict(os.environ, {"VOCAB_OBSIDIAN_DELAY": "400"})
        self._pop = m.patch.object(v.subprocess, "Popen")
        self.env = self._env.start()
        self.popen = self._pop.start()
        self.addCleanup(lambda: (self._env.stop(), self._pop.stop()))

    def test_delay_spawns_helper_and_skips_blocking_startfile(self):
        import unittest.mock as m
        gen = v.VocabCardGenerator(output_dir=tempfile.mkdtemp(),
                                   vault_root=str(Path.cwd()), vault_name="Vault")
        with m.patch.object(v.os, "startfile") as startfile:
            target = gen.open_file(Path.cwd() / "embed.md")
        self.assertIsNotNone(target)
        self.assertEqual(self.popen.call_count, 1)
        argv = self.popen.call_args[0][0]
        self.assertTrue(argv[0].endswith("pythonw.exe"))
        self.assertIn("time.sleep(0.400)", argv[2])
        self.assertIn("obsidian://open", argv[2])
        startfile.assert_not_called()  # nothing blocking in this process

    def test_no_delay_uses_direct_startfile(self):
        import unittest.mock as m
        gen = v.VocabCardGenerator(output_dir=tempfile.mkdtemp(),
                                   vault_root=str(Path.cwd()), vault_name="Vault")
        with m.patch.dict(os.environ, {}, clear=True), m.patch.object(v.os, "startfile") as startfile:
            gen.open_file(Path.cwd() / "embed.md")
        self.assertEqual(self.popen.call_count, 0)
        startfile.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
