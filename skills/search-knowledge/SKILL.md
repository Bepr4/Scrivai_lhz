---
name: search-knowledge
description: |
  Use when you need to find supporting evidence from the rules/cases/templates
  knowledge bases — laws, regulations, historical reviewed documents, or
  templates. Trigger this any time you are about to assert a verdict, cite a
  rule, or back a finding with evidence. Skipping this step almost always leads
  to ungrounded outputs and missing chunk_ids in the final report.
---

# Search Knowledge

When you are reasoning about a task — judging whether a clause is compliant,
deciding which template fits, or finding precedent — pull supporting material
from the knowledge libraries before you write the conclusion.

## When to use

- About to write a verdict, judgement, or assertion that should be backed
  by a rule or precedent
- About to compose text that should match an existing case or template
- The current document references a regulation you have not yet looked up

## How

```bash
scrivai-cli library search --type rules --query "<focused query>" --top-k 5
```

Pick the `--type` that matches what you need:

- `rules` — laws, regulations, technical standards
- `cases` — historical reviewed documents (gold-standard examples)
- `templates` — boilerplate / structural templates

## Why this matters

Two reasons:

1. **Grounded output** — every claim should trace back to a source chunk
   so a reviewer can verify it.
2. **Better recall on first attempt** — phrasing the same query 2–3
   different ways increases the chance of finding the actual relevant
   material. Don't accept zero hits as the final answer; rephrase.

## After getting hits

Each hit comes with a `chunk_id`. **Always include the `chunk_id` when
you cite the snippet** — downstream tools and human reviewers use it to
re-locate the source. If you need the chunk's surrounding context, use
the `inspect-document` skill.
