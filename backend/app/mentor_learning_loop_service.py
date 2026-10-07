from __future__ import annotations

import json
import os
import uuid

import backend.app.database as database

from backend.app.ai_provider_service import (
    get_ai_runtime,
)
from backend.app.ai_usage_guard import (
    guarded_responses_parse,
)
from backend.app.mentor_misconception_taxonomy import (
    normalize_misconception,
)
from backend.app.mentor_classifier_policy import (
    classifier_generation_kwargs,
    learning_evidence_classifier_rules,
)
from backend.app.mentor_orchestration_service import (
    determine_next_learning_phase,
)
from backend.app.mentor_reply_policy import (
    mentor_reply_rules,
)
from backend.app.mentor_action_planner_service import (
    render_planned_direct_reply,
    render_planned_local_support_reply,
)
from backend.app.models import (
    DataQualityFinding,
    LearningEvidenceContext,
    LearningEvidenceDecision,
    PrepareLearningPhaseEvaluation,
    PrepareMentorReply,
    Workspace,
    WorkspaceLearningLoop,
)


PREPARE_PHASES = (
    "observe",
    "reason",
    "decide",
    "implement",
    "validate",
    "explain",
)


def _phase_prompt(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
) -> str:
    target = (
        finding.column
        if finding.column
        else {
            "en": "the dataset",
            "nl": "de dataset",
            "tr": "veri seti",
        }[loop.language]
    )

    prompts = {
        "en": {
            "observe": (
                f"Inspect {target} first. "
                "What do you notice from the available evidence?"
            ),
            "reason": (
                "What might explain this? "
                "Which one piece of evidence would you check next?"
            ),
            "decide": (
                "What action would you choose? "
                "Give one short reason based on this data."
            ),
            "implement": (
                "Make the smallest safe change in the Workbench or notebook. "
                "Write and run the code yourself."
            ),
            "validate": (
                "Compare the result with the original data. "
                "Did the intended change happen safely?"
            ),
            "explain": (
                "What did you change, and which evidence shows it worked? "
                "Answer briefly in your own words."
            ),
            "completed": "This learning loop is complete.",
        },
        "nl": {
            "observe": (
                f"Bekijk eerst {target}. "
                "Wat valt je op in het beschikbare bewijs?"
            ),
            "reason": (
                "Wat kan dit verklaren? "
                "Welk bewijs zou je als volgende controleren?"
            ),
            "decide": (
                "Welke actie zou je kiezen? "
                "Geef één korte reden op basis van deze data."
            ),
            "implement": (
                "Voer de kleinste veilige wijziging uit in de Workbench of notebook. "
                "Schrijf en voer de code zelf uit."
            ),
            "validate": (
                "Vergelijk het resultaat met de oorspronkelijke data. "
                "Is de bedoelde wijziging veilig gelukt?"
            ),
            "explain": (
                "Wat heb je gewijzigd en welk bewijs toont dat het werkte? "
                "Antwoord kort in je eigen woorden."
            ),
            "completed": "Deze leerloop is voltooid.",
        },
        "tr": {
            "observe": (
                f"Önce {target} alanına bak. "
                "Eldeki kanıta göre ne fark ediyorsun?"
            ),
            "reason": (
                "Bunun nedeni ne olabilir? "
                "Bunu anlamak için önce hangi kanıta bakarsın?"
            ),
            "decide": (
                "Hangi işlemi seçersin? "
                "Bu veriye göre tek cümleyle nedenini söyle."
            ),
            "implement": (
                "Workbench veya notebook'ta en küçük güvenli değişikliği uygula. "
                "Kodu kendin yazıp çalıştır."
            ),
            "validate": (
                "Sonucu kaynak veriyle karşılaştır. "
                "İstediğin değişiklik güvenli şekilde gerçekleşti mi?"
            ),
            "explain": (
                "Neyi değiştirdin ve bunun çalıştığını hangi kanıt gösteriyor? "
                "Kısaca kendi cümlelerinle söyle."
            ),
            "completed": "Bu öğrenme döngüsü tamamlandı.",
        },
    }

    return prompts[loop.language][loop.current_phase]


def start_or_resume_prepare_learning_loop(
    *,
    workspace: Workspace,
    finding_index: int,
    finding: DataQualityFinding,
    skill_name: str,
    language: str = "en",
) -> tuple[WorkspaceLearningLoop, str]:
    for loop in workspace.learning_loops:
        if (
            loop.stage == "prepare"
            and loop.finding_index == finding_index
            and loop.status == "active"
        ):
            if language in {
                "en",
                "nl",
                "tr",
            }:
                loop.language = language

            return (
                loop,
                _phase_prompt(
                    loop=loop,
                    finding=finding,
                ),
            )

    loop = WorkspaceLearningLoop(
        loop_id=str(uuid.uuid4()),
        language=(
            language
            if language in {
                "en",
                "nl",
                "tr",
            }
            else "en"
        ),
        stage="prepare",
        finding_index=finding_index,
        skill_name=skill_name,
        target_type=(
            "column"
            if finding.column
            else "dataset"
        ),
        target_name=finding.column,
        current_phase="observe",
        completed_phases=[],
        status="active",
    )

    workspace.learning_loops.append(loop)

    return (
        loop,
        _phase_prompt(
            loop=loop,
            finding=finding,
        ),
    )


def evaluate_prepare_phase_response(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    response: str,
) -> PrepareLearningPhaseEvaluation:
    """
    Evaluate one learner-authored reasoning response.

    Only reasoning phases are reviewed from free text. Implement/validate
    remain gated by trusted Workbench transformation evidence.
    """
    if loop.current_phase not in {
        "observe",
        "reason",
        "decide",
        "explain",
    }:
        raise ValueError(
            "Current learning-loop phase is not a free-text reasoning phase."
        )

    payload = {
        "phase": loop.current_phase,
        "skill_name": loop.skill_name,
        "finding": finding.model_dump(),
        "learner_response": response,
    }

    phase_rubrics = {
        "observe": (
            "Success means the learner identifies a relevant observation "
            "from the supplied finding/evidence without inventing facts or "
            "jumping straight to a transformation."
        ),
        "reason": (
            "Success means the learner gives a plausible explanation or "
            "identifies evidence that would discriminate between possible "
            "causes. A bare fix without reasoning is not enough."
        ),
        "decide": (
            "Success means the learner chooses an action and justifies it "
            "from the available evidence. Automatic fill/drop rules without "
            "data-specific justification are insufficient."
        ),
        "explain": (
            "Success means the learner can explain what was changed, why the "
            "choice was appropriate, and how the trusted validation supports "
            "the result. Use trusted_validation from the loop when present."
        ),
    }

    instructions = f"""
    You evaluate one step in an adaptive Data Engineering learning loop.

    Current phase: {loop.current_phase}
    Skill: {loop.skill_name}

    Rubric:
    {phase_rubrics[loop.current_phase]}

    Rules:
    - Evaluate only the learner_response.
    - Finding is context, not learner evidence.
    - Do not reward confident wording by itself.
    - If it is a genuine attempt, set is_evidence=true and success true/false.
    - evidence_type should normally be "explanation" for observe/reason/decide/explain.
    - note must be concise and specific.

    Shared classifier policy:
    {learning_evidence_classifier_rules()}
    """

    runtime = get_ai_runtime(
        "guided_evaluator"
    )

    response_obj = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_learning_phase",
        model=runtime.model,
        input=json.dumps(
            {
                **payload,
                "trusted_validation":
                    loop.trusted_validation,
            },
            ensure_ascii=False,
            indent=2,
        ),
        instructions=instructions,
        text_format=PrepareLearningPhaseEvaluation,
        **classifier_generation_kwargs(),
    )

    evaluation = response_obj.output_parsed
    evaluation.misconception = normalize_misconception(
        success=evaluation.success,
        misconception=evaluation.misconception,
    )

    if evaluation.is_evidence:
        if (
            evaluation.success is None
            or evaluation.evidence_type is None
        ):
            raise ValueError(
                "Prepare phase evaluation is missing required evidence fields."
            )

    return evaluation


_LEARNING_UI_STRING_KEYS = {
    "active_workspace_stage",
    "active_prepare_stage",
    "workbench_view",
    "selected_notebook_id",
    "selected_notebook_dataset_kind",
    "selected_workbench_column",
}

_LEARNING_UI_BOOL_KEYS = {
    "validation_visible",
    "understand_visible",
    "source_preview_filter_builder_available",
    "source_preview_column_click_available",
    "source_preview_grouping_available",
    "source_preview_aggregation_available",
    "notebook_available",
}


def _safe_learning_ui_context(
    ui_context: dict | None,
) -> dict:
    """
    Keep only bounded UI state/capability fields that Guided Learning needs.

    UI context is navigation grounding, not learner evidence or dataset truth.
    """
    if not ui_context:
        return {}

    safe_context: dict = {}

    for key in _LEARNING_UI_STRING_KEYS:
        value = ui_context.get(key)

        if isinstance(value, str):
            safe_context[key] = value[:160]

    for key in _LEARNING_UI_BOOL_KEYS:
        value = ui_context.get(key)

        if isinstance(value, bool):
            safe_context[key] = value

    inspection = ui_context.get(
        "source_preview_inspection"
    )

    if isinstance(inspection, dict):
        safe_inspection: dict = {}

        dataset = inspection.get("dataset")
        if dataset in {"source", "working"}:
            safe_inspection["dataset"] = dataset

        columns = inspection.get("columns")
        if isinstance(columns, list):
            safe_inspection["columns"] = [
                item[:120]
                for item in columns[:80]
                if isinstance(item, str)
            ]

        column_types = inspection.get(
            "column_types"
        )
        if isinstance(column_types, dict):
            safe_column_types = {}

            for key, value in list(
                column_types.items()
            )[:80]:
                if (
                    isinstance(key, str)
                    and value in {
                        "text",
                        "number",
                        "datetime",
                        "boolean",
                    }
                ):
                    safe_column_types[
                        key[:120]
                    ] = value

            safe_inspection[
                "column_types"
            ] = safe_column_types

        for key in (
            "total_row_count",
            "filtered_row_count",
        ):
            value = inspection.get(key)
            if isinstance(value, int) and value >= 0:
                safe_inspection[key] = value

        filter_logic = inspection.get(
            "filter_logic"
        )
        if filter_logic in {"and", "or"}:
            safe_inspection[
                "filter_logic"
            ] = filter_logic

        active_filters = inspection.get(
            "active_filters"
        )
        if isinstance(active_filters, list):
            safe_filters = []

            for item in active_filters[:8]:
                if not isinstance(item, dict):
                    continue

                column = item.get("column")
                operator = item.get("operator")

                if (
                    not isinstance(column, str)
                    or not isinstance(operator, str)
                ):
                    continue

                safe_filters.append({
                    "column": column[:120],
                    "operator": operator[:80],
                    "value": (
                        str(item.get("value"))[:160]
                        if item.get("value") is not None
                        else None
                    ),
                    "value_to": (
                        str(item.get("value_to"))[:160]
                        if item.get("value_to") is not None
                        else None
                    ),
                })

            safe_inspection[
                "active_filters"
            ] = safe_filters

        if safe_inspection:
            safe_context[
                "source_preview_inspection"
            ] = safe_inspection

    return safe_context


def _safe_learning_history(
    learning_history: list[dict] | None,
) -> list[dict[str, str]]:
    if not learning_history:
        return []

    safe_history = []

    for item in learning_history[-6:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if (
            role not in {"user", "assistant"}
            or not isinstance(content, str)
        ):
            continue

        safe_history.append({
            "role": role,
            "content": content[:1200],
        })

    return safe_history


def _active_missing_filter_column(
    ui_context: dict | None,
) -> str | None:
    safe_context = _safe_learning_ui_context(
        ui_context
    )
    inspection = safe_context.get(
        "source_preview_inspection"
    )

    if not isinstance(inspection, dict):
        return None

    for item in inspection.get(
        "active_filters",
        [],
    ):
        if (
            isinstance(item, dict)
            and item.get("operator")
            == "is_missing"
            and isinstance(
                item.get("column"),
                str,
            )
        ):
            return item["column"]

    return None


def _direct_preview_filter_guidance(
    *,
    loop: WorkspaceLearningLoop,
    learner_response: str,
    ui_context: dict | None,
) -> str | None:
    """
    Deterministic navigation guard for a common Guided Learning failure mode:
    the learner already has the target missing-value filter active and asks
    whether another filter is needed to inspect another column.

    Filtering narrows rows; it does not compute a distribution. Keep this
    behavior out of the LLM so UI guidance remains reliable.
    """
    if loop.current_phase not in {
        "observe",
        "reason",
    }:
        return None

    target_column = (
        _active_missing_filter_column(
            ui_context
        )
    )
    if target_column is None:
        return None

    message = learner_response.casefold()

    filter_markers = (
        "filtre",
        "filter",
    )
    second_filter_markers = (
        "yeni",
        "ayrıca",
        "ayrica",
        "hangi",
        "bir daha",
        "another",
        "new",
        "which",
    )

    if not (
        any(
            marker in message
            for marker in filter_markers
        )
        and any(
            marker in message
            for marker in second_filter_markers
        )
    ):
        return None

    language = loop.language

    messages = {
        "tr": (
            f"Yeni filtre ekleme. {target_column} = Is missing filtresi açık "
            "kalsın; ikinci filtre satırları daha da daraltır, dağılımı göstermez."
        ),
        "nl": (
            f"Voeg geen nieuw filter toe. Laat {target_column} = Is missing "
            "actief; een tweede filter beperkt alleen de rijen en toont geen verdeling."
        ),
        "en": (
            f"Do not add another filter. Keep {target_column} = Is missing "
            "active; a second filter only narrows rows and does not show a distribution."
        ),
    }

    return messages[language]


def _direct_preview_frequency_navigation(
    *,
    loop: WorkspaceLearningLoop,
    learner_response: str,
    ui_context: dict | None,
) -> str | None:
    """
    Route unsupported frequency/distribution checks away from Source Preview.
    """
    if loop.current_phase not in {"observe", "reason"}:
        return None

    safe_context = _safe_learning_ui_context(ui_context)

    if (
        safe_context.get("source_preview_aggregation_available") is not False
        or safe_context.get("notebook_available") is not True
    ):
        return None

    message = learner_response.casefold()

    frequency_markers = (
        "en sık", "en sik", "dağılım", "dagilim",
        "kaç tane", "kac tane", "frekans",
        "frequency", "distribution", "most common", "count",
    )
    click_problem_markers = (
        "tıklayam", "tiklayam", "tıklanm", "tiklanm",
        "click", "source", "preview",
    )

    if not (
        any(marker in message for marker in frequency_markers)
        or (
            safe_context.get("source_preview_column_click_available") is False
            and any(marker in message for marker in click_problem_markers)
        )
    ):
        return None

    active_prepare_stage = safe_context.get("active_prepare_stage")
    workbench_view = safe_context.get("workbench_view")

    if loop.language == "tr":
        if active_prepare_stage != "workbench":
            return (
                "Source preview’da sütunlar tıklanabilir değil ve frekans sayımı yok. "
                "Önce Prepare > Workbench aşamasına geç."
            )
        if workbench_view != "notebook":
            return (
                "Workbench içindesin; şimdi üstteki Notebook sekmesine geç. "
                "Frekans sayımını orada yapacağız."
            )
        if safe_context.get(
            "selected_notebook_dataset_kind"
        ) != "raw":
            return (
                "Notebook’taki Dataset menüsünden Raw source sample seç. "
                "Working dataset temizlendiği için orijinal eksik Car satırları orada görünmez."
            )
        return None

    if loop.language == "nl":
        if active_prepare_stage != "workbench":
            return (
                "In Source preview zijn kolommen niet klikbaar en is er geen "
                "frequentietelling. Ga eerst naar Prepare > Workbench."
            )
        if workbench_view != "notebook":
            return (
                "Je bent in Workbench; ga nu naar het tabblad Notebook. "
                "Daar tellen we de frequenties."
            )
        if safe_context.get(
            "selected_notebook_dataset_kind"
        ) != "raw":
            return (
                "Kies in Notebook bij Dataset voor Raw source sample. "
                "De working dataset is al opgeschoond."
            )
        return None

    if active_prepare_stage != "workbench":
        return (
            "Source Preview columns are not clickable and it cannot calculate "
            "frequencies. First go to Prepare > Workbench."
        )
    if workbench_view != "notebook":
        return (
            "You are in Workbench; now open the Notebook tab. "
            "We will calculate the frequencies there."
        )
    if safe_context.get(
        "selected_notebook_dataset_kind"
    ) != "raw":
        return (
            "In Notebook, open the Dataset menu and select Raw source sample. "
            "The working dataset has already been cleaned."
        )
    return None


def _update_loop_language_from_message(
    loop: WorkspaceLearningLoop,
    message: str,
) -> None:
    normalized = message.casefold()

    if any(
        marker in normalized
        for marker in (
            "türkçe cevap", "turkce cevap",
            "türkçe yanıt", "turkce yanit",
            "bana türkçe", "bana turkce",
        )
    ):
        loop.language = "tr"
        return

    if any(
        marker in normalized
        for marker in (
            "antwoord in het nederlands",
            "in het nederlands",
            "nederlands antwoorden",
        )
    ):
        loop.language = "nl"
        return

    if any(
        marker in normalized
        for marker in (
            "answer in english",
            "reply in english",
        )
    ):
        loop.language = "en"


def render_zero_ai_prepare_support_reply(
    *,
    loop: WorkspaceLearningLoop,
    learner_response: str,
    mentor_context: dict | None,
) -> str | None:
    """
    Return a local reply for deterministic technical workflow states.

    These turns gather/inspect trusted execution evidence; they are not learner
    reasoning assessments and therefore must not spend classifier or Mentor LLM
    tokens.
    """
    _update_loop_language_from_message(
        loop,
        learner_response,
    )

    context = (
        mentor_context
        if isinstance(mentor_context, dict)
        else {}
    )
    workflow = context.get("workflow")
    if not isinstance(workflow, dict):
        return None

    state = workflow.get("state")
    zero_ai_states = {
        "NEED_SUBSET_RESULT",
        "SUBSET_RESULT_READY",
    }

    if state not in zero_ai_states:
        return None

    blocker = workflow.get("blocker")
    if (
        isinstance(blocker, dict)
        and blocker.get("kind")
        == "execution_error"
    ):
        # Error repair may require semantic code diagnosis.
        return None

    return render_planned_local_support_reply(
        action=context.get("next_action"),
        language=loop.language,
    )


def _compact_mentor_reply_context(
    mentor_context: dict | None,
) -> dict:
    if not isinstance(mentor_context, dict):
        return {}

    workflow = mentor_context.get("workflow")
    next_action = mentor_context.get("next_action")
    diagnosis = mentor_context.get("execution_diagnosis")
    playbook = mentor_context.get("playbook")
    learner = mentor_context.get("learner")
    supervisor = mentor_context.get("supervisor")

    compact: dict = {}

    if isinstance(workflow, dict):
        compact["workflow"] = {
            "state": workflow.get("state"),
            "phase": workflow.get("phase"),
            "issue_type": workflow.get("issue_type"),
            "target_name": workflow.get("target_name"),
            "blocker": workflow.get("blocker"),
            "investigation": workflow.get("investigation"),
        }

    if isinstance(next_action, dict):
        compact["next_action"] = {
            key: next_action.get(key)
            for key in (
                "id",
                "kind",
                "goal",
                "control_id",
                "code_template",
                "workflow_state",
                "target_column",
                "comparison_column",
                "subset_output",
                "baseline_output",
                "issue_code",
            )
            if key in next_action
        }

    if isinstance(diagnosis, dict):
        compact["execution_diagnosis"] = {
            key: diagnosis.get(key)
            for key in (
                "status",
                "issue_code",
                "misconception",
                "output",
            )
            if key in diagnosis
        }

    if isinstance(playbook, dict):
        compact["playbook"] = {
            "phase": playbook.get("phase"),
            "goal": playbook.get("goal"),
            "evidence": playbook.get("evidence"),
            "avoid": playbook.get("avoid"),
        }

    if isinstance(supervisor, dict):
        compact["supervisor"] = {
            "status": supervisor.get("status"),
            "next_objective": supervisor.get("next_objective"),
            "stop_exploration": supervisor.get("stop_exploration"),
        }

    if isinstance(learner, dict):
        compact["learner"] = {
            key: learner.get(key)
            for key in (
                "skill_name",
                "status",
                "success_rate",
                "last_assistance_level",
                "misconceptions",
            )
            if key in learner
        }

    return compact


def generate_prepare_mentor_reply(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    learner_response: str,
    evaluation: PrepareLearningPhaseEvaluation,
    assistance_level: str,
    ui_context: dict | None = None,
    learning_history: list[dict] | None = None,
    mentor_context: dict | None = None,
) -> str:
    """
    Generate the learner-facing Mentor reply after classification.

    The model does not choose success, assistance level, or the next learning
    phase. Those decisions are supplied by DataPilot's deterministic policy.
    """
    _update_loop_language_from_message(
        loop,
        learner_response,
    )

    next_phase = determine_next_learning_phase(
        current_phase=loop.current_phase,
        is_evidence=evaluation.is_evidence,
        success=evaluation.success,
    )

    planned_reply = (
        render_planned_direct_reply(
            action=(
                mentor_context or {}
            ).get("next_action"),
            language=loop.language,
        )
    )
    if planned_reply is not None:
        return planned_reply

    # Isolated/legacy callers may not yet supply centralized Mentor V2 context.
    if not mentor_context:
        direct_guidance = (
            _direct_preview_filter_guidance(
                loop=loop,
                learner_response=learner_response,
                ui_context=ui_context,
            )
        )
        if direct_guidance is not None:
            return direct_guidance

        frequency_navigation = _direct_preview_frequency_navigation(
            loop=loop,
            learner_response=learner_response,
            ui_context=ui_context,
        )
        if frequency_navigation is not None:
            return frequency_navigation

    runtime = get_ai_runtime(
        "guided_tutor"
    )

    instructions = f"""
    You are DataPilot's adaptive Data Engineering mentor.

    Learning evaluation and orchestration are already complete.
    Do not reclassify the learner. Do not choose a different assistance level
    or learning phase. Follow the supplied orchestration exactly.

    Response rules:
    {mentor_reply_rules()}

    Mentor V2/V3 backend context:
    - mentor_context.workflow is the authoritative deterministic technical
      workflow state when present. The learner's wording does not change that
      state. Use the learner message only to decide how to teach/explain the
      current state; never infer that a technical step completed from prose.
    - mentor_context.product is the authoritative DataPilot capability map for
      the learner's current location. Never invent a control not listed there.
    - mentor_context.playbook is the professional Data Engineering reasoning
      path for this issue and phase. Do not skip its evidence gates.
    - mentor_context.execution_diagnosis is deterministic review of the latest
      trusted notebook code/output when present. Address an execution error,
      wrong dataset context, premature transformation, or logic mismatch before
      assigning a new analysis step.
    - mentor_context.learner summarizes real progress and recurring
      misconceptions. Use it to choose explanation depth, not to lower standards.
    - mentor_context.next_action is the backend's deterministic next-action
      recommendation. If present, do not assign a different task. If it describes
      a code repair, explain that repair before any new analysis.
    - If the learner asks what current code means, what a parameter/function
      means, or says they could not write the code independently, explain that
      exact code/concept briefly before assigning another analysis step.
      Do not redirect them to documentation unless they explicitly ask for sources.
    - Respond in the loop's current language. An explicit learner language
      request has already updated that state.
    - Give only the next atomic action. Backend context is a map, not content to
      dump back to the learner.

    UI grounding:
    - ui_context contains only current DataPilot UI state/capabilities.
    - Treat it as navigation grounding, not as dataset evidence.
    - Name or tell the learner to use a specific UI control only when the
      supplied ui_context confirms that capability exists.
    - If the learner explicitly asks where/how to click and a relevant UI
      capability is available, give exactly one concrete UI action.
    - Never invent buttons, filters, tabs, controls, or actions that are absent
      or unknown in ui_context.
    - If source_preview_inspection shows that the relevant filter is already
      active, treat that navigation step as completed and DO NOT ask the learner
      to apply the same filter again.
    - Use filtered_row_count and available column names only as inspection
      context. Do not infer row values or business meaning that are not supplied.
    - During observe/reason, do not jump to "validate the business rule" before
      the learner has inspected a concrete pattern. Give one concrete inspection
      target at a time, grounded in available columns.
    - For missing-value reasoning, do NOT propose mean/median/mode/zero filling,
      deletion, or any other imputation before the learner has gathered evidence
      and reached the decide phase.
    - Do not infer business semantics from a column name alone. A name like
      "Car", "Type", or "Rooms" is not sufficient evidence for what it means.
    - When choosing the next manual preview check, prefer one EXISTING
      non-target categorical/text/boolean column from
      source_preview_inspection.column_types. Frame it as a pattern check, not
      as a causal rule.
    - Never invent a multi-column grouping rule. Only ask for grouping or
      aggregation if the context justifies it.
    - Source Preview column headers are clickable only when
      source_preview_column_click_available=true. Never tell the learner to
      click a Source Preview column when that capability is false.
    - For inspection of original missing-value rows, use a raw/source-backed
      notebook. A working notebook may no longer contain those missing values
      after cleaning.
    - If grouping/aggregation is actually needed but
      source_preview_grouping_available/source_preview_aggregation_available is
      false, do not tell the learner to perform it in Preview. If
      notebook_available=true and the learner asks where/how, guide them toward
      the Notebook one navigation step at a time.
    - recent_learning_history records the last Guided Learning turns. Respect
      completed actions stated there and do not loop back to the same instruction.
    """

    response_obj = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_learning_reply",
        model=runtime.model,
        instructions=instructions,
        input=json.dumps(
            {
                "finding":
                    finding.model_dump(),
                "learner_message":
                    learner_response,
                "learning_evaluation":
                    evaluation.model_dump(),
                "ui_context":
                    _safe_learning_ui_context(
                        ui_context
                    ),
                "recent_learning_history":
                    _safe_learning_history(
                        learning_history
                    )[-4:],
                "mentor_context":
                    _compact_mentor_reply_context(
                        mentor_context
                    ),
                "orchestration": {
                    "current_phase":
                        loop.current_phase,
                    "assistance_level":
                        assistance_level,
                    "next_phase":
                        next_phase,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        text_format=PrepareMentorReply,
    )

    return (
        response_obj.output_parsed
        .mentor_reply
        .strip()
    )


def record_prepare_phase_evidence(
    *,
    learner_id: str,
    workspace_id: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    assistance_level: str,
    evaluation: PrepareLearningPhaseEvaluation,
) -> LearningEvidenceDecision:
    evidence = LearningEvidenceDecision(
        is_evidence=evaluation.is_evidence,
        evidence_type=evaluation.evidence_type,
        success=evaluation.success,
        note=evaluation.note,
    )

    if not evidence.is_evidence:
        return evidence

    context = LearningEvidenceContext(
        workspace_id=workspace_id,
        stage="prepare",
        learning_phase=loop.current_phase,
        task_type=finding.issue_type,
        target_type=loop.target_type,
        target_name=loop.target_name,
        user_authored=True,
        deterministic_validation=False,
        misconception=evaluation.misconception,
        metadata={
            "finding_index": loop.finding_index,
            "loop_id": loop.loop_id,
        },
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=loop.skill_name,
        assistance_level=assistance_level,
        success=bool(evidence.success),
        evidence_type=str(evidence.evidence_type),
        note=evidence.note,
        session_id=None,
        context=context.model_dump(
            exclude_none=True,
        ),
    )

    return evidence


def apply_learning_phase_review(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    evidence: LearningEvidenceDecision,
) -> tuple[WorkspaceLearningLoop, str]:
    if loop.status == "completed":
        return (
            loop,
            "This learning loop is already complete.",
        )

    if loop.current_phase in {
        "implement",
        "validate",
    }:
        raise ValueError(
            "Implement and validate phases must be advanced by trusted "
            "Workbench/transformation validation, not free-text review."
        )

    if (
        not evidence.is_evidence
        or evidence.success is not True
    ):
        return (
            loop,
            _phase_prompt(
                loop=loop,
                finding=finding,
            ),
        )

    current_phase = loop.current_phase

    if current_phase not in loop.completed_phases:
        loop.completed_phases.append(
            current_phase
        )

    current_index = PREPARE_PHASES.index(
        current_phase
    )

    next_phase = PREPARE_PHASES[
        current_index + 1
    ]

    loop.current_phase = next_phase

    return (
        loop,
        _phase_prompt(
            loop=loop,
            finding=finding,
        ),
    )


def record_trusted_prepare_validation_evidence(
    *,
    learner_id: str,
    workspace_id: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    assistance_level: str,
    success: bool,
    validation_summary: dict,
) -> LearningEvidenceDecision:
    evidence = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=success,
        note=(
            "Trusted Workbench validation confirmed the learner's "
            "transformation."
            if success
            else
            "Trusted Workbench validation did not confirm the learner's "
            "transformation."
        ),
    )

    context = LearningEvidenceContext(
        workspace_id=workspace_id,
        stage="prepare",
        learning_phase="validate",
        task_type=finding.issue_type,
        target_type=loop.target_type,
        target_name=loop.target_name,
        user_authored=True,
        deterministic_validation=True,
        metadata={
            "finding_index": loop.finding_index,
            "loop_id": loop.loop_id,
            "validated_phases": [
                "implement",
                "validate",
            ],
            **validation_summary,
        },
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=loop.skill_name,
        assistance_level=assistance_level,
        success=success,
        evidence_type="application",
        note=evidence.note,
        session_id=None,
        context=context.model_dump(
            exclude_none=True,
        ),
    )

    return evidence


def apply_trusted_prepare_validation(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    success: bool,
) -> tuple[WorkspaceLearningLoop, str]:
    if loop.status == "completed":
        return (
            loop,
            "This learning loop is already complete.",
        )

    if loop.current_phase not in {
        "implement",
        "validate",
    }:
        raise ValueError(
            "Trusted transformation validation can only advance the "
            "implement/validate portion of the prepare learning loop."
        )

    if not success:
        loop.current_phase = "implement"

        return (
            loop,
            _phase_prompt(
                loop=loop,
                finding=finding,
            ),
        )

    loop.trusted_validation = {
        "success": True,
        "finding_type": finding.issue_type,
        "target_name": finding.column,
    }

    for phase in (
        "implement",
        "validate",
    ):
        if phase not in loop.completed_phases:
            loop.completed_phases.append(
                phase
            )

    loop.current_phase = "explain"

    return (
        loop,
        _phase_prompt(
            loop=loop,
            finding=finding,
        ),
    )


def complete_prepare_learning_loop(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    evidence: LearningEvidenceDecision,
) -> tuple[WorkspaceLearningLoop, str]:
    if loop.current_phase != "explain":
        raise ValueError(
            "Prepare learning loop can only be completed from explain phase."
        )

    if (
        not evidence.is_evidence
        or evidence.success is not True
    ):
        return (
            loop,
            _phase_prompt(
                loop=loop,
                finding=finding,
            ),
        )

    if "explain" not in loop.completed_phases:
        loop.completed_phases.append(
            "explain"
        )

    loop.current_phase = "completed"
    loop.status = "completed"

    completed_messages = {
        "en": (
            "Learning loop complete. The decision, implementation, validation, "
            "and explanation are now recorded as separate learning evidence."
        ),
        "nl": (
            "De leerloop is voltooid. Besluit, uitvoering, validatie en uitleg "
            "zijn nu als afzonderlijk leerbewijs opgeslagen."
        ),
        "tr": (
            "Öğrenme döngüsü tamamlandı. Karar, uygulama, doğrulama ve açıklama "
            "ayrı öğrenme kanıtları olarak kaydedildi."
        ),
    }

    return (
        loop,
        completed_messages[
            loop.language
        ],
    )
