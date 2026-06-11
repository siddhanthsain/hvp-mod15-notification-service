from fastapi import FastAPI
app = FastAPI(title="HVP MOD-15 Notification Service", version="0.1.0")
@app.get("/health")
async def health(): return {"status": "ok", "module": "MOD-15"}
