---
name: render-output
description: |
  Use when you are constructing a context dictionary that will eventually be
  fed to docxtpl to render a final .docx report. Triggers any time the task is
  about template-driven document generation, especially in the summarize phase
  of a GeneratorPES, or whenever you see {{ placeholder }} markers in a template
  and need to know how to fill them.
---

# Render Output

When the task is to fill a docxtpl template with structured content, the
schema of the context dict is the contract between you (the agent) and
the template. Get this right or the renderer will silently produce empty
fields.

## When to use

- The task is to fill a template (`.docx` with `{{ ... }}` markers)
- You see `placeholders` keys in the phase context — those are the
  template variables you must supply
- You are writing `output.json` whose contents will be passed to a
  renderer downstream

## docxtpl context conventions

A typical template context looks like:

```json
{
  "project_name": "X变电站升级改造",
  "author": "张三",
  "sections": [
    { "title": "概述", "body": "..." },
    { "title": "范围", "body": "..." }
  ]
}
```

Rules:

- Top-level keys map to `{{ key }}` placeholders in the template
- Lists map to `{% for item in items %}...{% endfor %}` loops; each item
  is a dict whose keys are then accessed inside the loop body
- Plain strings are inserted as text — markdown formatting in them is
  **not** interpreted by docxtpl

## Why this matters

docxtpl silently renders missing keys as empty strings — there is no
"key not found" error at render time. The only way to catch a mismatch
is to verify your context dict covers exactly the placeholders the
template advertises (run `scrivai-cli io render` outside of an agent run
if you want to test interactively).

## Tips

- If the template has a placeholder you do not have data for, write
  `null` or `""` rather than omitting the key — makes the gap visible
  in the rendered output instead of producing an empty section that
  looks intentional
- Avoid putting complex markdown (headings, tables) inside placeholder
  values; build the structure in the template, not the data
