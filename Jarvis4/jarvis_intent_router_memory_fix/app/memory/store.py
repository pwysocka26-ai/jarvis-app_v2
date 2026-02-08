from __future__ import annotations

import json
import os
from typing import List, Dict

class MemoryStore:
    """Pamięć w pliku JSON.
    - facts: krótkie fakty (zapamiętaj / zapomnij)
    - history: historia rozmowy (role/content)
    """

    def __init__(self, path: str, max_history: int = 30):
        self.path = path
        self.max_history = max_history
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            self._write({"facts": [], "history": []})

    def _read(self) -> dict:
        """Wczytuje pamięć i normalizuje format.
        Obsługuje migrację z bardzo starego formatu, gdzie plik był listą historii."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            # Stary format: plik był bezpośrednio listą wiadomości
            if isinstance(obj, list):
                data = {"facts": [], "history": obj}
                # migracja w miejscu (żeby błąd nie wracał)
                self._write(data)
                return data
            if isinstance(obj, dict):
                facts = obj.get("facts") if isinstance(obj.get("facts"), list) else []
                hist = obj.get("history") if isinstance(obj.get("history"), list) else []
                return {"facts": facts, "history": hist}
        except Exception:
            pass
        return {"facts": [], "history": []}
    def _write(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def remember(self, fact: str) -> None:
        data = self._read()
        facts = list(data.get("facts") or [])
        facts.append(fact)
        data["facts"] = facts[-200:]  # limit bezpieczeństwa
        self._write(data)

    def forget(self, needle: str) -> bool:
        data = self._read()
        facts = list(data.get("facts") or [])
        before = len(facts)
        needle_low = needle.lower()
        facts = [f for f in facts if needle_low not in str(f).lower()]
        data["facts"] = facts
        self._write(data)
        return len(facts) != before

    def load_facts(self) -> List[str]:
        data = self._read()
        return list(data.get("facts") or [])

    def load_history(self) -> List[Dict[str, str]]:
        data = self._read()
        return list(data.get("history") or [])

    def save_history(self, history: List[Dict[str, str]]) -> None:
        data = self._read()
        trimmed = (history or [])[-self.max_history:]
        data["history"] = trimmed
        self._write(data)
