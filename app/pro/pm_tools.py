from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Dict, List, Tuple

from .analyze import extract_keywords, extract_tasks
from .filesystem import FsPolicy, read_text_file, safe_resolve, write_text_file
from .index import build_index, list_index, open_db, summarize_index


HELP = """Tryb PRO – komendy lokalne (na Twoim komputerze)

  /scan <path>                indeksuje pliki ...
"""


def _policy_from_env() -> FsPolicy:
    root = os.getenv("JARVIS_FS_ROOT") or os.getcwd()
    allow_write = (
        (os.getenv("JARVIS_FS_ALLOW_WRITE") or os.getenv("JARVIS_FS_WRITE") or "0").strip().lower()
        in {"1", "true", "yes", "y"}
    )
    return FsPolicy(root=root, allow_write=allow_write)


def handle_pro_command(raw: str) -> Tuple[bool, str]:
    """Handle slash commands in PRO mode.

    Returns (handled, response_text)
    """

    raw = raw.strip()
    if not raw.startswith("/"):
        return False, ""

    parts = shlex.split(raw)
    if not parts:
        return False, ""

    cmd = parts[0].lower()
    args = parts[1:]
    policy = _policy_from_env()
    db = open_db()

    if cmd in {"/help", "/?"}:
        return True, HELP

    if cmd == "/scan":
        if not args:
            return True, "Podaj ścieżkę, np. /scan . albo /scan C:\\Users\\..."
        path = args[0]
        res = build_index(path, policy=policy, db=db)
        return True, (
            f"✅ Zindeksowano: {res.files} plików, {res.dirs} katalogów.\n"
            f"Root: {res.root}\n"
            f"Aby podejrzeć: /index"
        )

    if cmd == "/index":
        rows = list_index(db, limit=50)
        if not rows:
            return True, "Brak indeksu. Najpierw zrób /scan <path>."
        summ = summarize_index(rows)
        lines = [
            f"📌 Indeks: {summ['total_files']} plików (pokazuję 50 ostatnich)",
            "",
        ]
        for r in rows:
            lines.append(f"- {r['path']} ({r['ext']}, {r['size']} B)")
        return True, "\n".join(lines)

    if cmd == "/keywords":
        if not args:
            return True, "Podaj plik lub katalog, np. /keywords README.md"
        target = args[0]
        p = safe_resolve(policy.root, target)
        if p.is_dir():
            # aggregate top keywords from first N text files
            kws: Dict[str, int] = {}
            counted = 0
            for row in list_index(db, limit=5000):
                rp = Path(row["path"])
                if not str(rp).startswith(str(p)):
                    continue
                try:
                    txt = read_text_file(policy, str(rp), max_chars=40_000)
                except Exception:
                    continue
                for w, c in extract_keywords(txt, top_k=20):
                    kws[w] = kws.get(w, 0) + c
                counted += 1
                if counted >= 40:
                    break
            top = sorted(kws.items(), key=lambda x: x[1], reverse=True)[:20]
            out = [f"Słowa-klucze dla: {p} (na podstawie {counted} plików)", ""]
            out += [f"- {w} ({c})" for w, c in top]
            return True, "\n".join(out)
        else:
            txt = read_text_file(policy, target, max_chars=120_000)
            top = extract_keywords(txt, top_k=20)
            out = [f"Słowa-klucze: {p}", ""] + [f"- {w} ({c})" for w, c in top]
            return True, "\n".join(out)

    if cmd == "/tasks":
        if not args:
            return True, "Podaj katalog/plik, np. /tasks ."
        target = args[0]
        p = safe_resolve(policy.root, target)
        items = []
        if p.is_dir():
            # use index if exists; fallback to walking
            rows = list_index(db, limit=20000)
            if rows:
                paths = [Path(r["path"]) for r in rows if str(Path(r["path"])).startswith(str(p))]
            else:
                paths = list(p.rglob("*"))
            for fp in paths:
                if fp.is_dir():
                    continue
                try:
                    txt = read_text_file(policy, str(fp), max_chars=150_000)
                except Exception:
                    continue
                items += extract_tasks(txt, source=str(fp))
        else:
            txt = read_text_file(policy, str(p), max_chars=150_000)
            items = extract_tasks(txt, source=str(p))

        if not items:
            return True, "Nie znalazłem TODO/checkboxów/akcji w tym zakresie."

        # write report (requires write permission)
        report_lines = ["# Jarvis PRO – wyciągnięte zadania", ""]
        for t in items[:300]:
            report_lines.append(f"- {t.source}:{t.line} – {t.text}")
        report = "\n".join(report_lines)

        wrote = False
        report_path = "data/pro_tasks.md"
        try:
            write_text_file(policy, report_path, report)
            wrote = True
        except Exception:
            wrote = False

        head = "\n".join(report_lines[:60])
        msg = [f"✅ Znalazłem {len(items)} elementów.", ""]
        msg.append(head)
        if wrote:
            msg.append("")
            msg.append(f"📝 Pełny raport zapisany w: {report_path}")
        else:
            msg.append("")
            msg.append("(Nie zapisałem raportu, bo JARVIS_FS_WRITE=0. Jeśli chcesz zapis, ustaw JARVIS_FS_WRITE=1.)")
        return True, "\n".join(msg)

    if cmd == "/organize":
        # Heuristic organizer: create topic folders & propose moves (dry-run by default)
        if not args:
            return True, "Użycie: /organize <path> [--apply]"
        target = args[0]
        apply = "--apply" in args
        if apply and not policy.allow_write:
            return True, "Żeby przenosić pliki ustaw JARVIS_FS_WRITE=1 (bez tego działam tylko w trybie podglądu)."

        p = safe_resolve(policy.root, target)
        if not p.is_dir():
            return True, "Podaj katalog (folder), np. /organize ."

        buckets = {
            "01_requirements": ["req", "requirement", "wymag"],
            "02_meetings": ["meeting", "minutes", "notat", "standup"],
            "03_risks": ["risk", "ryzyk", "mitig"],
            "04_plans": ["plan", "gantt", "harmon"],
            "05_budget": ["budget", "koszt", "capex", "opex"],
            "06_misc": [],
        }

        candidates: List[Tuple[Path, str]] = []
        for fp in p.rglob("*"):
            if fp.is_dir():
                continue
            name = fp.name.lower()
            dest = "06_misc"
            for b, keys in buckets.items():
                if any(k in name for k in keys):
                    dest = b
                    break
            candidates.append((fp, dest))

        # prepare output
        preview = ["📦 Proponowany podział folderów (heurystyka nazw plików)", ""]
        for fp, dest in candidates[:80]:
            preview.append(f"- {fp.relative_to(p)} -> {dest}/")
        if len(candidates) > 80:
            preview.append(f"… +{len(candidates)-80} więcej")

        if not apply:
            preview.append("")
            preview.append("To jest PODGLĄD. Jeśli chcesz, żebym utworzył foldery i przeniósł pliki: /organize <path> --apply")
            preview.append("(Wymaga JARVIS_FS_WRITE=1)")
            return True, "\n".join(preview)

        # apply
        for b in buckets.keys():
            (p / b).mkdir(parents=True, exist_ok=True)
        moved = 0
        for fp, dest in candidates:
            dst = p / dest / fp.name
            if dst == fp:
                continue
            try:
                fp.replace(dst)
                moved += 1
            except Exception:
                continue
        return True, f"✅ Utworzyłem foldery i przeniosłem ~{moved} plików."

    return False, ""
