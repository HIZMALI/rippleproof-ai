"""Local browser-test harness. Creates a NEW graph; never targets live data.

The private control file is not an application endpoint. No HTTP test controls or
credentials are shipped to the browser bundle. Graphs are retained for audit.
"""

import argparse
import json
import secrets
import sys
import threading
import time
from pathlib import Path
from uuid import uuid4

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rippleproof.app import create_app  # noqa: E402
from rippleproof.config import Phase3Settings, Settings  # noqa: E402
from rippleproof.inbound_data import build_inbound_extension  # noqa: E402
from rippleproof.repository import GraphRepository  # noqa: E402
from rippleproof.seed_data import build_dataset  # noqa: E402
from tests.agent_provider import ScriptedProvider  # noqa: E402

STATE = ROOT / ".local/phase4-browser-state.json"
CONTROL = ROOT / ".local/phase4-browser-control.json"
ACK = ROOT / ".local/phase4-browser-ack.json"


def write(path, body):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(body), encoding="utf-8")
    # Windows file scanners/readers can briefly hold the destination open.
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def control(action):
    identity = uuid4().hex
    write(CONTROL, {"id": identity, "action": action})
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if ACK.exists():
            ack = json.loads(ACK.read_text())
            if ack["id"] == identity:
                if ack.get("error"):
                    raise RuntimeError(ack["error"])
                print(f"Isolated browser harness: {action} completed")
                return
        time.sleep(0.1)
    raise TimeoutError("Browser test control timed out")


def serve():
    ROOT.joinpath(".local").mkdir(exist_ok=True)
    settings = Settings(_env_file=None, graph=f"test_rippleproof_p4ui_{uuid4().hex}")
    repository = GraphRepository(settings)
    assert settings.graph.startswith("test_rippleproof_p4ui_")
    assert not repository.ready(), "Refusing to seed an existing graph"
    repository.seed(build_dataset())
    repository.migrate_inbound(build_inbound_extension())
    with repository.connect() as db:
        original_stock = (
            db.select_graph(settings.graph)
            .ro_query("MATCH (p:Part {id: $id}) RETURN p.stock_on_hand", {"id": "P-22"})
            .result_set[0][0]
        )
    token = secrets.token_urlsafe(36)
    empty_graph = f"test_rippleproof_p4empty_{uuid4().hex}"
    write(STATE, {"graph": settings.graph, "empty_graph": empty_graph, "token": token})
    # A fresh file revision prevents stale controls from previous runs executing.
    last_id = json.loads(CONTROL.read_text())["id"] if CONTROL.exists() else ""
    server = None
    thread = None

    def restart(mode):
        nonlocal server, thread
        if server:
            server.should_exit = True
            thread.join(timeout=12)
            assert not thread.is_alive(), "Previous browser-test backend did not stop"
        configured = settings
        if mode == "empty":
            configured = settings.model_copy(update={"graph": empty_graph})
        elif mode == "unavailable":
            configured = settings.model_copy(update={"port": 1})
        phase3 = Phase3Settings(
            _env_file=None,
            provider="disabled",
            allow_paid_calls=False,
            approval_secret=None if mode == "approval-disabled" else token,
        )
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(
                    configured,
                    phase3,
                    provider=ScriptedProvider() if mode == "controlled-agent" else None,
                ),
                host="127.0.0.1",
                port=18001,
                access_log=False,
                log_level="warning",
            )
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() > deadline:
                raise TimeoutError("Test backend startup failed")
            time.sleep(0.05)

    restart("normal")
    print(f"Isolated browser backend ready: {settings.graph}", flush=True)
    try:
        while True:
            if CONTROL.exists():
                command = json.loads(CONTROL.read_text())
                if command["id"] != last_id:
                    last_id = command["id"]
                    try:
                        if command["action"] in {"stale", "restore"}:
                            # Fixed, parameterized, isolated-test-only source mutation.
                            with repository.connect() as db:
                                db.select_graph(settings.graph).query(
                                    "MATCH (p:Part {id: $id}) SET p.stock_on_hand = $stock",
                                    {
                                        "id": "P-22",
                                        "stock": original_stock
                                        + (1 if command["action"] == "stale" else 0),
                                    },
                                )
                        else:
                            assert command["action"] in {
                                "normal",
                                "restart",
                                "empty",
                                "unavailable",
                                "approval-disabled",
                                "controlled-agent",
                            }
                            restart(command["action"])
                        write(ACK, {"id": last_id})
                    except Exception as exc:
                        write(ACK, {"id": last_id, "error": type(exc).__name__})
            time.sleep(0.1)
    finally:
        server.should_exit = True
        thread.join(timeout=12)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "serve",
            "normal",
            "restart",
            "empty",
            "unavailable",
            "approval-disabled",
            "controlled-agent",
            "stale",
            "restore",
        ],
    )
    args = parser.parse_args()
    if args.action == "serve":
        serve()
    else:
        control(args.action)
