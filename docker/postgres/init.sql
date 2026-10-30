-- Separate database for the test suites, so tests never touch demo data.
CREATE DATABASE condo_audit_test OWNER condo_audit;
\connect condo_audit
CREATE EXTENSION IF NOT EXISTS vector;
\connect condo_audit_test
CREATE EXTENSION IF NOT EXISTS vector;
