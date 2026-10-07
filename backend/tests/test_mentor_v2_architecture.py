from backend.app.mentor_execution_diagnosis_service import (
    diagnose_notebook_execution,
)
from backend.app.mentor_playbook_service import (
    get_playbook_context,
)
from backend.app.mentor_product_registry import (
    PRODUCT_REGISTRY,
    resolve_product_context,
)
from backend.app.models import (
    DataQualityFinding,
    WorkspaceLearningLoop,
)


def _loop() -> WorkspaceLearningLoop:
    return WorkspaceLearningLoop(
        loop_id="loop-1",
        language="tr",
        stage="prepare",
        finding_index=0,
        skill_name="null_analysis",
        target_type="column",
        target_name="age",
        current_phase="reason",
        completed_phases=["observe"],
        status="active",
    )


def _finding() -> DataQualityFinding:
    return DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="7 missing values",
        suggested_action="Investigate",
    )


def test_product_registry_covers_every_main_workspace_stage():
    for stage in (
        "source",
        "prepare.profile",
        "prepare.workbench",
        "prepare.validate",
        "prepare.understand",
        "data_model",
        "kpis",
        "bi_dataset",
        "analysis",
        "dashboard",
        "insights",
        "docs",
    ):
        assert stage in PRODUCT_REGISTRY

    notebook = PRODUCT_REGISTRY[
        "prepare.workbench.notebook"
    ]
    dataset_control = next(
        item
        for item in notebook["controls"]
        if item["id"] == "notebook.dataset"
    )
    assert "raw" in dataset_control["options"]


def test_product_context_resolves_nested_workbench_view():
    context = resolve_product_context({
        "active_workspace_stage": "prepare",
        "active_prepare_stage": "workbench",
        "workbench_view": "notebook",
    })

    assert (
        context["path"]
        == "prepare.workbench.notebook"
    )
    assert any(
        item["id"] == "notebook.run_cell"
        for item in context["controls"]
    )


def test_missing_value_playbook_is_evidence_first():
    context = get_playbook_context(
        "missing_values",
        "reason",
    )

    assert "pattern" in context["goal"].lower()
    assert any(
        "mean" in item
        for item in context["avoid"]
    )


def test_execution_diagnosis_catches_wrong_dataset_context():
    diagnosis = diagnose_notebook_execution(
        loop=_loop(),
        finding=_finding(),
        ui_context={
            "selected_notebook_state": {
                "notebook_id": "n1",
                "dataset_kind": "working",
                "latest_cell": {
                    "cell_id": "c1",
                    "code": "df['age'].isna().sum()",
                    "last_execution": {
                        "success": True,
                        "expression_kind": "scalar",
                        "output": "0",
                        "executed_at": "2026-10-07T10:00:00",
                    },
                },
            }
        },
    )

    assert diagnosis is not None
    assert (
        diagnosis["issue_code"]
        == "working_vs_raw_confusion"
    )


def test_execution_diagnosis_catches_failed_code():
    diagnosis = diagnose_notebook_execution(
        loop=_loop(),
        finding=_finding(),
        ui_context={
            "selected_notebook_state": {
                "notebook_id": "n1",
                "dataset_kind": "raw",
                "latest_cell": {
                    "cell_id": "c1",
                    "code": "df['age'.isna()]",
                    "last_execution": {
                        "success": False,
                        "expression_kind": "none",
                        "output": "AttributeError: 'str' object has no attribute 'isna'",
                        "executed_at": "2026-10-07T10:00:00",
                    },
                },
            }
        },
    )

    assert diagnosis is not None
    assert diagnosis["status"] == "error"
    assert diagnosis["issue_code"] == "AttributeError"
