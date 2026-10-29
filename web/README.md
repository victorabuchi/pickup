# Pickup — web

The hosted half of Pickup. The agent (`../pickup.py`) reads your machine; this
serves the account, the device handshake, and the dashboard that merges every
machine into one view.

Next.js 16 · React 19 · TypeScript · CSS Modules · Postgres via `pg`.
No ORM, no auth library — sessions are a signed cookie, the same pattern as
slotnook and pursecast.

## Run it

```sh
cp .env.example .env
createdb pickup
npm install
npm run migrate
npm run dev
```

| Variable | Purpose |
| --- | --- |
| `SESSION_SECRET` | 32+ characters. Signs session cookies. |
| `DATABASE_URL` | Postgres connection string. |
| `APP_URL` | Where the browser reaches this app; used in sign-in links. |

In development the sign-in link is printed to the server console instead of
being emailed. Wiring a real sender is the one `TODO` in
`src/app/api/auth/email/route.ts`.

## How a machine connects

The web app cannot read your disk, so the agent does, and reports. The
handshake is the same shape as the GitHub CLI:

1. `pickup login` asks `POST /api/device/code` and gets a code like `HPLC-JPRS`
2. It opens `/login?code=…`; you sign in and approve
3. `POST /api/device/approve` creates the device row and parks a one-time token
4. The agent polls `POST /api/device/poll`, collects the token once, and the
   stored copy is wiped
5. From then on it calls `POST /api/agent/sync` with a bearer token

Tokens are only ever stored hashed, so a dump of the `devices` table cannot be
replayed against the API.

## What syncs

Facts about work, never the work. Project names, paths, counts, commit
subjects, file names, timestamps. **Never file contents, diffs, or keys.**

Prompt history is **off by default** and only included after
`pickup --sync-prompts on`.

A sync replaces that device's rows wholesale, so a project deleted from disk
stops appearing. Projects hidden in the dashboard stay hidden across syncs —
the agent has no idea what was untracked here, so the route carries the flag
over.

## Routes

| Route | Does |
| --- | --- |
| `/` | Landing page |
| `/login` | Email sign-in, or approving a device code |
| `/app` | The dashboard; redirects to `/login` without a session |
| `POST /api/auth/email` | Issues a sign-in link |
| `GET /api/auth/verify` | Burns the token, creates the account, signs in |
| `POST /api/device/code` | Agent asks for a code |
| `POST /api/device/approve` | Browser approves it |
| `POST /api/device/poll` | Agent collects its token, once |
| `POST /api/agent/sync` | Agent reports its projects |
| `GET /api/projects` | Dashboard reads them |
| `POST /api/projects/ignore` | Hide or restore a project |

## Verified

Built and run against a real Postgres with the real agent:

- 13 routes build clean, `tsc --noEmit` passes
- Full flow end to end — sign-in link → session cookie → device approval →
  token collection → **28 real projects synced**
- `/app` returns 307 to `/login` without a session
- Untracking a project survives a resync

## Design

Shares the system used across these projects: Figtree for text, Bricolage
Grotesque for headings and numbers, `--spring` and `--ease` for motion, the
`--shadow-xs/sm/md/pop` scale, and semantic colour sets that each carry a
surface and a line. Tokens live in `src/app/globals.css`; light and dark follow
the system with a `data-theme` override.
