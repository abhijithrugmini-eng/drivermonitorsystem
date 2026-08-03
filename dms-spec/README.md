# dms-spec

Spec-driven change tracking for this repo, modeled on [OpenSpec](https://github.com/Fission-AI/openspec) and adapted for a POC. See `.claude/skills/dms-spec-workflow/SKILL.md` for the full process — this file is just the folder map.

```
dms-spec/
├── specs/            # living, canonical specs — one folder per capability, current state of the system
├── changes/          # in-flight change proposals, one folder per feature/story
│   └── archive/      # completed changes, moved here at the Archive stage
├── templates/        # copy into a new dms-spec/changes/<change-id>/ when starting a change
└── scripts/
    └── generate_release.py   # hook script that scaffolds each change's release.md
```

Cycle: **explore → design → propose → apply → review → release → archive**. Don't hand-write `release.md` — it's generated (and kept fresh by a `Stop` hook) by `scripts/generate_release.py`.
