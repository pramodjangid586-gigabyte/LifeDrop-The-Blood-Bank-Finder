from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.database.connection import query_all, query_one, execute_insert, execute_cmd
from app.services.distance_service import haversine_distance, resolve_location_name
from app.core.compatibility import get_compatible_donor_groups, DISCLAIMER_PLATFORM
from app.api.auth import require_auth
from app.core.config import settings

router = APIRouter(prefix="/api/emergency", tags=["Emergency Requests & Matching"])

class EmergencyRequestCreateSchema(BaseModel):
    patient_name: str = Field(min_length=2)
    hospital_name: str = Field(min_length=3)
    hospital_city: str = Field(default="New Delhi")
    hospital_location: Optional[str] = None
    hospital_lat: Optional[float] = None
    hospital_lng: Optional[float] = None
    blood_group: str
    component: str = "RBC"
    units_required: int = Field(default=1, ge=1, le=20)
    urgency_level: str = "CRITICAL_1HR"  # CRITICAL_1HR, URGENT_6HR, STANDARD_24HR
    contact_phone: str = Field(min_length=8)
    notes: Optional[str] = None

class DonorResponseSchema(BaseModel):
    response_type: str  # CAN_HELP, NOT_AVAILABLE
    note: Optional[str] = None
    contact_number_shared: Optional[str] = None

@router.post("/create")
def create_emergency_request(payload: EmergencyRequestCreateSchema, user: Dict[str, Any] = Depends(require_auth)):
    lat = payload.hospital_lat
    lng = payload.hospital_lng

    if (lat is None or lng is None) and payload.hospital_location:
        resolved = resolve_location_name(payload.hospital_location)
        if resolved:
            lat, lng, _ = resolved

    if lat is None or lng is None:
        lat = settings.DEFAULT_LAT
        lng = settings.DEFAULT_LNG

    clean_group = payload.blood_group.strip().upper()
    clean_comp = payload.component.strip().upper()

    request_id = execute_insert(
        """
        INSERT INTO emergency_requests (
            requester_id, patient_name, hospital_name, hospital_city,
            hospital_lat, hospital_lng, blood_group, component,
            units_required, urgency_level, contact_phone, notes, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
        """,
        (
            user["id"], payload.patient_name.strip(), payload.hospital_name.strip(),
            payload.hospital_city.strip(), lat, lng, clean_group, clean_comp,
            payload.units_required, payload.urgency_level, payload.contact_phone.strip(),
            payload.notes
        )
    )

    # Find matching nearby available donors to notify
    compatible_groups = get_compatible_donor_groups(clean_group, clean_comp)
    
    donors = query_all("""
        SELECT d.id as donor_profile_id, d.user_id, d.approx_lat, d.approx_lng, d.blood_group
        FROM donor_profiles d
        WHERE d.is_available = 1
    """)

    notified_count = 0
    for d in donors:
        if d["blood_group"] in compatible_groups:
            dist = haversine_distance(lat, lng, d["approx_lat"], d["approx_lng"])
            if dist <= 30.0:  # Within 30 km radius
                msg = f"EMERGENCY: {payload.units_required} unit(s) of {clean_group} ({clean_comp}) urgently needed at {payload.hospital_name} (~{dist:.1f} km away). Can you help?"
                execute_insert(
                    """
                    INSERT INTO notifications (user_id, title, message, notification_type, reference_id)
                    VALUES (?, 'URGENT BLOOD REQUEST NEAR YOU', ?, 'EMERGENCY_REQUEST', ?)
                    """,
                    (d["user_id"], msg, request_id)
                )
                notified_count += 1

    return {
        "status": "success",
        "request_id": request_id,
        "matching_donors_notified": notified_count,
        "disclaimer": DISCLAIMER_PLATFORM,
        "message": f"Emergency request broadcasted. {notified_count} eligible nearby donor(s) were notified."
    }

@router.get("/active")
def list_active_emergency_requests(
    limit: int = 20,
    blood_group: Optional[str] = None
):
    sql = """
        SELECT r.*, u.full_name as requester_name,
               (SELECT COUNT(*) FROM donor_responses WHERE request_id = r.id AND response_type = 'CAN_HELP') as helpers_count
        FROM emergency_requests r
        JOIN users u ON u.id = r.requester_id
        WHERE r.status = 'OPEN'
    """
    params = []
    if blood_group:
        sql += " AND r.blood_group = ?"
        params.append(blood_group.strip().upper())

    sql += " ORDER BY CASE r.urgency_level WHEN 'CRITICAL_1HR' THEN 1 WHEN 'URGENT_6HR' THEN 2 ELSE 3 END, r.created_at DESC LIMIT ?"
    params.append(limit)

    requests = query_all(sql, tuple(params))
    return {
        "total": len(requests),
        "disclaimer": DISCLAIMER_PLATFORM,
        "requests": requests
    }

@router.get("/my-requests")
def get_my_requests(user: Dict[str, Any] = Depends(require_auth)):
    requests = query_all("""
        SELECT * FROM emergency_requests 
        WHERE requester_id = ? 
        ORDER BY created_at DESC
    """, (user["id"],))

    detailed_requests = []
    for r in requests:
        responses = query_all("""
            SELECT resp.*, d.blood_group, d.city, d.area_name, u.full_name as donor_name
            FROM donor_responses resp
            JOIN donor_profiles d ON d.id = resp.donor_profile_id
            JOIN users u ON u.id = d.user_id
            WHERE resp.request_id = ?
            ORDER BY resp.responded_at DESC
        """, (r["id"],))
        detailed_requests.append({
            **r,
            "responses": responses
        })

    return {"requests": detailed_requests}

@router.post("/{request_id}/respond")
def respond_to_emergency_request(
    request_id: int, 
    payload: DonorResponseSchema, 
    user: Dict[str, Any] = Depends(require_auth)
):
    donor_profile = query_one("SELECT id, blood_group FROM donor_profiles WHERE user_id = ?", (user["id"],))
    if not donor_profile:
        raise HTTPException(status_code=403, detail="Only registered donors can submit a response.")

    req = query_one("SELECT * FROM emergency_requests WHERE id = ?", (request_id,))
    if not req:
        raise HTTPException(status_code=404, detail="Emergency request not found.")

    resp_type = payload.response_type.upper().strip()
    if resp_type not in ["CAN_HELP", "NOT_AVAILABLE"]:
        raise HTTPException(status_code=400, detail="Response must be 'CAN_HELP' or 'NOT_AVAILABLE'.")

    # Upsert donor response
    execute_cmd(
        """
        INSERT INTO donor_responses (request_id, donor_profile_id, response_type, note, contact_number_shared)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(request_id, donor_profile_id) DO UPDATE SET
            response_type = ?,
            note = ?,
            contact_number_shared = ?,
            responded_at = CURRENT_TIMESTAMP
        """,
        (
            request_id, donor_profile["id"], resp_type, payload.note, payload.contact_number_shared,
            resp_type, payload.note, payload.contact_number_shared
        )
    )

    # Notify requester if donor can help
    if resp_type == "CAN_HELP":
        execute_insert(
            """
            INSERT INTO notifications (user_id, title, message, notification_type, reference_id)
            VALUES (?, 'A DONOR HAS VOLUNTEERED TO HELP!', ?, 'DONOR_RESPONSE', ?)
            """,
            (
                req["requester_id"],
                f"A donor ({donor_profile['blood_group']}) can help with your request for {req['blood_group']} at {req['hospital_name']}! Contact: {payload.contact_number_shared or 'Via BloodConnect'}",
                request_id
            )
        )

    return {
        "status": "success",
        "message": "Your response has been recorded. Thank you for your support!",
        "response_type": resp_type
    }
