import socket

from fastapi.testclient import TestClient

from rippleproof.app import create_app
from rippleproof.config import Settings


def test_actual_refused_connection_returns_503_without_fixtures():
    # Reserve a port WITHOUT listening. This makes a real TCP connection fail,
    # without mocking the repository, client or Redis transport.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        settings = Settings(
            _env_file=None,
            host="127.0.0.1",
            port=reserved.getsockname()[1],
            connect_timeout_s=0.1,
            socket_timeout_s=0.1,
        )
        with TestClient(create_app(settings)) as client:
            response = client.get("/health")
            assert response.status_code == 503
            assert response.json() == {
                "status": "unavailable",
                "database": "unavailable",
                "graph": settings.graph,
                "graph_exists": None,
            }
            for path in (
                "/api/graph/summary",
                "/api/impact-paths?supplier_id=S-04",
                "/api/alternatives?part_id=P-22&as_of=2026-10-15",
            ):
                response = client.get(path)
                assert response.status_code == 503
                assert response.json()["error"]["code"] == "database_unavailable"
                assert "paths" not in response.json()
                assert "candidates" not in response.json()
            response = client.post(
                "/api/scenarios/simulate",
                json={
                    "supplier_id": "S-04",
                    "as_of": "2026-10-15",
                    "outage_start": "2026-10-16",
                    "outage_end_exclusive": "2026-10-24",
                },
            )
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "database_unavailable"
