from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.analyze import router as analyze_router


app = FastAPI(title="Tech Truth Engine API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Tech Truth Engine API is running.",
        "health": "/health",
        "analyze": "/analyze",
    }


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
    
#updated