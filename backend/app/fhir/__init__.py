"""
HAPI FHIR integration client. FastAPI communicates with HAPI FHIR server via REST API.
This module does NOT reimplement a FHIR server.

SRS responsibility: Translates and exchanges clinical resources via FHIR
SRS constraint: Never persists a global copy of records
"""
