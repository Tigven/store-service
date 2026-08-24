-- Покупка предмета: лог покупок и инвентарь игрока.

ALTER TABLE store_items ADD COLUMN stock INTEGER;
ALTER TABLE store_items ADD COLUMN available_until TIMESTAMPTZ;

CREATE TABLE purchases (
    id              UUID PRIMARY KEY,
    player_id       UUID        NOT NULL REFERENCES players (id),
    item_id         UUID        NOT NULL REFERENCES store_items (id),
    idempotency_key TEXT        NOT NULL,
    price_paid      BIGINT      NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'completed',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_purchases_idempotency_key ON purchases (idempotency_key);
CREATE INDEX idx_purchases_player ON purchases (player_id, created_at DESC);

CREATE TABLE inventory (
    id          UUID PRIMARY KEY,
    player_id   UUID        NOT NULL REFERENCES players (id),
    item_id     UUID        NOT NULL REFERENCES store_items (id),
    purchase_id UUID        NOT NULL REFERENCES purchases (id),
    quantity    INTEGER     NOT NULL DEFAULT 1,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_inventory_player ON inventory (player_id);
CREATE INDEX idx_inventory_item ON inventory (item_id);
