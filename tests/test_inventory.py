import pytest
from app.services.inventory_service import process_inventory_event, calculate_availability_status
from app.database.connection import query_one
from app.database.seed_data import seed

@pytest.fixture(autouse=True)
def setup_database():
    seed()

def test_inventory_addition_and_subtraction():
    """
    Test the exact example in the prompt:
    Initial: O+ RBC = 5 units
    Simulated update: +10 units -> 15 units
    Another update: -3 units -> 12 units
    """
    # 1. Check initial state for AIIMS (bank_id=1)
    # Ensure baseline is set to 5
    process_inventory_event(
        blood_bank_id=1,
        blood_group="O+",
        component="RBC",
        event_type="INVENTORY_CORRECTION",
        quantity=5,
        source_name="Test Setup"
    )

    stock_initial = query_one(
        "SELECT units_available FROM blood_inventory WHERE blood_bank_id = 1 AND blood_group = 'O+' AND component = 'RBC'"
    )
    assert stock_initial["units_available"] == 5

    # 2. Receive 10 units
    received_res = process_inventory_event(
        blood_bank_id=1,
        blood_group="O+",
        component="RBC",
        event_type="BLOOD_RECEIVED",
        quantity=10,
        source_name="Authorized Blood Bank"
    )
    assert received_res["resulting_units"] == 15
    assert received_res["quantity_change"] == 10

    stock_after_add = query_one(
        "SELECT units_available FROM blood_inventory WHERE blood_bank_id = 1 AND blood_group = 'O+' AND component = 'RBC'"
    )
    assert stock_after_add["units_available"] == 15

    # 3. Issue 3 units
    issued_res = process_inventory_event(
        blood_bank_id=1,
        blood_group="O+",
        component="RBC",
        event_type="BLOOD_ISSUED",
        quantity=3,
        source_name="Authorized Blood Bank"
    )
    assert issued_res["resulting_units"] == 12
    assert issued_res["quantity_change"] == -3

    stock_after_sub = query_one(
        "SELECT units_available FROM blood_inventory WHERE blood_bank_id = 1 AND blood_group = 'O+' AND component = 'RBC'"
    )
    assert stock_after_sub["units_available"] == 12

def test_prevent_negative_inventory():
    """Issuing more than available stock should cap at 0 without negative stock."""
    process_inventory_event(
        blood_bank_id=1,
        blood_group="AB-",
        component="RBC",
        event_type="INVENTORY_CORRECTION",
        quantity=2,
        source_name="Test Setup"
    )

    res = process_inventory_event(
        blood_bank_id=1,
        blood_group="AB-",
        component="RBC",
        event_type="BLOOD_ISSUED",
        quantity=5,
        source_name="Test Hospital"
    )
    assert res["resulting_units"] == 0

def test_outdated_status_and_disclaimer():
    """Stock older than 24 hours must be classified as DATA OUTDATED with warning."""
    old_time = "2026-09-10 10:00:00"
    stat = calculate_availability_status(
        units_available=10,
        last_updated_at=old_time,
        facility_verification="VERIFIED",
        threshold_hours=24
    )
    assert stat["status"] == "DATA OUTDATED"
    assert stat["is_outdated"] is True
    assert "Availability information may be outdated" in stat["outdated_warning"]

def test_idempotency_duplicate_rejection():
    """Duplicate event_id must be rejected to prevent double counting."""
    import uuid
    evt_id = f"test-unique-idemp-{uuid.uuid4().hex[:10]}"
    process_inventory_event(
        blood_bank_id=1,
        blood_group="B+",
        component="RBC",
        event_type="BLOOD_RECEIVED",
        quantity=2,
        source_name="Test API",
        event_id=evt_id
    )

    with pytest.raises(ValueError, match="Duplicate event_id detected"):
        process_inventory_event(
            blood_bank_id=1,
            blood_group="B+",
            component="RBC",
            event_type="BLOOD_RECEIVED",
            quantity=2,
            source_name="Test API",
            event_id=evt_id
        )
