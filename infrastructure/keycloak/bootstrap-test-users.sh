#!/bin/bash
set -e

echo "Waiting for Keycloak realm..."
until /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://keycloak:8080 \
  --realm master \
  --user "$KEYCLOAK_ADMIN" \
  --password "$KEYCLOAK_ADMIN_PASSWORD" >/dev/null 2>&1; do
  sleep 3
done

until /opt/keycloak/bin/kcadm.sh get realms/healthnet >/dev/null 2>&1; do
  sleep 3
done

/opt/keycloak/bin/kcadm.sh update realms/healthnet -s registrationAllowed=true

# Make every self-registered account a patient by default.
if /opt/keycloak/bin/kcadm.sh get roles/default-roles-healthnet -r healthnet >/dev/null 2>&1; then
  /opt/keycloak/bin/kcadm.sh add-roles -r healthnet \
    --rname default-roles-healthnet \
    --rolename patient >/dev/null 2>&1 || true
fi

if ! /opt/keycloak/bin/kcadm.sh get users -r healthnet -q username=testauditor | grep -q '"username" : "testauditor"'; then
  /opt/keycloak/bin/kcadm.sh create users -r healthnet \
    -s username=testauditor \
    -s enabled=true \
    -s email=auditor@healthnet.dev \
    -s firstName=Test \
    -s lastName=Auditor
fi

/opt/keycloak/bin/kcadm.sh set-password -r healthnet \
  --username testauditor \
  --new-password auditor \
  --temporary=false

# The auditor test account must not inherit the patient role.
/opt/keycloak/bin/kcadm.sh remove-roles -r healthnet \
  --uusername testauditor \
  --rolename patient >/dev/null 2>&1 || true

/opt/keycloak/bin/kcadm.sh add-roles -r healthnet \
  --uusername testauditor \
  --rolename auditor

echo "HealthNet test auditor is ready."
