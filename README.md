# store-service

Игровой магазин: витрина предметов и баланс игрока в софт-валюте.

Стек: FastAPI + asyncpg, PostgreSQL 15, сырой SQL без ORM.

## Запуск

```bash
pip install -r requirements.txt
export DATABASE_URL=postgres://store:store@localhost:5432/store
psql "$DATABASE_URL" -f migrations/001_players.sql
psql "$DATABASE_URL" -f migrations/002_store_items.sql
uvicorn app.main:app --reload
```

## Деплой

Кубер, 5 реплик, HPA до 12 под нагрузкой. Одна primary-база, реплик для чтения нет.

## Тесты

```bash
pytest
```
