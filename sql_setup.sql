-- Registered devices table
CREATE TABLE devices (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    description     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ,
    last_ai_analysis_at TIMESTAMPTZ,
    location        TEXT,
    firmware_version TEXT
);

-- Stores every ESP32 reading
CREATE TABLE sensor_readings (
    id          BIGSERIAL PRIMARY KEY,
    device_id   TEXT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Motor
    motor_running   BOOLEAN,
    rpm             INTEGER,
    pulse           INTEGER,
    uptime_seconds  BIGINT,
    
    -- Power
    voltage     FLOAT,
    current     FLOAT,
    power       FLOAT,
    power_factor FLOAT,
    energy      FLOAT,
    frequency   FLOAT,
    
    -- Temperature
    temp1       FLOAT,
    temp2       FLOAT,
    
    -- Vibration
    accel_x     FLOAT,
    accel_y     FLOAT,
    accel_z     FLOAT,
    tap_detected BOOLEAN,
    
    -- Faults
    fault_overcurrent  BOOLEAN,
    fault_overtemp     BOOLEAN,
    fault_stall        BOOLEAN,
    fault_vibration    BOOLEAN,
    fault_overvoltage  BOOLEAN,
    fault_undervoltage BOOLEAN,

    -- Protection Configurations
    prot_max_current FLOAT,
    prot_max_temp FLOAT,
    prot_min_rpm FLOAT,
    prot_overvoltage FLOAT,
    prot_undervoltage FLOAT,
    prot_stall_current FLOAT,
    prot_startup_grace INTEGER,
    prot_fault_trip_count INTEGER,
    prot_vibration_ack_grace INTEGER,
    prot_tap_threshold_mg INTEGER,   -- ADXL345 tap threshold in milli-g
    prot_tap_duration_us  INTEGER,   -- ADXL345 tap duration in micro-seconds

    -- Maintenance Data
    maint_next_time TEXT,
    maint_total_hours FLOAT,
    maint_hours_limit FLOAT,
    maint_total_seconds BIGINT,
    maint_limit_seconds BIGINT
);

-- Stores fault events only (not every reading)
CREATE TABLE fault_events (
    id          BIGSERIAL PRIMARY KEY,
    device_id   TEXT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fault_type  TEXT NOT NULL,  -- 'overcurrent', 'overtemp', etc.
    value       FLOAT,          -- the sensor value that triggered it
    resolved    BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ
);

-- Stores prediction results
CREATE TABLE predictions (
    id              BIGSERIAL PRIMARY KEY,
    device_id       TEXT NOT NULL,
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prediction_type TEXT NOT NULL,  -- 'bearing_fault', 'overheating', 'stall_risk'
    confidence      FLOAT,          -- 0.0 to 1.0
    severity        TEXT,           -- 'low', 'medium', 'high'
    details         JSONB
);

-- Indexes for fast queries
CREATE INDEX idx_devices_active ON devices(is_active);
CREATE INDEX idx_readings_device_ts ON sensor_readings(device_id, ts DESC);
CREATE INDEX idx_faults_device_ts   ON fault_events(device_id, ts DESC);
CREATE INDEX idx_predictions_device ON predictions(device_id, ts DESC);
