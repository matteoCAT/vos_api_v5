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

-- Create permission table
CREATE TABLE IF NOT EXISTS permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    code VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    module VARCHAR(255) NOT NULL,
    description TEXT,
    company_id UUID NOT NULL,
    CONSTRAINT unique_permission_code_per_company UNIQUE (code, company_id)
);

DROP TABLE role CASCADE;
CREATE TABLE IF NOT EXISTS role (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    is_system_role BOOLEAN NOT NULL DEFAULT FALSE,
    company_id UUID NOT NULL,
    CONSTRAINT unique_role_name_per_company UNIQUE (name, company_id)
);

-- Create role_permissions table
DROP TABLE role_permissions CASCADE;
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permission(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
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

-- Insert base permissions
INSERT INTO permission (code, name, module, description, company_id)
SELECT 'users_create', 'Create Users', 'users', 'Allows creating new users', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'users_read', 'View Users', 'users', 'Allows viewing user information', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'users_update', 'Update Users', 'users', 'Allows updating user information', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'users_delete', 'Delete Users', 'users', 'Allows deleting users', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'users_manage_permissions', 'Manage User Permissions', 'users', 'Allows managing user permissions and roles', id
FROM public.company WHERE slug = 'default';

-- Role permissions
INSERT INTO permission (code, name, module, description, company_id)
SELECT 'roles_create', 'Create Roles', 'roles', 'Allows creating roles', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'roles_read', 'View Roles', 'roles', 'Allows viewing role information', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'roles_update', 'Update Roles', 'roles', 'Allows updating role information', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'roles_delete', 'Delete Roles', 'roles', 'Allows deleting roles', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'roles_manage_permissions', 'Manage Role Permissions', 'roles', 'Allows managing permissions for roles', id
FROM public.company WHERE slug = 'default';

-- Permission permissions
INSERT INTO permission (code, name, module, description, company_id)
SELECT 'permissions_create', 'Create Permissions', 'permissions', 'Allows creating permissions', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'permissions_read', 'View Permissions', 'permissions', 'Allows viewing permission information', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'permissions_update', 'Update Permissions', 'permissions', 'Allows updating permission information', id
FROM public.company WHERE slug = 'default';

INSERT INTO permission (code, name, module, description, company_id)
SELECT 'permissions_delete', 'Delete Permissions', 'permissions', 'Allows deleting permissions', id
FROM public.company WHERE slug = 'default';

-- Create an admin role with is_system_role=true
INSERT INTO role (name, description, is_system_role, company_id)
SELECT 'ADMIN', 'Administrator with full system access', TRUE, id
FROM public.company
WHERE slug = 'default'
ON CONFLICT DO NOTHING;

-- Create a staff role with is_system_role=true
INSERT INTO role (name, description, is_system_role, company_id)
SELECT 'STAFF', 'Staff/Employee with limited access', TRUE, id
FROM public.company
WHERE slug = 'default'
ON CONFLICT DO NOTHING;


INSERT INTO role_permissions (role_id, permission_id)
SELECT
    r.id,
    p.id
FROM
    role r,
    permission p
WHERE
    r.name = 'ADMIN' AND
    r.company_id = (SELECT id FROM public.company WHERE slug = 'default') AND
    p.company_id = (SELECT id FROM public.company WHERE slug = 'default');


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
