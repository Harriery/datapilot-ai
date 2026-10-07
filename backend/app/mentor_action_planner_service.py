from __future__ import annotations

from backend.app.models import (
    DataQualityFinding,
    WorkspaceLearningLoop,
)


_FREQUENCY_MARKERS = (
    "en sık", "en sik", "dağılım", "dagilim",
    "kaç tane", "kac tane", "frekans",
    "frequency", "distribution", "most common",
    "value_counts", "count by",
)
_FILTER_MARKERS = ("filtre", "filter")
_SECOND_FILTER_MARKERS = (
    "yeni", "ayrıca", "ayrica", "ikinci", "bir daha",
    "another", "new", "second", "which", "hangi",
)


def _contains_any(
    message: str,
    markers: tuple[str, ...],
) -> bool:
    normalized = message.casefold()
    return any(marker in normalized for marker in markers)


def _active_missing_filter(
    live_state: dict,
    target_name: str | None,
) -> bool:
    inspection = live_state.get("source_preview_inspection")
    if not isinstance(inspection, dict):
        return False

    for item in inspection.get("active_filters", []):
        if not isinstance(item, dict):
            continue
        if item.get("operator") != "is_missing":
            continue
        if target_name is None or item.get("column") == target_name:
            return True

    return False


def plan_guided_next_action(
    *,
    learner_message: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    mentor_context: dict,
) -> dict | None:
    """
    Choose only deterministic product actions/blockers.
    It never chooses the semantic data treatment for the learner.
    """
    diagnosis = mentor_context.get("execution_diagnosis")

    if isinstance(diagnosis, dict):
        status = diagnosis.get("status")
        issue_code = diagnosis.get("issue_code")

        if status == "error":
            return {
                "id": "repair_latest_notebook_error",
                "kind": "code_repair",
                "priority": "blocking",
                "control_id": "notebook.run_cell",
                "goal": (
                    "Explain the latest execution error and repair only that "
                    "current notebook cell before continuing."
                ),
                "issue_code": issue_code,
                "enforce_direct_reply": False,
            }

        if issue_code == "working_vs_raw_confusion":
            return {
                "id": "select_raw_notebook_dataset",
                "kind": "navigation",
                "priority": "blocking",
                "control_id": "notebook.dataset",
                "value": "raw",
                "goal": "Use original source rows for the missing-value investigation.",
                "enforce_direct_reply": True,
                "messages": {
                    "tr": (
                        "Notebook’taki Dataset menüsünden Raw source sample seç. "
                        "Orijinal eksik kayıtları working dataset’te aramayacağız."
                    ),
                    "nl": (
                        "Kies in Notebook bij Dataset voor Raw source sample. "
                        "Onderzoek de oorspronkelijke ontbrekende rijen niet in de working dataset."
                    ),
                    "en": (
                        "In Notebook, set Dataset to Raw source sample. "
                        "Do not investigate original missing rows in the working dataset."
                    ),
                },
            }

        if status in {"premature_action", "logic_mismatch", "off_task"}:
            return {
                "id": "repair_task_alignment",
                "kind": "code_reasoning",
                "priority": "blocking",
                "control_id": None,
                "goal": (
                    "Explain why the latest code is not aligned with the current "
                    "playbook phase, then give one correction target."
                ),
                "issue_code": issue_code,
                "enforce_direct_reply": False,
            }

    if (
        finding.issue_type != "missing_values"
        or loop.current_phase not in {"observe", "reason"}
    ):
        return None

    live_state = mentor_context.get("live_state")
    if not isinstance(live_state, dict):
        live_state = {}

    target_name = finding.column
    missing_filter_active = _active_missing_filter(
        live_state,
        target_name,
    )

    if (
        missing_filter_active
        and _contains_any(learner_message, _FILTER_MARKERS)
        and _contains_any(learner_message, _SECOND_FILTER_MARKERS)
    ):
        target_label = target_name or "target"
        return {
            "id": "keep_existing_missing_filter",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "raw_preview.filters",
            "goal": "Do not narrow rows with an unrelated second filter.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": (
                    f"Yeni filtre ekleme. {target_label} = Is missing filtresi açık "
                    "kalsın; ikinci filtre satırları daraltır, dağılımı hesaplamaz."
                ),
                "nl": (
                    f"Voeg geen nieuw filter toe. Laat {target_label} = Is missing "
                    "actief; een tweede filter beperkt rijen en berekent geen verdeling."
                ),
                "en": (
                    f"Do not add another filter. Keep {target_label} = Is missing "
                    "active; a second filter narrows rows and does not calculate a distribution."
                ),
            },
        }

    if not _contains_any(learner_message, _FREQUENCY_MARKERS):
        return None

    prepare_stage = live_state.get("active_prepare_stage")
    workbench_view = live_state.get("workbench_view")
    notebook = live_state.get("selected_notebook")
    notebook_count = int(live_state.get("notebook_count", 0) or 0)

    if prepare_stage != "workbench":
        return {
            "id": "open_workbench_for_frequency",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "workspace.prepare.workbench",
            "goal": "Move to a tool that can run a real frequency calculation.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": "Source Preview frekans hesabı yapmıyor. Önce Prepare > Workbench aşamasına geç.",
                "nl": "Source Preview berekent geen frequenties. Ga eerst naar Prepare > Workbench.",
                "en": "Source Preview cannot calculate frequencies. First go to Prepare > Workbench.",
            },
        }

    if workbench_view != "notebook":
        return {
            "id": "open_notebook_for_frequency",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "workbench.notebook",
            "goal": "Open Notebook for the calculation.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": "Workbench içindesin; şimdi Notebook görünümünü aç.",
                "nl": "Je bent in Workbench; open nu de Notebook-weergave.",
                "en": "You are in Workbench; now open the Notebook view.",
            },
        }

    if not isinstance(notebook, dict):
        if notebook_count > 0:
            messages = {
                "tr": "Notebook bölümünden mevcut notebook’lardan birini aç.",
                "nl": "Open een bestaand notebook in het Notebook-gedeelte.",
                "en": "Open one of the existing notebooks in the Notebook section.",
            }
            control_id = "artifact.notebook"
        else:
            messages = {
                "tr": "Workbench’te New notebook düğmesine bas.",
                "nl": "Klik in Workbench op New notebook.",
                "en": "In Workbench, click New notebook.",
            }
            control_id = "artifact.new_notebook"

        return {
            "id": "select_or_create_notebook",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": control_id,
            "goal": "Open a notebook before doing the calculation.",
            "enforce_direct_reply": True,
            "messages": messages,
        }

    if notebook.get("dataset_kind") != "raw":
        return {
            "id": "select_raw_notebook_dataset",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "notebook.dataset",
            "value": "raw",
            "goal": "Use original source rows for missing-value investigation.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": (
                    "Notebook’taki Dataset menüsünden Raw source sample seç. "
                    "Working dataset önceki cleaning adımlarını içeriyor."
                ),
                "nl": (
                    "Kies in Notebook bij Dataset voor Raw source sample. "
                    "De working dataset bevat al eerdere opschoningsstappen."
                ),
                "en": (
                    "In Notebook, set Dataset to Raw source sample. "
                    "The working dataset already contains prior cleaning steps."
                ),
            },
        }

    return {
        "id": "perform_scoped_frequency_check",
        "kind": "analysis",
        "priority": "current",
        "control_id": "notebook.run_cell",
        "goal": (
            "Use the raw notebook to calculate the requested frequency only "
            "within rows where the target column is missing. Teach the smallest "
            "code step appropriate to the assistance level."
        ),
        "target_column": target_name,
        "enforce_direct_reply": False,
    }


def render_planned_direct_reply(
    *,
    action: dict | None,
    language: str,
) -> str | None:
    if (
        not isinstance(action, dict)
        or action.get("enforce_direct_reply") is not True
    ):
        return None

    messages = action.get("messages")
    if not isinstance(messages, dict):
        return None

    value = messages.get(language) or messages.get("en")
    return str(value).strip() if value else None
