
import duckdb
from fastapi import FastAPI

from app.api.exception_handlers import register_handlers
from app.api.v1.router import create_router

app = FastAPI(
    title="API de Capital Prudencial",
    description="Motor local de cálculos regulatórios",
    version="0.1.0",
)

register_handlers(app)
app.include_router(create_router())


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "capital-prudencial-api",
    }


@app.get("/test/duckdb")
def test_duckdb():
    result = duckdb.sql("SELECT 40 + 2").fetchone()[0]

    return {
        "duckdb": "operational",
        "result": result,
    }


@app.get("/")
def home():
    return {
        "name": "APeX-API",
        "status": "running",
        "documentation": "/docs",
    }