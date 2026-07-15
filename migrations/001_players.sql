CREATE TABLE players (
    id         UUID PRIMARY KEY,
    nickname   TEXT        NOT NULL,
    balance    BIGINT      NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_players_nickname ON players (lower(nickname));
