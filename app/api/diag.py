from __future__ import annotations

from fastapi import APIRouter
from app.diagnostics.runtime import collect_runtime_diagnostics

router = APIRouter(tags=["diag"])

@router.get("/diag")
def diag():
    return collect_runtime_diagnostics()

@router.get("/v1/diag")
def diag_v1():
    return collect_runtime_diagnostics()
