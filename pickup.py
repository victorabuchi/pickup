#!/usr/bin/env python3
"""
pickup — where did I leave off?

Reports the state of every project folder on this machine using signals that
are already there: git, file activity, the README, and Claude Code's own
session transcripts. Read-only apart from its cache.

See SPEC.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Projects"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
CACHE_DIR = Path.home() / ".cache" / "pickup"
CONFIG_DIR = Path.home() / ".config" / "pickup"
CONFIG_PATH = CONFIG_DIR / "config.json"
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


def human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.0f} {unit}" if unit != "GB" else f"{num / 1:.1f} GB"
        num /= 1024
    return f"{num:.0f} B"


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

    # Recent history, for the drawer. One extra call, cached like everything else.
    history = []
    log = run_git(project, "log", "-25", "--format=%h%x00%ct%x00%s%x00%an")
    for line in log.splitlines():
        parts = line.split("\x00")
        if len(parts) == 4:
            try:
                when = float(parts[1])
            except ValueError:
                when = 0.0
            history.append({"hash": parts[0], "at": when,
                            "subject": parts[2], "author": parts[3]})
    info["history"] = history

    root = run_git(project, "log", "--max-parents=0", "--format=%ct")
    if root:
        try:
            info["first_commit"] = float(root.splitlines()[-1])
        except (ValueError, IndexError):
            pass

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
    total_bytes = 0
    recent: list = []          # (mtime, relative path) — trimmed at the end

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
                stat = os.stat(full, follow_symlinks=False)
            except OSError:
                continue
            mtime = stat.st_mtime
            total_bytes += stat.st_size
            age = now - mtime
            if age < 7 * DAY:
                counts["7"] += 1
            if age < 30 * DAY:
                counts["30"] += 1
            if age < 120 * DAY:
                counts["120"] += 1
            recent.append((mtime, full))
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
    import heapq

    top = heapq.nlargest(18, recent)
    edits = []
    for mtime, full in top:
        try:
            short = str(Path(full).relative_to(project))
        except ValueError:
            short = os.path.basename(full)
        edits.append({"path": short, "at": mtime})

    return {
        "newest_file": rel,
        "newest_mtime": newest_mtime,
        "counts": counts,
        "files": seen,
        "bytes": total_bytes,
        "edits": edits,
    }


def strip_markdown(text: str) -> str:
    """READMEs are markdown; a card should show the words, not the syntax."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)   # links
    text = re.sub(r"[*_`]{1,3}", "", text)                   # bold, italic, code
    text = re.sub(r"<[^>]+>", "", text)                      # stray html
    return " ".join(text.split())


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

    return {
        "title": strip_markdown(title),
        "summary": strip_markdown(summary),
        "stack": stack,
    }


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
                prompts.append((" ".join(text.split()), latest_ts))
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
                prompts.append((" ".join(text.split()), latest_ts))

    deduped: list = []
    seen_text: set = set()
    for text, when in reversed(prompts):
        if not is_human_prompt(text) or text in seen_text:
            continue
        seen_text.add(text)
        deduped.append({"text": text, "at": when})
        if len(deduped) >= 12:
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


def discover(root: Path, include_ignored: bool = False) -> list:
    if not root.is_dir():
        sys.exit(f"no such directory: {root}")
    ignored = {n.lower() for n in load_config()["ignored"]}
    found = []
    try:
        for entry in sorted(root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            hidden = is_ignored(entry, ignored)
            if hidden != include_ignored:
                continue
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


# ----------------------------------------------------------------- config


def load_config() -> dict:
    """User choices that outlive the cache — chiefly what not to track."""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("ignored", [])
    return data


def save_config(config: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(config, indent=2), encoding="utf-8")
        tmp.replace(CONFIG_PATH)
    except OSError as exc:
        print(f"  could not save config: {exc}")


def set_ignored(name: str, ignored: bool) -> bool:
    config = load_config()
    current = {n.lower() for n in config["ignored"]}
    if ignored:
        if name.lower() in current:
            return False
        config["ignored"].append(name)
    else:
        before = len(config["ignored"])
        config["ignored"] = [n for n in config["ignored"] if n.lower() != name.lower()]
        if len(config["ignored"]) == before:
            return False
    save_config(config)
    return True


def is_ignored(project: Path, ignored: set) -> bool:
    """Ignored by config, or by a .pickupignore file sitting in the folder."""
    if project.name.lower() in ignored:
        return True
    return (project / ".pickupignore").exists()


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


def scan_all(root: Path, use_cache: bool = True, include_ignored: bool = False) -> list:
    projects = discover(root, include_ignored=include_ignored)
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
        return prompts[0]["text"]
    if row["git"].get("subject"):
        return row["git"]["subject"]
    if prompts:
        return prompts[0]["text"]
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
            print(f"             · {trim(prompt['text'], 64)}")
    else:
        print("    claude   no sessions recorded")

    if row.get("error"):
        print(f"    PROBLEM  {row['error']}")
    print()


# ----------------------------------------------------------------- cloud


DEFAULT_API = "https://pickupwhere.com"


def api_base() -> str:
    return os.environ.get("PICKUP_API") or load_config().get("api") or DEFAULT_API


def post_json(url: str, payload: dict, token: str = "") -> tuple:
    """POST and return (status, parsed body). Standard library only."""
    import urllib.error
    import urllib.request

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}
    except OSError as exc:
        return 0, {"error": str(exc)}


def cmd_login(root: Path) -> int:
    """
    Device-code sign-in, the same shape as the GitHub CLI.

    The browser proves who you are; this machine only ever receives a token,
    and never handles a password.
    """
    import platform
    import webbrowser

    base = api_base().rstrip("/")
    status, body = post_json(
        f"{base}/api/device/code",
        {"deviceName": platform.node() or "this machine",
         "platform": f"{platform.system()} {platform.release()}"},
    )
    if status != 200 or "code" not in body:
        print(f"\n  could not reach {base} ({body.get('error') or status})\n")
        return 1

    code = body["code"]
    url = body.get("verifyUrl") or f"{base}/login?code={code}"
    print(f"\n  your code:  {code}")
    print(f"  opening:    {url}")
    print("\n  approve it in the browser; waiting…\n")
    webbrowser.open(url)

    deadline = time.time() + 15 * 60
    while time.time() < deadline:
        time.sleep(3)
        status, body = post_json(f"{base}/api/device/poll", {"code": code})
        if status == 200 and body.get("status") == "ready":
            config = load_config()
            config["token"] = body["token"]
            config["api"] = base
            save_config(config)
            print("  signed in. this machine is connected.\n")
            return cmd_sync(root)
        if status in (404, 410):
            print(f"  {body.get('status', 'expired')} — run login again\n")
            return 1
    print("  timed out waiting for approval\n")
    return 1


def cmd_sync(root: Path) -> int:
    """Send what this machine found. Metadata only — never file contents."""
    config = load_config()
    token = config.get("token")
    if not token:
        print("\n  not signed in — run: pickup login\n")
        return 1

    rows = scan_all(root)
    payload = to_payload(rows, root)
    projects = []
    for row, shaped in zip(rows, payload["rows"]):
        projects.append({
            "name": shaped["name"],
            "path": shaped["path"],
            "status": shaped["status"],
            "summary": shaped["summary"],
            "stack": shaped["stack"],
            "branch": shaped["branch"],
            "commits": shaped["commits"],
            "dirty": shaped["dirty"],
            "hasGit": shaped["repo"],
            "note": shaped["note"],
            "noteIsYours": shaped["note_said"],
            "lastActivity": int(row.get("last_activity") or 0) or None,
            "detail": {
                "touched": shaped["touched"],
                "newestFile": shaped["newest_file"],
                "subject": shaped["subject"],
                "size": shaped["size"],
                "filesCount": shaped["files_count"],
                "firstCommit": shaped["first_commit"],
                "age": shaped["age"],
                "history": shaped["history"],
                "edits": shaped["edits"],
                "prompts": shaped["prompts"] if config.get("sync_prompts") else [],
            },
        })

    base = (config.get("api") or api_base()).rstrip("/")
    status, body = post_json(f"{base}/api/agent/sync", {"projects": projects}, token)
    if status == 200:
        print(f"\n  synced {body.get('stored', len(projects))} projects to {base}\n")
        return 0
    if status == 401:
        print("\n  this machine is no longer connected — run: pickup login\n")
        return 1
    print(f"\n  sync failed ({status}): {body.get('error') or body}\n")
    return 1


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
        said = bool(prompts) and note == prompts[0]["text"]

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
            "prompts": [{"text": p["text"], "ago": ago(p["at"])} for p in prompts[:10]],
            "history": [
                {"hash": c["hash"], "subject": c["subject"],
                 "author": c["author"], "ago": ago(c["at"]), "date": ymd(c["at"])}
                for c in (git.get("history") or [])[:25]
            ],
            "edits": [
                {"path": e["path"], "ago": ago(e["at"])}
                for e in (files.get("edits") or [])[:18]
            ],
            "files_count": files.get("files", 0),
            "size": human_size(files.get("bytes", 0)),
            "first_commit": ymd(git["first_commit"]) if git.get("first_commit") else "",
            "age": ago(git["first_commit"]) if git.get("first_commit") else "",
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

        def do_POST(self) -> None:         # noqa: N802
            try:
                if not self.path.startswith("/api/ignore"):
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length) or b"{}")
                name = str(payload.get("name") or "")
                if not name:
                    self.send_error(400, "name required")
                    return
                set_ignored(name, bool(payload.get("ignored", True)))
                self._send(b'{"ok":true}', "application/json")
            except Exception as exc:
                self.send_error(500, str(exc)[:200])

        def do_GET(self) -> None:          # noqa: N802  (stdlib naming)
            try:
                if self.path.startswith("/api"):
                    rows = scan_all(root, include_ignored="ignored=1" in self.path)
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
    print(f"\n  pickup is live at {url}")
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
    parser.add_argument("--ignore", metavar="NAME", help="stop tracking a project")
    parser.add_argument("--unignore", metavar="NAME", help="track it again")
    parser.add_argument("--ignored", action="store_true", help="list what is not tracked")
    parser.add_argument("--login", action="store_true", help="connect this machine to your account")
    parser.add_argument("--sync", action="store_true", help="send this machine's projects")
    parser.add_argument("--sync-prompts", choices=["on", "off"],
                        help="include your prompt history in what is synced")
    args = parser.parse_args()

    root = Path(args.root).expanduser()

    if args.ignore:
        ok = set_ignored(args.ignore, True)
        print(f"\n  {'no longer tracking' if ok else 'already ignored'}: {args.ignore}\n")
        return 0
    if args.unignore:
        ok = set_ignored(args.unignore, False)
        print(f"\n  {'tracking again' if ok else 'was not ignored'}: {args.unignore}\n")
        return 0
    if args.ignored:
        hidden = discover(root, include_ignored=True)
        print()
        if not hidden:
            print("  tracking everything\n")
        else:
            for project in hidden:
                marker = " (.pickupignore)" if (project / ".pickupignore").exists() else ""
                print(f"  {project.name}{marker}")
            print(f"\n  {len(hidden)} not tracked · --unignore NAME to restore\n")
        return 0

    if args.sync_prompts:
        config = load_config()
        config["sync_prompts"] = args.sync_prompts == "on"
        save_config(config)
        state = "included in" if config["sync_prompts"] else "kept out of"
        print(f"\n  prompt history is now {state} what gets synced\n")
        return 0
    if args.login:
        return cmd_login(root)
    if args.sync:
        return cmd_sync(root)
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
