from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    candidates,
    evaluations,
    health,
    interviews,
    questions,
    recruiters,
    reports,
)

api_v1_router = APIRouter()

# Register core endpoint modules
api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(auth.router)
api_v1_router.include_router(candidates.router)
api_v1_router.include_router(recruiters.router)
api_v1_router.include_router(interviews.router)
api_v1_router.include_router(questions.router)
api_v1_router.include_router(evaluations.router)
api_v1_router.include_router(reports.router)
