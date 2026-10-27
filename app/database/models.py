"""
Database schema definition and initialization for BloodConnect.
"""

from app.database.connection import db_session

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'OFFICIAL_API', 'HOSPITAL_FEED', 'SIMULATION'
    api_key_hash TEXT NOT NULL,
    trust_level TEXT NOT NULL, -- 'OFFICIAL', 'VERIFIED_PARTNER', 'TEST_SIMULATOR'
    is_active INTEGER NOT NULL DEFAULT 1,
    last_heartbeat_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blood_banks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    license_number TEXT UNIQUE NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    district TEXT,
    state TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    phone TEXT NOT NULL,
    emergency_helpline TEXT,
    email TEXT,
    operating_hours TEXT DEFAULT '24/7 Emergency Service',
    data_source_id INTEGER REFERENCES data_sources(id),
    verification_status TEXT NOT NULL DEFAULT 'VERIFIED', -- 'UNVERIFIED', 'VERIFIED', 'VERIFICATION_REQUIRED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL, -- 'PATIENT', 'DONOR', 'BLOOD_BANK_STAFF', 'ADMIN'
    assigned_blood_bank_id INTEGER REFERENCES blood_banks(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS donor_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL,
    city TEXT NOT NULL,
    area_name TEXT,
    approx_lat REAL NOT NULL,
    approx_lng REAL NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 1,
    last_donation_date DATE,
    preferred_contact TEXT DEFAULT 'IN_APP', -- 'CALL', 'SMS', 'WHATSAPP', 'IN_APP'
    verification_status TEXT NOT NULL DEFAULT 'VERIFIED', -- 'UNVERIFIED', 'VERIFIED', 'VERIFICATION_REQUIRED'
    total_donations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blood_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL,
    component TEXT NOT NULL, -- 'RBC', 'WHOLE_BLOOD', 'PLATELETS', 'PLASMA', 'CRYO'
    units_available INTEGER NOT NULL DEFAULT 0,
    units_reserved INTEGER NOT NULL DEFAULT 0,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source_name TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'VERIFIED',
    UNIQUE(blood_bank_id, blood_group, component)
);

CREATE TABLE IF NOT EXISTS inventory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id),
    blood_group TEXT NOT NULL,
    component TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'BLOOD_RECEIVED', 'BLOOD_ISSUED', 'BLOOD_RESERVED', 'INVENTORY_CORRECTION', 'INVENTORY_EXPIRED'
    quantity_change INTEGER NOT NULL,
    resulting_units INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'VERIFIED',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS emergency_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL REFERENCES users(id),
    patient_name TEXT NOT NULL,
    hospital_name TEXT NOT NULL,
    hospital_city TEXT NOT NULL,
    hospital_lat REAL NOT NULL,
    hospital_lng REAL NOT NULL,
    blood_group TEXT NOT NULL,
    component TEXT NOT NULL,
    units_required INTEGER NOT NULL DEFAULT 1,
    urgency_level TEXT NOT NULL, -- 'CRITICAL_1HR', 'URGENT_6HR', 'STANDARD_24HR'
    contact_phone TEXT NOT NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'PARTIALLY_FULFILLED', 'FULFILLED', 'CANCELLED', 'EXPIRED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS donor_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES emergency_requests(id) ON DELETE CASCADE,
    donor_profile_id INTEGER NOT NULL REFERENCES donor_profiles(id),
    response_type TEXT NOT NULL, -- 'CAN_HELP', 'NOT_AVAILABLE'
    note TEXT,
    contact_number_shared TEXT,
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(request_id, donor_profile_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT NOT NULL, -- 'EMERGENCY_REQUEST', 'DONOR_RESPONSE', 'INVENTORY_ALERT', 'SYSTEM'
    reference_id INTEGER,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_blood_banks_coords ON blood_banks(lat, lng);
CREATE INDEX IF NOT EXISTS idx_donor_profiles_coords ON donor_profiles(approx_lat, approx_lng);
CREATE INDEX IF NOT EXISTS idx_donor_profiles_group ON donor_profiles(blood_group, is_available);
CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON blood_inventory(blood_group, component, units_available);
CREATE INDEX IF NOT EXISTS idx_events_lookup ON inventory_events(blood_bank_id, blood_group, recorded_at);
CREATE INDEX IF NOT EXISTS idx_requests_status ON emergency_requests(status, urgency_level);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
"""

def init_db():
    """Execute DDL schema to set up all tables and indexes."""
    with db_session() as conn:
        conn.executescript(SCHEMA_SQL)
