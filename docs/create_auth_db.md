# PostgreSQL Database Setup

## Prerequisites

Ensure you have PostgreSQL installed and configured for your project.

## Setup Instructions

### 1. Enable UUID Extension

Run this query in PostgreSQL **for the first time only**:

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


### 2. Create Database Tables

Use Alembic to create all database tables:

alembic upgrade head


### 3. Populate Roles Table

Run the initialization script to populate the roles table:

python scripts/db/postgresql/init_roles_table.py



## Notes

- The UUID extension is required before running migrations
- Ensure your Alembic configuration is properly set up before running migrations
- The roles table must be populated after table creation for proper authentication setup

