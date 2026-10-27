import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from app.services.inventory_service import process_inventory_event
from app.database.connection import query_all, db_session
from app.core.compatibility import BLOOD_GROUPS

SIMULATOR_SOURCE = "Authorized Blood Bank Automated Feed (Demo)"

def simulate_received_units(
    blood_bank_id: int, 
    blood_group: str = "O+", 
    component: str = "RBC", 
    units: int = 10
) -> Dict[str, Any]:
    """Demonstrate BLOOD_RECEIVED (+N units) automatic update."""
    return process_inventory_event(
        blood_bank_id=blood_bank_id,
        blood_group=blood_group,
        component=component,
        event_type="BLOOD_RECEIVED",
        quantity=units,
        source_name=SIMULATOR_SOURCE,
        source_type="SIMULATION",
        verification_status="VERIFIED",
        notes=f"Simulated voluntary donation drive intake (+{units} units)"
    )

def simulate_issued_units(
    blood_bank_id: int, 
    blood_group: str = "O+", 
    component: str = "RBC", 
    units: int = 3
) -> Dict[str, Any]:
    """Demonstrate BLOOD_ISSUED (-N units) automatic update."""
    return process_inventory_event(
        blood_bank_id=blood_bank_id,
        blood_group=blood_group,
        component=component,
        event_type="BLOOD_ISSUED",
        quantity=units,
        source_name=SIMULATOR_SOURCE,
        source_type="SIMULATION",
        verification_status="VERIFIED",
        notes=f"Simulated emergency room patient issuance (-{units} units)"
    )

def simulate_aging_stock(
    blood_bank_id: int, 
    blood_group: str = "O+", 
    component: str = "RBC", 
    hours_ago: int = 26
) -> Dict[str, Any]:
    """
    Demonstrate DATA OUTDATED state by intentionally backdating the last update time.
    Shows the user the safety warning: 'Availability information may be outdated...'
    """
    old_time = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
    with db_session() as conn:
        conn.execute(
            """
            UPDATE blood_inventory 
            SET last_updated_at = ? 
            WHERE blood_bank_id = ? AND blood_group = ? AND component = ?
            """,
            (old_time, blood_bank_id, blood_group, component)
        )
    return {
        "blood_bank_id": blood_bank_id,
        "blood_group": blood_group,
        "component": component,
        "backdated_to": old_time,
        "hours_ago": hours_ago,
        "status": "BACKDATED_FOR_OUTDATED_WARNING_DEMO"
    }

def simulate_random_event() -> Dict[str, Any]:
    """Trigger a realistic random inventory delta for live demonstration."""
    banks = query_all("SELECT id, name FROM blood_banks WHERE verification_status = 'VERIFIED' LIMIT 5")
    if not banks:
        return {"error": "No blood banks available"}

    bank = random.choice(banks)
    group = random.choice(["O+", "O-", "A+", "B+"])
    component = "RBC"
    
    # 60% chance of received, 40% chance of issued
    if random.random() > 0.4:
        units = random.randint(5, 12)
        event = simulate_received_units(bank["id"], group, component, units)
    else:
        units = random.randint(1, 4)
        event = simulate_issued_units(bank["id"], group, component, units)

    event["blood_bank_name"] = bank["name"]
    return event
