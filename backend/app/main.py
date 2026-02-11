from fastapi import FastAPI

app=FastAPI(title="Dispose API",description="API for Dispose ")


@app.get("/health")
def health():
    return {"status": "ok"}