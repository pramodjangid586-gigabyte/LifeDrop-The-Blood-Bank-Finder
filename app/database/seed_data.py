"""
Realistic Seed Dataset for BloodConnect
Populates authorized data sources, blood banks, diverse inventory, users, donors, and initial events.
"""

from datetime import datetime, timedelta, timezone
from app.database.connection import db_session
from app.database.models import init_db
from app.core.security import hash_password

def seed():
    init_db()
    
    with db_session() as conn:
        # Check if already seeded
        count = conn.execute("SELECT COUNT(*) as c FROM blood_banks").fetchone()["c"]
        if count > 0:
            pune_count = conn.execute("SELECT COUNT(*) as c FROM blood_banks WHERE city IN ('Pune', 'Pimpri-Chinchwad')").fetchone()["c"]
            if pune_count == 0:
                print("Existing Delhi records found. Seeding Pune & PCMC blood banks, donors, and inventory...")
                seed_pune(conn)
            else:
                print(f"Database already contains {pune_count} Pune/PCMC blood banks and Delhi records. Preserving existing records.")
            return

        print("Seeding BloodConnect database with comprehensive initial dataset...")

        # 1. Authorized Data Sources
        conn.execute("""
            INSERT INTO data_sources (id, name, source_type, api_key_hash, trust_level, is_active)
            VALUES 
            (1, 'AIIMS Integrated Hospital LIMS', 'HOSPITAL_FEED', 'hash_aiims_lims_feed_key', 'OFFICIAL', 1),
            (2, 'Indian Red Cross Society State Network', 'OFFICIAL_API', 'hash_redcross_api_key', 'OFFICIAL', 1),
            (3, 'Delhi State Blood Transfusion Council Feed', 'OFFICIAL_API', 'hash_state_council_key', 'OFFICIAL', 1),
            (4, 'Max Healthcare Central Blood Stream', 'HOSPITAL_FEED', 'hash_max_health_feed', 'VERIFIED_PARTNER', 1),
            (5, 'BloodConnect Automated Test Simulator', 'SIMULATION', 'hash_sim_test_key', 'TEST_SIMULATOR', 1)
        """)

        # 2. Blood Banks (realistic coordinates centered around Delhi NCR hub)
        blood_banks = [
            (
                1, "AIIMS Central Blood Bank & Transfusion Center", "BB-DL-AIIMS-01",
                "Sri Aurobindo Marg, Ansari Nagar", "New Delhi", "Central Delhi", "Delhi",
                28.5672, 77.2100, "+91 11 2658 8500", "+91 11 2659 4444", "bloodbank@aiims.edu",
                "24/7 Round the Clock Emergency", 1, "VERIFIED"
            ),
            (
                2, "Indian Red Cross Society National Blood Center", "BB-DL-IRCS-02",
                "1, Red Cross Road, Near Parliament", "New Delhi", "Central Delhi", "Delhi",
                28.6225, 77.2108, "+91 11 2371 6441", "+91 11 2371 6442", "bloodbank@indianredcross.org",
                "24/7 Emergency Transfusion Unit", 2, "VERIFIED"
            ),
            (
                3, "Safdarjung Hospital Regional Blood Center", "BB-DL-SJH-03",
                "Ring Road, Opposite AIIMS", "New Delhi", "South Delhi", "Delhi",
                28.5684, 77.2066, "+91 11 2616 5060", "+91 11 2616 8336", "bloodbank@safdarjung.nic.in",
                "24/7 Emergency Blood Bank", 3, "VERIFIED"
            ),
            (
                4, "Max Super Specialty Hospital Blood Center", "BB-DL-MAX-04",
                "1, 2, Press Enclave Marg, Saket", "New Delhi", "South Delhi", "Delhi",
                28.5244, 77.2167, "+91 11 2651 5050", "+91 11 4055 4055", "transfusion@maxhealthcare.com",
                "24/7 Licensed Blood Center", 4, "VERIFIED"
            ),
            (
                5, "Fortis Hospital Blood Center Shalimar Bagh", "BB-DL-FTS-05",
                "AA Block, Poorbi Shalimar Bag", "New Delhi", "North West Delhi", "Delhi",
                28.7166, 77.1547, "+91 11 4530 2222", "+91 11 4530 2233", "bloodservices@fortishealthcare.com",
                "24 Hours Open", 4, "VERIFIED"
            ),
            (
                6, "Dr. Ram Manohar Lohia Hospital Blood Bank", "BB-DL-RML-06",
                "Baba Kharak Singh Marg, Connaught Place Area", "New Delhi", "Central Delhi", "Delhi",
                28.6258, 77.1995, "+91 11 2336 5525", "+91 11 2340 4286", "bloodbank@rmlh.nic.in",
                "24/7 Trauma & Emergency Bank", 3, "VERIFIED"
            ),
            (
                7, "Community Life Care Blood Trust (Audit Pending)", "BB-DL-CLC-07",
                "Plot 14, Sector 7, Dwarka", "New Delhi", "South West Delhi", "Delhi",
                28.5835, 77.0700, "+91 11 2808 1122", "+91 11 2808 1133", "info@lifecaretrust.org",
                "08:00 AM - 10:00 PM", 5, "VERIFICATION REQUIRED"
            )
        ]

        for bb in blood_banks:
            conn.execute("""
                INSERT INTO blood_banks (
                    id, name, license_number, address, city, district, state,
                    lat, lng, phone, emergency_helpline, email, operating_hours,
                    data_source_id, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, bb)

        # 3. Users (Passwords: admin123, staff123, patient123, donor123)
        admin_hash = hash_password("admin123")
        staff_hash = hash_password("staff123")
        patient_hash = hash_password("patient123")
        donor_hash = hash_password("donor123")

        users = [
            (1, "admin@bloodconnect.org", admin_hash, "Dr. Arvind Swaminathan (Admin)", "+91 98110 00001", "ADMIN", None),
            (2, "staff.aiims@bloodconnect.org", staff_hash, "Dr. Neha Verma (AIIMS Staff)", "+91 98110 00002", "BLOOD_BANK_STAFF", 1),
            (3, "staff.redcross@bloodconnect.org", staff_hash, "Kavita Rao (Red Cross Officer)", "+91 98110 00003", "BLOOD_BANK_STAFF", 2),
            (4, "rahul.patient@gmail.com", patient_hash, "Rahul Sharma", "+91 98711 22334", "PATIENT", None),
            (5, "priya.donor@gmail.com", donor_hash, "Priya Nair", "+91 98101 55667", "DONOR", None),
            (6, "amit.donor@gmail.com", donor_hash, "Amit Patel", "+91 98202 66778", "DONOR", None),
            (7, "sneha.donor@gmail.com", donor_hash, "Sneha Kulkarni", "+91 98303 77889", "DONOR", None),
            (8, "vikram.donor@gmail.com", donor_hash, "Vikram Malhotra", "+91 98404 88990", "DONOR", None),
            (9, "ananya.donor@gmail.com", donor_hash, "Ananya Sengupta", "+91 98505 99001", "DONOR", None),
            (10, "karan.donor@gmail.com", donor_hash, "Karan Joshi", "+91 98606 11223", "DONOR", None)
        ]

        for u in users:
            conn.execute("""
                INSERT INTO users (id, email, password_hash, full_name, phone, role, assigned_blood_bank_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, u)

        # 4. Donor Profiles (Protected, approx coordinates rounded to ~1-2km)
        donors = [
            # user_id, blood_group, city, area_name, approx_lat, approx_lng, is_available, last_donation_date, preferred_contact, status, total
            (5, "O+", "New Delhi", "Saket / Malviya Nagar", 28.525, 77.215, 1, "2026-04-10", "IN_APP", "VERIFIED", 4),
            (6, "O-", "New Delhi", "Connaught Place / CP", 28.631, 77.218, 1, "2026-03-01", "CALL", "VERIFIED", 8),
            (7, "B+", "New Delhi", "Dwarka Sector 10", 28.585, 77.060, 1, "2026-05-15", "WHATSAPP", "VERIFIED", 3),
            (8, "A+", "New Delhi", "Rohini Sector 7", 28.710, 77.120, 1, "2026-02-20", "SMS", "VERIFIED", 5),
            (9, "AB+", "Noida", "Sector 62", 28.628, 77.365, 0, "2026-08-10", "IN_APP", "VERIFIED", 2), # Recently donated / unavailable
            (10, "O+", "Gurugram", "Cyber City / DLF Phase 2", 28.490, 77.090, 1, "2026-01-10", "IN_APP", "VERIFICATION REQUIRED", 1)
        ]

        for d in donors:
            conn.execute("""
                INSERT INTO donor_profiles (
                    user_id, blood_group, city, area_name, approx_lat, approx_lng,
                    is_available, last_donation_date, preferred_contact, verification_status, total_donations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, d)

        # 5. Blood Inventory
        # Notice: AIIMS starts with O+ RBC = 5 units exactly as in the user prompt example!
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        outdated_str = (datetime.now(timezone.utc) - timedelta(hours=28)).strftime("%Y-%m-%d %H:%M:%S")

        stock_items = [
            # AIIMS Central
            (1, "O+", "RBC", 5, 1, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),
            (1, "O-", "RBC", 2, 0, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),
            (1, "A+", "RBC", 14, 2, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),
            (1, "B+", "RBC", 9, 1, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),
            (1, "AB+", "RBC", 7, 0, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),
            (1, "AB-", "RBC", 0, 0, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),
            (1, "O+", "PLATELETS", 6, 0, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),
            (1, "O+", "PLASMA", 12, 0, now_str, "AIIMS Integrated Hospital LIMS", "VERIFIED"),

            # Red Cross (notice: O+ RBC is purposefully outdated by 28 hours to demonstrate OUTDATED state!)
            (2, "O+", "RBC", 16, 0, outdated_str, "Indian Red Cross Society State Network", "VERIFIED"),
            (2, "O-", "RBC", 3, 0, outdated_str, "Indian Red Cross Society State Network", "VERIFIED"),
            (2, "B+", "RBC", 11, 0, now_str, "Indian Red Cross Society State Network", "VERIFIED"),
            (2, "A+", "RBC", 8, 0, now_str, "Indian Red Cross Society State Network", "VERIFIED"),
            (2, "O+", "WHOLE_BLOOD", 15, 0, now_str, "Indian Red Cross Society State Network", "VERIFIED"),

            # Safdarjung
            (3, "O+", "RBC", 8, 2, now_str, "Delhi State Blood Transfusion Council Feed", "VERIFIED"),
            (3, "O-", "RBC", 1, 0, now_str, "Delhi State Blood Transfusion Council Feed", "VERIFIED"),
            (3, "B+", "RBC", 18, 1, now_str, "Delhi State Blood Transfusion Council Feed", "VERIFIED"),
            (3, "B+", "PLATELETS", 4, 0, now_str, "Delhi State Blood Transfusion Council Feed", "VERIFIED"),

            # Max Saket
            (4, "O+", "RBC", 12, 0, now_str, "Max Healthcare Central Blood Stream", "VERIFIED"),
            (4, "A+", "RBC", 10, 0, now_str, "Max Healthcare Central Blood Stream", "VERIFIED"),
            (4, "AB+", "PLATELETS", 5, 0, now_str, "Max Healthcare Central Blood Stream", "VERIFIED"),

            # Fortis Shalimar Bagh
            (5, "O+", "RBC", 7, 0, now_str, "Max Healthcare Central Blood Stream", "VERIFIED"),
            (5, "B+", "RBC", 6, 0, now_str, "Max Healthcare Central Blood Stream", "VERIFIED"),

            # RML Hospital
            (6, "O+", "RBC", 11, 1, now_str, "Delhi State Blood Transfusion Council Feed", "VERIFIED"),
            (6, "O-", "RBC", 4, 0, now_str, "Delhi State Blood Transfusion Council Feed", "VERIFIED"),

            # Unverified Trust (Dwarka)
            (7, "O+", "RBC", 9, 0, now_str, "BloodConnect Automated Test Simulator", "VERIFICATION REQUIRED")
        ]

        for s in stock_items:
            conn.execute("""
                INSERT INTO blood_inventory (
                    blood_bank_id, blood_group, component, units_available, units_reserved,
                    last_updated_at, data_source_name, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, s)

        # 6. Initial Inventory Events (Audit trail)
        events = [
            ("evt-init-001", 1, "O+", "RBC", "BLOOD_RECEIVED", 5, 5, "AIIMS Integrated Hospital LIMS", "HOSPITAL_FEED", "VERIFIED", now_str, "Initial stock baseline receipt"),
            ("evt-init-002", 1, "A+", "RBC", "BLOOD_RECEIVED", 14, 14, "AIIMS Integrated Hospital LIMS", "HOSPITAL_FEED", "VERIFIED", now_str, "Scheduled voluntary blood camp lot intake"),
            ("evt-init-003", 2, "O+", "RBC", "BLOOD_RECEIVED", 16, 16, "Indian Red Cross Society State Network", "OFFICIAL_API", "VERIFIED", outdated_str, "Routine red cross collection cycle")
        ]

        for ev in events:
            conn.execute("""
                INSERT INTO inventory_events (
                    event_id, blood_bank_id, blood_group, component, event_type,
                    quantity_change, resulting_units, source_name, source_type,
                    verification_status, recorded_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ev)

        # 7. Initial Emergency Requests
        conn.execute("""
            INSERT INTO emergency_requests (
                id, requester_id, patient_name, hospital_name, hospital_city,
                hospital_lat, hospital_lng, blood_group, component, units_required,
                urgency_level, contact_phone, notes, status, created_at
            ) VALUES 
            (1, 4, 'Suresh Sharma', 'AIIMS Trauma Center', 'New Delhi', 28.5672, 77.2100, 'O+', 'RBC', 2, 'CRITICAL_1HR', '+91 98711 22334', 'Patient scheduled for emergency cardiac surgery at OT-3', 'OPEN', ?),
            (2, 4, 'Kavita Gupta', 'Safdarjung Hospital Pediatric Ward', 'New Delhi', 28.5684, 77.2066, 'B+', 'PLATELETS', 1, 'URGENT_6HR', '+91 98711 22334', 'Severe dengue with low platelet count', 'OPEN', ?)
        """, (now_str, now_str))

        # 8. Notification to matching donor
        conn.execute("""
            INSERT INTO notifications (user_id, title, message, notification_type, reference_id, is_read, created_at)
            VALUES (5, 'CRITICAL BLOOD REQUEST NEARBY', 'Emergency O+ RBC requested at AIIMS Trauma Center (approx. 4.8 km from your area).', 'EMERGENCY_REQUEST', 1, 0, ?)
        """, (now_str,))

        # Call Pune seeding for complete coverage
        seed_pune(conn)
        print("Database successfully seeded with comprehensive real-world dataset (Delhi & Pune).")

def seed_pune(conn):
    """
    Seed verified Pune and PCMC (Maharashtra) blood banks, donors, and baseline inventory.
    Keeps all existing records completely intact.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # 1. Maharashtra Data Source
    conn.execute("""
        INSERT OR IGNORE INTO data_sources (id, name, source_type, api_key_hash, trust_level, is_active)
        VALUES 
        (6, 'Maharashtra State Blood Transfusion Council Feed', 'OFFICIAL_API', 'hash_sbtc_mah_feed_key', 'OFFICIAL', 1)
    """)

    # 2. 10 Verified Pune & PCMC Blood Banks (exact pinpoint coordinates)
    pune_banks = [
        (
            8, "Sassoon General Hospital & B.J. Govt Medical College Blood Centre", "BB-MH-PUN-01",
            "Station Road, Near Pune Railway Station, Sassoon Road", "Pune", "Pune", "Maharashtra",
            18.52570, 73.87190, "+91 20 2612 8000", "+91 20 2612 8050", "bloodbank@bjmcpmc.gov.in",
            "24/7 Round the Clock Emergency", 6, "VERIFIED"
        ),
        (
            9, "KEM Hospital & Research Centre Blood Bank", "BB-MH-PUN-02",
            "489, Sardar Moodliar Road, Rasta Peth", "Pune", "Pune", "Maharashtra",
            18.52025, 73.86712, "+91 20 2606 1000", "+91 20 6603 7300", "bloodbank@kemhospitalpune.org",
            "24/7 Emergency Transfusion Unit", 6, "VERIFIED"
        ),
        (
            10, "Deenanath Mangeshkar Hospital & Research Center Blood Bank", "BB-MH-PUN-03",
            "Near Mhatre Bridge, Erandwane", "Pune", "Pune", "Maharashtra",
            18.50198, 73.83217, "+91 20 4015 1000", "+91 20 4915 3100", "bloodbank@dmhospital.org",
            "24/7 Round the Clock Emergency", 6, "VERIFIED"
        ),
        (
            11, "Ruby Hall Clinic Blood Centre (Grant Medical Foundation)", "BB-MH-PUN-04",
            "40, Sassoon Road, Sangamvadi", "Pune", "Pune", "Maharashtra",
            18.53340, 73.87710, "+91 20 2616 3391", "+91 20 6645 5100", "bloodcentre@rubyhall.com",
            "24/7 Emergency Transfusion Unit", 6, "VERIFIED"
        ),
        (
            12, "Jankalyan Raktakendra (Charitable Blood Centre)", "BB-MH-PUN-05",
            "1003, Shukrawar Peth, Swargate / Saras Baug Road", "Pune", "Pune", "Maharashtra",
            18.50618, 73.84034, "+91 20 2444 9527", "+91 20 2444 1952", "contact@jankalyanraktakendra.org",
            "24/7 Round the Clock Service", 6, "VERIFIED"
        ),
        (
            13, "YCM Hospital Regional Blood Centre (PCMC)", "BB-MH-PUN-06",
            "Sant Tukaram Nagar, Pimpri Colony", "Pimpri-Chinchwad", "Pune", "Maharashtra",
            18.62200, 73.82110, "+91 20 2742 0000", "+91 20 2742 2291", "ycmhbloodbank@pcmcindia.gov.in",
            "24/7 Round the Clock Emergency", 6, "VERIFIED"
        ),
        (
            14, "Sahyadri Super Speciality Hospital Blood Centre", "BB-MH-PUN-07",
            "Plot No. 30 C, Erandwane, Karve Road, Deccan", "Pune", "Pune", "Maharashtra",
            18.51340, 73.84070, "+91 20 6721 3000", "+91 20 6721 3333", "bloodbank.deccan@sahyadrihospitals.com",
            "24/7 Licensed Blood Center", 6, "VERIFIED"
        ),
        (
            15, "AFMC Department of Transfusion Medicine & Blood Centre", "BB-MH-PUN-08",
            "Southern Command, Solapur Road, Wanowrie", "Pune", "Pune", "Maharashtra",
            18.50710, 73.89200, "+91 20 2633 4200", "+91 20 2630 6000", "transfusion@afmc.nic.in",
            "24/7 Defense & Emergency Services", 6, "VERIFIED"
        ),
        (
            16, "Poona Hospital & Research Centre Blood Bank", "BB-MH-PUN-09",
            "27, Sadashiv Peth, Near Alka Talkies", "Pune", "Pune", "Maharashtra",
            18.51063, 73.84195, "+91 20 2433 1795", "+91 20 6609 6000", "bloodbank@poonahospital.org",
            "24/7 Trauma & Emergency Bank", 6, "VERIFIED"
        ),
        (
            17, "Aditya Birla Memorial Hospital Blood Centre", "BB-MH-PUN-10",
            "Aditya Birla Hospital Marg, Thergaon, Chinchwad", "Pimpri-Chinchwad", "Pune", "Maharashtra",
            18.62890, 73.77440, "+91 20 3071 7500", "+91 20 3071 7777", "bloodbank@adityabirla.com",
            "24/7 Emergency Transfusion Unit", 6, "VERIFIED"
        )
    ]

    for pb in pune_banks:
        conn.execute("""
            INSERT OR IGNORE INTO blood_banks (
                id, name, license_number, address, city, district, state,
                lat, lng, phone, emergency_helpline, email, operating_hours,
                data_source_id, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pb)

    # 3. Pune Users & Volunteer Donors
    donor_hash = hash_password("donor123")
    pune_users = [
        (11, "tanvi.pune@gmail.com", donor_hash, "Tanvi Deshmukh", "+91 98220 11223", "DONOR", None),
        (12, "rohit.pune@gmail.com", donor_hash, "Rohit Joshi", "+91 98220 22334", "DONOR", None),
        (13, "shruti.pcmc@gmail.com", donor_hash, "Shruti Patil", "+91 98220 33445", "DONOR", None),
        (14, "sachin.pune@gmail.com", donor_hash, "Sachin Kulkarni", "+91 98220 44556", "DONOR", None),
        (15, "pooja.pune@gmail.com", donor_hash, "Pooja Shinde", "+91 98220 55667", "DONOR", None)
    ]

    for u in pune_users:
        conn.execute("""
            INSERT OR IGNORE INTO users (id, email, password_hash, full_name, phone, role, assigned_blood_bank_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, u)

    pune_donors = [
        (11, "O+", "Pune", "Kothrud / Paud Road", 18.508, 73.808, 1, "2026-05-10", "IN_APP", "VERIFIED", 4),
        (12, "O-", "Pune", "Shivajinagar / FC Road", 18.530, 73.845, 1, "2026-04-18", "CALL", "VERIFIED", 6),
        (13, "B+", "Pimpri-Chinchwad", "Pimpri / Thergaon", 18.622, 73.818, 1, "2026-06-01", "WHATSAPP", "VERIFIED", 3),
        (14, "A+", "Pune", "Baner / Aundh", 18.558, 73.790, 1, "2026-03-25", "SMS", "VERIFIED", 5),
        (15, "AB+", "Pune", "Hadapsar / Magarpatta", 18.508, 73.926, 1, "2026-07-12", "IN_APP", "VERIFIED", 2)
    ]

    for d in pune_donors:
        conn.execute("""
            INSERT OR IGNORE INTO donor_profiles (
                user_id, blood_group, city, area_name, approx_lat, approx_lng,
                is_available, last_donation_date, preferred_contact, verification_status, total_donations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, d)

    # 4. Realistic Sample Baseline Inventory for Pune & PCMC Blood Banks
    feed_label = "Maharashtra State Blood Transfusion Council Feed (Sample Baseline)"
    pune_stock = [
        # Sassoon General Hospital (ID 8)
        (8, "O+", "RBC", 14, 2, now_str, feed_label, "VERIFIED"),
        (8, "O-", "RBC", 4, 0, now_str, feed_label, "VERIFIED"),
        (8, "A+", "RBC", 11, 1, now_str, feed_label, "VERIFIED"),
        (8, "B+", "RBC", 16, 2, now_str, feed_label, "VERIFIED"),
        (8, "AB+", "RBC", 6, 0, now_str, feed_label, "VERIFIED"),
        (8, "O+", "PLATELETS", 8, 0, now_str, feed_label, "VERIFIED"),
        (8, "O+", "PLASMA", 10, 0, now_str, feed_label, "VERIFIED"),
        (8, "A+", "WHOLE_BLOOD", 7, 0, now_str, feed_label, "VERIFIED"),

        # KEM Hospital (ID 9)
        (9, "O+", "RBC", 12, 1, now_str, feed_label, "VERIFIED"),
        (9, "O-", "RBC", 3, 0, now_str, feed_label, "VERIFIED"),
        (9, "A+", "RBC", 9, 0, now_str, feed_label, "VERIFIED"),
        (9, "B+", "RBC", 15, 1, now_str, feed_label, "VERIFIED"),
        (9, "AB+", "RBC", 5, 0, now_str, feed_label, "VERIFIED"),
        (9, "B+", "PLATELETS", 6, 0, now_str, feed_label, "VERIFIED"),
        (9, "O+", "PLASMA", 8, 0, now_str, feed_label, "VERIFIED"),

        # Deenanath Mangeshkar Hospital (ID 10)
        (10, "O+", "RBC", 18, 2, now_str, feed_label, "VERIFIED"),
        (10, "O-", "RBC", 5, 1, now_str, feed_label, "VERIFIED"),
        (10, "A+", "RBC", 14, 1, now_str, feed_label, "VERIFIED"),
        (10, "A-", "RBC", 2, 0, now_str, feed_label, "VERIFIED"),
        (10, "B+", "RBC", 20, 3, now_str, feed_label, "VERIFIED"),
        (10, "AB+", "RBC", 8, 0, now_str, feed_label, "VERIFIED"),
        (10, "AB-", "RBC", 2, 0, now_str, feed_label, "VERIFIED"),
        (10, "O+", "PLATELETS", 12, 0, now_str, feed_label, "VERIFIED"),
        (10, "O+", "PLASMA", 15, 0, now_str, feed_label, "VERIFIED"),

        # Ruby Hall Clinic (ID 11)
        (11, "O+", "RBC", 15, 2, now_str, feed_label, "VERIFIED"),
        (11, "O-", "RBC", 3, 0, now_str, feed_label, "VERIFIED"),
        (11, "A+", "RBC", 12, 1, now_str, feed_label, "VERIFIED"),
        (11, "B+", "RBC", 14, 1, now_str, feed_label, "VERIFIED"),
        (11, "AB+", "RBC", 7, 0, now_str, feed_label, "VERIFIED"),
        (11, "O+", "PLATELETS", 9, 0, now_str, feed_label, "VERIFIED"),
        (11, "B+", "PLATELETS", 5, 0, now_str, feed_label, "VERIFIED"),
        (11, "O+", "PLASMA", 10, 0, now_str, feed_label, "VERIFIED"),

        # Jankalyan Raktakendra (Charitable) (ID 12)
        (12, "O+", "RBC", 22, 2, now_str, feed_label, "VERIFIED"),
        (12, "O-", "RBC", 6, 1, now_str, feed_label, "VERIFIED"),
        (12, "A+", "RBC", 16, 2, now_str, feed_label, "VERIFIED"),
        (12, "B+", "RBC", 19, 2, now_str, feed_label, "VERIFIED"),
        (12, "AB+", "RBC", 9, 0, now_str, feed_label, "VERIFIED"),
        (12, "O+", "WHOLE_BLOOD", 18, 0, now_str, feed_label, "VERIFIED"),
        (12, "O+", "PLATELETS", 10, 0, now_str, feed_label, "VERIFIED"),
        (12, "O+", "PLASMA", 14, 0, now_str, feed_label, "VERIFIED"),

        # YCM Hospital PCMC (ID 13)
        (13, "O+", "RBC", 16, 2, now_str, feed_label, "VERIFIED"),
        (13, "O-", "RBC", 4, 0, now_str, feed_label, "VERIFIED"),
        (13, "A+", "RBC", 10, 1, now_str, feed_label, "VERIFIED"),
        (13, "B+", "RBC", 14, 2, now_str, feed_label, "VERIFIED"),
        (13, "AB+", "RBC", 6, 0, now_str, feed_label, "VERIFIED"),
        (13, "O+", "PLATELETS", 7, 0, now_str, feed_label, "VERIFIED"),
        (13, "O+", "PLASMA", 11, 0, now_str, feed_label, "VERIFIED"),

        # Sahyadri Super Speciality (ID 14)
        (14, "O+", "RBC", 9, 1, now_str, feed_label, "VERIFIED"),
        (14, "O-", "RBC", 2, 0, now_str, feed_label, "VERIFIED"),
        (14, "A+", "RBC", 8, 0, now_str, feed_label, "VERIFIED"),
        (14, "B+", "RBC", 11, 1, now_str, feed_label, "VERIFIED"),
        (14, "AB+", "RBC", 4, 0, now_str, feed_label, "VERIFIED"),
        (14, "O+", "PLATELETS", 5, 0, now_str, feed_label, "VERIFIED"),

        # AFMC Blood Centre (ID 15)
        (15, "O+", "RBC", 14, 2, now_str, feed_label, "VERIFIED"),
        (15, "O-", "RBC", 5, 1, now_str, feed_label, "VERIFIED"),
        (15, "A+", "RBC", 12, 1, now_str, feed_label, "VERIFIED"),
        (15, "B+", "RBC", 15, 2, now_str, feed_label, "VERIFIED"),
        (15, "AB+", "RBC", 6, 0, now_str, feed_label, "VERIFIED"),
        (15, "O+", "PLASMA", 12, 0, now_str, feed_label, "VERIFIED"),
        (15, "O+", "WHOLE_BLOOD", 10, 0, now_str, feed_label, "VERIFIED"),

        # Poona Hospital (ID 16)
        (16, "O+", "RBC", 10, 1, now_str, feed_label, "VERIFIED"),
        (16, "O-", "RBC", 2, 0, now_str, feed_label, "VERIFIED"),
        (16, "A+", "RBC", 7, 0, now_str, feed_label, "VERIFIED"),
        (16, "B+", "RBC", 12, 1, now_str, feed_label, "VERIFIED"),
        (16, "AB+", "RBC", 5, 0, now_str, feed_label, "VERIFIED"),
        (16, "O+", "PLATELETS", 6, 0, now_str, feed_label, "VERIFIED"),

        # Aditya Birla Memorial Hospital PCMC (ID 17)
        (17, "O+", "RBC", 13, 2, now_str, feed_label, "VERIFIED"),
        (17, "O-", "RBC", 3, 0, now_str, feed_label, "VERIFIED"),
        (17, "A+", "RBC", 11, 1, now_str, feed_label, "VERIFIED"),
        (17, "B+", "RBC", 14, 2, now_str, feed_label, "VERIFIED"),
        (17, "AB+", "RBC", 5, 0, now_str, feed_label, "VERIFIED"),
        (17, "O+", "PLATELETS", 8, 0, now_str, feed_label, "VERIFIED"),
        (17, "O+", "PLASMA", 9, 0, now_str, feed_label, "VERIFIED")
    ]

    for ps in pune_stock:
        conn.execute("""
            INSERT OR IGNORE INTO blood_inventory (
                blood_bank_id, blood_group, component, units_available, units_reserved,
                last_updated_at, data_source_name, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ps)

    # 5. Audit Events for Pune intake
    pune_events = [
        ("evt-pune-init-001", 8, "O+", "RBC", "BLOOD_RECEIVED", 14, 14, "Maharashtra State Blood Transfusion Council Feed", "OFFICIAL_API", "VERIFIED", now_str, "Initial baseline stock sync via SBTC feed"),
        ("evt-pune-init-002", 12, "O+", "RBC", "BLOOD_RECEIVED", 22, 22, "Maharashtra State Blood Transfusion Council Feed", "OFFICIAL_API", "VERIFIED", now_str, "Voluntary camp intake batch sync"),
        ("evt-pune-init-003", 13, "O+", "RBC", "BLOOD_RECEIVED", 16, 16, "Maharashtra State Blood Transfusion Council Feed", "OFFICIAL_API", "VERIFIED", now_str, "PCMC regional hospital baseline receipt")
    ]

    for pev in pune_events:
        conn.execute("""
            INSERT OR IGNORE INTO inventory_events (
                event_id, blood_bank_id, blood_group, component, event_type,
                quantity_change, resulting_units, source_name, source_type,
                verification_status, recorded_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pev)

    print("Pune & PCMC dataset successfully seeded (10 blood banks, 5 donors, baseline inventory).")

if __name__ == "__main__":
    seed()
