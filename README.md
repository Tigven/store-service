# store-service

In-game store with an item catalog and player balances in soft currency.

Stack: FastAPI + asyncpg, PostgreSQL 15, raw SQL with no ORM.

## Running locally

```bash
pip install -r requirements.txt
export DATABASE_URL=postgres://store:store@localhost:5432/store
psql "$DATABASE_URL" -f migrations/001_players.sql
psql "$DATABASE_URL" -f migrations/002_store_items.sql
psql "$DATABASE_URL" -f migrations/003_purchases.sql
uvicorn app.main:app --reload
```

## API

- `GET /v1/store/items` — item catalog
- `GET /v1/store/players/{player_id}` — player balance
- `POST /v1/store/purchases` — buy an item
- `GET /v1/store/players/{player_id}/purchases` — purchase history

## Deployment

Kubernetes with 5 replicas, with HPA scaling up to 12 under load. A single primary database with no read replicas.

## Tests

```bash
pytest
```

