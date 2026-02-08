# Jarvis4 – Patch: Memory store list/dict crash fix

## Problem
`AttributeError: 'list' object has no attribute 'get'` in `app/memory/store.py` when `memory.json` contains a plain list.

## What this patch does
- Makes `Memory.load()` robust to:
  - dict format: {"history": [...], "facts": [...]}
  - list format: [...]  (treated as history)
  - empty/corrupted JSON (resets safely)
- Auto-migrates legacy list format into dict format.

## How to apply
1. Unzip this patch.
2. Copy the folder `app/memory/store.py` into your project, replacing the existing file:
   `Desktop\Jarvis4\app\memory\store.py`

(Optional but recommended)
- Delete the old memory file so you start clean:
  `del Desktop\Jarvis4\app\memory\memory.json`

## Test
- Start server: `python -m app.main`
- Run CLI: `python tools\chat_cli.py`
