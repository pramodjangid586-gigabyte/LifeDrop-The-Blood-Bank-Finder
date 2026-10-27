# BloodConnect – Emergency Blood & Donor Finder

BloodConnect is an emergency blood-coordination web platform engineered around **automated data ingestion** from authorized blood banks and hospital laboratory information management systems (LIMS). It helps patients in urgent need quickly find nearby blood stock and compatible volunteer donors without relying on manual data entry or hardcoded inventories.

---

## Key System Features

1. **Automatic Data Updates & Ingestion Layer**:
   - Webhook & API gateway (`POST /api/ingestion/events`) accepts authenticated stock updates from hospital systems and regional blood portals.
   - Handles transactions: `BLOOD_RECEIVED`, `BLOOD_ISSUED`, `BLOOD_RESERVED`, `INVENTORY_CORRECTION`, and `INVENTORY_EXPIRED`.
   - Immutable audit ledger in `inventory_events` table tracking every quantity delta (+10, -3, etc.), timestamp, and source.
   - Built-in Simulation Engine to test real-world events (+10 units received, -3 units issued, and backdating stock >24h to trigger outdated alerts).
   - Real-time Server-Sent Events (SSE) push live updates to the frontend without requiring a page refresh.

2. **Real-World Limitation & Compliance**:
   - Strictly enforces real-world integrity: does not scrape third-party websites without permission and never invents real-time blood availability.
   - Development data is explicitly tagged as `source_type: "SIMULATION"`.
   - Dynamic classification of inventory states:
     - **`AVAILABLE`** ($\ge 5$ units)
     - **`LIMITED`** ($1 - 4$ units)
     - **`NOT AVAILABLE`** ($0$ units)
     - **`DATA OUTDATED`** ($> 24$ hours since last verified feed update), accompanied by the prominent advisory:
       > *"Availability information may be outdated. Please contact the blood bank before travelling."*
     - **`VERIFICATION REQUIRED`** (unverified facilities).

3. **Role-Based Access Control (RBAC)**:
   - **Normal User / Patient**: Search blood banks and donors, view distance-sorted stock, create Emergency Blood Requests, and receive donor help notifications.
   - **Donor**: Profile management, instant availability toggle (`AVAILABLE` / `NOT CURRENTLY AVAILABLE`), nearby emergency request inbox, and "I CAN HELP" responses.
   - **Blood Bank Staff**: Dedicated dashboard for their assigned facility, real-time inventory overview, manual physical count reconciliation, and incoming event history.
   - **Administrator**: Oversight panel to verify facilities and donors (`VERIFIED`, `UNVERIFIED`, `VERIFICATION REQUIRED`), manage authorized data sources, and review system-wide audit logs.

4. **Donor Privacy & Safety Controls**:
   - Exact home addresses and GPS coordinates are never publicly exposed. Coordinates are fuzzed to a ~1-2 km neighborhood grid center (`approx_lat`, `approx_lng`).
   - Contact numbers remain private until a donor actively volunteers for an emergency request.
   - Prominently displays the mandatory medical advisory:
     > *"Eligibility must be confirmed according to applicable blood-donation guidelines."*

5. **Nearby Distance & Map Navigation**:
   - Geolocation search using the Haversine formula and spatial radius filtering (10 km, 20 km, 35 km, 50 km).
   - Interactive Leaflet.js / OpenStreetMap integration with color-coded stock pins (Green/Yellow/Red/Orange) and one-click "Get Directions" navigation to Google Maps.

---

## Project Structure

```
BloodConnect/
├── app/
│   ├── api/
│   │   ├── auth.py              # Register, Login, Forgot Password, Profile, Logout
│   │   ├── blood_banks.py       # Nearby blood bank search, details, facilities
│   │   ├── donors.py            # Donor search, profile updates, availability toggle
│   │   ├── emergency.py         # Emergency blood requests, donor matching, responses
│   │   ├── ingestion.py         # Webhook receiver for inventory events & simulator
│   │   ├── events.py            # Server-Sent Events (SSE) live broadcast bus
│   │   ├── admin.py             # Blood bank & donor verification, data source mgmt
│   │   └── notifications.py     # In-app user notifications router
│   ├── core/
│   │   ├── config.py            # Configuration settings & defaults
│   │   ├── security.py          # bcrypt password hashing & JWT token validation
│   │   └── compatibility.py     # ABO/Rh compatibility rules & legal disclaimers
│   ├── database/
│   │   ├── connection.py        # SQLite connection manager with WAL mode
│   │   ├── models.py            # Database DDL schema and indexes
│   │   └── seed_data.py         # Comprehensive seed data for blood banks, stock, donors
│   ├── services/
│   │   ├── inventory_service.py # Event application, ledger audit, recency evaluation
│   │   ├── distance_service.py  # Haversine spatial calculations & city resolver
│   │   └── simulator_service.py # Automated stock increase, decrease, and aging runner
│   ├── static/
│   │   ├── css/custom.css       # High-contrast emergency theme & flash animations
│   │   └── js/
│   │       ├── app.js           # Client utilities, toasts, simulator helpers
│   │       ├── map.js           # Leaflet.js map visualizer, pins, and radius circle
│   │       └── live_stream.js   # SSE event listener for dynamic DOM updates
│   ├── templates/
│   │   ├── base.html            # Layout with emergency header, navbar, alerts
│   │   ├── index.html           # Emergency-focused homepage with quick search
│   │   ├── search_blood.html    # Blood bank finder with filters & distance sort
│   │   ├── search_donors.html   # Privacy-first donor finder with request help modal
│   │   ├── map_view.html        # Interactive map view with radius overlay
│   │   ├── emergency_request.html # Emergency request creation form
│   │   ├── login.html           # Login with 1-click test credentials
│   │   ├── register.html        # Role-based registration
│   │   ├── forgot_password.html # Password recovery workflow
│   │   ├── profile.html         # User profile management
│   │   ├── dashboards/
│   │   │   ├── user_dashboard.html       # Patient request tracking & notifications
│   │   │   ├── donor_dashboard.html      # Availability toggle & nearby requests
│   │   │   ├── blood_bank_dashboard.html # Inventory manager & event history
│   │   │   └── admin_dashboard.html      # Verifications & data source manager
│   │   └── components/
│   │       ├── disclaimers.html          # Medical & coordination safety notices
│   │       └── simulation_modal.html     # Interactive simulator control drawer
│   └── main.py                  # FastAPI application entrypoint & lifespan manager
├── tests/
│   ├── test_inventory.py        # Automated tests for event ledger, delta, recency
│   ├── test_matching.py         # Automated tests for blood compatibility & distance
│   └── test_auth.py             # Automated tests for bcrypt hashing & JWT tokens
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Default Test Accounts & Credentials

For fast review and evaluation, pre-seeded accounts are provided:

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@bloodconnect.org` | `admin123` | Full system access, data source management, verifications |
| **Blood Bank Staff** | `staff.aiims@bloodconnect.org` | `staff123` | Assigned to AIIMS Central Blood Bank & Transfusion Center |
| **Blood Bank Staff** | `staff.redcross@bloodconnect.org` | `staff123` | Assigned to Indian Red Cross Society National Blood Center |
| **Patient / User** | `rahul.patient@gmail.com` | `patient123` | Has active emergency requests and received donor responses |
| **Donor (O+)** | `priya.donor@gmail.com` | `donor123` | Verified donor, South Delhi / Saket, Available |
| **Donor (O-)** | `amit.donor@gmail.com` | `donor123` | Verified universal donor, Central Delhi / Connaught Place |

*Tip: The Login page (`/login`) includes 1-click login buttons for each of these test accounts.*

---

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated Test Suite
```bash
python -m pytest tests/
```

### 3. Start the Web Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser at: **`http://127.0.0.1:8000`**  
API Documentation (Swagger UI): **`http://127.0.0.1:8000/docs`**

---

## Demonstrating Automated Ingestion & Stock Updates

Click the floating **"⚡ Ingestion Simulator (Demo)"** button at the bottom-right of any page to open the simulator drawer:

1. **Blood Received (+10 Units)**: Click `1. Blood Received (+10 Units)` to simulate a lot intake (e.g., 5 $\rightarrow$ 15 units). The search table flashes green and updates immediately via SSE.
2. **Blood Issued (-3 Units)**: Click `2. Blood Issued (-3 Units)` to simulate an emergency transfusion (15 $\rightarrow$ 12 units). The search table flashes red and decreases immediately.
3. **Simulate Outdated Stock (>24h)**: Click `3. Simulate Outdated Stock (>24h)` to backdate an inventory record to 26 hours ago. The status dynamically changes to **`DATA OUTDATED`**, and an advisory alert appears.

---

## Connecting Authorized Real-World Feeds

To connect an official hospital LIMS or blood bank system:
Send an authenticated HTTP POST request to:
`POST /api/ingestion/events`

**Headers**:
- `Content-Type: application/json`
- `X-API-Key: <registered_source_api_key>`

**Payload**:
```json
{
  "event_id": "evt-hospital-tx-98210",
  "blood_bank_license": "BB-DL-AIIMS-01",
  "blood_group": "O+",
  "component": "RBC",
  "event_type": "BLOOD_RECEIVED",
  "quantity": 10,
  "source_name": "AIIMS Central LIMS Blood Bank Server",
  "notes": "Verified cold storage intake lot #2026-981"
}
```

The system will deduplicate the event, verify the source, record the audit entry, recompute the availability status, and push the live update to connected clients.
