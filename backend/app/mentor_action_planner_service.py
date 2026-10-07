from __future__ import annotations

import re

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
_NEXT_STEP_MARKERS = (
    "ne yap", "nasil", "nasıl", "adim adim", "adım adım",
    "nereden", "nerde", "nerede", "yonlendir", "yönlendir",
    "kontrol edicem", "kontrol edeceğim", "inceleyecegim",
    "inceleyeceğim", "what next", "how do", "where do",
)
_CODE_HELP_MARKERS = (
    "ne yaz", "kodu bilmiyorum", "kod bilmiyorum", "kod ver",
    "nasil yaz", "nasıl yaz", "what do i write", "what code",
    "show me the code",
)
_CODE_EXPLANATION_MARKERS = (
    "bu kod ne", "kod ne anlama", "kod ne demek",
    "kodu anlamıyorum", "kodu anlamiyorum",
    "normalize ne", "normalize nedir", "dropna ne", "dropna nedir",
    "value_counts ne", "value_counts nedir",
    "what does this code", "what is normalize", "what is dropna",
    "explain the code",
)
_RESULT_EXPLANATION_MARKERS = (
    "sonuç ne", "sonuc ne", "sonuçlar ne", "sonuclar ne",
    "ne anlatıyor", "ne anlatiyor", "ne anlamalıyım", "ne anlamaliyim",
    "çıktı ne", "cikti ne", "output ne", "outputtaki",
    "buradan ne", "bu sonuçtan", "bu sonuctan",
    "what does the result", "what does this result",
    "what does the output", "what should i understand",
    "explain the result", "explain the output",
)


def _contains_any(message: str, markers: tuple[str, ...]) -> bool:
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


def _profile_columns(profile: dict) -> list[str]:
    columns = profile.get("columns")
    if not isinstance(columns, list):
        return []
    return [str(item) for item in columns if isinstance(item, str)]


def _mentioned_comparison_column(
    message: str,
    *,
    profile: dict,
    target_name: str | None,
) -> str | None:
    normalized = message.casefold()
    for column in _profile_columns(profile):
        if target_name is not None and column == target_name:
            continue
        if column.casefold() in normalized:
            return column
    return None


def _choose_pattern_column(
    *,
    profile: dict,
    target_name: str | None,
) -> str | None:
    """
    Choose a dataset-agnostic pattern-check column from real profile metadata.

    Prefer low-cardinality categorical/boolean columns. Numeric low-cardinality
    columns are only a fallback. We never infer business meaning from names.
    """
    columns = _profile_columns(profile)
    data_types = profile.get("data_types")
    distinct_counts = profile.get("distinct_counts")
    row_count = int(profile.get("row_count") or 0)

    if not isinstance(data_types, dict):
        data_types = {}
    if not isinstance(distinct_counts, dict):
        distinct_counts = {}

    categorical = []
    numeric_fallback = []

    for index, column in enumerate(columns):
        if column == target_name:
            continue

        distinct = distinct_counts.get(column)
        if not isinstance(distinct, int) or distinct < 2:
            continue

        dtype = str(data_types.get(column) or "").casefold()
        max_reasonable = min(30, max(8, int((row_count or 64) ** 0.5)))

        if distinct > max_reasonable:
            continue

        if any(token in dtype for token in ("object", "string", "category", "bool")):
            categorical.append((distinct, index, column))
            continue

        if any(token in dtype for token in ("int", "float", "number")) and distinct <= 12:
            numeric_fallback.append((distinct, index, column))

    pool = categorical or numeric_fallback
    if not pool:
        return None

    pool.sort(key=lambda item: (item[0], item[1]))
    return pool[0][2]


def _locked_investigation(
    loop: WorkspaceLearningLoop,
    *,
    finding: DataQualityFinding,
) -> dict | None:
    value = loop.active_investigation
    if not isinstance(value, dict) or not value:
        return None

    if (
        value.get("kind") != "missingness_pattern_frequency"
        or value.get("target_column") != finding.column
    ):
        return None

    return value


def _start_investigation_if_needed(
    *,
    learner_message: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    mentor_context: dict,
    missing_filter_active: bool,
) -> dict | None:
    existing = _locked_investigation(
        loop,
        finding=finding,
    )
    if existing is not None:
        return existing

    if not missing_filter_active:
        return None

    wants_next_step = (
        _contains_any(learner_message, _NEXT_STEP_MARKERS)
        or _contains_any(learner_message, _FREQUENCY_MARKERS)
    )
    if not wants_next_step:
        return None

    profile = mentor_context.get("profile")
    if not isinstance(profile, dict):
        profile = {}

    supervisor = mentor_context.get("supervisor")
    if not isinstance(supervisor, dict):
        supervisor = {}

    recommendation = supervisor.get(
        "recommended_investigation"
    )

    comparison = None
    if isinstance(recommendation, dict):
        candidate = recommendation.get(
            "comparison_column"
        )
        if isinstance(candidate, str):
            comparison = candidate

    if comparison is None:
        comparison = _mentioned_comparison_column(
            learner_message,
            profile=profile,
            target_name=finding.column,
        )

    if comparison is None:
        comparison = _choose_pattern_column(
            profile=profile,
            target_name=finding.column,
        )

    if comparison is None:
        return None

    loop.active_investigation = {
        "kind": "missingness_pattern_frequency",
        "target_column": finding.column,
        "comparison_column": comparison,
        "step": "subset_frequency",
        "subset_output": None,
        "baseline_output": None,
        "last_processed_observation_id": None,
    }
    return loop.active_investigation


def _subset_code(target: str, comparison: str) -> str:
    return (
        f"df.loc[df[{target!r}].isna(), {comparison!r}]"
        ".value_counts(normalize=True, dropna=False)"
    )


def _baseline_code(comparison: str) -> str:
    return (
        f"df[{comparison!r}]"
        ".value_counts(normalize=True, dropna=False)"
    )


def _code_teaching_action(
    *,
    learner_message: str,
    investigation: dict | None,
) -> dict | None:
    if (
        not isinstance(investigation, dict)
        or not _contains_any(
            learner_message,
            _CODE_EXPLANATION_MARKERS,
        )
    ):
        return None

    target = str(
        investigation.get("target_column")
        or "target"
    )
    comparison = str(
        investigation.get("comparison_column")
        or "comparison"
    )
    step = investigation.get("step")

    if step == "baseline_frequency":
        code = _baseline_code(comparison)
        tr = (
            f"Bu kod tüm raw veride {comparison} dağılımını ölçüyor. "
            f"value_counts() değerleri sayar; normalize=True sayıyı oran olarak verir "
            f"(0.52 ≈ %52); dropna=False boş {comparison} değerlerini de sonuçta tutar. "
            "Kodu ezberlemen gerekmiyor; şu an mantığını anlaman yeterli."
        )
        en = (
            f"This code measures the overall {comparison} distribution in raw data. "
            "value_counts() counts values, normalize=True returns proportions, and "
            "dropna=False keeps missing values in the result."
        )
        nl = (
            f"Deze code meet de totale verdeling van {comparison}. "
            "value_counts() telt waarden, normalize=True geeft verhoudingen en "
            "dropna=False houdt ontbrekende waarden in het resultaat."
        )
    else:
        code = _subset_code(target, comparison)
        tr = (
            f"Bu kod önce {target} değeri eksik olan satırları seçiyor, sonra yalnızca "
            f"o satırlardaki {comparison} dağılımını ölçüyor. value_counts() değerleri "
            "sayar; normalize=True oran verir; dropna=False boş değerleri de sayımda tutar. "
            "Kodu ezberlemen gerekmiyor."
        )
        en = (
            f"This code first keeps rows where {target} is missing, then measures "
            f"the {comparison} distribution inside that subset. normalize=True returns "
            "proportions and dropna=False includes missing values."
        )
        nl = (
            f"Deze code houdt eerst rijen waar {target} ontbreekt en meet daarna "
            f"de verdeling van {comparison}. normalize=True geeft verhoudingen en "
            "dropna=False telt ontbrekende waarden mee."
        )

    return {
        "id": "explain_locked_investigation_code",
        "kind": "teaching",
        "priority": "blocking",
        "control_id": None,
        "goal": (
            "Explain the current investigation code before assigning "
            "another analysis action."
        ),
        "code_template": code,
        "target_column": target,
        "comparison_column": comparison,
        "enforce_direct_reply": True,
        "messages": {
            "tr": tr,
            "nl": nl,
            "en": en,
        },
    }


def _result_teaching_action(
    *,
    learner_message: str,
    investigation: dict | None,
    diagnosis: dict | None,
) -> dict | None:
    """
    Explain the latest trusted investigation output without advancing state.

    The workflow engine owns progression. This helper only shapes teaching for
    the current state when the learner asks what the result means.
    """
    if (
        not isinstance(investigation, dict)
        or not _contains_any(
            learner_message,
            _RESULT_EXPLANATION_MARKERS,
        )
    ):
        return None

    target = str(
        investigation.get("target_column")
        or "target"
    )
    comparison = str(
        investigation.get("comparison_column")
        or "comparison"
    )

    issue_code = None
    output = None

    if isinstance(diagnosis, dict):
        issue_code = diagnosis.get("issue_code")
        if issue_code in {
            "missing_scoped_frequency_check",
            "baseline_frequency_check",
        }:
            output = diagnosis.get("output")

    if not output:
        if investigation.get("baseline_output"):
            issue_code = "baseline_frequency_check"
            output = investigation.get("baseline_output")
        elif investigation.get("subset_output"):
            issue_code = "missing_scoped_frequency_check"
            output = investigation.get("subset_output")

    if not output:
        return None

    if issue_code == "baseline_frequency_check":
        goal = (
            f"Explain the overall raw-data {comparison} distribution in simple "
            f"language and compare it with the already collected {target}-missing "
            "subset distribution. State only what the evidence supports; do not "
            "claim causality or open a new comparison column."
        )
    else:
        goal = (
            f"Explain that this output describes the {comparison} proportions only "
            f"inside rows where {target} is missing. Translate the proportions into "
            "plain language and state that this result alone cannot show whether "
            f"{target} missingness is concentrated by {comparison}; an overall "
            "baseline is still needed. Do not assign the baseline command in the "
            "same reply."
        )

    return {
        "id": "explain_current_investigation_result",
        "kind": "teaching_interpretation",
        "priority": "blocking",
        "control_id": None,
        "goal": goal,
        "target_column": target,
        "comparison_column": comparison,
        "output": output,
        "enforce_direct_reply": False,
    }


def _navigation_or_subset_action(
    *,
    learner_message: str,
    live_state: dict,
    investigation: dict,
) -> dict:
    target = str(investigation["target_column"])
    comparison = str(investigation["comparison_column"])

    prepare_stage = live_state.get("active_prepare_stage")
    workbench_view = live_state.get("workbench_view")
    notebook = live_state.get("selected_notebook")
    notebook_count = int(live_state.get("notebook_count", 0) or 0)

    if prepare_stage != "workbench":
        return {
            "id": "open_workbench_for_locked_investigation",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "workspace.prepare.workbench",
            "goal": (
                f"Keep the locked {target} missingness investigation using "
                f"{comparison}; move to a tool that can calculate proportions."
            ),
            "enforce_direct_reply": True,
            "messages": {
                "tr": (
                    f"Hedefimiz değişmiyor: {target} eksik satırlarında {comparison} "
                    "değerlerinin yoğunlaşıp yoğunlaşmadığını kontrol edeceğiz. "
                    "Source Preview oran hesaplamıyor; ilk adım olarak Prepare > Workbench’e geç."
                ),
                "nl": (
                    f"Ons doel blijft hetzelfde: controleer de verdeling van {comparison} "
                    f"binnen rijen waar {target} ontbreekt. Ga eerst naar Prepare > Workbench."
                ),
                "en": (
                    f"Keep the same goal: check whether {comparison} is concentrated "
                    f"where {target} is missing. First go to Prepare > Workbench."
                ),
            },
        }

    if workbench_view != "notebook":
        return {
            "id": "open_notebook_for_locked_investigation",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "workbench.notebook",
            "goal": "Open Notebook without changing the locked investigation target.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": (
                    f"{target} → {comparison} araştırmasına devam ediyoruz. "
                    "Şimdi Workbench içindeki Notebook görünümünü aç."
                ),
                "nl": f"We gaan verder met {target} → {comparison}. Open nu Notebook.",
                "en": f"Continue the {target} → {comparison} check. Open Notebook now.",
            },
        }

    if not isinstance(notebook, dict):
        if notebook_count > 0:
            message_tr = (
                f"Yeni bir analiz hedefi seçme; {target} → {comparison} aynı kalıyor. "
                "Notebook bölümünden mevcut notebook’lardan birini aç."
            )
            control_id = "artifact.notebook"
        else:
            message_tr = (
                f"{target} → {comparison} kontrolü için Workbench’te New notebook düğmesine bas."
            )
            control_id = "artifact.new_notebook"

        return {
            "id": "select_or_create_notebook_for_locked_investigation",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": control_id,
            "goal": "Open a notebook while preserving the current investigation.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": message_tr,
                "nl": "Open een notebook en houd hetzelfde onderzoeksdoel aan.",
                "en": "Open a notebook and keep the same investigation target.",
            },
        }

    if notebook.get("dataset_kind") != "raw":
        return {
            "id": "select_raw_notebook_dataset",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "notebook.dataset",
            "value": "raw",
            "goal": "Use original source rows for the locked missingness investigation.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": (
                    f"Notebook’taki Dataset menüsünden Raw source sample seç. "
                    f"{target} eksiklerini orijinal veride {comparison} ile karşılaştıracağız."
                ),
                "nl": "Kies in Notebook bij Dataset voor Raw source sample.",
                "en": "In Notebook, set Dataset to Raw source sample.",
            },
        }

    code = _subset_code(target, comparison)
    explicit_code_help = _contains_any(
        learner_message,
        _CODE_HELP_MARKERS,
    )

    return {
        "id": "run_locked_subset_frequency",
        "kind": "analysis",
        "priority": "current",
        "control_id": "notebook.run_cell",
        "goal": (
            f"Calculate normalized {comparison} frequencies only in rows where "
            f"{target} is missing. Do not change the comparison column."
        ),
        "target_column": target,
        "comparison_column": comparison,
        "code_template": code,
        "enforce_direct_reply": explicit_code_help,
        "messages": {
            "tr": (
                "Yeni notebook açmana gerek yok; açık notebook’u kullan. "
                f"Bir Python hücresine şu kodu yaz ve Run cell’a bas: "
                f"{code}"
            ),
            "nl": f"Gebruik het geopende notebook. Voer deze code uit: {code}",
            "en": f"Use the open notebook. Run this code: {code}",
        },
    }


def _state_driven_action(
    *,
    learner_message: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    mentor_context: dict,
) -> dict | None:
    workflow = mentor_context.get("workflow")
    if not isinstance(workflow, dict):
        return None

    state = workflow.get("state")
    live_state = mentor_context.get("live_state")
    if not isinstance(live_state, dict):
        live_state = {}

    diagnosis = mentor_context.get(
        "execution_diagnosis"
    )
    blocker = workflow.get("blocker")
    investigation = workflow.get(
        "investigation"
    )
    if not isinstance(investigation, dict):
        investigation = {}

    if isinstance(blocker, dict):
        if blocker.get("kind") == "execution_error":
            return {
                "id": "repair_latest_notebook_error",
                "kind": "code_repair",
                "priority": "blocking",
                "control_id": "notebook.run_cell",
                "goal": (
                    "Explain and repair the latest trusted notebook error "
                    "before continuing the current workflow state."
                ),
                "issue_code": blocker.get(
                    "issue_code"
                ),
                "workflow_state": state,
                "enforce_direct_reply": False,
            }

        if (
            blocker.get("issue_code")
            == "working_vs_raw_confusion"
        ):
            return {
                "id": "select_raw_notebook_dataset",
                "kind": "navigation",
                "priority": "blocking",
                "control_id": "notebook.dataset",
                "value": "raw",
                "goal": (
                    "Use raw source rows before continuing the locked investigation."
                ),
                "workflow_state": state,
                "enforce_direct_reply": True,
                "messages": {
                    "tr": (
                        "Bu inceleme orijinal eksik satırları gerektiriyor. "
                        "Notebook içindeki Dataset menüsünden Raw source sample seç."
                    ),
                    "nl": (
                        "Kies in Notebook bij Dataset voor Raw source sample."
                    ),
                    "en": (
                        "In Notebook, set Dataset to Raw source sample."
                    ),
                },
            }

        if (
            blocker.get("issue_code")
            == "investigation_target_mismatch"
        ):
            comparison = investigation.get(
                "comparison_column"
            )
            return {
                "id": "repair_locked_investigation_target",
                "kind": "code_reasoning",
                "priority": "blocking",
                "control_id": None,
                "goal": (
                    f"Return to the locked comparison column {comparison}; "
                    "the technical workflow state has not changed."
                ),
                "comparison_column": comparison,
                "workflow_state": state,
                "enforce_direct_reply": False,
            }

    if state == "NEED_SUBSET_RESULT":
        if not investigation:
            return None
        action = _navigation_or_subset_action(
            learner_message=learner_message,
            live_state=live_state,
            investigation=investigation,
        )
        action["workflow_state"] = state
        return action

    if state == "SUBSET_RESULT_READY":
        if _contains_any(
            learner_message,
            _RESULT_EXPLANATION_MARKERS,
        ):
            action = _result_teaching_action(
                learner_message=learner_message,
                investigation=investigation,
                diagnosis=diagnosis,
            )
            if action is not None:
                action["workflow_state"] = state
            return action

        if _contains_any(
            learner_message,
            _CODE_EXPLANATION_MARKERS,
        ):
            comparison = str(
                investigation.get(
                    "comparison_column"
                )
                or "comparison"
            )
            code = _baseline_code(comparison)
            return {
                "id": "explain_next_baseline_code",
                "kind": "teaching",
                "priority": "current",
                "control_id": None,
                "goal": (
                    "Explain the baseline code without claiming that it has run."
                ),
                "code_template": code,
                "workflow_state": state,
                "enforce_direct_reply": False,
            }

        comparison = str(
            investigation.get(
                "comparison_column"
            )
        )
        code = _baseline_code(comparison)
        return {
            "id": "run_locked_baseline_frequency",
            "kind": "analysis",
            "priority": "current",
            "control_id": "notebook.run_cell",
            "goal": (
                f"Calculate the overall raw-data {comparison} distribution "
                "to compare with the already-observed missing subset."
            ),
            "comparison_column": comparison,
            "code_template": code,
            "workflow_state": state,
            "enforce_direct_reply": True,
            "messages": {
                "tr": (
                    f"Şimdi aynı {comparison} sütununun tüm raw verideki dağılımını "
                    f"karşılaştırma tabanı olarak çıkar. Şunu çalıştır: {code}"
                ),
                "nl": (
                    f"Bereken nu de totale {comparison}-verdeling met: {code}"
                ),
                "en": (
                    f"Now calculate the overall {comparison} distribution with: {code}"
                ),
            },
        }

    if state == "NEED_COMPARISON_INTERPRETATION":
        return {
            "id": "interpret_locked_pattern",
            "kind": "reasoning",
            "priority": "current",
            "control_id": None,
            "goal": (
                "Compare the missing-subset distribution with the overall baseline. "
                "Explain what is actually different, avoid causal claims, and ask "
                "the learner for one evidence-based interpretation. Do not open "
                "another comparison column."
            ),
            "comparison_column":
                investigation.get(
                    "comparison_column"
                ),
            "subset_output":
                investigation.get(
                    "subset_output"
                ),
            "baseline_output":
                investigation.get(
                    "baseline_output"
                ),
            "workflow_state": state,
            "enforce_direct_reply": False,
        }

    if state == "READY_FOR_DECISION":
        supervisor = mentor_context.get(
            "supervisor"
        )
        if not isinstance(supervisor, dict):
            supervisor = {}
        return {
            "id": "make_evidence_based_issue_decision",
            "kind": "reasoning",
            "priority": "current",
            "control_id": None,
            "goal": supervisor.get(
                "next_objective"
            ) or (
                "Choose the treatment from the evidence already collected; "
                "do not restart exploration."
            ),
            "workflow_state": state,
            "enforce_direct_reply": False,
        }

    return None


def plan_guided_next_action(
    *,
    learner_message: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    mentor_context: dict,
) -> dict | None:
    """
    Choose deterministic product actions and preserve the active investigation.
    The LLM explains/interprets; it does not get to silently switch the task.
    """

    state_action = _state_driven_action(
        learner_message=learner_message,
        loop=loop,
        finding=finding,
        mentor_context=mentor_context,
    )
    if (
        isinstance(
            mentor_context.get("workflow"),
            dict,
        )
    ):
        return state_action
    live_state = mentor_context.get("live_state")
    if not isinstance(live_state, dict):
        live_state = {}

    target_name = finding.column
    missing_filter_active = _active_missing_filter(
        live_state,
        target_name,
    )

    investigation = _start_investigation_if_needed(
        learner_message=learner_message,
        loop=loop,
        finding=finding,
        mentor_context=mentor_context,
        missing_filter_active=missing_filter_active,
    )

    diagnosis = mentor_context.get("execution_diagnosis")

    supervisor = mentor_context.get("supervisor")
    if not isinstance(supervisor, dict):
        supervisor = {}

    teaching_action = _code_teaching_action(
        learner_message=learner_message,
        investigation=investigation,
    )
    if teaching_action is not None:
        return teaching_action

    if loop.current_phase == "decide":
        return {
            "id": "make_evidence_based_issue_decision",
            "kind": "reasoning",
            "priority": "current",
            "control_id": None,
            "goal": supervisor.get(
                "next_objective"
            ) or (
                "Choose the treatment from the evidence already collected; "
                "do not restart exploration."
            ),
            "supervisor_status": supervisor.get(
                "status"
            ),
            "enforce_direct_reply": False,
        }

    if loop.current_phase in {
        "implement",
        "validate",
        "explain",
        "completed",
    }:
        return None

    # The context is built twice during one request. Do not process the same
    # notebook execution twice; return the already-selected next investigation step.
    if (
        isinstance(investigation, dict)
        and isinstance(diagnosis, dict)
        and diagnosis.get("observation_id")
        and investigation.get("last_processed_observation_id")
        == diagnosis.get("observation_id")
    ):
        if investigation.get("step") == "baseline_frequency":
            comparison = str(investigation["comparison_column"])
            code = _baseline_code(comparison)
            return {
                "id": "run_locked_baseline_frequency",
                "kind": "analysis",
                "priority": "current",
                "control_id": "notebook.run_cell",
                "goal": (
                    f"Calculate the overall raw-data {comparison} proportions "
                    "for a valid baseline comparison."
                ),
                "comparison_column": comparison,
                "code_template": code,
                "enforce_direct_reply": True,
                "messages": {
                    "tr": (
                        f"İlk oran yalnızca eksik satırlara aitti. Şimdi karşılaştırma için "
                        f"tüm raw veride {comparison} oranını çıkar. Bir Python hücresinde "
                        f"şunu çalıştır: {code}"
                    ),
                    "nl": f"Bereken nu de totale {comparison}-verdeling met: {code}",
                    "en": f"Now calculate the overall {comparison} distribution with: {code}",
                },
            }
        if investigation.get("step") == "interpret":
            return {
                "id": "interpret_locked_pattern",
                "kind": "reasoning",
                "priority": "current",
                "control_id": None,
                "goal": (
                    "Compare the missing-subset proportions with the overall baseline "
                    "before choosing any treatment. Do not switch comparison columns."
                ),
                "comparison_column": investigation.get("comparison_column"),
                "subset_output": investigation.get("subset_output"),
                "baseline_output": investigation.get("baseline_output"),
                "enforce_direct_reply": False,
            }

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
                    "nl": "Kies in Notebook bij Dataset voor Raw source sample.",
                    "en": "In Notebook, set Dataset to Raw source sample.",
                },
            }

        if issue_code == "investigation_target_mismatch":
            comparison = (
                investigation.get("comparison_column")
                if isinstance(investigation, dict)
                else None
            )
            return {
                "id": "repair_locked_investigation_target",
                "kind": "code_reasoning",
                "priority": "blocking",
                "control_id": None,
                "goal": (
                    f"Return to the locked comparison column {comparison}; "
                    "do not silently switch to another attribute."
                ),
                "comparison_column": comparison,
                "enforce_direct_reply": True,
                "messages": {
                    "tr": (
                        f"Burada hedefi değiştirmeyelim. Şu anki araştırmamız "
                        f"{target_name} eksikleri ile {comparison} arasındaki örüntü; "
                        f"başka kolona geçmeden {comparison} kontrolünü tamamla."
                    ),
                    "nl": f"Blijf bij de vastgelegde vergelijking met {comparison}.",
                    "en": f"Keep the locked comparison with {comparison}; do not switch columns yet.",
                },
            }

        if issue_code == "missing_scoped_frequency_check" and isinstance(investigation, dict):
            investigation["subset_output"] = diagnosis.get("output")
            investigation["step"] = "baseline_frequency"
            investigation["last_processed_observation_id"] = diagnosis.get("observation_id")
            comparison = str(investigation["comparison_column"])
            code = _baseline_code(comparison)
            return {
                "id": "run_locked_baseline_frequency",
                "kind": "analysis",
                "priority": "current",
                "control_id": "notebook.run_cell",
                "goal": (
                    f"Calculate overall {comparison} proportions before interpreting "
                    "whether the missing subset is concentrated."
                ),
                "comparison_column": comparison,
                "code_template": code,
                "enforce_direct_reply": True,
                "messages": {
                    "tr": (
                        f"İlk sonucu aldık; ama tek başına yeterli değil. "
                        f"Şimdi tüm raw veride {comparison} oranını karşılaştırma tabanı olarak çıkar. "
                        f"Bir Python hücresinde şunu çalıştır: {code}"
                    ),
                    "nl": f"Bereken nu de totale {comparison}-verdeling met: {code}",
                    "en": f"Now calculate the overall {comparison} distribution with: {code}",
                },
            }

        if issue_code == "baseline_frequency_check" and isinstance(investigation, dict):
            investigation["baseline_output"] = diagnosis.get("output")
            investigation["step"] = "interpret"
            investigation["last_processed_observation_id"] = diagnosis.get("observation_id")
            return {
                "id": "interpret_locked_pattern",
                "kind": "reasoning",
                "priority": "current",
                "control_id": None,
                "goal": (
                    "Compare subset and baseline proportions. Explain concentration "
                    "without claiming causality, then ask for the learner's interpretation."
                ),
                "comparison_column": investigation.get("comparison_column"),
                "subset_output": investigation.get("subset_output"),
                "baseline_output": investigation.get("baseline_output"),
                "enforce_direct_reply": False,
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
                "nl": f"Voeg geen nieuw filter toe. Laat {target_label} = Is missing actief.",
                "en": f"Do not add another filter. Keep {target_label} = Is missing active.",
            },
        }

    if isinstance(investigation, dict):
        return _navigation_or_subset_action(
            learner_message=learner_message,
            live_state=live_state,
            investigation=investigation,
        )

    if supervisor.get("stop_exploration") is True:
        return {
            "id": "stop_extra_issue_exploration",
            "kind": "reasoning",
            "priority": "current",
            "control_id": None,
            "goal": supervisor.get(
                "next_objective"
            ) or (
                "Interpret the evidence already collected instead of opening another check."
            ),
            "enforce_direct_reply": False,
        }

    if not _contains_any(learner_message, _FREQUENCY_MARKERS):
        return None

    # Backward-compatible frequency navigation when a caller has no profile
    # metadata to create a locked investigation.
    prepare_stage = live_state.get("active_prepare_stage")
    workbench_view = live_state.get("workbench_view")
    notebook = live_state.get("selected_notebook")

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

    if isinstance(notebook, dict) and notebook.get("dataset_kind") != "raw":
        return {
            "id": "select_raw_notebook_dataset",
            "kind": "navigation",
            "priority": "blocking",
            "control_id": "notebook.dataset",
            "value": "raw",
            "goal": "Use original source rows for missing-value investigation.",
            "enforce_direct_reply": True,
            "messages": {
                "tr": "Notebook’taki Dataset menüsünden Raw source sample seç.",
                "nl": "Kies in Notebook bij Dataset voor Raw source sample.",
                "en": "In Notebook, set Dataset to Raw source sample.",
            },
        }

    return None


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



def _normalized_series_items(
    output: str | None,
) -> list[tuple[str, float]]:
    if not isinstance(output, str):
        return []

    items: list[tuple[str, float]] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.casefold()
        if (
            lowered.startswith("name:")
            or lowered.startswith("dtype:")
            or "dtype:" in lowered
        ):
            continue

        match = re.match(
            r"^(.*?)\s+(-?\d+(?:\.\d+)?)$",
            line,
        )
        if match is None:
            continue

        label = match.group(1).strip()
        try:
            value = float(match.group(2))
        except ValueError:
            continue

        if not label or value < 0:
            continue

        items.append((label, value))

    return items[:8]


def _render_result_interpretation_locally(
    *,
    action: dict,
    language: str,
) -> str:
    target = str(
        action.get("target_column")
        or "target"
    )
    comparison = str(
        action.get("comparison_column")
        or "comparison"
    )
    items = _normalized_series_items(
        action.get("output")
    )

    if items:
        top = items[:4]
        if language == "tr":
            values = ", ".join(
                f"{label}: %{value * 100:.1f}"
                for label, value in top
            )
            return (
                f"Bu çıktı yalnızca {target} değeri eksik olan satırlardaki "
                f"{comparison} dağılımını gösteriyor: {values}. "
                f"Yani eksik grubun yapısını görüyoruz; ama bunun özel bir yoğunlaşma "
                f"olup olmadığını söylemek için tüm verideki {comparison} dağılımıyla "
                "karşılaştırmamız gerekir."
            )
        if language == "nl":
            values = ", ".join(
                f"{label}: {value * 100:.1f}%"
                for label, value in top
            )
            return (
                f"Deze output toont alleen de verdeling van {comparison} in rijen "
                f"waar {target} ontbreekt: {values}. Om te weten of dit echt een "
                "concentratie is, moeten we dit vergelijken met de totale verdeling."
            )

        values = ", ".join(
            f"{label}: {value * 100:.1f}%"
            for label, value in top
        )
        return (
            f"This output shows only the {comparison} distribution in rows where "
            f"{target} is missing: {values}. To know whether that is a real "
            "concentration, we still need the overall distribution for comparison."
        )

    if language == "tr":
        return (
            f"Bu çıktı yalnızca {target} eksik olan satırlardaki {comparison} "
            "dağılımını gösteriyor. Tek başına bir yoğunlaşma olduğunu kanıtlamaz; "
            "genel dağılımla karşılaştırmak gerekir."
        )
    if language == "nl":
        return (
            f"Deze output toont alleen de verdeling van {comparison} waar {target} "
            "ontbreekt. Voor een conclusie is vergelijking met de totale verdeling nodig."
        )
    return (
        f"This output shows only the {comparison} distribution where {target} "
        "is missing. It needs an overall baseline before drawing a conclusion."
    )


def render_planned_local_support_reply(
    *,
    action: dict | None,
    language: str,
) -> str | None:
    """
    Render support turns without external AI.

    This is intentionally limited to actions whose semantics are already known
    deterministically by the workflow engine. It does not assess learner
    reasoning or advance a learning phase.
    """
    if not isinstance(action, dict):
        return None

    direct = render_planned_direct_reply(
        action=action,
        language=language,
    )
    if direct is not None:
        return direct

    if (
        action.get("kind")
        == "teaching_interpretation"
    ):
        return _render_result_interpretation_locally(
            action=action,
            language=language,
        )

    messages = action.get("messages")
    if isinstance(messages, dict):
        value = (
            messages.get(language)
            or messages.get("en")
        )
        if value:
            return str(value).strip()

    return None
