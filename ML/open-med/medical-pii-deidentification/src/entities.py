"""
HIPAA 18 Identifiers and Entity Type Definitions

The HIPAA Privacy Rule identifies 18 types of information that are considered
Protected Health Information (PHI) when linked to health information.
"""

from enum import Enum
from typing import Dict, List


class EntityType(str, Enum):
    """HIPAA Safe Harbor De-identification - 18 Identifiers"""

    # Direct Identifiers
    NAME = "NAME"                    # Names
    DATE = "DATE"                    # Dates (except year) related to individual
    TIME = "TIME"                    # Clock times related to individual
    PHONE = "PHONE"                  # Telephone numbers
    FAX = "FAX"                      # Fax numbers
    EMAIL = "EMAIL"                  # Email addresses
    SSN = "SSN"                      # Social Security numbers
    MRN = "MRN"                      # Medical record numbers
    ACCOUNT = "ACCOUNT"              # Account numbers
    LICENSE = "LICENSE"              # Certificate/license numbers
    VEHICLE = "VEHICLE"              # Vehicle identifiers and serial numbers
    DEVICE = "DEVICE"                # Device identifiers and serial numbers
    URL = "URL"                      # Web URLs
    IP = "IP"                        # IP addresses
    BIOMETRIC = "BIOMETRIC"          # Biometric identifiers
    PHOTO = "PHOTO"                  # Full-face photographs
    AGE = "AGE"                      # Ages over 89
    LOCATION = "LOCATION"            # Geographic data (address, city, zip)
    OTHER_ID = "OTHER_ID"            # Any other unique identifying number

    # Additional clinical entities
    PROVIDER = "PROVIDER"            # Healthcare provider names
    ORGANIZATION = "ORGANIZATION"    # Hospital/clinic names
    PATIENT_ID = "PATIENT_ID"        # Patient identifiers


# Mapping from model labels to our entity types
# Covers both BIO-prefixed (B-/I-) and aggregated (no prefix) forms
def _make_mapping() -> Dict[str, EntityType]:
    pairs = [
        ("first_name",                  EntityType.NAME),
        ("last_name",                   EntityType.NAME),
        ("date",                        EntityType.DATE),
        ("date_of_birth",               EntityType.DATE),
        ("date_time",                   EntityType.DATE),
        ("time",                        EntityType.TIME),
        ("phone_number",                EntityType.PHONE),
        ("fax_number",                  EntityType.FAX),
        ("email",                       EntityType.EMAIL),
        ("ssn",                         EntityType.SSN),
        ("medical_record_number",       EntityType.MRN),
        ("account_number",              EntityType.ACCOUNT),
        ("health_plan_beneficiary_number", EntityType.ACCOUNT),
        ("customer_id",                 EntityType.ACCOUNT),
        ("employee_id",                 EntityType.OTHER_ID),
        ("certificate_license_number",  EntityType.LICENSE),
        ("tax_id",                      EntityType.LICENSE),
        ("vehicle_identifier",          EntityType.VEHICLE),
        ("license_plate",               EntityType.VEHICLE),
        ("device_identifier",           EntityType.DEVICE),
        ("mac_address",                 EntityType.DEVICE),
        ("url",                         EntityType.URL),
        ("ipv4",                        EntityType.IP),
        ("ipv6",                        EntityType.IP),
        ("age",                         EntityType.AGE),
        ("street_address",              EntityType.LOCATION),
        ("city",                        EntityType.LOCATION),
        ("state",                       EntityType.LOCATION),
        ("postcode",                    EntityType.LOCATION),
        ("country",                     EntityType.LOCATION),
        ("county",                      EntityType.LOCATION),
        ("coordinate",                  EntityType.LOCATION),
        ("company_name",                EntityType.ORGANIZATION),
        ("biometric_identifier",        EntityType.BIOMETRIC),
        ("unique_id",                   EntityType.OTHER_ID),
        ("api_key",                     EntityType.OTHER_ID),
        ("password",                    EntityType.OTHER_ID),
        ("pin",                         EntityType.OTHER_ID),
        ("cvv",                         EntityType.OTHER_ID),
        ("credit_debit_card",           EntityType.OTHER_ID),
        ("bank_routing_number",         EntityType.OTHER_ID),
        ("swift_bic",                   EntityType.OTHER_ID),
        ("http_cookie",                 EntityType.OTHER_ID),
        ("user_name",                   EntityType.OTHER_ID),
        ("blood_type",                  EntityType.OTHER_ID),
        ("gender",                      EntityType.OTHER_ID),
        ("race_ethnicity",              EntityType.OTHER_ID),
        ("sexuality",                   EntityType.OTHER_ID),
        ("religious_belief",            EntityType.OTHER_ID),
        ("political_view",              EntityType.OTHER_ID),
        ("education_level",             EntityType.OTHER_ID),
        ("employment_status",           EntityType.OTHER_ID),
        ("occupation",                  EntityType.OTHER_ID),
        ("language",                    EntityType.OTHER_ID),
    ]
    mapping: Dict[str, EntityType] = {}
    for label, entity_type in pairs:
        mapping[label] = entity_type
        mapping[f"B-{label}"] = entity_type
        mapping[f"I-{label}"] = entity_type
    return mapping

MODEL_LABEL_MAPPING: Dict[str, EntityType] = _make_mapping()


# Entity descriptions for documentation
HIPAA_ENTITIES: Dict[EntityType, Dict] = {
    EntityType.NAME: {
        "description": "Names of patients, doctors, and other individuals",
        "examples": ["John Smith", "Dr. Sarah Johnson", "Jane Doe"],
        "replacement": "[NAME]"
    },
    EntityType.DATE: {
        "description": "Dates related to an individual (birth, admission, discharge, death)",
        "examples": ["03/15/1985", "January 10, 2024", "1985-03-15"],
        "replacement": "[DATE]"
    },
    EntityType.TIME: {
        "description": "Clock times related to an individual",
        "examples": ["14:30", "2:00 PM", "09:45 AM"],
        "replacement": "[TIME]"
    },
    EntityType.PHONE: {
        "description": "Telephone numbers",
        "examples": ["555-123-4567", "(555) 123-4567", "+1-555-123-4567"],
        "replacement": "[PHONE]"
    },
    EntityType.FAX: {
        "description": "Fax numbers",
        "examples": ["555-123-4568 (fax)", "Fax: 555-123-4568"],
        "replacement": "[FAX]"
    },
    EntityType.EMAIL: {
        "description": "Email addresses",
        "examples": ["john.smith@email.com", "patient@hospital.org"],
        "replacement": "[EMAIL]"
    },
    EntityType.SSN: {
        "description": "Social Security numbers",
        "examples": ["123-45-6789", "123456789"],
        "replacement": "[SSN]"
    },
    EntityType.MRN: {
        "description": "Medical record numbers",
        "examples": ["MRN: 123456789", "Patient ID: ABC123"],
        "replacement": "[MRN]"
    },
    EntityType.ACCOUNT: {
        "description": "Health plan beneficiary numbers and account numbers",
        "examples": ["Account #: 12345", "Policy: HMO-123456"],
        "replacement": "[ACCOUNT]"
    },
    EntityType.LICENSE: {
        "description": "Certificate/license numbers (medical, driver's)",
        "examples": ["License: D1234567", "NPI: 1234567890"],
        "replacement": "[LICENSE]"
    },
    EntityType.VEHICLE: {
        "description": "Vehicle identifiers including license plates",
        "examples": ["VIN: 1HGCM82633A123456", "Plate: ABC-1234"],
        "replacement": "[VEHICLE]"
    },
    EntityType.DEVICE: {
        "description": "Device identifiers and serial numbers",
        "examples": ["Pacemaker SN: 12345", "Implant ID: ABC123"],
        "replacement": "[DEVICE]"
    },
    EntityType.URL: {
        "description": "Web Universal Resource Locators (URLs)",
        "examples": ["https://patient-portal.example.com", "www.hospital.org/patient/123"],
        "replacement": "[URL]"
    },
    EntityType.IP: {
        "description": "Internet Protocol (IP) addresses",
        "examples": ["192.168.1.1", "10.0.0.1"],
        "replacement": "[IP]"
    },
    EntityType.BIOMETRIC: {
        "description": "Biometric identifiers (fingerprints, retinal scans, voice prints)",
        "examples": ["Fingerprint ID: FP-12345", "Voice signature verified"],
        "replacement": "[BIOMETRIC]"
    },
    EntityType.PHOTO: {
        "description": "Full-face photographs and comparable images",
        "examples": ["[Photo attached]", "Patient photo on file"],
        "replacement": "[PHOTO]"
    },
    EntityType.AGE: {
        "description": "Ages over 89 (grouped as 90+)",
        "examples": ["92 years old", "Age: 95"],
        "replacement": "[AGE>89]"
    },
    EntityType.LOCATION: {
        "description": "Geographic subdivisions smaller than a State",
        "examples": ["123 Main St", "Boston, MA 02101", "Memorial Hospital"],
        "replacement": "[LOCATION]"
    },
    EntityType.OTHER_ID: {
        "description": "Any other unique identifying number or code",
        "examples": ["Employee ID: E12345", "Badge #: 9876"],
        "replacement": "[ID]"
    },
    EntityType.PROVIDER: {
        "description": "Healthcare provider names",
        "examples": ["Dr. Smith", "Nurse Johnson"],
        "replacement": "[PROVIDER]"
    },
    EntityType.ORGANIZATION: {
        "description": "Healthcare organization names",
        "examples": ["Memorial Hospital", "City Medical Center"],
        "replacement": "[ORGANIZATION]"
    },
    EntityType.PATIENT_ID: {
        "description": "Patient identifiers",
        "examples": ["Patient #12345", "Case ID: ABC-789"],
        "replacement": "[PATIENT_ID]"
    },
}


def get_replacement_text(entity_type: EntityType) -> str:
    """Get the replacement text for a given entity type."""
    return HIPAA_ENTITIES.get(entity_type, {}).get("replacement", f"[{entity_type.value}]")


def map_model_label(label: str) -> EntityType:
    """Map a model output label to our EntityType enum."""
    return MODEL_LABEL_MAPPING.get(label, EntityType.OTHER_ID)


def get_all_entity_types() -> List[EntityType]:
    """Return all supported entity types."""
    return list(EntityType)
