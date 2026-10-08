-- Create separate databases for each service.
-- healthnet_db is created automatically by POSTGRES_DB.
CREATE DATABASE keycloak_db;
CREATE DATABASE hapi_fhir_db;
CREATE DATABASE hapi_odisha_db;
CREATE DATABASE hapi_karnataka_db;
CREATE DATABASE hapi_maldives_db;

GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO healthnet;
GRANT ALL PRIVILEGES ON DATABASE hapi_fhir_db TO healthnet;
GRANT ALL PRIVILEGES ON DATABASE hapi_odisha_db TO healthnet;
GRANT ALL PRIVILEGES ON DATABASE hapi_karnataka_db TO healthnet;
GRANT ALL PRIVILEGES ON DATABASE hapi_maldives_db TO healthnet;
