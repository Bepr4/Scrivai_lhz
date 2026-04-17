---
name: inspect-document
description: |
  Use when you have a chunk_id (typically from a library search hit) and need to
  read the original document context around it — the full markdown of the chunk,
  surrounding metadata, or the parent document. Trigger this any time you want
  to verify whether a search hit is actually on-topic before citing it.
---

# Inspect Document

When a search returns a chunk_id and the snippet alone is not enough
context to judge relevance, fetch the full chunk to see the surrounding text.

## When to use

- A `library search` hit looks promising but the snippet is truncated
- You need to verify a quote is faithful to the source before citing it
- You want to see the chunk's metadata (e.g. which document / section it
  came from) before using it as evidence

## How

```bash
qmd document get --collection <name> --id <chunk_id>
```

Returns:
```json
{ "id": "...", "markdown": "...full chunk text...", "metadata": {...}, "chunk_count": 1 }
```

The `metadata` typically includes the source document name, section, or
other locator the original ingestion pipeline put there.

## Why this matters

A search hit's snippet may be truncated or surrounded by qualifiers that
flip its meaning. Always fetch the full chunk before using a snippet as
the basis for a verdict — especially "negative" findings ("rule X
prohibits Y") where context can invert the conclusion.
