"""
Trust/Integrity Ledger.
SRS: Stores hashes, authorization references, transfer status
SRS constraint: NEVER stores any PHI/PII or clinical content

Append-only hash-chain trust ledger. MVP implementation.
FORBIDDEN: patient name, diagnosis, prescription, image, lab result, clinical note, Aadhaar, passport, SSN, cleartext Health ID, FHIR clinical content, PHI, PII.
"""
