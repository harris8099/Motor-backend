"""
motor_predictor.py
==================
Phase 1: Physics-based motor health estimation
Phase 2: Transitions to real ML once enough data is collected

Fetches data from ESP32 /data endpoint, stores to PostgreSQL,
computes bearing life, coil health, and maintenance date estimates.

Usage:
    python motor_predictor.py --host 192.168.x.x
    python motor_predictor.py --host 192.168.x.x --interval 30
    python motor_predictor.py --host 192.168.x.x --report   (print report and exit)

Requirements:
    pip install requests sqlalchemy psycopg2-binary
"""

import argparse
import math
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ─────────────────────────── CONFIGURATION ────────────────────────────────────

DEFAULT_HOST         = "192.168.0.1"
DEFAULT_PORT         = 80
POLL_INTERVAL_SEC    = 30          # how often to fetch from ESP32

# PostgreSQL connection — set via env var or edit directly
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/motordb"
)

# Motor nameplate — adjust to your motor
RATED_CURRENT_A      = 5.0        # motor rated current (A)
RATED_TEMP_C         = 75.0       # max safe winding temp (°C)
SERVICE_INTERVAL_HRS = 500.0      # hours between scheduled maintenance
BEARING_L10_HRS      = 20000.0    # bearing L10 life in hours (from datasheet)

# Vibration baseline (g) — auto-calibrated from first 100 readings
VIBRATION_BASELINE_G = None       # set to e.g. 0.05 to override auto-calibration

# Thresholds for health scoring
VIB_WARNING_MULT     = 2.0
VIB_CRITICAL_MULT    = 4.0
CURRENT_WARNING_PCT  = 85.0
CURRENT_CRITICAL_PCT = 100.0
TEMP_WARNING_PCT     = 80.0
TEMP_CRITICAL_PCT    = 95.0

# Minimum data points before ML model is used instead of physics
ML_MIN_SAMPLES       = 5000       # ~1.7 days at 30s interval

# ──────────────────────────── DATABASE ────────────────────────────────────────

def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS readings (
                id              SERIAL PRIMARY KEY,
                ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ts_unix         DOUBLE PRECISION NOT NULL,
                uptime_s        INTEGER,
                motor_running   BOOLEAN,
                rpm             INTEGER,
                voltage         REAL,
                current_a       REAL,
                power_w         REAL,
                power_factor    REAL,
                energy_kwh      REAL,
                frequency_hz    REAL,
                temp1_c         REAL,
                temp2_c         REAL,
                accel_x         REAL,
                accel_y         REAL,
                accel_z         REAL,
                accel_mag       REAL,
                tap_detected    BOOLEAN,
                fault_overcurrent  BOOLEAN,
                fault_overtemp     BOOLEAN,
                fault_stall        BOOLEAN,
                fault_vibration    BOOLEAN,
                fault_overvoltage  BOOLEAN,
                fault_undervoltage BOOLEAN
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS predictions (
                id                      SERIAL PRIMARY KEY,
                ts                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ts_unix                 DOUBLE PRECISION NOT NULL,
                bearing_health_pct      REAL,
                bearing_rul_hrs         REAL,
                coil_health_pct         REAL,
                maintenance_due_hrs     REAL,
                next_maintenance_date   TEXT,
                vib_baseline_g          REAL,
                notes                   TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS calibration (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """))


def insert_reading(engine, data: dict) -> None:
    now     = datetime.now()
    ts_unix = now.timestamp()

    motor  = data.get("motor", {})
    power  = data.get("power", {})
    temp   = data.get("temperature", {})
    vib    = data.get("vibration", {})
    faults = data.get("faults", {})

    ax  = float(vib.get("x", 0))
    ay  = float(vib.get("y", 0))
    az  = float(vib.get("z", 0))
    mag = math.sqrt(ax*ax + ay*ay + az*az)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO readings (
                ts, ts_unix, uptime_s, motor_running, rpm,
                voltage, current_a, power_w, power_factor, energy_kwh, frequency_hz,
                temp1_c, temp2_c,
                accel_x, accel_y, accel_z, accel_mag,
                tap_detected,
                fault_overcurrent, fault_overtemp, fault_stall, fault_vibration,
                fault_overvoltage, fault_undervoltage
            ) VALUES (
                :ts, :ts_unix, :uptime_s, :motor_running, :rpm,
                :voltage, :current_a, :power_w, :power_factor, :energy_kwh, :frequency_hz,
                :temp1_c, :temp2_c,
                :accel_x, :accel_y, :accel_z, :accel_mag,
                :tap_detected,
                :fault_overcurrent, :fault_overtemp, :fault_stall, :fault_vibration,
                :fault_overvoltage, :fault_undervoltage
            )
        """), {
            "ts":                 now.isoformat(),
            "ts_unix":            ts_unix,
            "uptime_s":           data.get("uptime"),
            "motor_running":      bool(motor.get("running")),
            "rpm":                motor.get("rpm", 0),
            "voltage":            power.get("voltage", 0),
            "current_a":          power.get("current", 0),
            "power_w":            power.get("power", 0),
            "power_factor":       power.get("powerFactor", 0),
            "energy_kwh":         power.get("energy", 0),
            "frequency_hz":       power.get("frequency", 0),
            "temp1_c":            temp.get("t1", 0),
            "temp2_c":            temp.get("t2", 0),
            "accel_x":            ax,
            "accel_y":            ay,
            "accel_z":            az,
            "accel_mag":          mag,
            "tap_detected":       bool(vib.get("tap")),
            "fault_overcurrent":  bool(faults.get("overcurrent")),
            "fault_overtemp":     bool(faults.get("overtemp")),
            "fault_stall":        bool(faults.get("stall")),
            "fault_vibration":    bool(faults.get("vibration")),
            "fault_overvoltage":  bool(faults.get("overvoltage")),
            "fault_undervoltage": bool(faults.get("undervoltage")),
        })


def get_sample_count(engine) -> int:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT COUNT(*) AS n FROM readings")).mappings().fetchone()
        return int(row["n"]) if row else 0


def get_calibration(engine, key: str) -> Optional[str]:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT value FROM calibration WHERE key = :key"),
            {"key": key}
        ).mappings().fetchone()
        return row["value"] if row else None


def set_calibration(engine, key: str, value: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO calibration (key, value) VALUES (:key, :value) "
                 "ON CONFLICT (key) DO UPDATE SET value = :value"),
            {"key": key, "value": value}
        )


# ──────────────────────────── VIBRATION BASELINE ──────────────────────────────

def compute_vibration_baseline(engine) -> float:
    global VIBRATION_BASELINE_G

    if VIBRATION_BASELINE_G is not None:
        return VIBRATION_BASELINE_G

    stored = get_calibration(engine, "vib_baseline_g")
    if stored is not None:
        return float(stored)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT accel_mag FROM readings
            WHERE motor_running = TRUE AND accel_mag > 0.01
            ORDER BY ts_unix ASC
            LIMIT 100
        """)).mappings().fetchall()

    if len(rows) < 20:
        return 0.05

    mags = sorted([r["accel_mag"] for r in rows])
    idx = max(0, int(len(mags) * 0.10))
    baseline = max(0.01, mags[idx])

    set_calibration(engine, "vib_baseline_g", str(baseline))
    print(f"[CALIBRATION] Vibration baseline set to {baseline:.4f} g from {len(rows)} samples")
    return baseline


# ──────────────────────────── PHYSICS MODELS ──────────────────────────────────

def bearing_health_physics(engine, uptime_s: int) -> dict:
    """
    Bearing health using Palmgren-Miner damage accumulation rule.
    L10 life is derated by vibration severity.
    """
    baseline   = compute_vibration_baseline(engine)
    uptime_hrs = uptime_s / 3600.0

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT AVG(accel_mag) AS avg_mag, MAX(accel_mag) AS max_mag
            FROM readings
            WHERE motor_running = TRUE
              AND ts_unix >= (SELECT MAX(ts_unix) FROM readings) - 3600
        """)).mappings().fetchone()

    avg_mag   = float(rows["avg_mag"] or baseline)
    vib_ratio = avg_mag / baseline if baseline > 0 else 1.0

    if vib_ratio < VIB_WARNING_MULT:
        damage_rate = 1.0
    elif vib_ratio < VIB_CRITICAL_MULT:
        damage_rate = 1.0 + (vib_ratio - VIB_WARNING_MULT) * 3.0
    else:
        damage_rate = (1.0 + (VIB_CRITICAL_MULT - VIB_WARNING_MULT) * 3.0
                       + (vib_ratio - VIB_CRITICAL_MULT) * 6.0)

    effective_l10 = BEARING_L10_HRS / damage_rate
    health_pct    = max(0.0, min(100.0, (1.0 - uptime_hrs / effective_l10) * 100.0))
    rul_hrs       = max(0.0, effective_l10 - uptime_hrs)

    status = "GOOD"
    if vib_ratio >= VIB_CRITICAL_MULT:
        status = "CRITICAL — abnormal vibration"
    elif vib_ratio >= VIB_WARNING_MULT:
        status = "WARNING — elevated vibration"
    elif health_pct < 20:
        status = "WARNING — approaching end of L10 life"

    return {
        "health_pct":  round(health_pct, 1),
        "rul_hrs":     round(rul_hrs, 0),
        "vib_ratio":   round(vib_ratio, 2),
        "avg_mag_g":   round(avg_mag, 4),
        "baseline_g":  round(baseline, 4),
        "damage_rate": round(damage_rate, 2),
        "status":      status,
    }


def coil_health_physics(engine) -> dict:
    """
    Coil (winding) health based on thermal stress, overcurrent, and fault history.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                AVG(temp1_c)                                        AS avg_temp,
                MAX(temp1_c)                                        AS max_temp,
                AVG(current_a)                                      AS avg_current,
                MAX(current_a)                                      AS max_current,
                SUM(CASE WHEN fault_overcurrent THEN 1 ELSE 0 END)  AS oc_events,
                SUM(CASE WHEN fault_overtemp    THEN 1 ELSE 0 END)  AS ot_events,
                COUNT(*)                                            AS total_samples,
                SUM(CASE WHEN motor_running     THEN 1 ELSE 0 END)  AS running_samples
            FROM readings
        """)).mappings().fetchone()

    if not rows or rows["total_samples"] == 0:
        return {"health_pct": 100.0, "status": "Insufficient data", "notes": ""}

    avg_temp    = float(rows["avg_temp"]    or 25.0)
    max_temp    = float(rows["max_temp"]    or 25.0)
    avg_current = float(rows["avg_current"] or 0.0)
    oc_events   = int(rows["oc_events"]     or 0)
    ot_events   = int(rows["ot_events"]     or 0)

    # Arrhenius thermal degradation
    insulation_rated_c = 155.0
    if avg_temp > insulation_rated_c:
        thermal_factor = 2.0 ** ((avg_temp - insulation_rated_c) / 10.0)
    elif avg_temp > RATED_TEMP_C:
        thermal_factor = 1.0 + (avg_temp - RATED_TEMP_C) / (insulation_rated_c - RATED_TEMP_C)
    else:
        thermal_factor = 1.0

    thermal_score = max(0.0, 100.0 - (thermal_factor - 1.0) * 30.0)

    load_pct = (avg_current / RATED_CURRENT_A * 100.0) if RATED_CURRENT_A > 0 else 0.0
    if load_pct <= CURRENT_WARNING_PCT:
        current_score = 100.0
    elif load_pct <= CURRENT_CRITICAL_PCT:
        current_score = 100.0 - (load_pct - CURRENT_WARNING_PCT) * 2.0
    else:
        current_score = max(0.0, 70.0 - (load_pct - CURRENT_CRITICAL_PCT) * 3.0)

    fault_penalty = min(30.0, oc_events * 0.5 + ot_events * 0.3)
    health_pct = max(0.0, min(100.0,
        thermal_score * 0.50 +
        current_score * 0.35 +
        (100.0 - fault_penalty) * 0.15
    ))

    notes = []
    if thermal_factor > 1.5:
        notes.append(f"High thermal stress (avg {avg_temp:.1f}°C)")
    if load_pct > CURRENT_WARNING_PCT:
        notes.append(f"High load ({load_pct:.0f}% of rated current)")
    if oc_events > 5:
        notes.append(f"{oc_events} overcurrent events recorded")
    if max_temp > RATED_TEMP_C:
        notes.append(f"Max temp reached {max_temp:.1f}°C")

    status = "GOOD"
    if health_pct < 30:
        status = "CRITICAL"
    elif health_pct < 60:
        status = "WARNING"

    return {
        "health_pct":         round(health_pct, 1),
        "thermal_score":      round(thermal_score, 1),
        "current_score":      round(current_score, 1),
        "load_pct_of_rated":  round(load_pct, 1),
        "oc_events":          oc_events,
        "ot_events":          ot_events,
        "status":             status,
        "notes":              "; ".join(notes) if notes else "Normal operation",
    }


def maintenance_prediction(engine, uptime_s: int) -> dict:
    uptime_hrs = uptime_s / 3600.0

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT AVG(current_a) AS avg_current
            FROM readings
            WHERE motor_running = TRUE
              AND ts_unix >= (SELECT MAX(ts_unix) FROM readings) - 86400
        """)).mappings().fetchone()

        avg_current = float(row["avg_current"] or 0.0) if row else 0.0
        load_factor = max(0.1, min(2.0, avg_current / RATED_CURRENT_A) if RATED_CURRENT_A > 0 else 1.0)

        fault_row = conn.execute(text("""
            SELECT SUM(
                CASE WHEN fault_overcurrent THEN 1 ELSE 0 END +
                CASE WHEN fault_overtemp    THEN 1 ELSE 0 END +
                CASE WHEN fault_stall       THEN 1 ELSE 0 END
            ) AS faults
            FROM readings
            WHERE ts_unix >= (SELECT MAX(ts_unix) FROM readings) - 604800
        """)).mappings().fetchone()
        recent_faults = int(fault_row["faults"] or 0) if fault_row else 0

        run_row = conn.execute(text("""
            SELECT
                SUM(CASE WHEN motor_running THEN 1 ELSE 0 END) AS run_samples,
                COUNT(*)                                        AS total_samples,
                (MAX(ts_unix) - MIN(ts_unix)) / 3600.0         AS span_hrs
            FROM readings
            WHERE ts_unix >= (SELECT MAX(ts_unix) FROM readings) - 604800
        """)).mappings().fetchone()

    adjusted_interval_hrs = SERVICE_INTERVAL_HRS / load_factor
    fault_penalty_pct = min(20.0, recent_faults * 0.1)
    adjusted_interval_hrs *= (1.0 - fault_penalty_pct / 100.0)
    remaining_hrs = max(0.0, adjusted_interval_hrs - uptime_hrs)

    if run_row and run_row["span_hrs"] and run_row["span_hrs"] > 1:
        run_ratio    = (run_row["run_samples"] or 0) / max(1, run_row["total_samples"])
        daily_run_hrs = run_ratio * 24.0
    else:
        daily_run_hrs = 8.0

    if daily_run_hrs > 0:
        days_until = remaining_hrs / daily_run_hrs
        next_date  = datetime.now() + timedelta(days=days_until)
        next_date_str = next_date.strftime("%Y-%m-%d")
    else:
        days_until    = None
        next_date_str = "Unknown (motor not running)"

    overdue = uptime_hrs >= adjusted_interval_hrs
    return {
        "uptime_hrs":              round(uptime_hrs, 1),
        "service_interval_hrs":    round(adjusted_interval_hrs, 0),
        "remaining_hrs":           round(remaining_hrs, 1),
        "daily_run_hrs_estimate":  round(daily_run_hrs, 1),
        "days_until_maintenance":  round(days_until, 0) if days_until else None,
        "next_maintenance_date":   next_date_str,
        "load_factor":             round(load_factor, 2),
        "overdue":                 overdue,
        "status":                  "OVERDUE" if overdue else ("DUE SOON" if remaining_hrs < 50 else "OK"),
    }


# ──────────────────────────── ML MODEL (FUTURE) ───────────────────────────────

def try_ml_prediction(engine) -> Optional[dict]:
    """
    Placeholder for real ML model. Activates when ML_MIN_SAMPLES readings collected.
    """
    n = get_sample_count(engine)
    if n < ML_MIN_SAMPLES:
        return None

    model_path = "bearing_model.pkl"
    if not os.path.exists(model_path):
        return None

    try:
        import joblib
        import numpy as np

        model = joblib.load(model_path)

        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    AVG(accel_mag) AS avg_mag,
                    AVG(temp1_c)   AS avg_temp,
                    AVG(current_a) AS avg_current,
                    MAX(uptime_s)  AS uptime_s
                FROM readings
                WHERE ts_unix >= (SELECT MAX(ts_unix) FROM readings) - 3600
                  AND motor_running = TRUE
            """)).mappings().fetchone()

        if not row:
            return None

        features = np.array([[
            float(row["avg_mag"]     or 0),
            float(row["avg_temp"]    or 0),
            float(row["avg_current"] or 0),
            float(row["uptime_s"]    or 0),
        ]])
        rul_hrs = float(model.predict(features)[0])
        return {"bearing_rul_hrs_ml": round(rul_hrs, 0), "source": "ML model"}

    except Exception as e:
        print(f"[ML] Prediction failed: {e}")
        return None


# ──────────────────────────── REPORT ──────────────────────────────────────────

def print_report(data: dict, bearing: dict, coil: dict, maintenance: dict,
                 sample_count: int, ml_result: Optional[dict]) -> None:
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime_s = data.get("uptime", 0)
    uptime_hrs = uptime_s / 3600.0

    print("\n" + "="*60)
    print(f"  MOTOR HEALTH REPORT — {ts}")
    print("="*60)
    print(f"  Uptime        : {uptime_hrs:.1f} hrs ({uptime_s}s)")
    print(f"  Data samples  : {sample_count}")
    print(f"  Motor running : {data.get('motor', {}).get('running', False)}")
    print()

    print("── BEARING HEALTH ──────────────────────────────────────")
    print(f"  Health        : {bearing['health_pct']}%")
    print(f"  Est. RUL      : {bearing['rul_hrs']:.0f} hrs")
    print(f"  Vibration     : {bearing['avg_mag_g']:.4f} g  "
          f"({bearing['vib_ratio']:.1f}× baseline of {bearing['baseline_g']:.4f} g)")
    print(f"  Damage rate   : {bearing['damage_rate']:.2f}×")
    print(f"  Status        : {bearing['status']}")
    if ml_result:
        print(f"  ML RUL        : {ml_result.get('bearing_rul_hrs_ml')} hrs  [{ml_result.get('source')}]")
    print()

    print("── COIL / WINDING HEALTH ───────────────────────────────")
    print(f"  Health        : {coil['health_pct']}%")
    print(f"  Load          : {coil['load_pct_of_rated']:.0f}% of rated current")
    print(f"  Thermal score : {coil['thermal_score']:.0f}/100")
    print(f"  Current score : {coil['current_score']:.0f}/100")
    print(f"  OC events     : {coil['oc_events']}")
    print(f"  OT events     : {coil['ot_events']}")
    print(f"  Status        : {coil['status']}")
    print(f"  Notes         : {coil['notes']}")
    print()

    print("── MAINTENANCE PREDICTION ──────────────────────────────")
    print(f"  Status        : {maintenance['status']}")
    print(f"  Service intv  : {maintenance['service_interval_hrs']:.0f} hrs  "
          f"(load factor {maintenance['load_factor']:.2f}×)")
    print(f"  Remaining     : {maintenance['remaining_hrs']:.1f} hrs")
    print(f"  Daily run est : {maintenance['daily_run_hrs_estimate']:.1f} hrs/day")
    print(f"  Days until    : {maintenance['days_until_maintenance']}")
    print(f"  Next date     : {maintenance['next_maintenance_date']}")
    print()

    if sample_count < ML_MIN_SAMPLES:
        pct = sample_count / ML_MIN_SAMPLES * 100
        print("── DATA COLLECTION PROGRESS ────────────────────────────")
        print(f"  {sample_count}/{ML_MIN_SAMPLES} samples collected ({pct:.0f}%)")
        print(f"  ML model activates at {ML_MIN_SAMPLES} samples")
        print(f"  (~{(ML_MIN_SAMPLES - sample_count) * POLL_INTERVAL_SEC / 3600:.1f} hrs remaining)")
    print("="*60 + "\n")


def save_prediction(engine, bearing: dict, coil: dict,
                    maintenance: dict, vib_baseline: float) -> None:
    now = datetime.now()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO predictions (
                ts, ts_unix,
                bearing_health_pct, bearing_rul_hrs,
                coil_health_pct,
                maintenance_due_hrs, next_maintenance_date,
                vib_baseline_g, notes
            ) VALUES (
                :ts, :ts_unix,
                :bearing_health_pct, :bearing_rul_hrs,
                :coil_health_pct,
                :maintenance_due_hrs, :next_maintenance_date,
                :vib_baseline_g, :notes
            )
        """), {
            "ts":                    now.isoformat(),
            "ts_unix":               now.timestamp(),
            "bearing_health_pct":    bearing["health_pct"],
            "bearing_rul_hrs":       bearing["rul_hrs"],
            "coil_health_pct":       coil["health_pct"],
            "maintenance_due_hrs":   maintenance["remaining_hrs"],
            "next_maintenance_date": maintenance["next_maintenance_date"],
            "vib_baseline_g":        vib_baseline,
            "notes":                 coil["notes"],
        })


# ──────────────────────────── FETCH ───────────────────────────────────────────

def fetch_data(host: str, port: int, timeout: int = 5) -> Optional[dict]:
    url = f"http://{host}:{port}/data"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to ESP32 at {url}")
        return None
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout connecting to {url}")
        return None
    except Exception as e:
        print(f"[ERROR] Fetch failed: {e}")
        return None


# ──────────────────────────── MAIN ────────────────────────────────────────────

def main():
    global RATED_CURRENT_A, SERVICE_INTERVAL_HRS, BEARING_L10_HRS, POLL_INTERVAL_SEC

    parser = argparse.ArgumentParser(description="ESP32 Motor Health Predictor")
    parser.add_argument("--host",          default=DEFAULT_HOST,         help="ESP32 IP address")
    parser.add_argument("--port",          default=DEFAULT_PORT,         type=int)
    parser.add_argument("--interval",      default=POLL_INTERVAL_SEC,    type=int)
    parser.add_argument("--db",            default=DATABASE_URL,         help="PostgreSQL URL")
    parser.add_argument("--report",        action="store_true",          help="Single report and exit")
    parser.add_argument("--rated-current", default=RATED_CURRENT_A,      type=float)
    parser.add_argument("--service-hrs",   default=SERVICE_INTERVAL_HRS, type=float)
    parser.add_argument("--l10-hrs",       default=BEARING_L10_HRS,      type=float)
    args = parser.parse_args()

    RATED_CURRENT_A      = args.rated_current
    SERVICE_INTERVAL_HRS = args.service_hrs
    BEARING_L10_HRS      = args.l10_hrs
    POLL_INTERVAL_SEC    = args.interval

    db_url = args.db
    print(f"Motor Health Predictor")
    print(f"  ESP32 : http://{args.host}:{args.port}/data")
    print(f"  DB    : {db_url}")
    print(f"  Rated : {RATED_CURRENT_A}A  |  Service: {SERVICE_INTERVAL_HRS}hrs  "
          f"|  L10: {BEARING_L10_HRS}hrs")
    print()

    engine = create_engine(db_url, pool_pre_ping=True)
    init_db(engine)

    if args.report:
        data = fetch_data(args.host, args.port)
        if not data:
            print("Cannot fetch data. Is ESP32 reachable?")
            return
        insert_reading(engine, data)
        uptime_s    = data.get("uptime", 0)
        bearing     = bearing_health_physics(engine, uptime_s)
        coil        = coil_health_physics(engine)
        maintenance = maintenance_prediction(engine, uptime_s)
        ml_result   = try_ml_prediction(engine)
        n           = get_sample_count(engine)
        vib_base    = compute_vibration_baseline(engine)
        print_report(data, bearing, coil, maintenance, n, ml_result)
        save_prediction(engine, bearing, coil, maintenance, vib_base)
        return

    print(f"Polling every {POLL_INTERVAL_SEC}s. Ctrl+C to stop.\n")
    last_report_time = 0.0

    while True:
        try:
            data = fetch_data(args.host, args.port)
            if data:
                insert_reading(engine, data)
                n           = get_sample_count(engine)
                uptime_s    = data.get("uptime", 0)
                bearing     = bearing_health_physics(engine, uptime_s)
                coil        = coil_health_physics(engine)
                maintenance = maintenance_prediction(engine, uptime_s)
                ml_result   = try_ml_prediction(engine)
                vib_base    = compute_vibration_baseline(engine)
                save_prediction(engine, bearing, coil, maintenance, vib_base)

                now = time.time()
                if now - last_report_time >= 1800:
                    print_report(data, bearing, coil, maintenance, n, ml_result)
                    last_report_time = now
                else:
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(
                        f"[{ts}] samples={n}  "
                        f"bearing={bearing['health_pct']}%  "
                        f"coil={coil['health_pct']}%  "
                        f"maint={maintenance['remaining_hrs']:.0f}hrs remaining  "
                        f"vib={bearing['avg_mag_g']:.4f}g"
                    )

            time.sleep(POLL_INTERVAL_SEC)

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected: {e}")
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
