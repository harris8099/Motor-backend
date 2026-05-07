import pytest

from app.routers import faults


class FakeResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar_value


class FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    async def execute(self, statement, params=None):
        self.calls.append({"sql": str(statement), "params": params or {}})
        if not self._results:
            raise AssertionError("Unexpected execute call")
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_detect_and_log_fault_creates_new_active_incident(monkeypatch):
    session = FakeSession([
        FakeResult(rows=[]),
        FakeResult(scalar_value=42),
    ])

    async def fake_get_fault_by_id(db, fault_id):
        return {"id": fault_id, "status": "active"}

    monkeypatch.setattr(faults, "_get_fault_by_id", fake_get_fault_by_id)

    result = await faults.detect_and_log_fault(session, "device-1", "overcurrent", 99)

    assert result == {"id": 42, "status": "active"}
    assert "status = 'active'" in session.calls[0]["sql"]
    assert "INSERT INTO fault_logs" in session.calls[1]["sql"]


@pytest.mark.asyncio
async def test_mark_fault_cleared_by_hardware_moves_fault_to_pending_close(monkeypatch):
    session = FakeSession([
        FakeResult(rows=[{"id": 7}]),
    ])

    async def fake_get_fault_by_id(db, fault_id):
        return {"id": fault_id, "status": "cleared_pending_close"}

    monkeypatch.setattr(faults, "_get_fault_by_id", fake_get_fault_by_id)

    result = await faults.mark_fault_cleared_by_hardware(session, "device-1", "overcurrent")

    assert result == {"id": 7, "status": "cleared_pending_close"}
    assert "status = 'cleared_pending_close'" in session.calls[0]["sql"]
    assert session.calls[0]["params"] == {"device_id": "device-1", "fault_type": "overcurrent"}


@pytest.mark.asyncio
async def test_mark_fault_cleared_by_hardware_returns_none_when_no_active_fault(monkeypatch):
    session = FakeSession([
        FakeResult(rows=[]),
    ])

    async def fake_get_fault_by_id(db, fault_id):
        raise AssertionError("_get_fault_by_id should not be called")

    monkeypatch.setattr(faults, "_get_fault_by_id", fake_get_fault_by_id)

    result = await faults.mark_fault_cleared_by_hardware(session, "device-1", "overcurrent")

    assert result is None
