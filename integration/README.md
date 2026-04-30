# Integration

> Shared workspace for multi-agent feature planning and cross-AI collaboration.

This folder is a **buffer between AI agents**. Use it to write plans, proposals, and implementation notes before touching any code.

---

## When to use this folder

- Planning a feature that spans backend + frontend
- Getting a second agent to review an implementation plan
- Leaving context for another agent to continue your work
- Documenting decisions made during a planning session

## File naming

```
{feature-name}.plan.md       ← implementation plan
{feature-name}.proposal.md   ← idea/RFC not yet decided
{feature-name}.notes.md      ← scratch notes, findings
{feature-name}.review.md     ← review output from another agent
```

Examples:
```
pdf-export-redesign.plan.md
custom-sections-v2.proposal.md
llm-retry-logic.notes.md
```

## Plan template

See [_template.plan.md](./_template.plan.md).

## Rules

- Write in **English**
- One file per feature
- **Delete the file when the feature is fully implemented** — these are temporary working files
- Do not put code here, only plans and notes
- This folder is local only — it is gitignored
