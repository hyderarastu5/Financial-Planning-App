from fastapi import FastAPI, HTTPException

from .engine import project
from .models import Plan, Projection

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
