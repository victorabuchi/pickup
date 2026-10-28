#!/usr/bin/env python3
"""
workcairn — where did I leave off?

Reports the state of every project folder on this machine using signals that
are already there: git, file activity, the README, and Claude Code's own
session transcripts. Read-only apart from its cache.

See SPEC.md.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Projects"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
CACHE_DIR = Path.home() / ".cache" / "workcairn"
CACHE_PATH = CACHE_DIR / "cache.json"

# Directories that are never interesting and are often enormous. Walking into
# node_modules is the difference between a fast tool and an unusable one.
IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".nuxt", ".venv", "venv",
    "__pycache__", "Pods", ".expo", "DerivedData", ".turbo", "coverage",
    ".cache", ".parcel-cache", "vendor", ".gradle", ".idea", "target",
    ".browser-profile", ".pytest_cache", ".mypy_cache", "site-packages",
}
IGNORE_FILES = {".DS_Store", "Thumbs.db"}

DAY = 86400
ACTIVE_DAYS = 14
STALLED_DAYS = 90
MAX_FILES = 40000          # pathological-tree guard
TAIL_BYTES = 3_000_000     # transcripts reach 55MB; only the end matters


# ----------------------------------------------------------------- helpers


def run_git(project: Path, *args: str) -> str:
    """Run a git command, returning '' on any failure."""
    try:
        done = subprocess.run(
            ["git", "-C", str(project), *args],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def ymd(epoch: float) -> str:
    if not epoch:
        return "—"
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d")


def ago(epoch: float) -> str:
    if not epoch:
        return "never"
    days = int((time.time() - epoch) // DAY)
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def trim(text: str, width: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


# ----------------------------------------------------------------- sources


def git_info(project: Path) -> dict:
    """Source 2. Everything stays empty when there is no repo."""
    if not (project / ".git").exists():
        return {"repo": False}

    info: dict = {"repo": True}
    head = run_git(project, "log", "-1", "--format=%ct%x00%h%x00%s")
    if head:
        parts = head.split("\x00")
        if len(parts) == 3:
            try:
                info["last_commit"] = float(parts[0])
            except ValueError:
                info["last_commit"] = 0.0
            info["hash"] = parts[1]
            info["subject"] = parts[2]

    info["branch"] = run_git(project, "rev-parse", "--abbrev-ref", "HEAD") or "—"

    status = run_git(project, "status", "--porcelain")
    info["dirty"] = len([ln for ln in status.splitlines() if ln.strip()])

    count = run_git(project, "rev-list", "--count", "HEAD")
    info["commits"] = int(count) if count.isdigit() else 0
    return info


def file_activity(project: Path) -> dict:
    """Source 3. Newest interesting file, plus recency buckets."""
    newest_path, newest_mtime = "", 0.0
    now = time.time()
    counts = {"7": 0, "30": 0, "120": 0}
    seen = 0

    for dirpath, dirnames, filenames in os.walk(project, topdown=True, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for name in filenames:
            if name in IGNORE_FILES:
                continue
            seen += 1
            if seen > MAX_FILES:
                break
            full = os.path.join(dirpath, name)
            try:
                mtime = os.stat(full, follow_symlinks=False).st_mtime
            except OSError:
                continue
            age = now - mtime
            if age < 7 * DAY:
                counts["7"] += 1
            if age < 30 * DAY:
                counts["30"] += 1
            if age < 120 * DAY:
                counts["120"] += 1
            if mtime > newest_mtime:
                newest_mtime, newest_path = mtime, full
        if seen > MAX_FILES:
            break

    rel = ""
    if newest_path:
        try:
            rel = str(Path(newest_path).relative_to(project))
        except ValueError:
            rel = os.path.basename(newest_path)
    return {"newest_file": rel, "newest_mtime": newest_mtime, "counts": counts}


def identity(project: Path) -> dict:
    """Source 4. What is this thing, and what is it built with."""
    title, summary = "", ""

    readme = None
    for name in ("README.md", "readme.md", "README.MD"):
        if (project / name).exists():
            readme = project / name
            break
    if readme:
        try:
            lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(("<", "![", "[!")):
                continue
            if stripped.startswith("#"):
                if not title:
                    title = stripped.lstrip("#").strip()
                continue
            if title and not summary:
                summary = stripped
                break
            if not title and not summary:
                summary = stripped

    pkg = project / "package.json"
    if pkg.exists() and (not title or not summary):
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            title = title or str(data.get("name") or "")
            summary = summary or str(data.get("description") or "")
        except (OSError, ValueError):
            pass

    stack = []
    if pkg.exists():
        stack.append("node")
    app_json = project / "app.json"
    if app_json.exists():
        try:
            if "expo" in json.loads(app_json.read_text(encoding="utf-8", errors="replace")):
                stack.append("expo")
        except (OSError, ValueError):
            pass
    if (project / "requirements.txt").exists() or (project / "pyproject.toml").exists():
        stack.append("python")
    if (project / "project.yml").exists() or list(project.glob("*.xcodeproj")):
        stack.append("swift")
    if (project / "go.mod").exists():
        stack.append("go")
    if (project / "Cargo.toml").exists():
        stack.append("rust")
    if (project / "prisma").is_dir():
        stack.append("prisma")

    return {"title": title, "summary": summary, "stack": stack}


def tail_lines(path: Path, max_bytes: int = TAIL_BYTES) -> list:
    """
    Read only the end of a file.

    These transcripts reach 55MB. Loading one whole would make the tool slower
    than opening the folder by hand, which is the thing it exists to replace.
    """
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            start = max(0, size - max_bytes)
            handle.seek(start)
            blob = handle.read()
    except OSError:
        return []
    lines = blob.split(b"\n")
    if start > 0 and lines:
        lines = lines[1:]          # first line is probably a fragment
    return lines


# Transcript entries include a lot that was never typed by a person: injected
# reminders, pasted blobs, task notifications, image placeholders. Showing
# those as "what you were doing" would make the whole column worthless.
NOISE_PREFIXES = (
    "<task-notification", "<system-reminder", "<local-command", "<command-name",
    "<command-message", "<bash-input", "<bash-stdout", "<user-prompt-submit",
    "[Image:", "[Request interrupted", "Caveat:", "<pasted_content",
    "API Error", "<function_results", "<attachment",
)


def is_human_prompt(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 4:
        return False
    for prefix in NOISE_PREFIXES:
        if stripped.startswith(prefix):
            return False
    # A line that is mostly tags is machinery, not a request.
    if stripped.count("<") > 2 and stripped.count(">") > 2:
        return False
    return True


def claude_info(project: Path) -> dict:
    """Source 5. What was I actually asking for in here, and when."""
    encoded = str(project.resolve()).replace("/", "-")
    session_dir = CLAUDE_PROJECTS / encoded
    if not session_dir.is_dir():
        return {"sessions": False}

    transcripts = []
    try:
        for entry in session_dir.iterdir():
            if entry.suffix == ".jsonl":
                try:
                    transcripts.append((entry.stat().st_mtime, entry))
                except OSError:
                    continue
    except OSError:
        return {"sessions": False}
    if not transcripts:
        return {"sessions": False}

    transcripts.sort(reverse=True)
    newest_mtime, newest = transcripts[0]

    prompts: list = []
    latest_ts = 0.0
    for raw in tail_lines(newest):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(entry, dict):
            continue

        stamp = entry.get("timestamp")
        if isinstance(stamp, str) and stamp:
            try:
                clean = stamp.replace("Z", "+00:00")
                latest_ts = max(latest_ts, datetime.fromisoformat(clean).timestamp())
            except ValueError:
                pass

        # "last-prompt" carries what was actually typed. Plain "user" entries
        # are mostly tool results, so they are only a fallback.
        if entry.get("type") == "last-prompt":
            text = entry.get("lastPrompt")
            if isinstance(text, str) and is_human_prompt(text):
                prompts.append(" ".join(text.split()))
        elif entry.get("type") == "user":
            content = (entry.get("message") or {}).get("content")
            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            if text.strip():
                prompts.append(" ".join(text.split()))

    deduped: list = []
    for text in reversed(prompts):
        if not is_human_prompt(text):
            continue
        if text not in deduped:
            deduped.append(text)
        if len(deduped) >= 5:
            break

    return {
        "sessions": True,
        "count": len(transcripts),
        "last_session": latest_ts or newest_mtime,
        "prompts": deduped,
    }


# ----------------------------------------------------------------- scanning


def status_of(row: dict) -> str:
    last = row.get("last_activity") or 0
    if not last:
        return "dead"
    age_days = (time.time() - last) / DAY
    if age_days <= ACTIVE_DAYS:
        return "active"
    if age_days <= STALLED_DAYS:
        return "stalled"
    return "dead"


def scan_project(project: Path) -> dict:
    row: dict = {"name": project.name, "path": str(project), "error": None}
    try:
        row["git"] = git_info(project)
        row["files"] = file_activity(project)
        row["identity"] = identity(project)
        row["claude"] = claude_info(project)
    except Exception as exc:                      # never lose the whole run
        row["error"] = f"{type(exc).__name__}: {exc}"
        row.setdefault("git", {"repo": False})
        row.setdefault("files", {"newest_mtime": 0, "newest_file": "", "counts": {}})
        row.setdefault("identity", {"title": "", "summary": "", "stack": []})
        row.setdefault("claude", {"sessions": False})

    row["last_activity"] = max(
        row["git"].get("last_commit") or 0,
        row["files"].get("newest_mtime") or 0,
        row["claude"].get("last_session") or 0,
    )
    row["status"] = status_of(row)
    return row


def discover(root: Path) -> list:
    if not root.is_dir():
        sys.exit(f"no such directory: {root}")
    found = []
    try:
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                found.append(entry)
    except OSError as exc:
        sys.exit(f"cannot read {root}: {exc}")
    return found


# ----------------------------------------------------------------- caching


def cache_key(project: Path) -> str:
    """Directory mtime plus newest transcript mtime: cheap and good enough."""
    try:
        stamp = project.stat().st_mtime
    except OSError:
        stamp = 0
    encoded = str(project.resolve()).replace("/", "-")
    session_dir = CLAUDE_PROJECTS / encoded
    newest = 0.0
    if session_dir.is_dir():
        try:
            for entry in session_dir.iterdir():
                if entry.suffix == ".jsonl":
                    newest = max(newest, entry.stat().st_mtime)
        except OSError:
            pass
    return f"{stamp:.0f}:{newest:.0f}"


def load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(cache: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache), encoding="utf-8")
        tmp.replace(CACHE_PATH)
    except OSError:
        pass


def scan_all(root: Path, use_cache: bool = True) -> list:
    projects = discover(root)
    cache = load_cache() if use_cache else {}
    fresh: dict = {}
    todo = []
    rows: dict = {}

    for project in projects:
        key = cache_key(project)
        hit = cache.get(str(project))
        if use_cache and hit and hit.get("_key") == key:
            rows[str(project)] = hit
        else:
            todo.append((project, key))

    if todo:
        workers = min(8, max(1, len(todo)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for (project, key), row in zip(todo, pool.map(lambda p: scan_project(p[0]), todo)):
                row["_key"] = key
                rows[str(project)] = row

    for project in projects:
        fresh[str(project)] = rows[str(project)]
    save_cache(fresh)

    ordered = [rows[str(p)] for p in projects]
    ordered.sort(key=lambda r: r.get("last_activity") or 0, reverse=True)
    return ordered


# ----------------------------------------------------------------- output


def note_for(row: dict) -> str:
    """The most recent human-meaningful thing about this project."""
    commit_at = row["git"].get("last_commit") or 0
    session_at = row["claude"].get("last_session") or 0
    prompts = row["claude"].get("prompts") or []

    if prompts and session_at >= commit_at:
        return prompts[0]
    if row["git"].get("subject"):
        return row["git"]["subject"]
    if prompts:
        return prompts[0]
    if row["status"] == "dead":
        newest = row["files"].get("newest_file")
        return f"last file: {newest}" if newest else "empty"
    return row["identity"].get("summary") or ""


def render_table(rows: list, use_colour: bool) -> None:
    colours = {"active": "\033[32m", "stalled": "\033[33m", "dead": "\033[90m", "live": "\033[36m"}
    reset = "\033[0m"

    name_w = max([len(r["name"]) for r in rows] + [7])
    name_w = min(name_w, 24)

    print()
    print(f"  {'PROJECT'.ljust(name_w)}  {'STATUS':<8} {'LAST':<12} {'GIT':<20} NOTE")
    for row in rows:
        status = row["status"]
        git = row["git"]
        if git.get("repo"):
            bits = f"{git.get('commits', 0)} commits"
            if git.get("dirty"):
                bits += f" {git['dirty']} dirty"
        else:
            bits = "no git"

        shown = status
        if use_colour and status in colours:
            shown = f"{colours[status]}{status}{reset}"
            pad = " " * (8 - len(status))
        else:
            pad = " " * (8 - len(status))

        print(
            f"  {trim(row['name'], name_w).ljust(name_w)}  {shown}{pad} "
            f"{ago(row['last_activity']):<12} {bits:<20} {trim(note_for(row), 44)}"
        )
    print()

    summary: dict = {}
    for row in rows:
        summary[row["status"]] = summary.get(row["status"], 0) + 1
    dirty = sum(1 for r in rows if r["git"].get("dirty"))
    parts = [f"{v} {k}" for k, v in sorted(summary.items())]
    if dirty:
        parts.append(f"{dirty} with uncommitted work")
    print(f"  {len(rows)} projects · " + " · ".join(parts))
    print()


def render_detail(row: dict) -> None:
    ident = row["identity"]
    git = row["git"]
    files = row["files"]
    claude = row["claude"]

    print()
    header = row["name"]
    if ident.get("title") and ident["title"].lower() != row["name"].lower():
        header += f" — {ident['title']}"
    print(f"  {header}")
    if ident.get("summary"):
        print(f"  {trim(ident['summary'], 76)}")
    print()
    print(f"    path     {row['path']}")
    if ident.get("stack"):
        print(f"    stack    {' '.join(ident['stack'])}")
    print(f"    status   {row['status']} · last activity {ago(row['last_activity'])}")

    if git.get("repo"):
        line = f"{git.get('branch', '—')} · {git.get('commits', 0)} commits"
        if git.get("dirty"):
            line += f" · {git['dirty']} uncommitted"
        if git.get("last_commit"):
            line += f" · {ymd(git['last_commit'])}"
        print(f"    git      {line}")
        if git.get("subject"):
            print(f"             \"{trim(git['subject'], 62)}\"")
    else:
        print("    git      not a repository")

    if files.get("newest_file"):
        print(f"    files    {trim(files['newest_file'], 50)}  ({ago(files['newest_mtime'])})")
        counts = files.get("counts") or {}
        if counts:
            print(f"             {counts.get('7', 0)} touched in 7d · "
                  f"{counts.get('30', 0)} in 30d · {counts.get('120', 0)} in 120d")
    else:
        print("    files    nothing but ignored files")

    if claude.get("sessions"):
        print(f"    claude   {claude.get('count', 0)} session(s) · "
              f"last {ago(claude.get('last_session', 0))}")
        for prompt in (claude.get("prompts") or [])[:4]:
            print(f"             · {trim(prompt, 64)}")
    else:
        print("    claude   no sessions recorded")

    if row.get("error"):
        print(f"    PROBLEM  {row['error']}")
    print()


# ----------------------------------------------------------------- dashboard

TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"
PLACEHOLDER = '/*__DATA__*/{"root":"","generated":"","rows":[]}'


def to_payload(rows: list, root: Path) -> dict:
    """Flatten the scan into exactly what the page needs."""
    out = []
    for row in rows:
        git = row.get("git") or {}
        files = row.get("files") or {}
        ident = row.get("identity") or {}
        claude = row.get("claude") or {}
        counts = files.get("counts") or {}

        touched = ""
        if counts:
            touched = (f"{counts.get('7', 0)} in 7d · {counts.get('30', 0)} in 30d · "
                       f"{counts.get('120', 0)} in 120d")

        note = note_for(row)
        prompts = claude.get("prompts") or []
        said = bool(prompts) and note in prompts

        out.append({
            "name": row["name"],
            "path": row["path"],
            "status": row["status"],
            "ago": ago(row.get("last_activity") or 0),
            "summary": ident.get("summary") or ident.get("title") or "",
            "stack": ident.get("stack") or [],
            "repo": bool(git.get("repo")),
            "commits": git.get("commits", 0),
            "dirty": git.get("dirty", 0),
            "branch": git.get("branch", ""),
            "subject": git.get("subject", ""),
            "newest_file": files.get("newest_file", ""),
            "touched": touched,
            "note": note,
            "note_said": said,
            "prompts": prompts[:5],
        })
    return {
        "root": str(root),
        "generated": datetime.now().strftime("%H:%M:%S"),
        "rows": out,
    }


def render_html(rows: list, root: Path) -> str:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
    except OSError:
        sys.exit(f"missing template: {TEMPLATE}")
    if PLACEHOLDER not in template:
        sys.exit("dashboard_template.html no longer contains the data placeholder")
    blob = json.dumps(to_payload(rows, root), ensure_ascii=False).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, blob)


def cmd_open(rows: list, root: Path) -> int:
    import webbrowser

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    page = CACHE_DIR / "dashboard.html"
    page.write_text(render_html(rows, root), encoding="utf-8")
    print(f"\n  wrote {page}")
    webbrowser.open(page.as_uri())
    return 0


def cmd_serve(root: Path, port: int) -> int:
    """
    Serve a live dashboard.

    Rescans on each request so the page is always current. Leave it running and
    the browser tab stays correct without touching the terminal again.
    """
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:          # noqa: N802  (stdlib naming)
            try:
                if self.path.startswith("/api"):
                    rows = scan_all(root)
                    body = json.dumps(to_payload(rows, root), ensure_ascii=False)
                    self._send(body.encode("utf-8"), "application/json; charset=utf-8")
                elif self.path in ("/", "/index.html"):
                    rows = scan_all(root)
                    self._send(render_html(rows, root).encode("utf-8"),
                               "text/html; charset=utf-8")
                else:
                    self.send_error(404)
            except Exception as exc:       # a bad project must not kill the server
                self.send_error(500, str(exc)[:200])

        def log_message(self, *args) -> None:
            pass                            # quiet

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        sys.exit(f"cannot bind port {port}: {exc}")

    url = f"http://127.0.0.1:{port}/"
    print(f"\n  workcairn is live at {url}")
    print("  leave this running; the page refreshes itself\n  ctrl-c to stop\n")
    import webbrowser
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped\n")
    return 0


def pick(rows: list, needle: str) -> list:
    needle = needle.lower()
    exact = [r for r in rows if r["name"].lower() == needle]
    if exact:
        return exact
    starts = [r for r in rows if r["name"].lower().startswith(needle)]
    if starts:
        return starts
    return [r for r in rows if needle in r["name"].lower()]


# ----------------------------------------------------------------- cli


def main() -> int:
    parser = argparse.ArgumentParser(description="Where did I leave off?")
    parser.add_argument("project", nargs="?", help="show detail for one project")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--dead", action="store_true", help="only stale projects")
    parser.add_argument("--dirty", action="store_true", help="only uncommitted work")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-colour", action="store_true")
    parser.add_argument("--open", action="store_true", dest="open_page",
                        help="write an HTML dashboard and open it")
    parser.add_argument("--serve", action="store_true",
                        help="run a live dashboard you can leave open")
    parser.add_argument("--port", type=int, default=7777)
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    if args.serve:
        return cmd_serve(root, args.port)

    started = time.time()
    rows = scan_all(root, use_cache=not args.no_cache)

    if args.open_page:
        return cmd_open(rows, root)

    if args.project:
        matches = pick(rows, args.project)
        if not matches:
            print(f"\n  no project matching {args.project!r}\n")
            return 1
        if args.as_json:
            print(json.dumps(matches if len(matches) > 1 else matches[0], indent=2, default=str))
            return 0
        for row in matches[:3]:
            render_detail(row)
        return 0

    if args.dead:
        rows = [r for r in rows if r["status"] == "dead"]
    if args.dirty:
        rows = [r for r in rows if r["git"].get("dirty")]

    if args.as_json:
        print(json.dumps(rows, indent=2, default=str))
        return 0

    if not rows:
        print("\n  nothing matches\n")
        return 0

    use_colour = sys.stdout.isatty() and not args.no_colour
    render_table(rows, use_colour)
    print(f"  scanned in {time.time() - started:.2f}s\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
