# Database Requirements (Gateway, Ranker, Scraper, Cube.js)

This document summarizes how the PostgreSQL database must be structured to support the gateway, ranker, scraper ETL, and Cube.js analytics.

## 1) Core Tables Required

### users
Used by gateway auth (`/auth/register`, `/auth/login`, `/auth/me`) and Cube.js (Users cube).

Minimum columns:
- id (PK, string/uuid or int)
- email (unique, text)
- hashed_password (text)
- role (text, default 'user')
- full_name (text, nullable)
- avatar_url (text, nullable)
- email_verified (boolean, default false)
- google_id (text, nullable)
- created_at (timestamp, default now)

### admins
Used by gateway admin login.

Minimum columns:
- id (PK)
- email (unique, text)
- hashed_password (text)
- full_name (text, nullable)
- avatar_url (text, nullable)
- created_at (timestamp, default now)

### categories
Used by scraper ETL, ranker category filtering, and Cube.js rollups.

Minimum columns:
- id (PK)
- name (text, not null)
- slug (text, unique, not null)
- parent_id (FK -> categories.id, nullable)
- path (text, ltree path format, nullable)
- dictionary (text, nullable)

Indexes:
- categories(id)
- categories(parent_id)
- categories(path) using ltree (if ltree enabled)

### category_mapping
Used to map scraper source categories to internal category IDs.

Minimum columns:
- id (PK)
- source_name (text, unique, not null)
- source_url (text, nullable)
- category_id (FK -> categories.id, not null)

### products
Used by ETL persistence, ranker retrieval, and Cube.js analytics.

Minimum columns (from scraper + ranker + Cube.js models):
- id (PK)
- description (text, not null)
- price (float, not null)
- category_id (FK -> categories.id, not null)
- urllink (text, not null)
- urlimg (text, not null)
- dictionary (text, nullable)
- embedding (vector(384) if pgvector enabled; nullable)

Indexes:
- products(category_id)
- products(price)
- products(embedding) ivfflat with vector_cosine_ops (pgvector)

## 2) Optional / Future Tables

### user_usage
Referenced in `/auth/me` but currently guarded in code.

Suggested columns:
- user_id (FK -> users.id)
- searches_this_month (int)

### search_events (analytics)
Recommended for business analytics (not currently implemented).

Suggested columns:
- id (PK)
- user_id (nullable FK -> users.id)
- query (text)
- normalized_query (text)
- results_count (int)
- clicked_product_id (nullable FK -> products.id)
- created_at (timestamp)

## 3) Extensions Required

### pgvector
Required for ranker semantic search and embeddings.

- CREATE EXTENSION IF NOT EXISTS vector;
- products.embedding should be `vector(384)`

### ltree
Required for category tree queries in ranker and ETL.

- CREATE EXTENSION IF NOT EXISTS ltree;
- categories.path stored in ltree-compatible format

## 4) Cube.js Analytics Expectations

Cube.js relies on the following tables/fields:
- products: id, price, urllink, category_id
- categories: id, name, parent_id
- users: id, email, full_name, avatar_url, email_verified, google_id, created_at

Rollups use joins:
- products.category_id -> categories.id
- categories.parent_id for top-level rollups

## 5) ETL Pipeline Requirements

Scraper writes:
- products table (full refresh)
- category_mapping for source category normalization

Ranker reads:
- products (price, description/dictionary, embedding)
- categories (path)
- category_mapping (only via ETL enrichment)

Gateway auth reads:
- users
- admins

## 6) Minimum SQL Bootstrap (Sketch)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS ltree;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  full_name TEXT,
  avatar_url TEXT,
  email_verified BOOLEAN DEFAULT FALSE,
  google_id TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE admins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE categories (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  parent_id INT REFERENCES categories(id) ON DELETE CASCADE,
  path LTREE,
  dictionary TEXT
);

CREATE TABLE category_mapping (
  id SERIAL PRIMARY KEY,
  source_name TEXT UNIQUE NOT NULL,
  source_url TEXT,
  category_id INT NOT NULL REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  description TEXT NOT NULL,
  price FLOAT NOT NULL,
  category_id INT NOT NULL REFERENCES categories(id),
  urllink TEXT NOT NULL,
  urlimg TEXT NOT NULL,
  dictionary TEXT,
  embedding VECTOR(384)
);
```

## 7) Notes
- Gateway auth assumes `users` + `admins` tables exist and contain hashed passwords.
- Ranker expects `categories.path` and `products.embedding` to be present for full capability.
- Cube.js analytics will fail or show empty charts if any of the above fields are missing.
