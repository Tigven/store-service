CREATE TABLE store_items (
    id         UUID PRIMARY KEY,
    sku        TEXT        NOT NULL,
    title      TEXT        NOT NULL,
    price      BIGINT      NOT NULL,
    kind       TEXT        NOT NULL,
    visible    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_store_items_sku ON store_items (sku);
CREATE INDEX idx_store_items_visible ON store_items (visible, kind);
