"""
Blood group compatibility rules, medical advisories, and disclaimer constants.
"""

from typing import List, Set

BLOOD_GROUPS = ["O-", "O+", "B-", "B+", "A-", "A+", "AB-", "AB+"]

BLOOD_COMPONENTS = [
    ("RBC", "Red Blood Cells (PRBC)"),
    ("WHOLE_BLOOD", "Whole Blood"),
    ("PLATELETS", "Platelets (RDP/SDP)"),
    ("PLASMA", "Fresh Frozen Plasma (FFP)"),
    ("CRYO", "Cryoprecipitate")
]

# Recipient -> Compatible Donor Groups for RBC & Whole Blood
RBC_COMPATIBILITY = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
}

# Plasma compatibility (Reverse of RBC)
PLASMA_COMPATIBILITY = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"]
}

# Mandatory Legal & Medical Disclaimers
DISCLAIMER_PLATFORM = (
    "BloodConnect is an emergency information and coordination platform. "
    "We do not supply blood directly, nor do we guarantee blood availability, "
    "donor response, or successful transfusion. Always contact the hospital "
    "or blood bank immediately."
)

DISCLAIMER_ELIGIBILITY = (
    "Eligibility must be confirmed according to applicable blood-donation guidelines. "
    "Medical professionals at the licensed donation facility will conduct health "
    "screenings (including hemoglobin, vitals, interval rules, and infectious markers) "
    "prior to collection."
)

DISCLAIMER_OUTDATED = (
    "Availability information may be outdated. Please contact the blood bank "
    "before travelling."
)

def normalize_blood_group(group: str) -> str:
    """
    Normalizes blood group strings, handling URL decoding where '+' can become a trailing space.
    e.g. 'O ' -> 'O+', 'a+' -> 'A+', 'B' -> 'B+'
    """
    if not group:
        return ""
    raw = group.upper()
    if raw.endswith(" ") and raw.strip() in ["O", "A", "B", "AB"]:
        return raw.strip() + "+"
    return raw.strip()

def get_compatible_donor_groups(patient_group: str, component: str = "RBC") -> List[str]:
    """
    Returns list of donor blood groups compatible with the patient's blood group
    for the specified component.
    """
    clean_group = patient_group.strip().upper()
    comp = component.strip().upper()
    
    if comp == "PLASMA":
        return PLASMA_COMPATIBILITY.get(clean_group, [clean_group])
    
    # Default to RBC & Whole Blood compatibility
    return RBC_COMPATIBILITY.get(clean_group, [clean_group])

def get_compatible_recipient_groups(donor_group: str, component: str = "RBC") -> List[str]:
    """
    Returns list of recipient blood groups that can safely receive blood from this donor.
    """
    clean_donor = donor_group.strip().upper()
    comp = component.strip().upper()
    
    matrix = PLASMA_COMPATIBILITY if comp == "PLASMA" else RBC_COMPATIBILITY
    
    recipients = []
    for recipient, compatible_donors in matrix.items():
        if clean_donor in compatible_donors:
            recipients.append(recipient)
    return recipients
