from backend.app.mentor_execution_diagnosis_service import (
    diagnose_notebook_execution,
    diagnose_generic_notebook_execution,
)
from backend.app.mentor_playbook_service import (
    get_playbook_context,
)
from backend.app.mentor_stage_playbook_service import (
    get_relevant_stage_playbooks,
)
from backend.app.mentor_product_registry import (
    PRODUCT_REGISTRY,
    resolve_product_context,
    retrieve_product_context,
)
from backend.app.mentor_action_planner_service import (
    plan_guided_next_action,
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



def test_product_retrieval_returns_current_and_only_referenced_stage():
    context = retrieve_product_context(
        ui_context={"active_workspace_stage": "source"},
        message="Dashboard'taki grid ve visual properties ne işe yarıyor?",
    )

    assert context["current"]["path"] == "source"
    assert any(
        item["path"] == "dashboard"
        for item in context["referenced"]
    )
    assert len(context["referenced"]) <= 2


def test_registry_has_detailed_model_kpi_dashboard_options():
    roles = next(
        item
        for item in PRODUCT_REGISTRY["data_model"]["controls"]
        if item["id"] == "model.column_role"
    )
    assert "foreign_key" in roles["options"]

    functions = next(
        item
        for item in PRODUCT_REGISTRY["kpis"]["controls"]
        if item["id"] == "kpi.custom_formula_functions"
    )
    assert "SAFE_DIVIDE" in functions["options"]

    theme = next(
        item
        for item in PRODUCT_REGISTRY["dashboard"]["controls"]
        if item["id"] == "dashboard.theme"
    )
    assert "slate" in theme["options"]


def test_action_planner_routes_frequency_work_to_raw_notebook():
    action = plan_guided_next_action(
        learner_message="En sık city değerini nasıl bulacağım?",
        loop=_loop(),
        finding=_finding(),
        mentor_context={
            "execution_diagnosis": None,
            "live_state": {
                "active_prepare_stage": "workbench",
                "workbench_view": "notebook",
                "selected_notebook": {
                    "notebook_id": "n1",
                    "dataset_kind": "working",
                },
                "notebook_count": 1,
                "source_preview_inspection": {
                    "active_filters": [
                        {"column": "age", "operator": "is_missing"}
                    ]
                },
            },
        },
    )

    assert action is not None
    assert action["id"] == "select_raw_notebook_dataset"
    assert action["value"] == "raw"


def test_action_planner_prioritizes_notebook_execution_error():
    action = plan_guided_next_action(
        learner_message="Şimdi ne yapacağım?",
        loop=_loop(),
        finding=_finding(),
        mentor_context={
            "execution_diagnosis": {
                "status": "error",
                "issue_code": "SyntaxError",
            },
            "live_state": {},
        },
    )

    assert action is not None
    assert action["id"] == "repair_latest_notebook_error"
    assert action["priority"] == "blocking"



def test_generic_notebook_observer_reports_failed_execution():
    diagnosis = diagnose_generic_notebook_execution({
        "notebook_id": "n1",
        "dataset_kind": "raw",
        "latest_cell": {
            "cell_id": "c1",
            "code": "df['age'.isna()]",
            "last_execution": {
                "success": False,
                "expression_kind": "none",
                "output": "AttributeError: bad expression",
                "executed_at": "2026-10-07T11:00:00",
            },
        },
    })

    assert diagnosis is not None
    assert diagnosis["status"] == "error"
    assert diagnosis["issue_code"] == "AttributeError"
    assert diagnosis["misconception"] == "code_execution_error"



def test_registry_covers_learning_support_areas():
    for path in ("practice", "progress", "tasks"):
        assert path in PRODUCT_REGISTRY


def test_stage_playbook_keeps_data_model_grain_first():
    playbooks = get_relevant_stage_playbooks({
        "current": {
            "path": "data_model",
        },
        "referenced": [],
    })

    assert len(playbooks) == 1
    model = playbooks[0]
    assert model["sequence"][0] == "lock fact grain"
    assert "grain" in model["evidence_gate"].lower()
