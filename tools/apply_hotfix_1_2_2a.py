\
import os
import re
import time
from pathlib import Path

PROJECT_ROOT = Path.cwd()
CORE = PROJECT_ROOT / "app" / "orchestrator" / "core.py"
HELPER_DIR = PROJECT_ROOT / "app" / "orchestrator"
HELPER = HELPER_DIR / "dev_intent.py"

MARK_BEGIN = "# --- DEV_INTENT_HOTFIX_1_2_2a_BEGIN ---"
MARK_END   = "# --- DEV_INTENT_HOTFIX_1_2_2a_END ---"

def die(msg: str, code: int = 1):
    print(f"[HOTFIX] {msg}")
    raise SystemExit(code)

def main():
    if not CORE.exists():
        die(f"Nie znaleziono: {CORE}. Uruchom skrypt w katalogu projektu (tam gdzie jest folder 'app').")

    # 1) helper
    HELPER_DIR.mkdir(parents=True, exist_ok=True)
    if not HELPER.exists():
        HELPER.write_text(Path(__file__).with_name("dev_intent.py").read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[HOTFIX] Dodano helper: {HELPER}")

    core_txt = CORE.read_text(encoding="utf-8")

    if MARK_BEGIN in core_txt and MARK_END in core_txt:
        print("[HOTFIX] Hotfix już jest w core.py – nic nie robię.")
        return

    # 2) backup
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = CORE.with_name(f"core.py.bak_{ts}")
    bak.write_text(core_txt, encoding="utf-8")
    print(f"[HOTFIX] Backup: {bak.name}")

    # 3) ensure import
    import_line = "from app.orchestrator.dev_intent import is_dev_intent, dev_intent_reply\n"
    if import_line not in core_txt:
        # spróbuj wstawić po innych importach z app.orchestrator
        lines = core_txt.splitlines(True)
        insert_at = 0
        for i, ln in enumerate(lines):
            if ln.startswith("from ") or ln.startswith("import "):
                insert_at = i + 1
            else:
                # pierwsza nie-importowa linia
                break
        lines.insert(insert_at, import_line)
        core_txt = "".join(lines)
        print("[HOTFIX] Dodano import dev_intent do core.py")

    # 4) wstaw DEV block do handle_chat
    # Heurystyka: znajdź definicję handle_chat i pierwsze miejsce gdzie dostępny jest tekst użytkownika.
    pattern_handle = re.compile(r"^(async\s+def|def)\s+handle_chat\s*\(.*?\)\s*:\s*$", re.M)
    m = pattern_handle.search(core_txt)
    if not m:
        die("Nie znaleziono funkcji handle_chat w app/orchestrator/core.py. Podeślij mi core.py, zrobię patch pod Twoją wersję.")

    start = m.end()
    # znajdź w środku handle_chat linię z 'text'/'user_text'/'message'
    # wstawimy blok po pierwszej takiej linii (albo tuż po def, jeśli nie znajdziemy).
    lines = core_txt.splitlines(True)
    # locate line index of handle_chat def
    def_line_idx = None
    running_pos = 0
    for i, ln in enumerate(lines):
        running_pos += len(ln)
        if running_pos >= start:
            def_line_idx = i
            break
    if def_line_idx is None:
        die("Nie mogę zlokalizować pozycji handle_chat w pliku.")

    # ustal indent wewnątrz funkcji (następna linia z wcięciem)
    indent = "    "
    for j in range(def_line_idx + 1, min(def_line_idx + 50, len(lines))):
        ln = lines[j]
        if ln.strip() == "" or ln.lstrip().startswith("#"):
            continue
        indent = re.match(r"^(\s+)", ln).group(1) if re.match(r"^(\s+)", ln) else "    "
        break

    insert_idx = def_line_idx + 1
    for j in range(def_line_idx + 1, len(lines)):
        ln = lines[j]
        if re.search(r"\b(user_text|text|message)\b\s*=", ln):
            insert_idx = j + 1
            break
        # stop when next def at same indent level
        if re.match(r"^(async\s+def|def)\s+\w+", ln) and not ln.startswith(indent):
            break

    block = (
        f"{indent}{MARK_BEGIN}\n"
        f"{indent}# Jeśli użytkownik mówi, że rozwija Jarvisa – zawsze wchodzimy w DEV_MODE i omijamy LLM (wariant A)\n"
        f"{indent}try:\n"
        f"{indent}    _txt = locals().get('user_text') or locals().get('text') or locals().get('message')\n"
        f"{indent}    _user_name = locals().get('user_id') or 'Paulina'\n"
        f"{indent}    if is_dev_intent(_txt):\n"
        f"{indent}        return {{'reply': dev_intent_reply(str(_user_name))}}\n"
        f"{indent}except Exception:\n"
        f"{indent}    # Hotfix ma NIE psuć normalnej ścieżki\n"
        f"{indent}    pass\n"
        f"{indent}{MARK_END}\n"
    )

    lines.insert(insert_idx, block)
    CORE.write_text("".join(lines), encoding="utf-8")
    print("[HOTFIX] Wstawiono DEV_INTENT hotfix do core.py")
    print("[HOTFIX] Gotowe. Uruchom ponownie serwer i przetestuj: 'Pracuję nad Jarvisem'.")

if __name__ == "__main__":
    main()
