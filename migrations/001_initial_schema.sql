-- Initial schema migration for the-lab-web-site-backend

-- Create applications table to store application submissions
CREATE TABLE IF NOT EXISTS applications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    telegram TEXT NOT NULL,
    motivation TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Note: The users table is automatically created and managed by Supabase Auth
-- It includes fields like id, email, created_at, etc.