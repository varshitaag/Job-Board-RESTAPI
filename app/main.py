from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .routers import auth, profiles, jobs, applications

# Auto-create all tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Job Board API",
    description="""
A headless REST API for a job board platform.

## Two user roles
- **Company** — post jobs, review and manage applications
- **Candidate** — browse jobs, apply, track application status

## Quick start
1. Register → `POST /auth/register`
2. Login → `POST /auth/login` (copy the token)
3. Create profile → `POST /company/profile` or `POST /candidate/profile`
4. Start using the board!
    """,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(jobs.router)
app.include_router(applications.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Job Board API is running."}