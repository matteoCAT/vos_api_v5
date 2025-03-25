-- Initialize schema and tables for the multi-tenant architecture
-- Run this script once to set up the initial database structure

-- Create extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- User directory table for central user registry
CREATE TABLE IF NOT EXISTS user_directory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    company_id UUID NOT NULL,
    schema_name VARCHAR(63) NOT NULL
);

-- Company table in public schema
CREATE TABLE IF NOT EXISTS company (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    schema_name VARCHAR(63) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    description TEXT,
    logo_url VARCHAR(255),
    contact_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    tax_id VARCHAR(50),
    registration_number VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Create a default company and schema
INSERT INTO company (
    name,
    slug,
    schema_name,
    display_name,
    is_active
)
VALUES (
    'Default Company',
    'default',
    'company_default',
    'Default Company',
    TRUE
)
ON CONFLICT (slug) DO NOTHING;

-- Create the default company schema
DO $$
BEGIN
    EXECUTE 'CREATE SCHEMA IF NOT EXISTS company_default';
END
$$;

-- Create role table in the default company schema
SET search_path TO company_default;
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


CREATE TABLE IF NOT EXISTS role (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    permissions VARCHAR(255),
    company_id UUID NOT NULL
);

-- Create role_permissions table
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    permission_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (role_id, permission_name)
);

-- Create user table
CREATE TABLE IF NOT EXISTS "user" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    surname VARCHAR(255) NOT NULL,
    telephone VARCHAR(255) NOT NULL,
    role_id UUID NOT NULL REFERENCES role(id),
    role VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    refresh_token VARCHAR(1024),
    last_login TIMESTAMP WITH TIME ZONE,
    company_id UUID NOT NULL
);


-- Create an admin role
INSERT INTO role (name, description, permissions, company_id)
SELECT 'ADMIN', 'Administrator with full system access', 'all', id
FROM public.company
WHERE slug = 'default'
ON CONFLICT DO NOTHING;

-- Create an admin user (password: admin123)
INSERT INTO "user" (email, username, hashed_password, name, surname, telephone, role_id, role, company_id)
SELECT
    'admin@example.com',
    'admin',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- bcrypt hash for 'admin123'
    'Admin',
    'User',
    '123-456-7890',
    r.id,
    'ADMIN',
    c.id
FROM
    public.company c,
    role r
WHERE
    c.slug = 'default' AND
    r.name = 'admin' AND
    r.company_id = c.id
ON CONFLICT DO NOTHING;

-- Reset search path to public to add to the user directory
SET search_path TO public;

-- Add the admin user to the central user directory
INSERT INTO user_directory (email, username, company_id, schema_name)
SELECT
    'admin@example.com',
    'admin',
    id,
    schema_name
FROM
    company
WHERE
    slug = 'default'
ON CONFLICT DO NOTHING;

-- Reset search path
SET search_path TO public;
