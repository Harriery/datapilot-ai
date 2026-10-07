from __future__ import annotations

from backend.app.mentor_execution_diagnosis_service import (
    diagnose_notebook_execution,
)
from backend.app.mentor_learner_model_service import (
    build_learner_snapshot,
)
from backend.app.mentor_playbook_service import (
    get_playbook_context,
)
from backend.app.mentor_product_registry import (
    resolve_product_context,
)
from backend.app.models import (
    DataQualityFinding,
    WorkspaceLearningLoop,
)


def build_guided_mentor_context(
    *,
    learner_id: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    ui_context: dict | None,
) -> dict:
    return {
        "product": resolve_product_context(
            ui_context
        ),
        "playbook": get_playbook_context(
            finding.issue_type,
            loop.current_phase,
        ),
        "execution_diagnosis":
            diagnose_notebook_execution(
                loop=loop,
                finding=finding,
                ui_context=ui_context,
            ),
        "learner": build_learner_snapshot(
            learner_id=learner_id,
            skill_name=loop.skill_name,
        ),
    }
