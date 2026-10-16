"""Export safety tests operate only on temporary files, never live graph data."""

import base64

import pytest

from scripts import release_candidate as release


@pytest.mark.parametrize(
    "name",
    [
        ".git/config",
        "frontend/node_modules/a.js",
        ".env",
        ".local/secret.json",
        "backup.rdb",
        "../escape.py",
        "frontend/test-results/result.json",
        "/absolute.txt",
    ],
)
def test_release_rejects_private_state_and_archive_traversal(name):
    assert release.prohibited(name)


def test_secret_scan_detects_values_without_printing_them():
    private = b"synthetic-private-value-for-unit-test"
    assert release.scan(private, {private})
    assert release.scan(b"sk-" + b"a" * 40, set())
    assert not release.scan(b"RIPPLEPROOF_OPENAI_API_KEY=", set())


def test_export_cannot_overwrite_and_excludes_private_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(release, "history_audit", lambda _: {"commits": 0, "blobs_scanned": 0})
    (tmp_path / "RIGHTS.md").write_text("All Rights Reserved", encoding="utf-8")
    (tmp_path / ".env").write_text("PRIVATE=synthetic\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# Synthetic test candidate\n\n![Workspace](docs/images/workbench.png)\n",
        encoding="utf-8",
    )
    image = tmp_path / "docs/images/workbench.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aLsAAAAAASUVORK5CYII="
        )
    )
    upstream = tmp_path / "docs/notices/upstream/NOTICE.md"
    upstream.parent.mkdir(parents=True)
    notice = b"Keep upstream terms verbatim: [License](../../LICENSE.txt)\n"
    upstream.write_bytes(notice)
    destination = tmp_path / ".local" / "release"
    candidate, _, audit = release.export(destination)
    assert audit["secret_matches"] == 0
    assert not (candidate / ".env").exists()
    assert not (candidate / "LICENSE").exists()
    assert (candidate / "RIGHTS.md").exists()
    assert (candidate / "docs/notices/upstream/NOTICE.md").read_bytes() == notice
    assert (candidate / "docs/images/workbench.png").read_bytes() == image.read_bytes()
    assert "![Workspace](docs/images/workbench.png)" in (candidate / "README.md").read_text()
    with pytest.raises(FileExistsError):
        release.export(destination)
