from __future__ import annotations

import re
from typing import Optional

# Canonical modes
CAR = "car"
TRANSIT = "transit"
BIKE = "bike"
WALK = "walk"

# Display labels in Polish
TRAVEL_MODE_LABELS = {
    CAR: "samochodem",
    TRANSIT: "komunikacją (autobus / metro / tramwaj)",
    BIKE: "rowerem",
    WALK: "pieszo",
}

_MODE_PATTERNS = [
    (CAR, re.compile(r"(auto|samoch[oó]d|samochodem|car)", re.I)),
    (TRANSIT, re.compile(r"(autobus|metro|tramwaj|komunikacj[aą]|zbiorkom|transit|bus)", re.I)),
    (BIKE, re.compile(r"(rower|rowerem|bike)", re.I)),
    (WALK, re.compile(r"(pieszo|spacer|walk)", re.I)),
]

def parse_travel_mode(text: str) -> Optional[str]:
    # Return canonical travel mode if detected in text.
    if not text:
        return None
    for mode, rx in _MODE_PATTERNS:
        if rx.search(text):
            return mode
    return None
