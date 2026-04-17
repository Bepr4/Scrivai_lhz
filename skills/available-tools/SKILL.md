---
name: available-tools
description: |
  The authoritative reference for all CLI commands available to the agent during
  document audit/generation tasks. Use this whenever you are about to call a
  scrivai-cli or qmd command from Bash, especially in the execute phase. Reading
  this prevents prompt drift, ensures correct flag names, and tells you the exact
  JSON shape to expect back.
---

# Available Tools

This skill is the **command manifest** for the agent. Whenever you are
about to invoke a CLI command from `Bash`, read the relevant section
below to confirm the correct flags and the JSON shape you should expect.

The two command families exposed to the agent are:

1. `scrivai-cli library` — knowledge library lookup (rules / cases / templates)
2. `qmd` — direct semantic search against any qmd collection

The agent **does not** invoke `scrivai-cli workspace` or `scrivai-cli
trajectory` — those are managed by the calling business layer.

---

## scrivai-cli library

All `library` subcommands accept `--type {rules|cases|templates}` to pick the
collection.

### library search

```
scrivai-cli library search --type rules --query "<query>" [--top-k 5] [--filters '{}']
```

Output:
```json
{
  "hits": [
    { "chunk_id": "...", "score": 0.83, "text": "...", "metadata": {} }
  ]
}
```

Error → stderr `{"error": "..."}` + exit 1.

### library get

```
scrivai-cli library get --type rules --entry-id <id>
```

Output:
```json
{ "entry_id": "rule-001", "markdown": "...", "metadata": {} }
```

Returns error if `entry-id` does not exist.

### library list

```
scrivai-cli library list --type rules
```

Output:
```json
{ "entry_ids": ["rule-001", "rule-002"] }
```

---

## qmd

For raw semantic search against any qmd collection (when the library
abstraction is not what you need):

```
qmd search --collection <name> --query "<q>" [--top-k 5] [--rerank]
qmd document get --collection <name> --id <chunk_id>
qmd document list --collection <name>
qmd collection info --name <name>
qmd collection list
```

`qmd document get` returns the full chunk including original markdown and
metadata — useful when you need to see the source context behind a search hit.

---

## Common patterns

- After a `library search` returns a hit, capture its `chunk_id` and use
  `qmd document get` if you need to read the surrounding context before
  using the snippet as evidence.
- Every command writes JSON to stdout on success and JSON to stderr on
  failure. Always check the exit code; a non-zero exit means stderr has
  the structured error.
