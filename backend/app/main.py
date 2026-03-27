from fastapi import FastAPI

app = FastAPI(title="access2")

@app.get("/")
def root():
    return {"message": "access2 backend is running"}

@app.get("/api/v1/health/live")
def live():
    return {"status": "ok"}
