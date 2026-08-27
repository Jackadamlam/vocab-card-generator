# Vocabulary Card Generator for Obsidian

Generate bilingual-ready, Obsidian-formatted vocabulary cards from the free
[Free Dictionary API](https://dictionaryapi.dev/). Type a word, get a clean
Markdown note with pronunciation, definitions, examples, verified word forms,
and Wiki Links to related words — ready to drop into your vault.

自动从免费词典 API 生成 Obsidian 词汇卡片：发音、释义、例句、经校验的词形变化，以及指向相关词的 Wiki 链接。

## Highlights / 功能特点

- **Dictionary lookup** — pronunciation, definitions, examples, synonyms, antonyms.
- **Smart base-form detection** — `embedded` → `embed`, `running` → `run`,
  `cities` → `city`, `arisen` → `arise`. Derived forms link back via a
  `base_form:` field; if the derived form has its own meaning it also gets a card.
- **Verified word forms** — plurals, tenses, comparatives are only written when
  the dictionary confirms them (no more fabricated `neuraller`).
- **Related Forms as Wiki Links** — `educate` links `[[education]]`, `[[educator]]`, …
- **Safe by default** — never overwrites an existing card. Use `--force` to replace
  or `--merge` to refresh dictionary fields while keeping your hand-written
  `My examples` bullets and trailing `中文释义` section.
- **Global command** — install once, then run `vocab <word>` from anywhere.

> Note: the generator does **not** auto-translate. The upstream API is
> English-only, so the `中文释义` section is something you add yourself;
> `--merge` preserves it across regenerations.

## Requirements / 依赖

- Python 3.8+
- `requests`

```bash
pip install -r requirements.txt
```

## Installation / 安装

### Windows (global `vocab` command)

1. Put this folder wherever you like (e.g. inside your vault):
   ```text
   D:\Obsidian Vault\EN_Learning\EN_Words\
   ```
2. Open PowerShell and run:
   ```powershell
   cd "D:\Obsidian Vault\EN_Learning\EN_Words"
   .\setup_vocab.ps1
   ```
3. Restart your terminal, then use `vocab` from any directory.

The setup script uses `$PSScriptRoot`, so it works no matter where the folder lives.

### Any OS (without PATH setup)

```bash
python vocab_card_generator.py embedding
```

## Usage / 用法

```bash
# Basic — creates embed.md in the tool folder
vocab embed

# Add tags (tags MUST follow -t)
vocab tokenizer -t ML LLM

# Multi-word phrase (joined with a hyphen -> hash-map.md)
vocab hash map

# Write cards into a specific folder
vocab algorithm -o "C:\Vault\Words"

# Refresh an existing card but keep your manual notes
vocab embed --merge

# Overwrite unconditionally
vocab embed --force

# Skip related-form discovery (fewer network calls)
vocab embed --no-related
```

> ⚠️ Tags require `-t`. `vocab tokenizer ML LLM` (without `-t`) is treated as the
> single phrase `tokenizer-ML-LLM`, not three tags.

### Options

| Flag | Meaning |
| --- | --- |
| `-o, --output DIR` | Output directory (default: the script's folder) |
| `-t, --tags A B C` | Extra tags for the card |
| `--force` | Overwrite an existing card |
| `--merge` | Regenerate dictionary fields, preserve manual sections |
| `--no-related` | Disable related-form Wiki Link discovery |
| `-h, --help` | Show help |

## Card structure / 卡片结构

A generated card looks like:

```markdown
---
word: host
pronunciation: /həʊst/
part_of_speech: noun, verb
date_added: 2026-08-27
plural: hosts
third_person: hosts
present_participle: hosting
past_tense: hosted
past_participle: hosted
tags: [noun, verb]
---

### Definition
#### Noun
1. One which receives or entertains a guest …

### Word Forms
- `hosts` (plural)
…

### Related Forms
- [[hostel]]
…

### Usage Notes
**Examples:**
- …
**My examples:**
- _Write your own sentence here:_
```

See [`examples/`](./examples) for sample output.

## File layout / 文件结构

```text
vocab_card_generator.py      # main program
vocab.bat                    # Windows command wrapper
setup_vocab.ps1              # one-time PATH + dependency check
requirements.txt             # Python dependencies
test_vocab_card_generator.py # offline unit tests (no network)
examples/                    # sample generated cards
```

## Tests / 测试

```bash
python -m unittest test_vocab_card_generator -v
```

The tests stub out all network access, so they run offline and fast.

## Troubleshooting / 故障排除

- **Command not found** — run `setup_vocab.ps1` and restart the terminal.
- **Word not found** — some technical terms aren't in the free dictionary; try the
  base form (`tokenize` instead of `tokenizer`).
- **Slow / intermittent failures** — the free API is rate-limited and occasionally
  slow. The tool caches lookups per run and caps total requests; re-run if a card
  looks incomplete, or pass `--no-related` to reduce calls.

## License

MIT — see [LICENSE](./LICENSE).
