from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database.connection import query_all, query_one, execute_cmd
from app.services.distance_service import haversine_distance, resolve_location_name, resolve_search_coordinates
from app.core.compatibility import get_compatible_donor_groups, normalize_blood_group, DISCLAIMER_ELIGIBILITY
from app.api.auth import require_auth
from app.core.config import settings

router = APIRouter(prefix="/api/donors", tags=["Donor Finder & Profiles"])

class AvailabilityToggleSchema(BaseModel):
    is_available: bool

class DonorProfileUpdateSchema(BaseModel):
    blood_group: Optional[str] = None
    city: Optional[str] = None
    area_name: Optional[str] = None
    preferred_contact: Optional[str] = None
    last_donation_date: Optional[str] = None

@router.get("/search")
def search_donors(
    blood_group: Optional[str] = Query(default=None, description="Patient's required blood group e.g. O+, A-"),
    component: Optional[str] = Query(default="RBC", description="Component required"),
    lat: Optional[float] = Query(default=None),
    lng: Optional[float] = Query(default=None),
    location: Optional[str] = Query(default=None),
    radius: float = Query(default=30.0, ge=1.0, le=150.0),
    include_unavailable: bool = Query(default=False),
    include_compatible: bool = Query(default=True, description="Include scientifically compatible donor groups")
):
    # Resolve search coordinates (handles explicit lat/lng, GPS, or location name)
    search_lat, search_lng, resolved_area = resolve_search_coordinates(
        lat=lat,
        lng=lng,
        location=location,
        default_lat=settings.DEFAULT_LAT,
        default_lng=settings.DEFAULT_LNG,
        default_name="Central Delhi Hub"
    )

    matching_groups = []
    if blood_group:
        clean_group = normalize_blood_group(blood_group)
        if include_compatible:
            matching_groups = get_compatible_donor_groups(clean_group, component)
        else:
            matching_groups = [clean_group]

    # Fetch donors with user display name
    query = """
        SELECT 
            d.id as donor_profile_id,
            d.blood_group,
            d.city,
            d.area_name,
            d.approx_lat,
            d.approx_lng,
            d.is_available,
            d.last_donation_date,
            d.verification_status,
            d.total_donations,
            d.preferred_contact,
            u.id as user_id,
            u.full_name
        FROM donor_profiles d
        JOIN users u ON u.id = d.user_id
        WHERE u.is_active = 1
    """
    params = []
    if not include_unavailable:
        query += " AND d.is_available = 1"

    donors = query_all(query, tuple(params))

    results = []
    for d in donors:
        # Check blood group filter
        if matching_groups and d["blood_group"] not in matching_groups:
            continue

        dist = haversine_distance(search_lat, search_lng, d["approx_lat"], d["approx_lng"])
        if dist > radius:
            continue

        # Mask donor name for privacy (e.g., Priya N. or Priya Nair)
        parts = d["full_name"].split()
        if len(parts) > 1:
            masked_name = f"{parts[0]} {parts[1][0]}."
        else:
            masked_name = parts[0]

        results.append({
            "donor_profile_id": d["donor_profile_id"],
            "display_name": masked_name,
            "blood_group": d["blood_group"],
            "general_area": f"{d['area_name']}, {d['city']}" if d["area_name"] else d["city"],
            "approx_lat": d["approx_lat"],
            "approx_lng": d["approx_lng"],
            "distance_km": dist,
            "is_available": bool(d["is_available"]),
            "verification_status": d["verification_status"],
            "total_donations": d["total_donations"],
            "last_donation_date": d["last_donation_date"],
            "preferred_contact": d["preferred_contact"]
        })

    # Sort by distance
    results.sort(key=lambda x: x["distance_km"])

    return {
        "search_center": {
            "lat": search_lat,
            "lng": search_lng,
            "resolved_name": resolved_area
        },
        "query_group": blood_group,
        "compatible_groups_searched": matching_groups,
        "medical_eligibility_notice": DISCLAIMER_ELIGIBILITY,
        "total_results": len(results),
        "results": results
    }

@router.put("/availability")
def toggle_availability(payload: AvailabilityToggleSchema, user: Dict[str, Any] = Depends(require_auth)):
    if user["role"] not in ["DONOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only registered donors can toggle donor availability.")
    
    val = 1 if payload.is_available else 0
    execute_cmd(
        "UPDATE donor_profiles SET is_available = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
        (val, user["id"])
    )
    return {
        "status": "success",
        "is_available": payload.is_available,
        "message": "Donor availability updated to " + ("AVAILABLE" if payload.is_available else "NOT CURRENTLY AVAILABLE")
    }

@router.get("/my-profile")
def get_my_donor_profile(user: Dict[str, Any] = Depends(require_auth)):
    if user["role"] not in ["DONOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Not a registered donor account.")

    donor = query_one("""
        SELECT d.*, u.full_name, u.email, u.phone
        FROM donor_profiles d
        JOIN users u ON u.id = d.user_id
        WHERE d.user_id = ?
    """, (user["id"],))

    if not donor:
        raise HTTPException(status_code=404, detail="Donor profile not found.")

    return {
        "profile": donor,
        "medical_guidance": DISCLAIMER_ELIGIBILITY
    }
