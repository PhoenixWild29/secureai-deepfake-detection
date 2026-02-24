# AGENTS.md

## Cursor Cloud specific instructions

### Repository overview

This repository is a **documentation-only** project describing the SecureAI DeepFake Detection system. It currently contains only markdown files:

- `README.md` — Product description, architecture, and aspirational project structure
- `design/morpheus_fl_hybrid_design.md` — Morpheus + Federated Learning hybrid design document

**There is no source code, no dependency manifests (`requirements.txt`, `package.json`, etc.), no configuration files, and no applications to build or run.**

The README describes an intended multi-component system (Python/Flask API, React frontend, Solana blockchain, etc.), but none of this has been implemented yet.

### Linting

Markdown files can be linted with `markdownlint`:

```bash
markdownlint '**/*.md'
```

`markdownlint-cli` is installed globally via npm. The existing markdown files have known lint warnings (line length, heading spacing, trailing punctuation) that are part of the upstream content.

### Testing and building

There are no automated tests, build steps, or runnable applications in this repository. Future agents should check whether source code has been added before attempting to run tests or start services.

### Git branches

- `main` — primary branch
- `master` — legacy branch (merged into main)
- `gh-pages` — GitHub Pages deployment
