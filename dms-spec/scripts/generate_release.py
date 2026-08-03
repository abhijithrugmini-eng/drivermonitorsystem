#!/usr/bin/env python3
"""dms-spec release generator.

Runs as a Claude Code `Stop` hook (see .claude/settings.json) after every turn.
Deterministic and dependency-free (stdlib only) on purpose — this is a plain
script, not an LLM call. For any change under dms-spec/changes/ whose tasks.md
is fully checked off and whose release.md is missing or stale, it (re)builds a
scaffold: an implementation summary from completed tasks.md items, a Mermaid
change-flow diagram (reused from design.md if present), and exact run/Docker
commands pulled straight out of the touched components' own READMEs. See the
dms-spec-workflow skill's "Release" stage for how the scaffold gets polished
by hand afterward — this script writes structure, not prose.

Usage:
    python3 dms-spec/scripts/generate_release.py                # scan all changes
    python3 dms-spec/scripts/generate_release.py <change-id>    # only this change
    python3 dms-spec/scripts/generate_release.py --force        # regenerate even if release.md looks current
    python3 dms-spec/scripts/generate_release.py --check        # dry run; exit 1 if anything would change
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

CHECKBOX_RE = re.compile(r"^-\s*\[( |x|X)\]\s*(.+)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
COMPONENT_DIRS = ["dms-backend", "dms-ui", "dms-edge", "fleet-simulator"]
PIPELINE_ORDER = ["fleet-simulator", "dms-edge", "dms-backend", "dms-ui"]


def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return parent
    return start.resolve()


def read(path: Path) -> str:
    try:
        return path.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def parse_tasks(tasks_md: str) -> tuple[list[tuple[str | None, str]], int, int]:
    """Returns (completed_items, total_count, done_count). completed_items is
    a list of (nearest_heading, item_text) for every checked-off checkbox."""
    current_heading: str | None = None
    completed: list[tuple[str | None, str]] = []
    total = 0
    done = 0
    for line in tasks_md.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            current_heading = heading.group(2).strip()
            continue
        box = CHECKBOX_RE.match(line.strip())
        if box:
            total += 1
            checked = box.group(1).lower() == "x"
            if checked:
                done += 1
                completed.append((current_heading, box.group(2).strip()))
    return completed, total, done


def extract_section(markdown: str, heading_word: str) -> str:
    """Body of the first heading containing heading_word as a whole word
    (case-insensitive), up to the next heading of the same or shallower level."""
    word_re = re.compile(r"\b" + re.escape(heading_word) + r"\b", re.IGNORECASE)
    lines = markdown.splitlines()
    start_idx = None
    start_level = None
    for i, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if heading and word_re.search(heading.group(2)):
            start_idx = i
            start_level = len(heading.group(1))
            break
    if start_idx is None:
        return ""
    body: list[str] = []
    for line in lines[start_idx + 1 :]:
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) <= start_level:
            break
        body.append(line)
    return "\n".join(body).strip()


def _dequote(block: str) -> str:
    """Strip a common leading '> ' (blockquote) prefix if every line has one —
    happens when a fenced block sits inside a markdown blockquote note."""
    lines = block.splitlines()
    if lines and all(line.startswith(">") for line in lines if line.strip()):
        lines = [line[1:].lstrip() if line.startswith("> ") else line.lstrip(">") for line in lines]
    return "\n".join(lines)


def extract_fenced_blocks(markdown: str) -> list[str]:
    blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", markdown, re.DOTALL)
    return [_dequote(b) for b in blocks]


def extract_mermaid(markdown: str) -> str | None:
    match = re.search(r"```mermaid\n(.*?)```", markdown, re.DOTALL)
    return match.group(1).strip() if match else None


def git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5, check=False
        )
        return result.stdout.strip()
    except Exception:
        return ""


def touched_components(repo_root: Path) -> list[str]:
    changed: set[str] = set()

    for line in git(["diff", "--name-only", "HEAD"], repo_root).splitlines():
        for comp in COMPONENT_DIRS:
            if line.startswith(comp + "/"):
                changed.add(comp)

    for line in git(["status", "--porcelain"], repo_root).splitlines():
        parts = line.strip().split(maxsplit=1)
        path = parts[1] if len(parts) > 1 else ""
        for comp in COMPONENT_DIRS:
            if path.startswith(comp + "/"):
                changed.add(comp)

    if changed:
        return sorted(changed)
    # Fallback (e.g. already committed with a clean tree): show every
    # component that exists rather than an empty "how to run" section.
    return [c for c in COMPONENT_DIRS if (repo_root / c).exists()]


def run_commands_for(component: str, repo_root: Path) -> str:
    readme = read(repo_root / component / "README.md")
    if not readme:
        return f"_(no {component}/README.md found — check manually)_"
    section = extract_section(readme, "Run") or extract_section(readme, "Quick start")
    blocks = extract_fenced_blocks(section) if section else []
    if not blocks:
        return f"_(no \"## Run\" section found in {component}/README.md — check it manually)_"
    return "\n\n".join(f"```bash\n{block.strip()}\n```" for block in blocks)


def docker_commands(repo_root: Path) -> str:
    if not (repo_root / "docker-compose.yml").exists():
        return ""
    root_readme = read(repo_root / "README.md")
    section = extract_section(root_readme, "Run with Docker")
    blocks = extract_fenced_blocks(section) if section else []
    if not blocks:
        return "```bash\ndocker compose up --build\n```"
    return "\n\n".join(f"```bash\n{block.strip()}\n```" for block in blocks)


def build_mermaid(design_md: str, change_id: str, repo_root: Path) -> str:
    mermaid = extract_mermaid(design_md)
    if mermaid:
        return mermaid

    comps = touched_components(repo_root)
    ordered = [c for c in PIPELINE_ORDER if c in comps]
    node = lambda c: f'{c.replace("-", "_")}["{c}"]'  # noqa: E731

    if len(ordered) >= 2:
        return "graph LR\n" + "\n".join(
            f"  {node(a)} --> {node(b)}" for a, b in zip(ordered, ordered[1:])
        )
    if ordered:
        return f"graph LR\n  {node(ordered[0])}"
    return f'graph LR\n  change["{change_id}"]'


def build_implementation_summary(completed: list[tuple[str | None, str]]) -> str:
    if not completed:
        return "_(no completed tasks found in tasks.md)_"
    lines: list[str] = []
    current: str | None = "__unset__"
    for heading, item in completed:
        if heading != current:
            lines.append(f"\n**{heading or 'Tasks'}**")
            current = heading
        lines.append(f"- {item}")
    return "\n".join(lines).strip()


def title_from_proposal(proposal_md: str, fallback: str) -> str:
    for line in proposal_md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_release_md(change_dir: Path, repo_root: Path) -> str:
    change_id = change_dir.name
    proposal_md = read(change_dir / "proposal.md")
    design_md = read(change_dir / "design.md")
    tasks_md = read(change_dir / "tasks.md")

    completed, total, done_count = parse_tasks(tasks_md)
    title = title_from_proposal(proposal_md, change_id)
    summary = build_implementation_summary(completed)
    mermaid = build_mermaid(design_md, change_id, repo_root)

    comps = touched_components(repo_root)
    run_sections = "\n\n".join(
        f"### {comp}\n\n{run_commands_for(comp, repo_root)}"
        for comp in comps
        if (repo_root / comp).exists()
    )
    docker_section = docker_commands(repo_root)
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    parts = [
        f"# Release — {title}",
        "",
        "_Generated by `dms-spec/scripts/generate_release.py` — this is a scaffold,"
        " not final copy. Polish the Implementation Summary prose by hand; the run"
        " commands are pulled live from each component's README and shouldn't need"
        f" hand-editing. Last generated {generated_at}._",
        "",
        f"**Change:** `{change_id}` · **Tasks:** {done_count}/{total} complete",
        "",
        "## Implementation Summary",
        "",
        summary,
        "",
        "## Change Flow",
        "",
        "```mermaid",
        mermaid,
        "```",
        "",
        "## How to Run",
        "",
        run_sections or "_(no touched components detected — run manually)_",
    ]
    if docker_section:
        parts += ["", "### Docker (optional)", "", docker_section]

    return "\n".join(parts) + "\n"


def process_change(change_dir: Path, repo_root: Path, force: bool, check_only: bool) -> bool:
    tasks_path = change_dir / "tasks.md"
    release_path = change_dir / "release.md"
    if not tasks_path.exists():
        return False

    _, total, done_count = parse_tasks(read(tasks_path))
    if total == 0 or done_count < total:
        return False  # not ready for release yet

    if release_path.exists() and not force:
        if release_path.stat().st_mtime >= tasks_path.stat().st_mtime:
            return False  # already up to date

    if check_only:
        return True

    release_path.write_text(build_release_md(change_dir, repo_root))
    print(f"[dms-spec] generated {release_path.relative_to(repo_root)}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("change_id", nargs="?", help="Only process this change (dms-spec/changes/<change_id>)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if release.md looks current")
    parser.add_argument("--check", action="store_true", help="Dry run; exit 1 if anything would change")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(__file__).parent)
    changes_root = repo_root / "dms-spec" / "changes"
    if not changes_root.exists():
        sys.exit(0)

    any_generated = False
    for change_dir in sorted(changes_root.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        if args.change_id and change_dir.name != args.change_id:
            continue
        if process_change(change_dir, repo_root, args.force, args.check):
            any_generated = True

    if args.check:
        sys.exit(1 if any_generated else 0)


if __name__ == "__main__":
    main()
