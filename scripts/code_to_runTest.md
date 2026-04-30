# Scripts Test Guide

Run all commands from:

```powershell
cd "C:\Users\TUF\Desktop\Main project\AI ml backend"
```

## Before Running Anything

Make sure:

```powershell
python --version
```

```powershell
pip install -r requirements.txt
```

Your backend env is configured so `app.database.settings` can connect to the database.

## Script Summary

### `scripts\test_website_features.py`

Purpose:
- Full backend smoke test for the website features.
- Tests health, devices, telemetry, forecast, predictions, AI endpoints, faults, and command/settings APIs.
- Writes a detailed log file to `scripts\logs\`.

Looks correct:
- `Yes`
- Syntax checked with `python -m py_compile`

Safe to run:
- `Mostly yes`
- It creates a temporary device and deletes it afterward unless you use `--keep-device`
- It will create temporary faults/commands during the run

API key behavior:
- It now auto-loads `API_KEY` from the backend `.env` file by default
- You can still override it with `--api-key`
- `--username` and `--password` only cover `/auth/*` testing
- Most website APIs still require the backend `x-api-key`

Run:

```powershell
python scripts\test_website_features.py --base-url http://localhost:8000
```

With auth testing too:

```powershell
python scripts\test_website_features.py --base-url http://localhost:8000 --username your_user --password your_pass
```

Keep the temporary test device:

```powershell
python scripts\test_website_features.py --keep-device
```

Override API key manually:

```powershell
python scripts\test_website_features.py --api-key "YOUR_REAL_API_KEY"
```

Custom timeout and latency warning threshold:

```powershell
python scripts\test_website_features.py --timeout 30 --warn-latency-ms 1500
```

What to check:
- Exit code `0` means all tested steps passed
- Detailed failures are logged in `scripts\logs\website-feature-test-*.log`
- Each passing step now logs latency in milliseconds
- Slow endpoints are marked with `[SLOW]`

### `scripts\test_faults.py`

Purpose:
- Manual fault workflow test helper.
- Create sample faults, list active faults, resolve faults, or clear all faults.

Looks correct:
- `Yes`
- Logic is fine for fault UI testing

Cautions:
- `--clear` deletes all rows from `fault_logs`
- This is a real DB mutation script, not just read-only testing

Create one test fault:

```powershell
python scripts\test_faults.py --device esp32-001 --fault overtemp --severity critical
```

Create multiple sample faults:

```powershell
python scripts\test_faults.py --sample
```

List active faults:

```powershell
python scripts\test_faults.py --list-faults
```

Resolve a fault:

```powershell
python scripts\test_faults.py --resolve 1 --technician "Your Name"
```

Delete all faults:

```powershell
python scripts\test_faults.py --clear
```

### `scripts\create_dummy_data.py`

Purpose:
- Fills the database with sample devices, sensor readings, fault events, and predictions.
- Useful for populating charts and pages when there is no live ESP data.

Looks correct:
- `Yes, with one caution`
- It is usable, but it is data-seeding logic, not a verification script

Cautions:
- It deletes existing data for devices matching `esp32-%` or `motor-%` in:
  - `sensor_readings`
  - `fault_events`
  - `predictions`
- Use it only when you want demo/test data regenerated

Run:

```powershell
python scripts\create_dummy_data.py
```

Best use:
- Run this when the frontend is empty and you want realistic-looking test data

### `scripts\seed_devices.py`

Purpose:
- Seeds a richer set of industrial-style sample devices and generates realistic sensor data if those devices do not already have readings.

Looks correct:
- `Mostly yes`

Known issue:
- It contains a hardcoded project path:

```python
sys.path.insert(0, "c:\\Users\\TUF\\Desktop\\Main project\\AI ml backend")
```

- This is fine on your machine, but it is not portable to another computer or folder.

Other note:
- It skips generating readings for devices that already have sensor data.

Run:

```powershell
python scripts\seed_devices.py
```

Best use:
- Good for creating a more realistic demo dataset than the smaller helper scripts

### `scripts\check_data.py`

Purpose:
- Quick database check for `esp32-001`
- Prints sensor-reading count and the latest few rows
- Also prints grouped reading counts for all devices

Looks correct:
- `Yes`
- Very simple and read-only

Run:

```powershell
python scripts\check_data.py
```

Best use:
- Quick sanity check to confirm data exists in `sensor_readings`

### `scripts\verify_data.py`

Purpose:
- Read-only verification of seeded/demo data
- Prints devices, predictions, sensor counts, and fault events

Looks correct:
- `Yes`

Known issue:
- The terminal output has encoding noise in some emoji/text on Windows, like `ðŸ”`
- This is a display/encoding issue, not a database logic issue

Run:

```powershell
python scripts\verify_data.py
```

Best use:
- Run after `create_dummy_data.py` or `seed_devices.py` to confirm the DB was populated

## Recommended Workflows

### 1. Full website/API test

```powershell
python scripts\test_website_features.py --base-url http://localhost:8000
```
```powershell
python scripts\test_website_features.py --base-url http://localhost:8000 --api-key "YOUR_REAL_API_KEY" --username your_user --password your_pass
```

### 2. Populate DB for frontend demo/testing

Option A:

```powershell
python scripts\create_dummy_data.py
```

Option B:

```powershell
python scripts\seed_devices.py
```

Then verify:

```powershell
python scripts\verify_data.py
```

### 3. Test only fault-related UI

```powershell
python scripts\test_faults.py --sample
```

Then later:

```powershell
python scripts\test_faults.py --list-faults
```

## Which Script Should You Use?

- Use `test_website_features.py` for the broadest feature test.
- Use `test_faults.py` for fault banner / resolution testing.
- Use `create_dummy_data.py` when you want lots of demo rows fast.
- Use `seed_devices.py` when you want more realistic industrial device records.
- Use `check_data.py` for a quick DB sanity check.
- Use `verify_data.py` for a read-only overview after seeding.

## Notes About Existing Scripts

- `verify_data.py`, `create_dummy_data.py`, and `seed_devices.py` show mojibake/encoding noise in printed output on Windows terminals. The scripts are still usable.
- `seed_devices.py` should ideally be refactored later to remove the hardcoded absolute path.
- `test_faults.py --clear` is intentionally destructive for `fault_logs`.
- `create_dummy_data.py` is intentionally destructive for test/demo device data.
