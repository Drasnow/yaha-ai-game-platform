from fastapi import FastAPI

app = FastAPI(title="Yaha Agent Service")

@app.get("/health")
def health():
    return {"status": "ok"}