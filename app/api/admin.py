from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.database.connection import query_all, query_one, execute_cmd, execute_insert
from app.api.auth import require_auth

router = APIRouter(prefix="/api/admin", tags=["Administrator Management"])

class VerificationUpdateSchema(BaseModel):
    status: str  # 'VERIFIED', 'UNVERIFIED', 'VERIFICATION REQUIRED'

class DataSourceCreateSchema(BaseModel):
    name: str
    source_type: str  # 'OFFICIAL_API', 'HOSPITAL_FEED', 'SIMULATION'
    trust_level: str  # 'OFFICIAL', 'VERIFIED_PARTNER', 'TEST_SIMULATOR'

def require_admin(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user

@router.get("/overview")
def get_admin_overview(admin: Dict[str, Any] = Depends(require_admin)):
    total_banks = query_one("SELECT COUNT(*) as c FROM blood_banks")["c"]
    total_donors = query_one("SELECT COUNT(*) as c FROM donor_profiles")["c"]
    available_donors = query_one("SELECT COUNT(*) as c FROM donor_profiles WHERE is_available = 1")["c"]
    total_units = query_one("SELECT SUM(units_available) as s FROM blood_inventory")["s"] or 0
    open_requests = query_one("SELECT COUNT(*) as c FROM emergency_requests WHERE status = 'OPEN'")["c"]
    pending_verifications = (
        query_one("SELECT COUNT(*) as c FROM blood_banks WHERE verification_status != 'VERIFIED'")["c"] +
        query_one("SELECT COUNT(*) as c FROM donor_profiles WHERE verification_status != 'VERIFIED'")["c"]
    )
    total_events = query_one("SELECT COUNT(*) as c FROM inventory_events")["c"]

    return {
        "total_blood_banks": total_banks,
        "total_donors": total_donors,
        "available_donors": available_donors,
        "total_units_in_stock": total_units,
        "open_emergency_requests": open_requests,
        "pending_verifications": pending_verifications,
        "total_inventory_events_logged": total_events
    }

@router.get("/blood-banks")
def list_admin_blood_banks(admin: Dict[str, Any] = Depends(require_admin)):
    return query_all("""
        SELECT b.*, s.name as data_source_name, s.trust_level,
               (SELECT SUM(units_available) FROM blood_inventory WHERE blood_bank_id = b.id) as total_units
        FROM blood_banks b
        LEFT JOIN data_sources s ON s.id = b.data_source_id
        ORDER BY b.id ASC
    """)

@router.put("/blood-banks/{bank_id}/verification")
def update_bank_verification(
    bank_id: int, 
    payload: VerificationUpdateSchema, 
    admin: Dict[str, Any] = Depends(require_admin)
):
    status = payload.status.upper().strip()
    if status not in ["VERIFIED", "UNVERIFIED", "VERIFICATION REQUIRED"]:
        raise HTTPException(status_code=400, detail="Invalid verification status.")

    execute_cmd(
        "UPDATE blood_banks SET verification_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, bank_id)
    )
    # Also update stock verification status
    execute_cmd(
        "UPDATE blood_inventory SET verification_status = ? WHERE blood_bank_id = ?",
        (status, bank_id)
    )
    return {"status": "success", "message": f"Blood bank status updated to {status}."}

@router.get("/donors")
def list_admin_donors(admin: Dict[str, Any] = Depends(require_admin)):
    return query_all("""
        SELECT d.*, u.full_name, u.email, u.phone
        FROM donor_profiles d
        JOIN users u ON u.id = d.user_id
        ORDER BY d.id ASC
    """)

@router.put("/donors/{donor_id}/verification")
def update_donor_verification(
    donor_id: int, 
    payload: VerificationUpdateSchema, 
    admin: Dict[str, Any] = Depends(require_admin)
):
    status = payload.status.upper().strip()
    if status not in ["VERIFIED", "UNVERIFIED", "VERIFICATION REQUIRED"]:
        raise HTTPException(status_code=400, detail="Invalid verification status.")

    execute_cmd(
        "UPDATE donor_profiles SET verification_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, donor_id)
    )
    return {"status": "success", "message": f"Donor status updated to {status}."}

@router.get("/data-sources")
def list_data_sources(admin: Dict[str, Any] = Depends(require_admin)):
    return query_all("SELECT * FROM data_sources ORDER BY id ASC")

@router.post("/data-sources")
def add_data_source(payload: DataSourceCreateSchema, admin: Dict[str, Any] = Depends(require_admin)):
    ds_id = execute_insert(
        """
        INSERT INTO data_sources (name, source_type, api_key_hash, trust_level, is_active)
        VALUES (?, ?, 'hash_' || lower(hex(randomblob(16))), ?, 1)
        """,
        (payload.name.strip(), payload.source_type, payload.trust_level)
    )
    return {"status": "success", "id": ds_id, "message": f"Data source '{payload.name}' registered."}

@router.get("/audit-logs")
def get_audit_logs(limit: int = 100, admin: Dict[str, Any] = Depends(require_admin)):
    return query_all("""
        SELECT e.*, b.name as blood_bank_name
        FROM inventory_events e
        JOIN blood_banks b ON b.id = e.blood_bank_id
        ORDER BY e.recorded_at DESC
        LIMIT ?
    """, (limit,))
