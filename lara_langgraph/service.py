from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .graph import handle_turn


class LaraTurnRequest(BaseModel):
    session_id: str = Field(min_length=1)
    phone: str = ""
    profile_name: str = ""
    message: str = Field(min_length=1)
    qa_mode: bool = False
    state: dict[str, Any] = Field(default_factory=dict)
    available_slots: list[dict[str, str]] = Field(default_factory=list)


app = FastAPI(title="Lara LangGraph Runtime", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/lara/turn")
def lara_turn(request: LaraTurnRequest) -> dict[str, Any]:
    try:
        return handle_turn(request.model_dump())
    except Exception as exc:  # pragma: no cover - FastAPI boundary
        raise HTTPException(status_code=500, detail="lara_langgraph_failed") from exc
