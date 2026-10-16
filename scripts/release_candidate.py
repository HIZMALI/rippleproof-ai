"""Create a separate, audited source candidate. No Git/network/publish mutations.

Uses an explicit source selection, rejects links/outside paths, scans selected
content and reachable Git history, enumerates ZIP members, and never overwrites
an existing candidate. Original workstation state/backups remain untouched.
"""

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DENIED = {
    ".git",
    ".local",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "dist",
    "backups",
}
ROOT_FILES = {
    "README.md",
    "RIGHTS.md",
    "THIRD_PARTY_NOTICES.md",
    "compose.yaml",
    "Dockerfile",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    ".gitignore",
    ".dockerignore",
    ".env.example",
}
SCRIPT_FILES = {
    "release_candidate.py",
    "verify_clean_install.py",
    "phase4_test_backend.py",
    "third_party_notices.py",
    "verify_provider_contract.py",
}
FRONTEND_FILES = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "vite.config.ts",
    "playwright.config.ts",
    "eslint.config.mjs",
    "index.html",
    "Dockerfile",
    "nginx.conf",
    ".dockerignore",
}
PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    re.compile(rb"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{25,}\b"),
    re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
]


def prohibited(name):
    path = PurePosixPath(name)
    return (
        path.is_absolute()
        or ".." in path.parts
        or bool(set(path.parts) & DENIED)
        or any(p.startswith(".env") and p != ".env.example" for p in path.parts)
        or path.suffix.lower() in {".rdb", ".aof", ".har", ".pem", ".key", ".sqlite", ".zip"}
    )


def selected(path):
    relative = path.relative_to(ROOT)
    name = relative.as_posix()
    if prohibited(name):
        return False
    if len(relative.parts) == 1:
        return name in ROOT_FILES
    top = relative.parts[0]
    if top in {"rippleproof", "tests"}:
        return path.suffix == ".py"
    if top == "scripts":
        return len(relative.parts) == 2 and path.name in SCRIPT_FILES
    if top == "frontend":
        return (
            (len(relative.parts) == 2 and path.name in FRONTEND_FILES)
            or relative.parts[1] in {"src", "public", "tests", "e2e", "scripts"}
            and path.suffix in {".ts", ".tsx", ".css", ".svg", ".mjs"}
        )
    if top == "docs":
        return (
            path.suffix == ".md"
            or relative.parts[1] == "notices"
            or len(relative.parts) >= 3
            and relative.parts[1] == "images"
            and path.suffix == ".png"
            and path.stat().st_size < 500_000
        )
    return False


def known_secrets():
    values = set()

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {"token", "approval_secret", "openai_api_key", "secret"}:
                    if isinstance(item, str) and len(item) >= 16:
                        values.add(item.encode())
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for path in ROOT.joinpath(".local").rglob("*.json"):
        if path.stat().st_size < 2_000_000:
            try:
                visit(json.loads(path.read_text(encoding="utf-8")))
            except (ValueError, UnicodeError):
                pass
    envfile = ROOT / ".env"
    if envfile.exists():
        for line in envfile.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if any(term in key.upper() for term in ("SECRET", "TOKEN", "API_KEY")):
                value = value.strip().strip("\"'")
                if len(value) >= 16:
                    values.add(value.encode())
    return values


def scan(data, secrets):
    return any(p.search(data) for p in PATTERNS) or any(value in data for value in secrets)


def history_audit(secrets):
    result = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    objects = [line.split(" ", 1)[0] for line in result.stdout.splitlines()]
    blobs = 0
    for identity in objects:
        kind = subprocess.check_output(["git", "cat-file", "-t", identity], cwd=ROOT).strip()
        if kind == b"blob":
            blobs += 1
            if scan(
                subprocess.check_output(["git", "cat-file", "blob", identity], cwd=ROOT), secrets
            ):
                raise ValueError("Potential secret in Git object; operator review required")
    commits = int(subprocess.check_output(["git", "rev-list", "--all", "--count"], cwd=ROOT))
    return {
        "commits": commits,
        "blobs_scanned": blobs,
        "note": "No history rewritten or invented; unborn repository"
        if not commits
        else "Existing reachable objects inspected; author/date review still required",
    }


def normalized_document(text, relative):
    # Workstation names/paths are irrelevant to judges. Only export copies change.
    text = text.replace(str(ROOT), "<repository>").replace(ROOT.as_posix(), "<repository>")
    text = re.sub(r"[A-Za-z]:[\\/]Users[\\/][^\s`<>)\"']+", "<local-path>", text)

    # Old execution archives stay private; do not ship dangling historical links.
    def link(match):
        target = match[2].split("#", 1)[0].strip("<>")
        if not target or re.match(r"[a-zA-Z]+:", target) or target.startswith("#"):
            return match[0]
        candidate = (ROOT / relative.parent / target).resolve()
        if candidate.is_relative_to(ROOT) and candidate.is_file() and selected(candidate):
            return match[0]
        return match[1] + " (historical local artifact; excluded from public candidate)"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)


def export(destination, *, phase="phase5a"):
    if phase not in {"phase5a", "phase5b1"}:
        raise ValueError("Unknown release phase")
    destination = destination.resolve()
    assert destination.is_relative_to(ROOT / ".local"), (
        "Export must stay in ignored workspace .local"
    )
    destination.mkdir(parents=True, exist_ok=False)
    candidate = destination / "rippleproof-ai"
    candidate.mkdir()
    secrets = known_secrets()
    history = history_audit(secrets)
    manifest, changed_docs = [], []
    paths = []
    for folder, directories, files in ROOT.walk():
        directories[:] = [name for name in directories if name not in DENIED]
        paths.extend(folder / name for name in files)
    for path in sorted(paths):
        # Avoid recursive copying the new candidate or reading dependency state.
        if not path.is_file() or not selected(path):
            continue
        assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
        relative = path.relative_to(ROOT)
        data = path.read_bytes()
        if path.suffix == ".md" and not relative.is_relative_to("docs/notices"):
            original = data
            data = normalized_document(data.decode("utf-8"), relative).encode()
            if original != data:
                changed_docs.append(relative.as_posix())
        if scan(data, secrets):
            raise ValueError(
                f"Potential secret in selected file: {relative.as_posix()}; value withheld"
            )
        if path.suffix in {".md", ".txt", ".json"} and re.search(
            rb"[A-Za-z]:[\\/]+Users[\\/]+", data
        ):
            raise ValueError(f"Private workstation path remains in {relative.as_posix()}")
        target = candidate / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest.append(
            {
                "path": relative.as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    assert not (candidate / "LICENSE").exists(), "Owner chose no project LICENSE"
    assert (candidate / "RIGHTS.md").is_file()
    archive = destination / f"rippleproof-ai-{phase}-candidate.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in manifest:
            bundle.write(candidate / item["path"], "rippleproof-ai/" + item["path"])
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.namelist()
        assert len(members) == len(manifest) and not any(prohibited(name) for name in members)
        assert all(not scan(bundle.read(name), secrets) for name in members)
    audit = {
        "phase": phase,
        "created_utc": datetime.now(UTC).isoformat(),
        "file_count": len(manifest),
        "zip_bytes": archive.stat().st_size,
        "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "secret_matches": 0,
        "known_private_values_checked": len(secrets),
        "history": history,
        "license": "All Rights Reserved; no project LICENSE; see RIGHTS.md",
        "export_only_document_sanitization": changed_docs,
        "files": manifest,
    }
    (destination / "manifest.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in audit.items() if k != "files"}, indent=2))
    print("Candidate:", candidate)
    return candidate, archive, audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--phase", choices=["phase5a", "phase5b1"], default="phase5a")
    args = parser.parse_args()
    folder = args.destination or ROOT / ".local/releases" / datetime.now(UTC).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    export(folder, phase=args.phase)
