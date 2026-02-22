from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1.router import api_router
import traceback

app=FastAPI(
    title="Dispose API",
    version="0.1.0",
    description="API for Dispose ")

app.include_router(api_router,prefix="/api/v1") 


@app.get("/health")
def health():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(exc)})