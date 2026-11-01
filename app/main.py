"""Web/API scaffold (Week 3): serves sample observations with genuine metadata. No model is attached yet,
so /api/predict answers 503 instead of an invented result. Run from the repo root:
python -m uvicorn app.main:app --port 8000"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

HERE = Path(__file__).parent
RECORDS = json.loads((HERE / "sample_records.json").read_text(encoding="utf-8"))
app = FastAPI(title="Sidewalk passage obstruction screening", version="0.1.0")


@app.get("/")
def index():
    return FileResponse(HERE / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_version": None}


@app.get("/api/observations")
def observations():
    return RECORDS


@app.post("/api/predict")
def predict():
    raise HTTPException(status_code=503, detail="No trained model is deployed yet.")
