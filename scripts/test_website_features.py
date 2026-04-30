import argparse
import json
import os
import time
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "logs"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env_value(key, default=""):
    env_value = os.environ.get(key)
    if env_value:
        return env_value
    if not ENV_FILE.exists():
        return default
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            env_key, env_raw = stripped.split("=", 1)
            if env_key.strip() != key:
                continue
            value = env_raw.strip().strip('"').strip("'")
            if value:
                return value
    except OSError:
        return default
    return default


DEFAULT_BASE_URL = os.environ.get("TEST_API_BASE_URL", "http://localhost:8000")
DEFAULT_API_KEY = (
    load_env_value("TEST_API_KEY")
    or load_env_value("API_KEY")
    or load_env_value("VITE_API_KEY")
    or "your-secret-key-same-as-esp32"
)
DEFAULT_USERNAME = os.environ.get("TEST_AUTH_USERNAME", "")
DEFAULT_PASSWORD = os.environ.get("TEST_AUTH_PASSWORD", "")
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("TEST_TIMEOUT_SECONDS", "20"))
DEFAULT_WARN_LATENCY_MS = int(os.environ.get("TEST_WARN_LATENCY_MS", "1200"))


class SkipTest(Exception):
    pass


class ApiClient:
    def __init__(self, base_url, api_key, timeout=20):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def request(
        self,
        method,
        path,
        *,
        json_body=None,
        form_body=None,
        params=None,
        token=None,
        use_api_key=True,
        expected_status=(200,),
    ):
        url = f"{self.base_url}{path}"
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}?{query}"

        headers = {"Accept": "application/json"}
        body = None

        if use_api_key:
            headers["x-api-key"] = self.api_key
        if token:
            headers["Authorization"] = f"Bearer {token}"

        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form_body is not None:
            body = urllib.parse.urlencode(form_body).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = urllib.request.Request(url, data=body, method=method.upper(), headers=headers)
        started_at = time.perf_counter()

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                latency_ms = (time.perf_counter() - started_at) * 1000.0
                raw = response.read()
                text = raw.decode("utf-8", errors="replace")
                payload = self._parse_payload(text)
                if response.status not in expected_status:
                    raise RuntimeError(f"Unexpected status {response.status}: {text}")
                return response.status, payload, text, latency_ms
        except urllib.error.HTTPError as exc:
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            text = exc.read().decode("utf-8", errors="replace")
            payload = self._parse_payload(text)
            if exc.code in expected_status:
                return exc.code, payload, text, latency_ms
            raise RuntimeError(f"HTTP {exc.code}: {text}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Connection error while calling {url}: {exc.reason}") from exc

    @staticmethod
    def _parse_payload(text):
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


class TestRunner:
    def __init__(self, client, log_path, username="", password="", cleanup=True, warn_latency_ms=1200):
        self.client = client
        self.log_path = log_path
        self.username = username
        self.password = password
        self.cleanup = cleanup
        self.warn_latency_ms = warn_latency_ms
        self.failures = []
        self.successes = []
        self.skips = []
        self.performance_warnings = []
        self.auth_token = None
        self.test_device_id = f"website-test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self.created_fault_id = None
        self.created_manual_fault_id = None
        self.last_latency_ms = None

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def record_success(self, name, detail=""):
        self.successes.append(name)
        latency_detail = ""
        if self.last_latency_ms is not None:
            latency_detail = f" [{self.last_latency_ms:.0f} ms]"
            if self.last_latency_ms > self.warn_latency_ms:
                self.performance_warnings.append(
                    f"{name} exceeded latency threshold: {self.last_latency_ms:.0f} ms > {self.warn_latency_ms} ms"
                )
                latency_detail += " [SLOW]"
        self.log(f"PASS  {name}{latency_detail}{': ' + detail if detail else ''}")

    def record_skip(self, name, detail=""):
        self.skips.append(name)
        self.log(f"SKIP  {name}{': ' + detail if detail else ''}")

    def record_failure(self, name, error):
        self.failures.append(name)
        self.log(f"FAIL  {name}: {error}")
        tb = traceback.format_exc()
        if tb and tb.strip() != "NoneType: None":
            self.log(tb.rstrip())

    def run_step(self, name, func):
        self.last_latency_ms = None
        try:
            detail = func()
            self.record_success(name, detail if isinstance(detail, str) else "")
        except SkipTest as exc:
            self.record_skip(name, str(exc))
        except Exception as exc:
            self.record_failure(name, exc)

    def _sample_sensor_payload(self):
        now = datetime.now(timezone.utc)
        return {
            "deviceId": self.test_device_id,
            "timestamp_ms": int(now.timestamp() * 1000),
            "uptime": 3600,
            "motor": {
                "running": True,
                "rpm": 1480,
                "pulse": 24,
                "uptime": 3600,
            },
            "power": {
                "voltage": 229.4,
                "current": 8.6,
                "power": 1.97,
                "powerFactor": 0.91,
                "energy": 7.4,
                "frequency": 49.9,
            },
            "temperature": {
                "t1": 64.8,
                "t2": 61.9,
            },
            "vibration": {
                "x": 1.73,
                "y": 0.21,
                "z": 9.62,
                "tap": False,
            },
            "faults": {
                "overcurrent": False,
                "overtemp": False,
                "stall": False,
                "vibration": True,
                "overvoltage": False,
                "undervoltage": False,
            },
            "protection": {
                "maxCurrentA": 12.5,
                "maxTempC": 85.0,
                "minRpm": 1200,
                "overvoltageV": 260.0,
                "undervoltageV": 190.0,
                "stallCurrentA": 2.2,
                "startupGraceMs": 3000,
                "faultTripCount": 3,
                "vibrationAckGraceMs": 1500,
            },
            "maintenance": {
                "nextMaintenanceTime": now.isoformat().replace("+00:00", "Z"),
                "totalLifeCycleHours": 250.5,
                "maintenanceHoursLimit": 500.0,
                "totalLifeCycleSeconds": 901800,
                "maintenanceHoursLimitSeconds": 1800000,
            },
        }

    def test_health(self):
        status, payload, _, latency_ms = self.client.request("GET", "/health", use_api_key=False)
        self.last_latency_ms = latency_ms
        if payload.get("status") != "ok":
            raise RuntimeError(f"Unexpected health payload: {payload}")
        return f"status={status}"

    def test_api_key(self):
        if not self.client.api_key or self.client.api_key == "your-secret-key-same-as-esp32":
            raise RuntimeError(
                "API key is missing or still using the placeholder value. "
                "Pass --api-key or set API_KEY in the backend .env file."
            )
        _, payload, _, latency_ms = self.client.request("GET", "/devices", params={"include_inactive": "true"})
        self.last_latency_ms = latency_ms
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected /devices response while verifying API key: {payload}")
        return "x-api-key accepted"

    def test_auth_login(self):
        if not self.username or not self.password:
            raise SkipTest("Set TEST_AUTH_USERNAME and TEST_AUTH_PASSWORD to test login flows.")
        _, payload, _, latency_ms = self.client.request(
            "POST",
            "/auth/login",
            form_body={"username": self.username, "password": self.password},
            use_api_key=False,
        )
        self.last_latency_ms = latency_ms
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"No access token returned: {payload}")
        self.auth_token = token
        return f"user={self.username}"

    def test_auth_verify(self):
        if not self.auth_token:
            raise SkipTest("Login step was skipped or failed.")
        _, payload, _, latency_ms = self.client.request("POST", "/auth/verify", token=self.auth_token, use_api_key=False)
        self.last_latency_ms = latency_ms
        if not payload.get("valid"):
            raise RuntimeError(f"Token verify failed: {payload}")
        return f"user={payload.get('username', '--')}"

    def test_auth_me(self):
        if not self.auth_token:
            raise SkipTest("Login step was skipped or failed.")
        _, payload, _, latency_ms = self.client.request("GET", "/auth/me", token=self.auth_token, use_api_key=False)
        self.last_latency_ms = latency_ms
        if "username" not in payload:
            raise RuntimeError(f"Unexpected /auth/me response: {payload}")
        return f"user={payload['username']}"

    def test_create_device(self):
        _, payload, _, latency_ms = self.client.request(
            "POST",
            "/devices",
            json_body={
                "id": self.test_device_id,
                "name": "Website Feature Test Device",
                "description": "Temporary device created by integration smoke test",
                "location": "Integration Lab",
            },
        )
        self.last_latency_ms = latency_ms
        if payload.get("id") != self.test_device_id:
            raise RuntimeError(f"Unexpected device payload: {payload}")
        return self.test_device_id

    def test_list_devices(self):
        _, payload, _, latency_ms = self.client.request("GET", "/devices", params={"include_inactive": "true"})
        self.last_latency_ms = latency_ms
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected devices response: {payload}")
        return f"count={len(payload)}"

    def test_get_device(self):
        _, payload, _, latency_ms = self.client.request("GET", f"/devices/{self.test_device_id}")
        self.last_latency_ms = latency_ms
        if payload.get("id") != self.test_device_id:
            raise RuntimeError(f"Unexpected device detail: {payload}")
        return payload.get("name", self.test_device_id)

    def test_update_device(self):
        _, payload, _, latency_ms = self.client.request(
            "PUT",
            f"/devices/{self.test_device_id}",
            json_body={
                "description": "Updated by website feature smoke test",
                "firmware_version": "test-fw-1.0.0",
                "location": "QA Bench",
            },
        )
        self.last_latency_ms = latency_ms
        if payload.get("firmware_version") != "test-fw-1.0.0":
            raise RuntimeError(f"Device update not reflected: {payload}")
        return payload.get("location", "--")

    def test_device_heartbeat(self):
        _, payload, _, latency_ms = self.client.request("POST", f"/devices/{self.test_device_id}/heartbeat")
        self.last_latency_ms = latency_ms
        return payload.get("message", "heartbeat updated")

    def test_post_sensor_data(self):
        _, payload, _, latency_ms = self.client.request("POST", "/data", json_body=self._sample_sensor_payload())
        self.last_latency_ms = latency_ms
        if payload.get("ok") is not True:
            raise RuntimeError(f"Unexpected /data response: {payload}")
        return "telemetry accepted"

    def test_get_sensor_data(self):
        _, payload, _, latency_ms = self.client.request("GET", f"/data/{self.test_device_id}", params={"limit": 5})
        self.last_latency_ms = latency_ms
        rows = payload.get("data", [])
        if not rows:
            raise RuntimeError("No sensor rows returned after posting test payload")
        return f"rows={len(rows)}"

    def test_forecast(self):
        _, payload, _, latency_ms = self.client.request(
            "GET",
            f"/forecast/{self.test_device_id}",
            params={"electricity_rate": "8.0", "hours": "24"},
        )
        self.last_latency_ms = latency_ms
        if "forecast" not in payload or "summary" not in payload:
            raise RuntimeError(f"Unexpected forecast response: {payload}")
        return payload["summary"].get("trend", "no-trend")

    def test_predictions(self):
        _, payload, _, latency_ms = self.client.request("GET", f"/predictions/{self.test_device_id}", params={"limit": 10})
        self.last_latency_ms = latency_ms
        if "data" not in payload:
            raise RuntimeError(f"Unexpected predictions response: {payload}")
        return f"rows={len(payload['data'])}"

    def test_local_ai(self):
        _, payload, _, latency_ms = self.client.request("POST", f"/ai/local-analyze/{self.test_device_id}")
        self.last_latency_ms = latency_ms
        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected local AI response: {payload}")
        return payload.get("message", "local AI triggered")

    def test_cloud_ai(self):
        _, payload, _, latency_ms = self.client.request("POST", f"/ai/analyze/{self.test_device_id}")
        self.last_latency_ms = latency_ms
        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected cloud AI response: {payload}")
        return payload.get("message", payload.get("success", "cloud AI response received"))

    def test_latest_ai(self):
        _, payload, _, latency_ms = self.client.request("GET", f"/ai/latest/{self.test_device_id}")
        self.last_latency_ms = latency_ms
        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected latest AI response: {payload}")
        return "latest AI endpoint reachable"

    def test_ai_mode(self):
        _, payload, _, latency_ms = self.client.request("POST", "/ai/mode", json_body={"mode": "commentary"})
        self.last_latency_ms = latency_ms
        if payload.get("mode") != "commentary":
            raise RuntimeError(f"AI mode not updated: {payload}")
        return payload.get("message", "mode updated")

    def test_fault_summary(self):
        _, payload, _, latency_ms = self.client.request("GET", "/faults/summary")
        self.last_latency_ms = latency_ms
        if "total_active" not in payload:
            raise RuntimeError(f"Unexpected faults summary: {payload}")
        return f"active={payload['total_active']}"

    def test_active_faults(self):
        _, payload, _, latency_ms = self.client.request("GET", "/faults/active")
        self.last_latency_ms = latency_ms
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected active faults response: {payload}")
        return f"active_faults={len(payload)}"

    def _load_device_fault(self):
        _, payload, _, latency_ms = self.client.request(
            "GET",
            f"/faults/device/{self.test_device_id}",
            params={"limit": 10},
        )
        self.last_latency_ms = latency_ms
        if not isinstance(payload, list) or not payload:
            raise RuntimeError("No device fault found after posting faulted telemetry")
        self.created_fault_id = payload[0]["id"]
        return payload

    def test_device_faults(self):
        faults = self._load_device_fault()
        return f"faults={len(faults)}"

    def test_all_faults(self):
        _, payload, _, latency_ms = self.client.request("GET", "/faults", params={"device_id": self.test_device_id, "limit": 20})
        self.last_latency_ms = latency_ms
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected /faults response: {payload}")
        return f"faults={len(payload)}"

    def test_fault_context(self):
        if self.created_fault_id is None:
            self._load_device_fault()
        _, payload, _, latency_ms = self.client.request("GET", f"/faults/{self.created_fault_id}/context")
        self.last_latency_ms = latency_ms
        if "fault" not in payload or "sensor_snapshot" not in payload:
            raise RuntimeError(f"Unexpected fault context response: {payload}")
        return f"fault_id={self.created_fault_id}"

    def test_resolve_fault(self):
        if self.created_fault_id is None:
            self._load_device_fault()
        _, payload, _, latency_ms = self.client.request(
            "POST",
            f"/faults/{self.created_fault_id}/resolve",
            json_body={
                "root_cause": "mechanical_failure",
                "actions_taken": "Validated integration test fault resolution path",
                "parts_replaced": "none",
                "resolved_by": "integration-test",
                "notes": "Auto-resolved by website feature smoke test",
            },
        )
        self.last_latency_ms = latency_ms
        if payload.get("status") != "resolved":
            raise RuntimeError(f"Fault was not resolved: {payload}")
        return f"fault_id={self.created_fault_id}"

    def test_create_manual_fault(self):
        _, payload, _, latency_ms = self.client.request(
            "POST",
            "/faults",
            json_body={
                "device_id": self.test_device_id,
                "fault_type": "maintenance_due",
                "severity": "info",
                "message": "Manual fault created by website feature smoke test",
            },
        )
        self.last_latency_ms = latency_ms
        self.created_manual_fault_id = payload.get("id")
        if not self.created_manual_fault_id:
            raise RuntimeError(f"Manual fault creation failed: {payload}")
        return f"fault_id={self.created_manual_fault_id}"

    def test_delete_manual_fault(self):
        if not self.created_manual_fault_id:
            raise RuntimeError("No manual fault was created for delete test")
        _, payload, _, latency_ms = self.client.request("DELETE", f"/faults/{self.created_manual_fault_id}")
        self.last_latency_ms = latency_ms
        return payload.get("message", "fault deleted")

    def test_command_set_protection(self):
        _, payload, _, latency_ms = self.client.request(
            "POST",
            f"/command/{self.test_device_id}/set_protection",
            json_body={"maxCurrentA": 11.5, "maxTempC": 82.0, "faultTripCount": 4},
        )
        self.last_latency_ms = latency_ms
        return f"replaced={payload.get('replacedPendingCommands', 0)}"

    def test_command_pending(self):
        _, payload, _, latency_ms = self.client.request("GET", f"/command/{self.test_device_id}/pending")
        self.last_latency_ms = latency_ms
        if payload.get("command") is None:
            raise RuntimeError("Expected a pending command but queue was empty")
        return f"id={payload['id']}"

    def test_command_done(self):
        _, pending, _, _ = self.client.request("GET", f"/command/{self.test_device_id}/pending")
        pending_id = pending.get("id")
        if not pending_id:
            raise RuntimeError("No pending command available to acknowledge")
        _, payload, _, latency_ms = self.client.request(
            "POST",
            f"/command/{self.test_device_id}/done",
            json_body={"id": pending_id},
        )
        self.last_latency_ms = latency_ms
        if payload.get("ok") is not True:
            raise RuntimeError(f"Ack failed: {payload}")
        return f"id={pending_id}"

    def test_command_set_maintenance(self):
        _, payload, _, latency_ms = self.client.request(
            "POST",
            f"/command/{self.test_device_id}/set_maintenance",
            json_body={
                "nextMaintenanceTime": datetime.now(timezone.utc).isoformat(),
                "totalLifeCycleHours": 320.0,
                "maintenanceHoursLimit": 640.0,
                "totalLifeCycleSeconds": 1152000,
                "maintenanceHoursLimitSeconds": 2304000,
            },
        )
        self.last_latency_ms = latency_ms
        return f"replaced={payload.get('replacedPendingCommands', 0)}"

    def test_command_set_runtime(self):
        _, payload, _, latency_ms = self.client.request(
            "POST",
            f"/command/{self.test_device_id}/set_runtime",
            json_body={"uptimeSeconds": 7200},
        )
        self.last_latency_ms = latency_ms
        return f"replaced={payload.get('replacedPendingCommands', 0)}"

    def test_command_reset_energy(self):
        _, payload, _, latency_ms = self.client.request("POST", f"/command/{self.test_device_id}/reset_energy", json_body={})
        self.last_latency_ms = latency_ms
        return f"replaced={payload.get('replacedPendingCommands', 0)}"

    def test_command_clear_maintenance(self):
        _, payload, _, latency_ms = self.client.request("POST", f"/command/{self.test_device_id}/clear_maintenance", json_body={})
        self.last_latency_ms = latency_ms
        return f"replaced={payload.get('replacedPendingCommands', 0)}"

    def test_command_ack_faults(self):
        _, payload, _, latency_ms = self.client.request(
            "POST",
            f"/command/{self.test_device_id}/ack_faults",
            json_body={"faults": ["vibration"]},
        )
        self.last_latency_ms = latency_ms
        return f"replaced={payload.get('replacedPendingCommands', 0)}"

    def test_command_history(self):
        _, payload, _, latency_ms = self.client.request("GET", f"/command/{self.test_device_id}/history", params={"limit": 10})
        self.last_latency_ms = latency_ms
        commands = payload.get("commands", [])
        if not isinstance(commands, list):
            raise RuntimeError(f"Unexpected history response: {payload}")
        return f"history={len(commands)}"

    def cleanup_device(self):
        if not self.cleanup:
            self.record_skip("cleanup_device", f"Temporary device {self.test_device_id} left in place by request.")
            return
        try:
            _, payload, _, latency_ms = self.client.request("DELETE", f"/devices/{self.test_device_id}")
            self.last_latency_ms = latency_ms
            self.record_success("cleanup_device", payload.get("message", "device deleted"))
        except Exception as exc:
            self.record_failure("cleanup_device", exc)

    def run(self):
        self.log(f"Website feature smoke test started for {self.client.base_url}")
        self.log(f"Logs will be written to {self.log_path}")

        steps = [
            ("health", self.test_health),
            ("api_key", self.test_api_key),
            ("auth_login", self.test_auth_login),
            ("auth_verify", self.test_auth_verify),
            ("auth_me", self.test_auth_me),
            ("create_device", self.test_create_device),
            ("list_devices", self.test_list_devices),
            ("get_device", self.test_get_device),
            ("update_device", self.test_update_device),
            ("device_heartbeat", self.test_device_heartbeat),
            ("post_sensor_data", self.test_post_sensor_data),
            ("get_sensor_data", self.test_get_sensor_data),
            ("forecast", self.test_forecast),
            ("predictions", self.test_predictions),
            ("local_ai", self.test_local_ai),
            ("cloud_ai", self.test_cloud_ai),
            ("latest_ai", self.test_latest_ai),
            ("ai_mode", self.test_ai_mode),
            ("fault_summary", self.test_fault_summary),
            ("active_faults", self.test_active_faults),
            ("device_faults", self.test_device_faults),
            ("all_faults", self.test_all_faults),
            ("fault_context", self.test_fault_context),
            ("resolve_fault", self.test_resolve_fault),
            ("create_manual_fault", self.test_create_manual_fault),
            ("delete_manual_fault", self.test_delete_manual_fault),
            ("command_set_protection", self.test_command_set_protection),
            ("command_pending", self.test_command_pending),
            ("command_done", self.test_command_done),
            ("command_set_maintenance", self.test_command_set_maintenance),
            ("command_set_runtime", self.test_command_set_runtime),
            ("command_reset_energy", self.test_command_reset_energy),
            ("command_clear_maintenance", self.test_command_clear_maintenance),
            ("command_ack_faults", self.test_command_ack_faults),
            ("command_history", self.test_command_history),
        ]

        for name, func in steps:
            self.run_step(name, func)

        self.cleanup_device()

        self.log("")
        self.log("Test summary")
        self.log(f"Passed: {len(self.successes)}")
        self.log(f"Failed: {len(self.failures)}")
        self.log(f"Skipped: {len(self.skips)}")
        self.log(f"Latency threshold: {self.warn_latency_ms} ms")
        if self.performance_warnings:
            self.log(f"Slow endpoints: {len(self.performance_warnings)}")
            for warning in self.performance_warnings:
                self.log(f"WARN  {warning}")
        if self.failures:
            self.log("Failing checks: " + ", ".join(self.failures))
            return 1
        return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Exercise the backend APIs that power the website and log any failures."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend base URL, default: %(default)s")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="x-api-key used by the website APIs")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Optional username for /auth/login")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Optional password for /auth/login")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Per-request timeout in seconds")
    parser.add_argument(
        "--warn-latency-ms",
        type=int,
        default=DEFAULT_WARN_LATENCY_MS,
        help="Warn when a request exceeds this many milliseconds",
    )
    parser.add_argument(
        "--keep-device",
        action="store_true",
        help="Keep the temporary test device instead of deleting it at the end",
    )
    return parser


def main():
    args = build_parser().parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"website-feature-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

    client = ApiClient(args.base_url, args.api_key, timeout=args.timeout)
    runner = TestRunner(
        client,
        log_path,
        username=args.username,
        password=args.password,
        cleanup=not args.keep_device,
        warn_latency_ms=args.warn_latency_ms,
    )
    exit_code = runner.run()
    print(f"\nDetailed log: {log_path}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
