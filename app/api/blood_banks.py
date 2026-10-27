from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.database.connection import query_all, query_one
from app.services.distance_service import haversine_distance, resolve_location_name, resolve_search_coordinates, KNOWN_LOCATIONS
from app.services.inventory_service import calculate_availability_status, get_inventory_history
from app.core.compatibility import normalize_blood_group
from app.core.config import settings

router = APIRouter(prefix="/api/blood-banks", tags=["Blood Banks & Stock Search"])

@router.get("/search")
def search_blood_banks(
    blood_group: Optional[str] = Query(default=None, description="Blood group e.g. O+, A-"),
    component: Optional[str] = Query(default="RBC", description="Blood component e.g. RBC, PLATELETS"),
    units_required: int = Query(default=1, ge=1),
    lat: Optional[float] = Query(default=None),
    lng: Optional[float] = Query(default=None),
    location: Optional[str] = Query(default=None, description="Manual city / area query"),
    radius: float = Query(default=35.0, ge=1.0, le=200.0, description="Radius in km")
):
    # Resolve search coordinates (handles explicit lat/lng, GPS, or location name)
    search_lat, search_lng, resolved_area_name = resolve_search_coordinates(
        lat=lat,
        lng=lng,
        location=location,
        default_lat=settings.DEFAULT_LAT,
        default_lng=settings.DEFAULT_LNG,
        default_name="Central Delhi (Default Hub)"
    )

    clean_group = normalize_blood_group(blood_group) if blood_group else None
    clean_comp = component.strip().upper() if component else "RBC"

    # Query all active blood banks
    banks = query_all("""
        SELECT b.*, s.name as data_source_name, s.trust_level
        FROM blood_banks b
        LEFT JOIN data_sources s ON s.id = b.data_source_id
    """)

    results = []
    for bank in banks:
        dist = haversine_distance(search_lat, search_lng, bank["lat"], bank["lng"])
        if dist > radius:
            continue

        # Fetch inventory for the requested group/component if specified
        stock_query = """
            SELECT units_available, units_reserved, last_updated_at, data_source_name, verification_status
            FROM blood_inventory
            WHERE blood_bank_id = ?
        """
        params = [bank["id"]]
        if clean_group:
            stock_query += " AND blood_group = ? AND component = ?"
            params.extend([clean_group, clean_comp])
            stock_row = query_one(stock_query, tuple(params))
        else:
            stock_row = None

        if stock_row:
            status_info = calculate_availability_status(
                units_available=stock_row["units_available"],
                last_updated_at=stock_row["last_updated_at"],
                facility_verification=bank["verification_status"],
                threshold_hours=settings.OUTDATED_THRESHOLD_HOURS
            )
            units_avail = stock_row["units_available"]
            last_updated = stock_row["last_updated_at"]
            inv_source = stock_row["data_source_name"]
        else:
            # If no specific stock row found or no filter applied
            if clean_group:
                units_avail = 0
                last_updated = bank["updated_at"]
                inv_source = bank["data_source_name"] or "Hospital System"
                status_info = calculate_availability_status(
                    units_available=0,
                    last_updated_at=last_updated,
                    facility_verification=bank["verification_status"]
                )
            else:
                # Count total units available in this facility
                total_stock = query_one(
                    "SELECT SUM(units_available) as total FROM blood_inventory WHERE blood_bank_id = ?",
                    (bank["id"],)
                )
                units_avail = total_stock["total"] or 0
                last_updated = bank["updated_at"]
                inv_source = bank["data_source_name"] or "Authorized Feed"
                status_info = calculate_availability_status(
                    units_available=units_avail,
                    last_updated_at=last_updated,
                    facility_verification=bank["verification_status"]
                )

        results.append({
            "id": bank["id"],
            "name": bank["name"],
            "license_number": bank["license_number"],
            "address": bank["address"],
            "city": bank["city"],
            "district": bank["district"],
            "lat": bank["lat"],
            "lng": bank["lng"],
            "distance_km": dist,
            "phone": bank["phone"],
            "emergency_helpline": bank["emergency_helpline"],
            "operating_hours": bank["operating_hours"],
            "verification_status": bank["verification_status"],
            "blood_group": clean_group or "All Groups",
            "component": clean_comp,
            "units_available": units_avail,
            "units_required": units_required,
            "last_updated_at": last_updated,
            "data_source": inv_source,
            "availability_status": status_info["status"],
            "badge_class": status_info["badge_class"],
            "is_outdated": status_info["is_outdated"],
            "hours_since_update": status_info["hours_since_update"],
            "outdated_warning": status_info["outdated_warning"]
        })

    # Sort results by distance ascending
    results.sort(key=lambda x: x["distance_km"])

    return {
        "search_center": {
            "lat": search_lat,
            "lng": search_lng,
            "resolved_name": resolved_area_name
        },
        "radius_km": radius,
        "query_group": clean_group,
        "query_component": clean_comp,
        "total_results": len(results),
        "results": results
    }

@router.get("/{bank_id}")
def get_blood_bank_details(bank_id: int):
    bank = query_one("""
        SELECT b.*, s.name as data_source_name, s.trust_level
        FROM blood_banks b
        LEFT JOIN data_sources s ON s.id = b.data_source_id
        WHERE b.id = ?
    """, (bank_id,))
    if not bank:
        raise HTTPException(status_code=404, detail="Blood bank facility not found.")

    inventory = query_all("""
        SELECT * FROM blood_inventory 
        WHERE blood_bank_id = ? 
        ORDER BY blood_group, component
    """, (bank_id,))

    processed_inventory = []
    for item in inventory:
        stat = calculate_availability_status(
            units_available=item["units_available"],
            last_updated_at=item["last_updated_at"],
            facility_verification=bank["verification_status"],
            threshold_hours=settings.OUTDATED_THRESHOLD_HOURS
        )
        processed_inventory.append({
            **item,
            "status": stat["status"],
            "badge_class": stat["badge_class"],
            "is_outdated": stat["is_outdated"],
            "hours_since_update": stat["hours_since_update"],
            "outdated_warning": stat["outdated_warning"]
        })

    return {
        "blood_bank": bank,
        "inventory": processed_inventory
    }

@router.get("/{bank_id}/history")
def get_bank_history(bank_id: int, limit: int = 50):
    return get_inventory_history(bank_id, limit=limit)
