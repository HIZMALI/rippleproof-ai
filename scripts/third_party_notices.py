"""Inventory pinned dependency metadata and preserve installed license notices."""

import importlib.metadata as metadata
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICES = ROOT / "docs/notices"


def main():
    NOTICES.mkdir(exist_ok=True)
    rows = []
    names = set()
    for filename in ("requirements.txt", "requirements-dev.txt"):
        names.update(re.findall(r"^([A-Za-z0-9_-]+)==", (ROOT / filename).read_text(), re.M))
    for name in sorted(names):
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            rows.append(
                ("Python", name, "platform-specific", "Not installed on inventory host", "")
            )
            continue
        license_id = dist.metadata.get("License-Expression") or dist.metadata.get("License")
        if not license_id:
            license_id = next(
                (
                    v.rsplit(" :: ", 1)[-1]
                    for v in dist.metadata.get_all("Classifier", [])
                    if v.startswith("License ::")
                ),
                "See retained license text",
            )
        links = []
        for item in dist.files or []:
            if not any(term in item.name.lower() for term in ("license", "notice", "copying")):
                continue
            source = dist.locate_file(item)
            if source.is_file():
                folder = NOTICES / "python" / f"{name}-{dist.version}"
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / str(item).replace("/", "_").replace("\\", "_")
                target.write_bytes(source.read_bytes())
                links.append(f"[{item.name}]({target.relative_to(ROOT).as_posix()})")
        rows.append(
            ("Python", name, dist.version, str(license_id).splitlines()[0], ", ".join(links))
        )
    packages = json.loads((ROOT / "frontend/package-lock.json").read_text(encoding="utf-8"))[
        "packages"
    ]
    for path, package in sorted(packages.items()):
        if not path:
            continue
        name = path.rsplit("node_modules/", 1)[-1]
        folder = ROOT / "frontend" / path
        links = []
        if folder.is_dir():
            for item in folder.iterdir():
                if item.is_file() and any(
                    item.name.lower().startswith(s) for s in ("license", "notice", "copying")
                ):
                    target = NOTICES / "npm" / name.replace("/", "_") / item.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(item.read_bytes())
                    links.append(f"[{item.name}]({target.relative_to(ROOT).as_posix()})")
        rows.append(
            (
                "npm",
                name,
                package.get("version", "unknown"),
                package.get("license", "See package metadata"),
                ", ".join(links) or "Platform optional / not redistributed as source",
            )
        )
    body = """# Third-party notices

RippleProof original project source remains All Rights Reserved; no project
LICENSE has been selected. This policy does not replace dependency licenses.
The following inventory comes from pinned requirements, the npm lockfile and
actual installed distribution notices. Retained texts preserve upstream authors,
copyright and permission conditions; none identify the RippleProof owner.

The source candidate downloads dependencies rather than vendoring their code.
The React production bundle contains third-party runtime code, so retain this
notice directory when distributing that bundle. Platform-optional build tools
not installed here are recorded from lockfile metadata. Review platform package
licenses again if distributing additional binaries.

FalkorDB **server** is SSPLv1 (separate from its MIT Python client), as documented
by [FalkorDB](https://docs.falkordb.com/). The pinned container and its base images
retain upstream terms, not the project's rights policy. This local source
candidate does not redistribute container layers. Review the SSPL service/source
requirements before any commercial hosting or modified server redistribution.
Container OS component notices remain in the upstream images; a complete image
SBOM/commercial compliance review is not claimed by this source inventory.

| Ecosystem | Component | Pinned version | Reported license | Retained notices |
| --- | --- | --- | --- | --- |
"""
    body += "\n".join(
        "| " + " | ".join(value.replace("|", "\\|") for value in row) + " |" for row in rows
    )
    (ROOT / "THIRD_PARTY_NOTICES.md").write_text(body + "\n", encoding="utf-8")
    retained = sum(p.is_file() for p in NOTICES.rglob("*"))
    print(f"Recorded {len(rows)} dependency entries; retained {retained} notice files")


if __name__ == "__main__":
    main()
