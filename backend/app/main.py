from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat import router as chat_router
from .api.sources import router as sources_router

app = FastAPI(title="AI-Powered Computer Engineering Student Advisor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(chat_router)
app.include_router(sources_router)


@app.get("/")
def read_root():
    return {"message": "AI-Powered Computer Engineering Student Advisor API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
