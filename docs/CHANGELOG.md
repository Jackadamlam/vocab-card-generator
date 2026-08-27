# Changelog

All notable changes to the Vocabulary Card Generator are documented here.
This project follows a simple versioning scheme; the current major rewrite is **v2.0**.

## v2.2 — 2026-08-27 (latency)
- **Circuit breaker for the flaky free API**: the first request timeout marks the
  API dead for the rest of the run instead of stalling every later probe.
- **`VOCAB_OBSIDIAN_DELAY` env var** — hands the Obsidian deep link to a detached
  micro-helper so the generator exits instantly and Listary's window closes
  without waiting for Obsidian's cold start.
- Listary recipe now recommends `--no-related` (skips ~12 extra probes/card);
  measured typical jump: 40–90 s → 3–7 s.

## v2.1 — 2026-08-27

## v2.0 — 2026-08-27

A correctness, safety and honesty overhaul after a full code review.

### Fixed (P0)
- **No more silent data loss.** `save_card()` no longer overwrites an existing
  card by default. Existing cards are *skipped*; add `--force` to replace or
  `--merge` to refresh dictionary fields while preserving hand-written
  `My examples` bullets and the trailing `中文释义` section.
- **CLI tags fixed.** Tags now require `-t/--tags`. Previously
  `vocab tokenizer ML LLM` silently produced a single hyphenated word
  `tokenizer-ML-LLM`; multiple positional words are still joined into a phrase
  but this is now announced clearly.
- **Canonical spelling.** Headwords are normalized to the dictionary's form, so
  input `Estimated` yields `estimate.md` instead of capitalized files.
- **Bad comparatives eliminated.** Multi-syllable / non-gradable adjectives no
  longer get fabricated forms like `neuraller` / `neurallest`.
- **Irregular-verb ambiguity resolved.** The reverse lookup maps each surface to
  a *list* of bases and is skipped when the word is itself a base verb, so
  `lay` is no longer mis-resolved to `lie`.
- **Windows console crash fixed.** Status output is forced to UTF-8, so the tool
  no longer aborts on `✓`/IPA glyphs under legacy GBK/cp936 code pages.

### Added
- **`--open` deep link** — after saving, jump straight to the card in Obsidian
  (via `obsidian://open`, configured with `--vault-root/--vault-name` or the
  `VOCAB_OBSIDIAN_ROOT`/`VOCAB_OBSIDIAN_VAULT` env vars). Pairs with Listary
  custom commands for a zero-terminal workflow; documented in README.
- **Related Forms as Wiki Links** (`educate` → `[[education]]`, `[[educator]]`) —
  previously advertised in the README but never implemented. Toggle with
  `--no-related`.
- **Request caching + a per-run request budget** and a shorter timeout to keep
  runs fast against the rate-limited free API.
- **Did-you-mean suggestions** for unknown words.
- `requirements.txt`, offline unit tests, MIT `LICENSE`, `.gitignore`, and
  curated `examples/`.

### Changed
- `setup_vocab.ps1` uses `$PSScriptRoot` (portable) and verifies Python +
  `requests` before touching PATH.
- `vocab.bat` checks that `python` exists and fails with a clear message.
- README rewritten to match actual behavior and render well on GitHub.

## v1.x — initial release
- Original generator: dictionary lookup, base-form detection, verified word
  forms, Obsidian Markdown output, global `vocab` command.
