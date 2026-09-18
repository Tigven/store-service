CREATE TABLE purchases (
    id         UUID PRIMARY KEY,
    player_id  UUID        NOT NULL,
    item_id    UUID        NOT NULL,
    quantity   INT         NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_purchases_player ON purchases (player_id);
