# NewsRadar Frontend — Setup Guide

## Prerequisites

- Node.js 18+
- PostgreSQL 14+

## 1. Install dependencies

```bash
npm install
```

## 2. PostgreSQL setup

Install PostgreSQL and create the database and user:

```bash
# Create user (password: newsradar)
createuser newsradar -P

# Create database owned by the new user
createdb newsradar -O newsradar
```

Run the migration script to create tables and indexes:

```bash
psql -d newsradar -f scripts/migrate.sql
```

## 3. Environment variables

Copy the example env file and adjust if needed:

```bash
cp .env.example .env.local
```

Default values in `.env.example`:

```
NEXT_PUBLIC_API_URL=/api
DATABASE_URL=postgresql://newsradar:newsradar@localhost:5432/newsradar
PGHOST=localhost
PGPORT=5432
PGDATABASE=newsradar
PGUSER=newsradar
PGPASSWORD=newsradar
```

If your trendmap JSON or LLM analysis JSON files live outside the default paths, set `TRENDMAP_JSON` and `LLM_JSON` in `.env.local`.

## 4. Seed data

Load existing JSON data (trendmap + LLM analysis) into PostgreSQL:

```bash
npx tsx scripts/seed.ts
```

The seed script uses upsert logic, so it's safe to run multiple times without creating duplicates.

## 5. Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## 6. Tests

```bash
npm test
```
