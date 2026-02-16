from fastapi import FastAPI
from app.api.v1.router import api_router

app=FastAPI(
    title="Dispose API",
    version="0.1.0",
    description="API for Dispose ")

app.include_router(api_router,prefix="/api/v1") 


@app.get("/health")
def health():
    return {"status": "ok"}