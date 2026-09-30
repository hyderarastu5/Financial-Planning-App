from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import market_data
from .compare import Comparison, ComparisonKind, compare
from .engine import project
from .holdings import analyze_account
from .models import AccountAnalysis, Holding, Plan, Projection, Simulation, SimulationRequest
from .simulation import simulate

app = FastAPI(title="Financial Planning App")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/project", response_model=Projection)
def project_plan(plan: Plan) -> Projection:
    try:
        return project(plan)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/simulate", response_model=Simulation)
def simulate_plan(req: SimulationRequest) -> Simulation:
    try:
        return simulate(req.plan, runs=req.runs, seed=req.seed)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/holdings/analyze", response_model=AccountAnalysis)
def analyze_holdings(holdings: List[Holding]) -> AccountAnalysis:
    try:
        return analyze_account(holdings)
    except market_data.MarketDataUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


class CompareRequest(BaseModel):
    plan: Plan
    kind: ComparisonKind


@app.post("/api/compare", response_model=Comparison)
def compare_scenarios(req: CompareRequest) -> Comparison:
    try:
        return compare(req.plan, req.kind)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
