# Prompts

Paste these one at a time into Claude Code, run from
`~/Projects/pickup`. Wait for each to finish and actually look at the output
before moving on — the whole point is that it reports the truth about your
folders, and you are the only one who can tell whether it does.

`SPEC.md` sits beside this file. Every prompt refers to it, so don't retype the
details.

---

## Prompt 1 — scanner and table

```
Read SPEC.md in this folder. Build the first version of pickup: sources 1-4
only (project discovery, git, file activity, identity), plus the status rules
and the plain `pickup` table.

Skip Claude history, URL checking, PLAN.md and the HTML dashboard for now.

Python 3.9, standard library only, single file `pickup.py` with a `main()`.
Call git as a subprocess. Scan projects in a thread pool.

Then run it against my real ~/Projects and show me the output. I have 28
folders; several have no git at all (kuopas, onshipy, rannikon) and those must
appear correctly rather than crash or be skipped.
```

**Check before continuing:** does every folder appear? Are the dead ones marked
dead? Is it under 2 seconds?

---

## Prompt 2 — Claude Code history

```
Add source 5 from SPEC.md: the Claude Code session history.

The directory name is the project's absolute path with every "/" replaced by
"-". Read the newest .jsonl in it.

These files reach 55MB, so do not read one whole. Seek to the end of the file
and read backwards in chunks until you have the last few user messages and the
newest timestamp. Lines are JSON objects of mixed shape and some have no user
content at all, so skip anything that doesn't parse or doesn't match.

Fold the session timestamp into the activity calculation, and show the last
thing I asked as the NOTE column when it is more recent than the last commit.

Then run it and show me the timing. Reading history must not make the table
slower than 2 seconds. Verify against ~/.claude/projects/-Users-victorabuchi-Projects-statiku
which has a 55MB transcript.
```

**Check:** does the NOTE column now show things you actually said? Still fast?

---

## Prompt 3 — caching

```
Add the caching described in SPEC.md: ~/.cache/pickup/cache.json, keyed on
each project directory's mtime plus the newest transcript's mtime, with
--no-cache to bypass it.

Show me cold and warm timings side by side, and prove the cache invalidates by
touching a file in one project and re-running.
```

**Check:** warm run should be near-instant, and a touched file must show up
immediately.

---

## Prompt 4 — detail view and plan progress

```
Add `pickup <name>` (fuzzy prefix match) laid out like the statiku example in
SPEC.md, and source 7, the PLAN.md checkbox progress.

No project has a PLAN.md yet, so also add `pickup --init-plan <name>` which
writes a starter PLAN.md into that project with five empty checkboxes and a
heading. That is the one exception to the read-only rule and it must refuse to
overwrite an existing file.

Run the detail view on statiku and on kuopas (which is dead and has no git) and
show me both.
```

**Check:** does the detail view actually help you re-enter a project cold?

---

## Prompt 5 — dashboard and liveness

```
Add --open (single self-contained HTML file written to the cache dir, then
opened) and --check-urls with the caching and timeouts from SPEC.md.

The page should work in light and dark mode, group by status, and make dead
projects easy to spot. No external CSS or JS.

Liveness checks must never block the table: run them in the thread pool with a
2s timeout and show "unknown" rather than hanging.
```

---

## Prompt 6 — hardening

```
Now try to break it. Write tests for: a project directory I can't read, a
broken symlink, a corrupt .jsonl line, a repo with zero commits, a folder
containing only .DS_Store, and a project whose name collides with the fuzzy
matcher.

Fix whatever breaks. One bad project must never take down the run; it should be
reported against that project and the rest should still print.
```

---

## After it works

Add a shell alias so it is one word from anywhere:

```sh
echo 'alias wai="python3 ~/Projects/pickup/pickup.py"' >> ~/.zshrc
```

Then write a real `PLAN.md` in the three or four projects you actually intend
to finish. That is what turns the tool from a status report into something that
tells you what to do next.

## A note on the prompts

Each one ends by asking the agent to run it and show you real output. Keep that
habit. The failure mode with generated code is that it looks right and quietly
reports nothing useful — exactly what happened with the Instagram scraper,
which looked like it was working while it silently captured the same 192 rows
over and over.
