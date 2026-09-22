-- Create separate databases for each service
-- healthnet_db is created automatically by POSTGRES_DB env var

CREATE DATABASE keycloak_db;
CREATE DATABASE hapi_fhir_db;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO healthnet;
GRANT ALL PRIVILEGES ON DATABASE hapi_fhir_db TO healthnet;
