# whereami — spec

A local command-line tool that answers one question for every project on this
machine: **where did I leave off?**

Rename it to whatever you like. `whereami` is the working name.

## The problem

There are 28 folders in `~/Projects`. Opening one costs 20 minutes of rebuilding
context: what is this, does it still run, what was I doing, is it deployed, did
I leave something uncommitted. Some folders have had no activity in four months
and there is currently no way to know that without opening each one.

## What it does

```
$ whereami

PROJECT              STATUS   LAST         GIT                 NOTE
notchlight           live     2026-10-24   122 commits clean   Sparkle appcast + 1.5 release
statiku              live     2026-10-24    39 commits  3 dirty wired notchlight.com
ig-follower-cleanup  active   2026-10-28    15 commits clean   detect silent throttling
chronkeep            stalled  2026-10-13    73 commits clean   mobile pages done
kuopas               dead     —            no git              no activity in 120 days
onshipy              dead     —            no git              newest file is .DS_Store
```

```
$ whereami statiku

statiku — live analytics for websites, SaaS and apps
  stack      node
  status     live   https://statiku.onrender.com  (200, checked 2m ago)
  git        main · 39 commits · 3 uncommitted · last 2026-10-24
             "wire notchlight.com property"
  files      src/routes/ingest.ts edited 2026-10-24 14:02
  plan       7/11 done · next: "Swift SDK into the app"
  last asked Claude (2026-10-24):
             - "add the swift sdk to notchlight"
             - "why is the realtime count stuck at 0"
```

## Data sources (all local, read-only)

1. **Project discovery** — each directory under a configurable root
   (default `~/Projects`). Skip dotfiles and anything in the ignore list.

2. **Git** (if `.git` exists) — last commit date, short hash and subject,
   current branch, count of uncommitted files, total commit count.
   Must work fine when there is no git at all.

3. **File activity** — newest modified file, and counts of files modified in
   the last 7 / 30 / 120 days. Must exclude `node_modules`, `.git`, `dist`,
   `build`, `.next`, `.venv`, `venv`, `__pycache__`, `Pods`, `.expo`,
   `DerivedData`. Ignore `.DS_Store` when picking the newest file.

4. **Identity** — first heading and first non-empty paragraph of `README.md`;
   else `package.json` `name`/`description`. Stack detected from:
   `package.json` → node, `app.json` with expo key → expo,
   `requirements.txt`/`pyproject.toml` → python, `project.yml`/`*.xcodeproj` →
   swift, `go.mod` → go, `Cargo.toml` → rust, `prisma/` → adds prisma.

5. **Claude Code history** — `~/.claude/projects/<encoded>/` where `<encoded>`
   is the absolute project path with every `/` replaced by `-`
   (so `/Users/me/Projects/statiku` → `-Users-me-Projects-statiku`).
   Inside are `.jsonl` transcripts. Take the newest by mtime, read the **last
   few user messages** and the newest timestamp.
   **These files reach 55MB. Never read one whole.** Seek to the end and read
   backwards in chunks until enough lines are recovered.

6. **Deploy liveness** (optional, `--check-urls`) — a URL from `package.json`
   `homepage`, or the first `https://` link in the README. `HEAD` request,
   2s timeout, result cached for an hour. Never let this block the table.

7. **Plan progress** (optional) — `PLAN.md` in the project root containing
   markdown checkboxes. Count `- [x]` vs `- [ ]`, report the first unchecked
   item as the next step. Absent for every project today; it is a habit to
   adopt, not something to infer.

## Status rules

Computed from the most recent of (last commit, newest file, last Claude
session):

| Status    | Rule                                   |
| --------- | -------------------------------------- |
| `live`    | a URL was checked and answered 2xx/3xx |
| `active`  | activity within 14 days                |
| `stalled` | activity 14–90 days ago                |
| `dead`    | no activity for over 90 days           |

`dirty` is a separate flag, not a status — a project can be active and dirty.

## Commands

| Command | Behaviour |
| --- | --- |
| `whereami` | table of every project, most recently active first |
| `whereami <name>` | detail view for one project (fuzzy prefix match) |
| `whereami --json` | machine-readable, same data |
| `whereami --dead` | only projects with no activity in 90+ days |
| `whereami --dirty` | only projects with uncommitted changes |
| `whereami --check-urls` | include liveness checks |
| `whereami --open` | write and open an HTML dashboard |
| `whereami --root <path>` | scan somewhere other than `~/Projects` |
| `whereami --no-cache` | ignore the cache |

## Constraints

- **Python 3, standard library only.** No pip install. `git` is called as a
  subprocess. This machine has Python 3.9, so no `match`, no `X | Y` in
  annotations at runtime.
- **Fast: under 2 seconds for 28 projects**, warm or cold. Scan projects in
  parallel with a thread pool. Cache per project in
  `~/.cache/whereami/cache.json`, keyed on the project directory's mtime plus
  the newest transcript's mtime. Liveness cached separately with its own TTL.
- **Read-only.** It must never write inside a project directory. The only
  writes are its own cache and, with `--open`, an HTML file in the cache dir.
- **Never crash on one bad project.** Permission errors, broken symlinks,
  corrupt JSON, a missing git binary — record the problem against that project
  and carry on.

## Out of scope for v1

Release automation, anything that writes to projects, remote/GitHub API calls,
and multi-machine sync.
