# Searchily Analytics

## Prerequisites
The main project stack MUST be running before starting analytics.
pfa-network is created by the main docker-compose.yml.

## Setup
1. Copy .env.example to .env and fill in values from Projet_Fin_Annee/.env
2. Start the main stack first:
   cd .. && docker compose up -d
3. Start analytics:
   cd analytics && docker compose up -d

## Services
- Cube.js API: http://localhost:4000
- Dashboard: http://localhost:3001

## Startup Order (IMPORTANT)
Main stack must be running first. Never start analytics alone.
