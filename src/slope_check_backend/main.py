from fastapi import FastAPI

app = FastAPI(title="Slope Check Backend")


@app.get("/health")
async def health():
    return {"status": "healthy"}
