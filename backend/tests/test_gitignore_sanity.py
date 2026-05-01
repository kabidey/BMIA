"""Pre-deploy sanity check — ensures .gitignore never blocks .env files.

BMIA deploys require backend/.env and frontend/.env to ship with the repo so
the platform can inject production MONGO_URL / REACT_APP_BACKEND_URL at deploy
time. If .gitignore silently re-adds `.env` or `*.env` patterns (as has
happened at least twice in this project's history — Apr 24 2026), prod ends up
with a stale preview URL and users see "Connection failed" on login.

Run: `pytest backend/tests/test_gitignore_sanity.py -v`
Also runs in CI as a belt-and-braces check before every push.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = REPO_ROOT / ".gitignore"
REQUIRED_ENV_FILES = [
    "backend/.env",
    "frontend/.env",
]

# Patterns that would match .env files and therefore break deploys.
DANGEROUS_PATTERNS = {
    ".env",
    ".env.*",
    "*.env",
    "env",
    "**/.env",
}


def _read_gitignore_lines() -> list[str]:
    if not GITIGNORE.exists():
        pytest.skip(".gitignore not found at repo root")
    return [
        ln.strip()
        for ln in GITIGNORE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def test_gitignore_does_not_block_env_files_by_pattern():
    """Fail fast if .gitignore has a bare .env / *.env rule — those catch
    backend/.env and frontend/.env and silently break deploys."""
    lines = _read_gitignore_lines()
    offenders = [ln for ln in lines if ln in DANGEROUS_PATTERNS]
    assert not offenders, (
        f".gitignore has dangerous patterns that will block required .env "
        f"files from deployment: {offenders}. "
        f"Remove these lines — .env files MUST ship with the repo so the "
        f"platform can inject production credentials at deploy time."
    )


def test_gitignore_allows_required_env_files():
    """Use `git check-ignore` to prove that the actual .env files are NOT
    ignored. More robust than pattern-matching since it handles negations,
    nested .gitignores, etc.

    With `-v`, `git check-ignore` returns:
      exit 0 + a pattern line  ⇒  path matches some rule; may be ignored OR
                                   force-included via a negation pattern
      exit 1 + no output       ⇒  path does not match any rule (not ignored)

    So the safe check is: either exit 1, OR exit 0 with a negation pattern
    (line starting with `!`) — both mean the file ships."""
    for rel in REQUIRED_ENV_FILES:
        f = REPO_ROOT / rel
        if not f.exists():
            continue  # Not a blocker — repo layout may vary across forks
        res = subprocess.run(
            ["git", "check-ignore", "-v", rel],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if res.returncode == 1:
            continue  # plain "not ignored"
        # exit 0 — must be a negation pattern to still be OK
        output = (res.stdout or res.stderr).strip()
        is_negation = (
            "\t!" in output            # tab-separated: pattern col starts with `!`
            or output.startswith("!")
            or ":!" in output           # "file:line:!pattern\tpath"
            or bool([
                line for line in output.splitlines()
                # The pattern field (3rd tab-separated col) starts with `!`
                if len(line.split("\t")) >= 2
                and line.split("\t")[0].split(":")[-1].startswith("!")
            ])
        )
        assert is_negation, (
            f"{rel} is being ignored by git! This will break deployment.\n"
            f"git check-ignore output: {output}"
        )
