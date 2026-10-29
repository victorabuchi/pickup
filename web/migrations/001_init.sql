-- Pickup: accounts, the machines that report to them, and what those machines
-- found. Project rows are facts about work, never the work itself.

CREATE TABLE IF NOT EXISTS accounts (
  id          TEXT PRIMARY KEY,
  email       TEXT NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Single-use links emailed to prove the address.
CREATE TABLE IF NOT EXISTS login_tokens (
  token       TEXT PRIMARY KEY,
  email       TEXT NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL,
  used_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS login_tokens_email ON login_tokens (email);

-- One row per machine running the agent.
CREATE TABLE IF NOT EXISTS devices (
  id          TEXT PRIMARY KEY,
  account_id  TEXT NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  platform    TEXT NOT NULL DEFAULT '',
  token_hash  TEXT NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS devices_account ON devices (account_id);

-- The device-code handshake: the agent shows a code, the browser approves it,
-- the agent polls until a token appears. Same shape as the GitHub CLI.
CREATE TABLE IF NOT EXISTS device_codes (
  code         TEXT PRIMARY KEY,
  device_name  TEXT NOT NULL DEFAULT '',
  platform     TEXT NOT NULL DEFAULT '',
  account_id   TEXT REFERENCES accounts (id) ON DELETE CASCADE,
  device_id    TEXT REFERENCES devices (id) ON DELETE SET NULL,
  secret       TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at   TIMESTAMPTZ NOT NULL,
  claimed_at   TIMESTAMPTZ
);

-- What a machine reported. Code never lands here: names, counts and timestamps.
CREATE TABLE IF NOT EXISTS projects (
  id            TEXT PRIMARY KEY,
  account_id    TEXT NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
  device_id     TEXT NOT NULL REFERENCES devices (id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  path          TEXT NOT NULL,
  status        TEXT NOT NULL,
  summary       TEXT NOT NULL DEFAULT '',
  stack         TEXT[] NOT NULL DEFAULT '{}',
  branch        TEXT NOT NULL DEFAULT '',
  commits       INTEGER NOT NULL DEFAULT 0,
  dirty         INTEGER NOT NULL DEFAULT 0,
  has_git       BOOLEAN NOT NULL DEFAULT false,
  note          TEXT NOT NULL DEFAULT '',
  note_is_yours BOOLEAN NOT NULL DEFAULT false,
  last_activity TIMESTAMPTZ,
  detail        JSONB NOT NULL DEFAULT '{}'::jsonb,
  ignored       BOOLEAN NOT NULL DEFAULT false,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (device_id, path)
);
CREATE INDEX IF NOT EXISTS projects_account ON projects (account_id, ignored);
CREATE INDEX IF NOT EXISTS projects_activity ON projects (account_id, last_activity DESC);
