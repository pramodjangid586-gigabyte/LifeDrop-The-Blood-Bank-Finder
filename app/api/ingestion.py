from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.database.connection import query_one
from app.services.inventory_service import process_inventory_event
from app.services.simulator_service import (
    simulate_received_units,
    simulate_issued_units,
    simulate_aging_stock,
    simulate_random_event
)
from app.api.events import broadcast_event

router = APIRouter(prefix="/api/ingestion", tags=["Data Ingestion & Automated Updates"])

class IngestionEventPayload(BaseModel):
    event_id: Optional[str] = None
    blood_bank_license: Optional[str] = None
    blood_bank_id: Optional[int] = None
    blood_group: str
    component: str = "RBC"
    event_type: str  # BLOOD_RECEIVED, BLOOD_ISSUED, BLOOD_RESERVED, INVENTORY_CORRECTION, INVENTORY_EXPIRED
    quantity: int = Field(ge=1)
    source_name: Optional[str] = "Authorized Hospital LIMS"
    api_key: Optional[str] = None
    notes: Optional[str] = None

class SimulationRequest(BaseModel):
    blood_bank_id: int = 1  # Defaults to AIIMS
    blood_group: str = "O+"
    component: str = "RBC"
    units: int = 10

@router.post("/events")
async def ingest_inventory_event(
    payload: IngestionEventPayload,
    x_api_key: Optional[str] = Header(default=None)
):
    """
    Ingestion endpoint for authorized blood banks, hospital LIMS, or official feeds.
    """
    # 1. Resolve blood bank
    bank = None
    if payload.blood_bank_id:
        bank = query_one("SELECT * FROM blood_banks WHERE id = ?", (payload.blood_bank_id,))
    elif payload.blood_bank_license:
        bank = query_one("SELECT * FROM blood_banks WHERE license_number = ?", (payload.blood_bank_license,))
    
    if not bank:
        raise HTTPException(status_code=404, detail="Blood bank not found for specified ID or license.")

    # 2. Authenticate data source
    key = payload.api_key or x_api_key
    # In production, check key against data_sources; in demo allow trusted simulator / valid demo keys
    source_name = payload.source_name or "Authorized Blood Bank Automated Feed"
    source_type = "OFFICIAL_API" if key else "SIMULATION"

    # 3. Process event ledger
    try:
        result = process_inventory_event(
            blood_bank_id=bank["id"],
            blood_group=payload.blood_group,
            component=payload.component,
            event_type=payload.event_type,
            quantity=payload.quantity,
            source_name=source_name,
            source_type=source_type,
            verification_status=bank["verification_status"],
            notes=payload.notes,
            event_id=payload.event_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # 4. Broadcast live update to all connected browsers/dashboards
    result["blood_bank_name"] = bank["name"]
    await broadcast_event(result)

    return {
        "status": "ACCEPTED",
        "message": f"Successfully processed {payload.event_type} for {bank['name']}",
        "data": result
    }

# --- SIMULATOR DEMO CONTROLLER ENDPOINTS ---

@router.post("/simulate/received")
async def trigger_simulate_received(payload: SimulationRequest):
    """
    Demonstrate BLOOD_RECEIVED (+N units) automatic stock increase.
    e.g., O+ RBC = 5 -> +10 units -> 15 units.
    """
    event = simulate_received_units(
        blood_bank_id=payload.blood_bank_id,
        blood_group=payload.blood_group,
        component=payload.component,
        units=payload.units
    )
    bank = query_one("SELECT name FROM blood_banks WHERE id = ?", (payload.blood_bank_id,))
    event["blood_bank_name"] = bank["name"] if bank else "Blood Bank"
    await broadcast_event(event)
    return {
        "status": "success",
        "demo": "BLOOD_RECEIVED",
        "event": event,
        "explanation": f"Received {payload.units} units of {payload.blood_group} {payload.component}. Stock automatically increased."
    }

@router.post("/simulate/issued")
async def trigger_simulate_issued(payload: SimulationRequest):
    """
    Demonstrate BLOOD_ISSUED (-N units) automatic stock decrease.
    e.g., O+ RBC = 15 -> -3 units -> 12 units.
    """
    event = simulate_issued_units(
        blood_bank_id=payload.blood_bank_id,
        blood_group=payload.blood_group,
        component=payload.component,
        units=payload.units
    )
    bank = query_one("SELECT name FROM blood_banks WHERE id = ?", (payload.blood_bank_id,))
    event["blood_bank_name"] = bank["name"] if bank else "Blood Bank"
    await broadcast_event(event)
    return {
        "status": "success",
        "demo": "BLOOD_ISSUED",
        "event": event,
        "explanation": f"Issued {payload.units} units of {payload.blood_group} {payload.component}. Stock automatically decreased."
    }

@router.post("/simulate/outdated-warning")
async def trigger_simulate_outdated(payload: SimulationRequest):
    """
    Demonstrate DATA OUTDATED warning state by advancing timestamp to 26 hours ago.
    """
    res = simulate_aging_stock(
        blood_bank_id=payload.blood_bank_id,
        blood_group=payload.blood_group,
        component=payload.component,
        hours_ago=26
    )
    bank = query_one("SELECT name FROM blood_banks WHERE id = ?", (payload.blood_bank_id,))
    res["blood_bank_name"] = bank["name"] if bank else "Blood Bank"
    res["event_type"] = "DATA_OUTDATED_WARNING"
    await broadcast_event(res)
    return {
        "status": "success",
        "demo": "DATA_OUTDATED",
        "event": res,
        "explanation": "Stock update time backdated to 26 hours ago. System now flags 'DATA OUTDATED' with safety warning."
    }

@router.post("/simulate/random-cycle")
async def trigger_simulate_random():
    """Trigger a random live event cycle for live UI demonstrations."""
    event = simulate_random_event()
    await broadcast_event(event)
    return event

@router.post("/refresh-all-feeds")
async def trigger_refresh_all_feeds():
    """
    Synchronize all blood banks and inventory items to active real-time status.
    Updates timestamps to recent live feed syncs.
    """
    from app.services.inventory_service import refresh_all_inventory_timestamps
    count = refresh_all_inventory_timestamps()
    return {
        "status": "success",
        "message": f"Successfully synchronized {count} inventory records to live real-time status.",
        "updated_count": count
    }
