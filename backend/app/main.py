from fastapi import FastAPI

app = FastAPI(
    title="ORCA",
    description="Oceanic Reasoning & Collaborative Agents",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "project": "ORCA",
        "status": "running",
        "message": "ORCA backend is operational",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }