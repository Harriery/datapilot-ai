from fastapi import (
    APIRouter,
    HTTPException,
)

import backend.app.database as database

from backend.app.models import (
    TaskSummaryResponse,
)

from backend.app.task_summary_service import (
    get_task_summary,
)


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get(
    "/{learner_id}",
    response_model=TaskSummaryResponse,
)
def list_tasks(
    learner_id: str,
):
    learner = database.get_learner_profile_by_id(
        learner_id
    )

    if learner is None:
        raise HTTPException(
            status_code=404,
            detail="Learner bulunamadı.",
        )

    return get_task_summary(
        learner_id=learner_id
    )