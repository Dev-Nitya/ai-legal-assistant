import json
import time
import logging
from typing import Any, Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import httpx
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import get_db
from config.settings import settings
from models.eval_run import EvalRun

logger = logging.getLogger(__name__)
router = APIRouter()

class EvalRunAndStore(BaseModel):
    name: str
    limit: int
    created_by: str | None = None
    user_id: str | None = None

def get_result(eval_response):
    if isinstance(eval_response, JSONResponse):
        body = eval_response.body
        try:
            eval_result = json.loads(body.decode() if isinstance(body, (bytes, bytearray)) else body)
        except Exception:
            eval_result = eval_response.content if hasattr(eval_response, "content") else {}
    elif hasattr(eval_response, "dict"):
        eval_result = eval_response.dict()
    elif isinstance(eval_response, dict):
        eval_result = eval_response
    else:
        # last-resort attempts
        try:
            eval_result = eval_response.json() if hasattr(eval_response, "json") else {}
        except Exception:
            eval_result = getattr(eval_response, "content", {}) or {}

    return eval_result

@router.post("/eval/run_and_store")
async def run_and_store_evaluation(
    payload: EvalRunAndStore, db: Session = Depends(get_db),
):
    """
    Run the batch evaluator (server-side) and store the result as an EvalRun.

    Params:
      - name: unique name for this run (required)
      - limit: number of eval queries to run (optional)
      - created_by: optional author string

    Behavior:
    1. Try to call the existing evaluate/batch logic directly (fast, in-process).
      2. If direct call fails (import or signature mismatch), POST to the evaluate/batch HTTP route.
      3. Persist returned metrics/samples/meta into the EvalRun table (upsert by name).
      4. Return saved run id / timestamp.
    """
    name = payload.name
    limit = payload.limit or 100
    created_by = payload.created_by

    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")

    # Step A: call evaluator
    eval_result = None
    # Attempt direct import and call to avoid an HTTP round-trip
    try:
        from routes.evaluation import evaluate_batch_questions, BatchEvaluationRequest

        # Build the request model expected by the route handler.
        req_model = BatchEvaluationRequest(max_questions=limit)
        # Call the route handler directly (it's async)
        eval_response = await evaluate_batch_questions(req_model, user_id=payload.user_id)

        eval_result = get_result(eval_response)
            
    except Exception:
        # Fallback: call the HTTP endpoint (works even if direct import fails)
        backend_url = getattr(settings, "BACKEND_URL", "http://localhost:8000")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{backend_url}/api/evaluate/batch",
                    json={"max_questions": limit},
                )
                resp.raise_for_status()
                eval_result = resp.json()

        except Exception as exc:
            logger.exception("Failed to run batch evaluator: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to run batch evaluator")

    # Step B: normalize result shape (expect metrics, samples, meta)
    metrics = eval_result.get("metrics", {}) if isinstance(eval_result, dict) else {}
    samples = eval_result.get("samples", []) if isinstance(eval_result, dict) else []
    meta = eval_result.get("meta", {}) if isinstance(eval_result, dict) else {}

    # Step C: upsert into DB (reuse the same logic as post_eval_results)
    ts = int(time.time() * 1000)
    metrics_json = json.dumps(metrics)
    samples_json = json.dumps(samples)
    meta_json = json.dumps(meta)

    MAX_SAMPLES = 200
    samples = samples[:MAX_SAMPLES]
    for s in samples:
        if isinstance(s, dict) and len(s.get("generated_answer_preview", "")) > 5000:
            s["generated_answer_preview"] = s["generated_answer_preview"][:5000] + "..."

    existing = db.query(EvalRun).filter(EvalRun.name == name).one_or_none()
    if existing:
        existing.metrics = metrics_json
        existing.samples = samples_json
        existing.meta = meta_json
        existing.created_by = created_by
        existing.created_ts = ts
        db.add(existing)
        db.commit()
        db.refresh(existing)
        record = existing
    else:
        record = EvalRun(
            name=name,
            created_by=created_by,
            created_ts=ts,
            metrics=metrics_json,
            samples=samples_json,
            meta=meta_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return {"success": True, "name": record.name, "id": record.id, "ts": record.created_ts}

@router.post("/eval/results")
async def post_eval_results(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Save an evaluation run.
    payload should include:
      - name: string (unique name)
      - metrics: dict with named numeric metrics
      - samples: optional list of sample objects (failures, etc.)
      - meta: optional dict (notes, commit, config)
    """
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name' in payload")

    metrics_json = json.dumps(payload.get("metrics", {}))
    samples_json = json.dumps(payload.get("samples", []))
    meta_json = json.dumps(payload.get("meta", {}))
    created_by = payload.get("created_by", None)
    ts = int(time.time() * 1000)

    existing = db.query(EvalRun).filter(EvalRun.name == name).one_or_none()
    if existing:
        existing.metrics = metrics_json
        existing.samples = samples_json
        existing.meta = meta_json
        existing.created_by = created_by
        existing.created_ts = ts
        db.add(existing)
        db.commit()
        db.refresh(existing)
        record = existing
    else:
        record = EvalRun(
            name=name,
            created_by=created_by,
            created_ts=ts,
            metrics=metrics_json,
            samples=samples_json,
            meta=meta_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return {"success": True, "name": record.name, "id": record.id, "ts": record.created_ts}

@router.get("/eval/list")
async def list_eval_runs(db: Session = Depends(get_db)):
    rows = db.query(EvalRun).order_by(EvalRun.created_ts.desc()).all()
    runs = [{"name": r.name, "id": r.id, "ts": r.created_ts} for r in rows]
    return {"runs": runs}

@router.get("/eval/report")
async def get_eval_report(name: str, db: Session = Depends(get_db)):
    row = db.query(EvalRun).filter(EvalRun.name == name).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row.to_dict()


@router.get("/eval/compare")
async def compare_runs(base: str, exp: str, db: Session = Depends(get_db)):
    """
    Compare numeric metrics between two runs stored in DB.
    """
    b_row = db.query(EvalRun).filter(EvalRun.name == base).one_or_none()
    e_row = db.query(EvalRun).filter(EvalRun.name == exp).one_or_none()
    if not b_row or not e_row:
        raise HTTPException(status_code=404, detail="One or both runs not found")

    b = b_row.to_dict()
    e = e_row.to_dict()

    metrics_b = b.get("metrics", {}) or {}
    metrics_e = e.get("metrics", {}) or {}

    numeric_keys = sorted(
        k for k in set(list(metrics_b.keys()) + list(metrics_e.keys()))
        if isinstance(metrics_b.get(k, metrics_e.get(k)), (int, float))
    )

    diffs = {}
    for k in numeric_keys:
        vb = float(metrics_b.get(k, 0.0))
        ve = float(metrics_e.get(k, 0.0))
        delta = ve - vb
        pct = (delta / (vb if vb != 0 else 1)) * 100.0
        diffs[k] = {"base": vb, "exp": ve, "delta": delta, "pct_change": pct}

    samples = e.get("samples", [])[:10]

    return {"diffs": diffs, "base_meta": b.get("meta", {}), "exp_meta": e.get("meta", {}), "exp_samples": samples}