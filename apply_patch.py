#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jarvis patch: restore/ensure app.orchestrator.core.handle_chat exists
and (optional) harden API error handling to avoid opaque HTTP 500s.

How to use:
  1) Unzip into the ROOT of your Jarvis project (where 'app/' exists)
  2) Run:  python apply_patch.py
It will create *.bak backups next to patched files.
"""
import re
import sys
import uuid
from pathlib import Path

def die(msg: str, code: int = 1):
    print(f"[PATCH][ERROR] {msg}")
    sys.exit(code)

def info(msg: str):
    print(f"[PATCH] {msg}")

def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        bak.write_bytes(path.read_bytes())
        info(f"Backup created: {bak}")
    else:
        info(f"Backup already exists: {bak}")

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "app").is_dir():
            return cur
        cur = cur.parent
    die("Nie znalazłem katalogu 'app/' (uruchom patch z katalogu głównego projektu).")

def patch_core_py(core_path: Path):
    txt = core_path.read_text(encoding="utf-8", errors="replace")

    if re.search(r"^def\\s+handle_chat\\s*\\(", txt, flags=re.M):
        info("core.py: handle_chat już istnieje — pomijam.")
        return

    candidates = [
        "handle_chat_request",
        "handle_chat_text",
        "handle_chat_core",
        "handle_chat_message",
        "chat",
    ]
    present = None
    for fn in candidates:
        if re.search(rf"^def\\s+{re.escape(fn)}\\s*\\(", txt, flags=re.M):
            present = fn
            break

    wrapper_lines = []
    wrapper_lines.append("")
    wrapper_lines.append("")
    wrapper_lines.append("def handle_chat(*args, **kwargs):")
    wrapper_lines.append('    """Compatibility wrapper.')
    wrapper_lines.append("    app/main.py importuje handle_chat z app.orchestrator.core.")
    wrapper_lines.append("    Ten wrapper przywraca stabilne API po zmianach w patchach.")
    wrapper_lines.append('    """')

    if present:
        wrapper_lines.append(f"    return {present}(*args, **kwargs)")
        info(f"core.py: dodaję wrapper handle_chat delegujący do: {present}")
    else:
        if "get_llm_reply" in txt:
            wrapper_lines.append("    # Fallback: get_llm_reply")
            wrapper_lines.append("    text = kwargs.get('text') or (args[0] if args else None)")
            wrapper_lines.append("    if text is None:")
            wrapper_lines.append("        raise TypeError('handle_chat: brakuje argumentu text')")
            wrapper_lines.append("    return get_llm_reply(text=text, **{k:v for k,v in kwargs.items() if k!='text'})")
            info("core.py: dodaję wrapper handle_chat z fallbackiem na get_llm_reply.")
        else:
            wrapper_lines.append("    raise RuntimeError('handle_chat wrapper: brak wykrytego handlera (np. handle_chat_request).')")
            info("core.py: dodaję wrapper handle_chat bez delegacji (brak wykrytego handlera).")

    if not txt.endswith("\\n"):
        txt += "\\n"
    txt += "\\n".join(wrapper_lines) + "\\n"
    core_path.write_text(txt, encoding="utf-8")
    info("core.py: zapisano.")

def patch_main_py(main_path: Path):
    txt = main_path.read_text(encoding="utf-8", errors="replace")

    if "FASTAPI_ERROR_HARDENED" in txt:
        info("main.py: hardening już jest — pomijam.")
        return

    # Find decorator containing /v1/chat above a def
    pattern = re.compile(r"(^@[^\\n]*/v1/chat[^\\n]*\\n(?:@[^\\n]*\\n)*def\\s+(\\w+)\\s*\\([^\\)]*\\):\\n)", re.M)
    m = pattern.search(txt)
    if not m:
        info("main.py: nie znalazłem endpointu /v1/chat (pomijam hardening).")
        return

    header_end = m.end(1)
    indent = " " * 4
    if txt[header_end:header_end+20].lstrip().startswith("try:"):
        info("main.py: wygląda na to, że try/except już jest — pomijam.")
        return

    lines = txt.splitlines(True)

    # locate body start line index by byte position
    pos = 0
    idx = 0
    while idx < len(lines) and pos + len(lines[idx]) <= header_end:
        pos += len(lines[idx])
        idx += 1
    body_start = idx

    # find end of function: next top-level decorator/def/class
    j = body_start
    while j < len(lines):
        line = lines[j]
        if (re.match(r"^(def|class)\\s+", line) or re.match(r"^@", line)) and not line.startswith(indent):
            break
        j += 1

    body = "".join(lines[body_start:j])
    indented_body = "".join((indent + l if l.strip() else l) for l in body.splitlines(True))

    hardened = []
    hardened.append(f"{indent}# FASTAPI_ERROR_HARDENED")
    hardened.append(f"{indent}try:")
    hardened.append(indented_body.rstrip("\\n"))
    hardened.append(f"{indent}except Exception as e:")
    hardened.append(f"{indent}    trace_id = str(uuid.uuid4())")
    hardened.append(f"{indent}    return {{'error_code': 'internal_error', 'message': f'Unexpected error: {{e}}', 'details': None, 'trace_id': trace_id}}")
    hardened_block = "\\n".join(hardened) + "\\n"

    new_txt = "".join(lines[:body_start]) + hardened_block + "".join(lines[j:])
    main_path.write_text(new_txt, encoding="utf-8")
    info("main.py: dodano hardening /v1/chat.")

def main():
    root = find_repo_root(Path.cwd())
    info(f"Repo root: {root}")

    core = root / "app" / "orchestrator" / "core.py"
    if not core.exists():
        die(f"Brak pliku: {core}")
    backup(core)
    patch_core_py(core)

    main_py = root / "app" / "main.py"
    if main_py.exists():
        backup(main_py)
        patch_main_py(main_py)
    else:
        info("main.py: brak (pomijam).")

    info("OK. Uruchom ponownie serwer: uvicorn app.main:app --reload --port 8010")
    info("Jeśli nadal masz HTTP 500, wklej traceback z konsoli serwera (nie z CLI).")

if __name__ == "__main__":
    main()
