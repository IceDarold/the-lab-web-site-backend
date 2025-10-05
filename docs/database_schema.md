# Database Schema Documentation

## Overview

The application uses Supabase as the database backend, providing PostgreSQL with built-in authentication and real-time capabilities.

## Tables

### applications

Stores application submissions from users. Applications can be submitted anonymously without requiring user authentication.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `UUID` | Primary key, auto-generated using `gen_random_uuid()` |
| `name` | `TEXT` | Applicant's full name (required) |
| `telegram` | `TEXT` | Telegram username/handle (required) |
| `motivation` | `TEXT` | Application motivation text (required) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Auto-set creation timestamp using `NOW()` |

**Constraints:**
- `id` is the primary key
- All fields except `id` and `created_at` are NOT NULL

### auth.users (Supabase Auth)

This table is automatically created and managed by Supabase Auth. It stores user authentication data.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `UUID` | Primary key |
| `email` | `TEXT` | User's email address (unique) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Account creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Last update timestamp |
| `email_confirmed_at` | `TIMESTAMP WITH TIME ZONE` | Email confirmation timestamp |
| `...` | `...` | Additional auth-related fields |

## Relationships

Currently, there are no foreign key relationships defined. Applications are stored independently of user accounts. Future enhancements could add a `user_id` column to link applications to registered users.

## Indexes

- Primary key index on `applications.id`
- Unique index on `auth.users.email`
- Default indexes on other auth-related fields

## Row Level Security (RLS)

Supabase RLS policies should be configured based on access requirements:

- `applications` table: Allow public inserts, restrict reads/updates to admin users
- `auth.users` table: Managed by Supabase Auth policies

## Migrations

Database schema changes are managed through SQL migration files in the `migrations/` directory. These should be executed in Supabase's SQL editor in numerical order.

Current migration: `001_initial_schema.sql`