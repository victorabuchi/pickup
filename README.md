# workcairn

**Where did I leave off?**

A cairn is the stack of stones walkers leave on a trail so the next person — or
their own return trip — can find the way. This is that, for a machine full of
half-finished projects.

workcairn reads every project folder on your disk and tells you what state each
one is in, when you last touched it, and *what you were actually trying to do*
— recovered from your own Claude Code transcripts, not just commit messages.

No accounts, no server, no telemetry. Python standard library only. It reads
your disk and writes nothing except its own cache.

---

## Why

Twenty-eight folders in `~/Projects`. Opening one costs twenty minutes of
rebuilding context: what is this, does it still run, what was I doing, is it
deployed, did I leave something uncommitted. Four of them had been dead for
months and there was no way to know without opening each one.

## Install

Nothing to install. Python 3 is already on macOS.

```sh
git clone https://github.com/victorabuchi/workcairn.git ~/Projects/workcairn
echo 'alias wc="python3 ~/Projects/workcairn/workcairn.py"' >> ~/.zshrc
source ~/.zshrc
```

## Use

The dashboard is the main way in. Start it once and leave it:

```sh
wc --serve
```

It opens `http://127.0.0.1:7777`, rescans on every request, and the page
refreshes itself every 30 seconds — so the tab stays correct without going back
to the terminal.

In the terminal:

```sh
wc                  # table of every project, most recently active first
wc statiku          # everything known about one project
wc --dirty          # only projects with uncommitted work
wc --dead           # candidates for deletion
wc --open           # write a static HTML file instead of serving
wc --json           # machine-readable, for piping somewhere else
```

### Options

| Flag | Default | Does |
| --- | --- | --- |
| `--root PATH` | `~/Projects` | scan somewhere else |
| `--serve` | — | live dashboard you can leave open |
| `--port N` | `7777` | port for `--serve` |
| `--open` | — | write and open a static dashboard |
| `--json` | — | machine-readable output |
| `--dead` | — | only projects idle 90+ days |
| `--dirty` | — | only projects with uncommitted changes |
| `--no-cache` | — | ignore the cache and rescan everything |
| `--no-colour` | — | plain output for pipes |

## What it reads

Everything comes from signals already on the disk. Nothing is sent anywhere.

| Source | Answers |
| --- | --- |
| `git log` / `status` / `rev-list` | last commit and its message, branch, uncommitted file count, total commits |
| file modification times | the actual last file you edited, and how many files changed in 7 / 30 / 120 days |
| `README.md`, `package.json` | what the project is, and what it is built with |
| `~/.claude/projects/*/*.jsonl` | the last things **you asked for** in that folder |

That last row is the one that matters. A commit message says what you
finished; your own prompts say what you were in the middle of.

### Status

Derived from the most recent of: last commit, newest file, last Claude session.

| Status | Rule |
| --- | --- |
| `active` | activity within 14 days |
| `stalled` | activity 14–90 days ago |
| `dead` | nothing for over 90 days |

`uncommitted` is a separate flag, not a status — a project can be active *and*
have work sitting unstaged.

## Dashboard

A fixed sidebar carries the filters with live counts; the top bar holds search
(`/` to focus). Stat tiles summarise the whole machine. Clicking a project
opens a drawer with its path, last file edited, file activity, last commit, and
your recent prompts quoted in full.

Light and dark follow the system, with a `data-theme` override. All motion
collapses under `prefers-reduced-motion`.

## Performance

29 projects scan cold in about 1.1 seconds and warm from cache in under 0.01.

Two things make that possible:

- **`node_modules` and friends are never walked.** The ignore list covers
  `node_modules`, `Pods`, `DerivedData`, `.venv`, `dist`, `build`, `.next` and
  the rest.
- **Transcripts are read backwards from the end of the file.** They reach
  55MB — one project's was exactly that — so the tool seeks to the end and
  reads back in chunks rather than parsing the whole thing.

Results cache in `~/.cache/workcairn/cache.json`, keyed on each project
directory's mtime plus its newest transcript's mtime, so a touched file shows
up immediately and nothing else is rescanned.

## Design

Follows the same system as the other projects here: Figtree for text and
Bricolage Grotesque for headings and numbers, a named motion pair
(`--spring` for movement, `--ease` for everything else), the
`--shadow-xs/sm/md/pop` scale, and semantic colour sets that each carry a
surface and a line.

## Not yet built

- URL liveness checks, so deployed projects get their own `live` status
- `PLAN.md` progress tracking with `--init-plan`, turning the status report into
  something that tells you what to do next

## Notes

- Read-only. The only writes are `~/.cache/workcairn/` and, with `--open`, the
  HTML file in it.
- One bad project never takes down a run — permission errors, broken symlinks,
  corrupt transcript lines and repos with zero commits are recorded against
  that project and the scan continues.
- Moving a project folder changes where Claude Code stores its transcripts, so
  history for a renamed project starts fresh.

## Licence

MIT
