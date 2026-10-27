from app.core.compatibility import (
    get_compatible_donor_groups,
    get_compatible_recipient_groups,
    DISCLAIMER_ELIGIBILITY,
    DISCLAIMER_PLATFORM
)
from app.services.distance_service import haversine_distance, resolve_location_name

def test_blood_compatibility_rules():
    """Verify scientific ABO and Rh compatibility matching."""
    # O+ patient can receive RBC from O- and O+
    o_pos_donors = get_compatible_donor_groups("O+", "RBC")
    assert "O-" in o_pos_donors
    assert "O+" in o_pos_donors
    assert "A+" not in o_pos_donors

    # O- is universal donor for RBC
    o_neg_recipients = get_compatible_recipient_groups("O-", "RBC")
    assert len(o_neg_recipients) == 8  # All groups

    # AB+ is universal recipient for RBC
    ab_pos_donors = get_compatible_donor_groups("AB+", "RBC")
    assert len(ab_pos_donors) == 8  # Can receive from all

    # Plasma: AB is universal donor, O is universal recipient
    ab_plasma_recipients = get_compatible_recipient_groups("AB+", "PLASMA")
    assert "O+" in ab_plasma_recipients

def test_haversine_distance_calculation():
    """Test distance calculation between known landmarks."""
    # AIIMS (28.5672, 77.2100) to Connaught Place (28.6315, 77.2167) is approx 7.2 km
    dist = haversine_distance(28.5672, 77.2100, 28.6315, 77.2167)
    assert 6.0 <= dist <= 8.5

def test_location_name_resolution():
    """Test resolution of text queries to coordinates for both Delhi and Pune regions."""
    resolved_saket = resolve_location_name("Saket")
    assert resolved_saket is not None
    assert resolved_saket[2] == "Saket"

    resolved_pune = resolve_location_name("Pune")
    assert resolved_pune is not None
    assert resolved_pune[2] == "Pune"
    assert abs(resolved_pune[0] - 18.5204) < 0.001

    resolved_pcmc = resolve_location_name("Pimpri-Chinchwad")
    assert resolved_pcmc is not None
    assert "Pimpri" in resolved_pcmc[2]

    resolved_kothrud = resolve_location_name("Kothrud")
    assert resolved_kothrud is not None
    assert resolved_kothrud[2] == "Kothrud"

def test_pune_haversine_distance():
    """Test distance calculation between Sassoon Hospital and YCM Hospital in Pune/PCMC."""
    # Sassoon (18.5258, 73.8722) to YCM Hospital (18.6250, 73.8210) ~12.2 km
    dist = haversine_distance(18.5258, 73.8722, 18.6250, 73.8210)
    assert 11.0 <= dist <= 14.0

def test_required_disclaimers_present():
    """Disclaimers must contain required regulatory language."""
    assert "Eligibility must be confirmed according to applicable blood-donation guidelines" in DISCLAIMER_ELIGIBILITY
    assert "coordination platform" in DISCLAIMER_PLATFORM
