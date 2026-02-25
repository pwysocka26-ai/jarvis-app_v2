from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
import traceback
from pathlib import Path
from datetime import datetime
import threading


# ==========================
# Config (env overrides)
# ==========================
API_URL = os.getenv("API_URL", "http://127.0.0.1:8010/v1/chat").strip()
API_TOKEN = os.getenv("API_TOKEN", "dev-token").strip()
CLI_TIMEOUT_S = float(os.getenv("CLI_TIMEOUT_S", "180"))
DEBUG = (os.getenv("JARVIS_CLI_DEBUG", "1").strip() in {"1", "true", "True", "YES", "yes"})
REMINDER_POLL_S = float(os.getenv("JARVIS_REMINDER_POLL_S", "10"))

BASE_DIR = Path(__file__).resolve().parents[1]  # .../Jarvis4
TASKS_FILE = BASE_DIR / "data" / "memory" / "tasks.json"


# ==========================
# Logging
# ==========================
LOG_DIR = Path("data/runtime")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cli.log"

def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        LOG_FILE.write_text(LOG_FILE.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")
    except Exception:
        try:
            LOG_FILE.write_text(line + "\n", encoding="utf-8")
        except Exception:
            pass
    if DEBUG:
        print(f"[DBG] {msg}")


def pretty(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


# ==========================
# HTTP helpers
# ==========================
def _read_json(resp) -> dict:
    raw = resp.read().decode("utf-8", errors="ignore")
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw}


def _post_chat(message: str, mode: str) -> dict:
    payload = {"message": message, "mode": mode}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Token": API_TOKEN,
        },
    )

    log(f"POST {API_URL} payload={payload!r}")

    with urllib.request.urlopen(req, timeout=CLI_TIMEOUT_S) as resp:
        out = _read_json(resp)
        log(f"POST /v1/chat status={getattr(resp, 'status', '?')} keys={list(out.keys())}")
        return out


def _get_diag() -> dict:
    base = API_URL.rstrip("/")
    if base.endswith("/v1/chat"):
        base = base[:-len("/v1/chat")]
    url = base + "/diag"

    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    log(f"GET {url}")

    with urllib.request.urlopen(req, timeout=5) as resp:
        out = _read_json(resp)
        log(f"GET /diag status={getattr(resp, 'status', '?')}")
        return out


# ==========================
# Reminder watcher (CLI side)
# ==========================
def _load_tasks_db() -> dict:
    if not TASKS_FILE.exists():
        return {"tasks": []}
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"tasks": []}

def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)

def _save_tasks_db(db: dict) -> None:
    _atomic_write(TASKS_FILE, json.dumps(db, ensure_ascii=False, indent=2))

def _parse_iso(dt: str) -> datetime | None:
    if not dt:
        return None
    try:
        # accepts YYYY-MM-DDTHH:MM(:SS)
        return datetime.fromisoformat(dt)
    except Exception:
        try:
            return datetime.strptime(dt, "%Y-%m-%dT%H:%M")
        except Exception:
            return None

def _notify(text: str) -> None:
    # Print a notification without breaking the program.
    # We don't redraw the input line perfectly in all terminals,
    # but this is good enough for MVP.
    print("\n" + text)
    print("Ty> ", end="", flush=True)

def reminder_watcher(stop: threading.Event) -> None:
    log(f"Reminder watcher start poll={REMINDER_POLL_S}s tasks_file={TASKS_FILE}")
    seen_local: set[tuple[int, str]] = set()

    while not stop.is_set():
        try:
            db = _load_tasks_db()
            tasks = db.get("tasks") if isinstance(db, dict) else []
            if not isinstance(tasks, list):
                tasks = []

            now = datetime.now()
            changed = False

            for t in tasks:
                try:
                    tid = int(t.get("id") or 0)
                except Exception:
                    continue

                if not t.get("reminder_enabled"):
                    continue

                reminder_at = t.get("reminder_at") or ""
                ra = _parse_iso(str(reminder_at))
                if not ra:
                    continue

                if ra > now:
                    continue

                fired = t.get("reminder_fired_at")
                if fired:
                    continue

                key = (tid, str(reminder_at))
                if key in seen_local:
                    continue

                title = (t.get("title") or "(zadanie)").strip()
                loc = (t.get("location") or "").strip()
                when = ra.strftime("%H:%M")
                suffix = f" — {loc}" if loc else ""
                _notify(f"⏰ PRZYPOMNIENIE {when}: {title}{suffix}")

                t["reminder_fired_at"] = now.isoformat(timespec="seconds")
                changed = True
                seen_local.add(key)

            if changed:
                _save_tasks_db(db)

        except Exception as e:
            log(f"Reminder watcher error: {e!r}")

        stop.wait(REMINDER_POLL_S)

    log("Reminder watcher stopped")


# ==========================
# Utilities
# ==========================
def extract_reply(obj: dict) -> str:
    if isinstance(obj, dict):
        if isinstance(obj.get("reply"), str):
            return obj["reply"]
        meta = obj.get("meta")
        if isinstance(meta, dict) and isinstance(meta.get("response"), str):
            return meta["response"]
        if isinstance(obj.get("response"), str):
            return obj["response"]
        if isinstance(obj.get("raw"), str):
            return obj["raw"]
    return str(obj)


def cmd_ps_8010() -> None:
    if os.name != "nt":
        print("Jarvis> /ps działa tylko na Windows.")
        return

    import subprocess

    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=6)
        lines = [l for l in result.stdout.splitlines() if ":8010" in l and "LISTENING" in l]
        if not lines:
            print("Jarvis> Brak procesów nasłuchujących na porcie 8010.")
            return

        pids = []
        print("\nProcesy nasłuchujące na 8010:")
        for l in lines:
            print(l.strip())
            pid = l.split()[-1]
            pids.append(pid)

        uniq = sorted(set(pids), key=lambda x: int(x) if x.isdigit() else x)
        print("\nSzczegóły:")
        for pid in uniq:
            print(f"PID {pid}:")
            subprocess.run(["tasklist", "/FI", f"PID eq {pid}"])
            print("")

        if len(uniq) > 1:
            print("Jarvis> ⚠️ Wykryto więcej niż 1 proces na 8010 (możliwe zombie).")
            print("Jarvis> Możesz ubić: taskkill /PID <PID> /F\n")
    except Exception as e:
        log(f"/ps error: {e!r}")
        print(f"Jarvis> [PS ERROR] {e}")


def cmd_diag(mode: str) -> None:
    try:
        d = _get_diag()
        intent_router = d.get("intent_router") or {}
        data_files = d.get("data_files") or {}
        tasks_json = (data_files.get("tasks_json") or {})
        pending_json = (data_files.get("pending_travel_json") or {})

        print("\n========== DIAGNOSTYKA (SERVER) ==========")
        print(f"API_URL     : {API_URL}")
        print(f"MODE        : {mode}")
        print(f"instance_id : {d.get('instance_id')}")
        print(f"pid         : {d.get('pid')}")
        print(f"cwd         : {d.get('cwd')}")
        print(f"router.file : {intent_router.get('file')}")
        print(f"tasks.json  : {tasks_json.get('abs_path')} (exists={tasks_json.get('exists')}, mtime={tasks_json.get('mtime_iso')})")
        if pending_json.get("abs_path"):
            print(f"pending     : {pending_json.get('abs_path')} (exists={pending_json.get('exists')}, mtime={pending_json.get('mtime_iso')})")
        if d.get("tasks_count") is not None:
            print(f"tasks_count : {d.get('tasks_count')}")
        if d.get("tasks_read_error"):
            print(f"tasks_error : {d.get('tasks_read_error')}")
        print("==========================================\n")

        if DEBUG:
            print("[DBG] Full /diag JSON:")
            print(pretty(d))
            print("")
    except Exception as e:
        log(f"/diag error: {e!r}\n{traceback.format_exc()}")
        print(f"Jarvis> [DIAG ERROR] {e}")


# ==========================
# Main
# ==========================
def main() -> int:
    mode = (os.getenv("JARVIS_MODE") or "b2c").strip().lower()
    if mode not in {"b2c", "pro"}:
        mode = "b2c"

    print(f"Jarvis CLI. API: {API_URL}")
    print("Wyjdź: Ctrl+C lub /exit")
    print("Tryb: /mode b2c  |  /mode pro")
    print("Narzędzia: /diag | /ps | /debug on|off")
    print(f"Aktualny tryb: {mode}")
    log(f"CLI start API_URL={API_URL} mode={mode} DEBUG={DEBUG}")

    # start reminder watcher (MVP background reminders)
    stop = threading.Event()
    t = threading.Thread(target=reminder_watcher, args=(stop,), daemon=True)
    t.start()

    try:
        while True:
            try:
                msg = input("Ty> ").strip()
            except KeyboardInterrupt:
                print("\nJarvis> Pa!")
                log("CLI exit via Ctrl+C")
                return 0

            if not msg:
                continue

            low = msg.lower()

            # --- local commands (not sent to API) ---
            if low in ("/exit", "exit", "quit"):
                print("Jarvis> Pa!")
                log("CLI exit via /exit")
                return 0

            if low.startswith("/mode"):
                parts = msg.split(maxsplit=1)
                if len(parts) == 1:
                    print(f"Jarvis> Aktualny tryb: {mode}")
                else:
                    new_mode = parts[1].strip().lower()
                    if new_mode in {"b2c", "pro"}:
                        mode = new_mode
                        print(f"Jarvis> ✅ Ustawiono tryb: {mode}")
                        log(f"Mode changed to {mode}")
                    else:
                        print("Jarvis> Dostępne tryby: b2c, pro")
                continue

            if low == "/diag":
                cmd_diag(mode)
                continue

            if low == "/ps":
                cmd_ps_8010()
                continue

            if low.startswith("/debug"):
                parts = msg.split(maxsplit=1)
                if len(parts) == 1:
                    print(f"Jarvis> DEBUG={'ON' if DEBUG else 'OFF'} (env: JARVIS_CLI_DEBUG)")
                else:
                    val = parts[1].strip().lower()
                    new = val in {"1", "on", "true", "yes"}
                    os.environ["JARVIS_CLI_DEBUG"] = "1" if new else "0"
                    print(f"Jarvis> OK (następny start CLI): DEBUG={'ON' if new else 'OFF'}")
                continue

            # --- send to API ---
            try:
                resp = _post_chat(msg, mode=mode)
                reply = extract_reply(resp)
                print(f"Jarvis> {reply}")
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                log(f"HTTPError {e.code} {e.reason} body={body[:500]!r}")
                print(f"Jarvis> [HTTP {e.code}] {e.reason}")
                if body:
                    print(body)
            except Exception as e:
                log(f"Request error: {e!r}\n{traceback.format_exc()}")
                print(f"Jarvis> [ERR] {e}")
    finally:
        stop.set()
        try:
            t.join(timeout=1)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
