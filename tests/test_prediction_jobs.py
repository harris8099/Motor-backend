import asyncio

from app.services import prediction_jobs


def test_resolve_dispatch_mode_background_without_redis(monkeypatch):
    monkeypatch.setattr(prediction_jobs.settings, "prediction_dispatch_mode", "auto")
    monkeypatch.setattr(prediction_jobs.settings, "redis_url", "")
    assert prediction_jobs._resolve_dispatch_mode() == "background"


def test_resolve_dispatch_mode_redis_when_configured(monkeypatch):
    monkeypatch.setattr(prediction_jobs.settings, "prediction_dispatch_mode", "auto")
    monkeypatch.setattr(prediction_jobs.settings, "redis_url", "redis://localhost:6379/0")
    assert prediction_jobs._resolve_dispatch_mode() == "redis"


def test_enqueue_prediction_job_falls_back_to_inline(monkeypatch):
    recorded = {}

    async def fake_process(payload_data):
        recorded["payload"] = payload_data

    monkeypatch.setattr(prediction_jobs.settings, "prediction_dispatch_mode", "background")
    monkeypatch.setattr(prediction_jobs, "process_prediction_payload", fake_process)

    payload = {"deviceId": "esp32-001"}
    mode = asyncio.run(prediction_jobs.enqueue_prediction_job(payload, background_tasks=None))

    assert mode == "inline"
    assert recorded["payload"] == payload
