from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class MemoryStore:
    """Prosty, odporny na format store pamięci (plik JSON).

    Obsługuje:
    - listę luźnych faktów (items) dla komend typu: zapamiętaj: X / zapomnij: X
    - słownik KV (kv) dla danych strukturalnych: profil, cele itp.

    Format na dysku:
    {
      "items": ["Tatry", "Nie lubi deszczu"],
      "kv": {"profile": {...}, "goal": "...", "goals": [...]}
    }
    """

    def __init__(self, path: Union[str, Path], max_history: int = 50, **_: Any) -> None:
        self.max_history = max_history
        self.path = Path(path)

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"items": [], "kv": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"items": [], "kv": {}}
            data.setdefault("items", [])
            data.setdefault("kv", {})
            if not isinstance(data["items"], list):
                data["items"] = []
            if not isinstance(data["kv"], dict):
                data["kv"] = {}
            return data
        except Exception:
            return {"items": [], "kv": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # --------- LUŹNE FAKTY (LISTA) ---------

    def remember_fact(self, fact: str) -> None:
        fact = (fact or "").strip()
        if not fact:
            return
        data = self._load()
        if fact not in data["items"]:
            data["items"].append(fact)
            self._save(data)

    def forget_fact(self, fact: str) -> None:
        fact = (fact or "").strip()
        if not fact:
            return
        data = self._load()
        data["items"] = [x for x in data["items"] if x != fact]
        self._save(data)

    def list_facts(self) -> List[str]:
        data = self._load()
        return list(data.get("items", []))

    # --------- DANE STRUKTURALNE (KV) ---------

    def set_kv(self, key: str, value: Any) -> None:
        key = (key or "").strip()
        if not key:
            return
        data = self._load()
        data.setdefault("kv", {})
        data["kv"][key] = value
        self._save(data)

    def get_kv(self, key: str, default: Any = None) -> Any:
        key = (key or "").strip()
        if not key:
            return default
        data = self._load()
        kv = data.get("kv", {})
        if not isinstance(kv, dict):
            return default
        return kv.get(key, default)

    def delete_kv(self, key: str) -> None:
        key = (key or "").strip()
        if not key:
            return
        data = self._load()
        kv = data.get("kv", {})
        if isinstance(kv, dict) and key in kv:
            del kv[key]
            self._save(data)

    def all_kv(self) -> Dict[str, Any]:
        data = self._load()
        kv = data.get("kv", {})
        return dict(kv) if isinstance(kv, dict) else {}
