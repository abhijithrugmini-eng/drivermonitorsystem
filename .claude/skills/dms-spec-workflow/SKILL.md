---
name: dms-spec-workflow
description: >-
  Top-level process skill for implementing ANY feature or story in this
  repo — enforces a spec-driven cycle (explore, design, propose, apply,
  review, release, archive), modeled on OpenSpec
  (github.com/Fission-AI/openspec), with proposals tracked under
  dms-spec/changes/ and living specs under dms-spec/specs/. Use this
  whenever the user asks to build/add/implement a feature or story, start
  a change, write a proposal, or wants "the process" followed instead of
  jumping straight to code. Triggers on requests like "implement feature
  X", "let's add Y", "start a change for Z", "write a proposal for",
  "let's design this properly", "what's the status of this change",
  "release this change", "archive this change", or any multi-step feature
  work spanning more than a trivial edit.
---

# DMS Spec Workflow — Explore → Design → Propose → Apply → Review → Release → Archive

This is the parent **process** skill for the whole repo — it governs *how* any non-trivial feature/story gets built, the same way `.claude/skills/dms-agentic-architecture/SKILL.md` governs *how* agents are structured. Modeled on [OpenSpec](https://github.com/Fission-AI/openspec)'s spec-driven workflow (`explore → propose → apply → archive`, changes as folders with `proposal.md`/`design.md`/`tasks.md`, a living `specs/` directory), adapted with two extra stages this POC needs: an explicit **Design** step before proposing (technical approach gets written down, not just implied), and a **Release** step after apply/review (because this is a POC being demoed, not a versioned product — every shipped change needs a record of what it does and exactly how to run it).

## When this applies

- Any feature/story request that's more than a trivial edit (a typo, a one-line config change, a copy fix) — those, just do directly. This mirrors OpenSpec's own "fluid not rigid" philosophy: the cycle serves the work, not the other way around.
- Component-specific technical detail still comes from the relevant `dms-*-dev` skill or `dms-agentic-architecture` — this skill governs the *process* around that work, not component internals.
- If the user already knows exactly what they want and just wants it built, it's fine to move through Explore/Design quickly (even collapse them into one short pass) — don't manufacture ceremony for its own sake. But still leave the artifacts: they're cheap to write and are what makes Release/Archive possible later.

## The `dms-spec/` folder

```
dms-spec/
├── specs/                        # living, canonical specs — current state of the system, one folder per capability
│   └── <capability>/spec.md      # SHALL-requirement + Scenario format — see specs/violation-detection/spec.md for a real example
├── changes/                      # in-flight change proposals
│   └── <change-id>/              # kebab-case, verb-led: add-fleet-simulator, fix-alarm-ack-race
│       ├── explore.md
│       ├── proposal.md
│       ├── design.md
│       ├── tasks.md
│       ├── review.md
│       └── release.md            # generated — see "Release" below, don't hand-write this
│   └── archive/
│       └── YYYY-MM-DD-<change-id>/   # moved here at Archive
├── templates/                    # copy these when starting a new change
│   ├── explore.md
│   ├── proposal.md
│   ├── design.md
│   ├── tasks.md
│   └── review.md
└── scripts/
    └── generate_release.py       # the release hook script — see "Release" below
```

## The seven stages

### 1. Explore

No commitment yet — a no-stakes look at the problem before anything is written in stone. Read relevant code, `dms-spec/specs/*`, and the applicable `dms-*-dev`/`dms-agentic-architecture` skill(s); weigh options; surface real forks to the user via `AskUserQuestion` (not to rubber-stamp a foregone conclusion).

**Output**: `dms-spec/changes/<change-id>/explore.md` (create the change folder now, from `dms-spec/templates/`).
**Exit**: the user is aligned on a direction, even a rough one.

### 2. Design

The technical approach, written down before code. If the change touches an agent (edge or backend), it must align with `dms-agentic-architecture`'s `BaseAgent` contract and name things after the drawio boxes — don't invent a parallel structure.

**Output**: `design.md` — approach, architecture/flow (include a Mermaid diagram if there's non-trivial data/control flow; **Release reuses it verbatim**), files touched, data/API contract changes.
**Exit**: someone else could implement from this without guessing.

### 3. Propose

The commitment gate, and where the "story" (not just the technical plan) gets written down: why, for whom, what's in/out of scope, acceptance criteria.

**Output**: `proposal.md` (Problem/Why, Story — "as a `<role>` I want `<capability>` so that `<benefit>`", Scope, Non-goals, Acceptance criteria, affected `dms-spec/specs/*` capabilities) + `tasks.md` (numbered checklist grouped by area, OpenSpec-style `- [ ] 1.1 ...`).
**Exit**: for substantial changes, this is a real approval gate — use the `ExitPlanMode`/plan-mode workflow here rather than inventing separate approval mechanics; `proposal.md` + `tasks.md` become the durable record of what got approved, plan-mode approval is the interactive moment itself.

### 4. Apply

Implement. Use `TodoWrite` for in-session progress as usual, but `tasks.md` is the durable record — flip its checkboxes as items land, and only ever mark one `[x]` once it's actually verified working (run it, don't just typecheck — same bar as everywhere else in this repo).

**Output**: code changes + an accurate `tasks.md`.
**Exit**: every task checked, working code, verified per this repo's normal bar.

### 5. Review

Catch what Apply missed. A self-review pass or a `/code-review` run against the change's diff — either is fine for a POC-scale change; use judgment on how much rigor a given change warrants.

**Output**: `review.md` — findings, and what was fixed vs. accepted as-is vs. deferred (with why).
**Exit**: no open findings above the bar the user cares about for this change.

### 6. Release

Capture what shipped, and — because this is a POC being demoed rather than a versioned product with its own release process — make sure a stranger (including future-you) could actually run the result from this file alone.

**Output**: `release.md`, generated by `dms-spec/scripts/generate_release.py`, wired as a Claude Code `Stop` hook (see `.claude/settings.json`) so it regenerates automatically once a change's `tasks.md` is fully checked off. It contains an implementation summary, a change-flow Mermaid diagram, and exact run/Docker commands. The script is deterministic and dependency-free on purpose — **hooks are plain scripts, not model calls** — so it builds a scaffold (task summary from checked items, commands pulled straight out of each touched component's own README so they can't drift, the `design.md` diagram if there is one) rather than writing prose. **After it runs, polish the Implementation Summary prose by hand** — don't ship the raw mechanical bullet list as the final word. Run it manually any time: `python3 dms-spec/scripts/generate_release.py [change-id] [--force]`.

**Exit**: `release.md` exists, its prose has been reviewed/polished, and its run commands actually work (spot-check them, don't just trust the extraction).

### 7. Archive

Close the loop; fold what shipped into the living spec so `dms-spec/specs/` never goes stale.

**Actions**:
1. Update `dms-spec/specs/<capability>/spec.md` — add/modify/remove `### Requirement:` blocks to match what actually shipped (not what was originally proposed, if they diverged).
2. Move the whole change folder to `dms-spec/changes/archive/YYYY-MM-DD-<change-id>/`.

**Exit**: `dms-spec/changes/` (excluding `archive/`) has no trace of the completed change; `dms-spec/specs/` reflects reality.

## Spec format (`dms-spec/specs/*/spec.md`)

Plain Markdown, OpenSpec-style, no special syntax to learn:

```markdown
### Requirement: <name>
The system SHALL <behavior>.

#### Scenario: <case>
- **WHEN** <trigger>
- **THEN** <expected outcome>
```

`dms-spec/specs/violation-detection/spec.md` is a real, already-written example (documents `dms-backend`'s actual rule engine, including the "growing violations" behavior) — read it as the template, not the empty ones in `templates/`.

## The release hook

`dms-spec/scripts/generate_release.py` runs as a Claude Code `Stop` hook — after each turn, it scans `dms-spec/changes/*/` for any change whose `tasks.md` is fully checked off and whose `release.md` is missing or older than `tasks.md`, and regenerates it. It:

1. Parses `tasks.md`'s checked items into an Implementation Summary skeleton.
2. Reuses `design.md`'s Mermaid diagram for Change Flow if present, otherwise derives a minimal one from which components (`dms-backend`/`dms-ui`/`dms-edge`/`fleet-simulator`) the change's `git diff` touched.
3. Extracts the "Run" section straight out of each touched component's own `README.md` (and the root `README.md`'s Docker section, if `docker-compose.yml` exists) — so the commands in `release.md` can never drift from what those READMEs actually say. If a README's Run section changes shape and extraction comes up empty, the script says so explicitly rather than guessing.

It's silent/no-op if no change is ready (nothing to do most turns). Flags: `--force` (regenerate even if it looks current), `--check` (dry run, exit 1 if anything would change — useful for CI or a pre-flight check).

## When starting any feature request

1. Trivial edit → just do it, no ceremony.
2. Otherwise, check `dms-spec/changes/` for an existing in-flight folder for this work before creating a new one.
3. Copy `dms-spec/templates/*.md` into a new `dms-spec/changes/<change-id>/` and start at Explore (or later, if the user already knows what they want).
4. Pull component-specific technical detail from the relevant `dms-*-dev`/`dms-agentic-architecture` skill during Design/Apply — this skill governs the cycle, those govern the components.
