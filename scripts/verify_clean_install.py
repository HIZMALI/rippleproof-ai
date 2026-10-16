"""Fresh source-only install in a unique Compose project/volume. No cleanup.

Exports/extracts into a NEW directory, scrubs inherited provider/graph settings,
checks empty graph and distinct volume before seeding, and leaves it running.
Never accepts the live project name or deletes any directory, graph or volume.
"""

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.release_candidate import export, prohibited  # noqa: E402

SCENARIO = {
    "supplier_id": "S-04",
    "as_of": "2026-10-15",
    "outage_start": "2026-10-16",
    "outage_end_exclusive": "2026-10-24",
    "include_mitigation": True,
}


def http(base, path, body=None):
    request = urllib.request.Request(
        base + path,
        headers={"Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(request, timeout=110) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as response:
        return response.code, json.load(response)


def main():
    identity = uuid4().hex[:12]
    project = f"phase5a_{identity}"
    folder = ROOT / ".local/cleanrooms" / identity
    folder.mkdir(parents=True, exist_ok=False)
    _, archive, manifest = export(ROOT / ".local/releases" / (identity + "_tested"))
    source = folder / "source"
    source.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        assert not any(prohibited(name) for name in bundle.namelist())
        bundle.extractall(source)
    source = source / "rippleproof-ai"
    assert not any(
        (source / name).exists()
        for name in (".local", ".venv", ".git", ".env", "frontend/node_modules")
    )
    handles = [socket.socket() for _ in range(3)]
    for handle in handles:
        handle.bind(("127.0.0.1", 0))
    ports = [handle.getsockname()[1] for handle in handles]
    for handle in handles:
        handle.close()
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("RIPPLEPROOF_", "FALKORDB_"))
        and k not in {"API_PORT", "WEB_PORT", "COMPOSE_PROJECT_NAME", "COMPOSE_FILE"}
    }
    environment.update(
        API_PORT=str(ports[0]),
        WEB_PORT=str(ports[1]),
        FALKORDB_PORT=str(ports[2]),
        FALKORDB_GRAPH=f"clean_{identity}",
        RIPPLEPROOF_PROVIDER="disabled",
        RIPPLEPROOF_ALLOW_PAID_CALLS="false",
    )
    transcript = []

    def compose(*args):
        assert project.startswith("phase5a_") and project != "rippleproof-ai"
        command = ["docker", "compose", "-p", project, *args]
        result = subprocess.run(
            command, cwd=source, env=environment, capture_output=True, text=True, encoding="utf-8"
        )
        transcript.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        (folder / "commands.json").write_text(json.dumps(transcript, indent=2), encoding="utf-8")
        result.check_returncode()
        return result.stdout

    base = f"http://127.0.0.1:{ports[0]}"
    web = f"http://127.0.0.1:{ports[1]}"

    def wait_ready():
        for _ in range(60):
            try:
                if http(base, "/health")[0] == 200:
                    return
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        raise TimeoutError("Clean backend did not become ready")

    compose("up", "-d", "--build", "--wait", "--wait-timeout", "120")
    volumes = json.loads(
        subprocess.check_output(["docker", "inspect", f"{project}-falkordb-1"], text=True)
    )[0]["Mounts"]
    volume = next(
        item["Name"] for item in volumes if item["Destination"] == "/var/lib/falkordb/data"
    )
    assert volume == project + "_graph-data" and volume != "rippleproof-ai_graph-data"
    assert http(base, "/health")[1]["graph_exists"] is False
    assert http(base, "/api/graph/summary")[1]["node_count"] == 0
    compose("exec", "-T", "backend", "python", "-m", "rippleproof.seed")
    compose("exec", "-T", "backend", "python", "-m", "rippleproof.migrate")
    first = http(base, "/api/graph/summary")[1]
    compose("exec", "-T", "backend", "python", "-m", "rippleproof.migrate")
    assert http(base, "/api/graph/summary")[1] == first
    assert (first["node_count"], first["relationship_count"]) == (145, 291)
    status, scenario = http(base, "/api/scenarios/simulate", SCENARIO)
    assert status == 200 and [
        len(scenario[key]["on_time_orders"]) for key in ("baseline", "disrupted", "mitigated")
    ] == [19, 18, 20]
    assert scenario["estimated_additional_procurement_cost"] == "1364.00"
    assert not http(base, "/api/agent/capabilities")[1]["agent_available"]
    smoke = compose("exec", "-T", "backend", "python", "-m", "rippleproof.mcp_smoke")
    assert '"transport": "stdio"' in smoke
    for action in [
        ("restart",),
        ("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120"),
    ]:
        compose(*action)
        wait_ready()
        assert http(base, "/api/scenarios/simulate", SCENARIO)[1] == scenario
    outage = {}
    try:
        compose("stop", "--timeout", "3", "falkordb")
        for label, path, body in [
            ("impact", "/api/impact-paths?supplier_id=S-04", None),
            ("simulation", "/api/scenarios/simulate", SCENARIO),
            (
                "guided_mcp",
                "/api/agent/run",
                {"question": "Explain the source outage", "scenario": SCENARIO, "mode": "guided"},
            ),
        ]:
            status, data = http(base, path, body)
            assert status == 503, (label, status)
            outage[label] = {
                "http_status": status,
                "error_code": data.get("error_code") or data.get("error", {}).get("code"),
            }
    finally:
        compose("start", "falkordb")
        wait_ready()
    assert http(base, "/api/scenarios/simulate", SCENARIO)[1] == scenario
    # External browser driver is test infrastructure. The installed app itself
    # has no dependency on the original node_modules, .venv or private fixtures.
    browser = subprocess.run(
        ["node", "scripts/clean-demo.mjs", web, str(folder / "browser")],
        cwd=ROOT / "frontend",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    transcript.append(
        {
            "command": ["node", "scripts/clean-demo.mjs", web, "<isolated-browser-evidence>"],
            "exit_code": browser.returncode,
            "stdout": browser.stdout,
            "stderr": browser.stderr,
        }
    )
    (folder / "commands.json").write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    browser.check_returncode()
    proof = {
        "project": project,
        "graph": f"clean_{identity}",
        "volume": volume,
        "api_origin": base,
        "web_origin": web,
        "db_port": ports[2],
        "initial_empty": True,
        "summary": first,
        "fingerprint": scenario["snapshot_fingerprint"],
        "scenario_id": scenario["scenario_id"],
        "migration_idempotent": True,
        "restart_and_recreation_equal": True,
        "database_removal_breaks_graph_functions": outage,
        "browser": json.loads(browser.stdout),
        "provider_remote_calls": 0,
        "live_approvals": 0,
        "retained_running": True,
        "tested_source_files": manifest["files"],
        "tested_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    (folder / "proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    ROOT.joinpath(".local/phase5a-clean-current.json").write_text(
        json.dumps({"directory": str(folder)}), encoding="utf-8"
    )
    public = {k: v for k, v in proof.items() if k != "tested_source_files"}
    for key in ("api_origin", "web_origin"):
        public[key] += " (local verification only)"
    target = folder / "summary.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(public, indent=2), encoding="utf-8")
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
