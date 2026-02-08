from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


_STOPWORDS = {
    # PL
    "i", "oraz", "a", "ale", "że", "to", "na", "w", "we", "z", "ze", "do", "od", "po",
    "jest", "są", "być", "by", "się", "nie", "tak", "jak", "czy", "dla", "pod", "nad",
    "ten", "ta", "te", "tę", "jego", "jej", "ich", "mnie", "cię", "nam", "wam",
    # EN
    "the", "and", "or", "a", "an", "to", "of", "in", "on", "for", "with", "is", "are",
    "be", "as", "by", "it", "this", "that", "from", "at", "we", "you", "i", "they", "he", "she",
}


_WORD_RE = re.compile(r"[\w\u00C0-\u024F\u1E00-\u1EFF]+", re.UNICODE)


@dataclass
class TaskItem:
    source: str
    line: int
    text: str


def extract_keywords(text: str, top_k: int = 12) -> List[Tuple[str, int]]:
    words = [w.lower() for w in _WORD_RE.findall(text)]
    words = [w for w in words if len(w) >= 3 and w not in _STOPWORDS]
    return Counter(words).most_common(top_k)


def extract_tasks(text: str, source: str) -> List[TaskItem]:
    tasks: List[TaskItem] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        # markdown checkboxes
        if re.match(r"^[-*]\s*\[[ xX]\]\s+", s):
            tasks.append(TaskItem(source=source, line=idx, text=s))
            continue
        # common markers
        if re.search(r"\b(TODO|FIXME|ACTION|ZADANIE|DO ZROBIENIA|DO\s*DO|TO\s*DO)\b", s, re.IGNORECASE):
            tasks.append(TaskItem(source=source, line=idx, text=s))
            continue
    return tasks


def summarize_index(index_rows: Iterable[Dict[str, str]]) -> Dict[str, object]:
    """Create a lightweight, non-LLM summary of an index."""

    ext_counter = Counter()
    for r in index_rows:
        ext_counter[(r.get("ext") or "").lower()] += 1
    return {
        "by_ext": dict(ext_counter),
        "total_files": sum(ext_counter.values()),
    }
