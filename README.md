# whereami

Where did I leave off? A dashboard over every project folder on this machine,
built from signals that are already there — git state, file activity, the
README, and Claude Code's own session transcripts.

## Run it

```sh
python3 whereami.py --serve
```

Opens `http://127.0.0.1:7777`. It rescans on every request and the page
refreshes itself, so the tab stays correct without touching the terminal again.

```sh
python3 whereami.py            # table in the terminal
python3 whereami.py statiku    # detail for one project
python3 whereami.py --dirty    # only uncommitted work
python3 whereami.py --dead     # candidates for deletion
python3 whereami.py --open     # static HTML file instead of the server
```

Add an alias so it is one word from anywhere:

```sh
echo 'alias wai="python3 ~/Projects/whereami/whereami.py"' >> ~/.zshrc
```

## What it reads

| Source | Answers |
| --- | --- |
| `git log` / `status` | last commit, branch, uncommitted work |
| file mtimes | the actual last file edited, activity in 7/30/120 days |
| `README.md`, `package.json` | what this project is, what it is built with |
| `~/.claude/projects/*/*.jsonl` | what you last asked for in that folder |

Transcripts are read backwards from the end of the file. Statiku's is 55MB and
loading it whole would make the tool slower than opening the folder by hand.

## Status

| Status | Rule |
| --- | --- |
| `active` | activity within 14 days |
| `stalled` | activity 14–90 days ago |
| `dead` | nothing for over 90 days |

`uncommitted` is a separate flag — a project can be active and dirty.

## Design

Follows the same system as the other projects here: Figtree for text and
Bricolage Grotesque for headings and numbers, a named motion pair
(`--spring`, `--ease`), the `--shadow-xs/sm/md/pop` scale, and semantic colour
sets that each carry a surface and a line. Light and dark switch on
`prefers-color-scheme` with a `data-theme` override.

Python 3 standard library only. Read-only apart from its own cache in
`~/.cache/whereami`.

See [SPEC.md](SPEC.md) for the full specification.
