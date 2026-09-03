from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from faceproof.api import create_app
from faceproof.blockchain import BlockchainStatus
from faceproof.config import Settings
from faceproof.domain import RunStatus
from faceproof.store import RunStore


def test_index_and_security_headers(settings: Settings, monkeypatch) -> None:
    monkeypatch.setattr(
        "faceproof.api.BaseSepoliaClient.status",
        lambda _: BlockchainStatus(True, 84532, None, None),
    )
    client = TestClient(create_app(settings))

    response = client.get("/")

    assert response.status_code == 200
    assert "Find a face" in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_health_reports_each_real_dependency(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        models_dir=tmp_path / "models",
        runs_dir=tmp_path / "runs",
        wallet_file=tmp_path / "wallet.json",
        serpapi_api_key=None,
    )
    settings.ensure_runtime_dirs()
    monkeypatch.setattr(
        "faceproof.api.BaseSepoliaClient.status",
        lambda _: BlockchainStatus(True, 84532, "0x1111111111111111111111111111111111111111", 0),
    )
    client = TestClient(create_app(settings))

    response = client.get("/api/health")

    assert response.status_code == 200
    health = response.json()
    assert health["status"] == "setup_required"
    assert health["search_configured"] is False
    assert health["wallet_configured"] is True
    assert health["wallet_funded"] is False
    assert health["blockchain_reachable"] is True


def test_rejects_untrusted_hosts_and_cross_origin_mutations(settings: Settings) -> None:
    client = TestClient(create_app(settings))

    untrusted_host = client.get("/", headers={"host": "attacker.example"})
    cross_origin = client.post(
        "/api/wallet",
        headers={"origin": "https://attacker.example"},
    )

    assert untrusted_host.status_code == 400
    assert cross_origin.status_code == 403
    assert cross_origin.json()["error"]["code"] == "origin_rejected"
    assert not settings.wallet_file.exists()


def test_unknown_runs_are_404_and_publication_cannot_be_canceled(settings: Settings) -> None:
    store = RunStore(settings.runs_dir)
    record = store.create("face.jpg")
    record.status = RunStatus.PUBLISHING
    store.save(record)
    client = TestClient(create_app(settings))

    missing = client.post("/api/runs/not-a-run/verify")
    cancellation = client.post(f"/api/runs/{record.run_id}/cancel")

    assert missing.status_code == 404
    assert cancellation.status_code == 400
    assert "cannot be canceled" in cancellation.json()["error"]["message"]
    assert store.get(record.run_id).status == RunStatus.PUBLISHING
