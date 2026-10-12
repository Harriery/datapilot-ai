"""Bounded, evidence-first context for Mentor chat requests.

All limits are in characters, not provider tokens. This is a protective bound
rather than a guarantee that any individual provider will accept a request.
The full workspace and Notebook remain stored server-side.
"""
from __future__ import annotations

import json


MAX_WORKSPACE_CHARS = 6500
MAX_HISTORY_ITEM_CHARS = 700


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _clip(value, limit: int):
    """Bound arbitrary workspace data without claiming the omitted data was read."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "… [truncated]"
    if isinstance(value, dict):
        selected = list(value.items())[:16]
        return {
            str(key)[:100]: _clip(item, max(80, limit // max(1, len(selected))))
            for key, item in selected
        }
    if isinstance(value, (list, tuple)):
        return [_clip(item, max(80, limit // 6)) for item in value[:6]]
    return value


def _bounded(value, limit: int):
    if len(_json(value)) <= limit:
        return value
    if isinstance(value, str):
        return _clip(value, max(80, limit - 30))
    if isinstance(value, dict):
        return {"preview": _json(value)[: max(80, limit - 55)],
                "truncated": True}
    if isinstance(value, list):
        return {"preview": _json(value)[: max(80, limit - 55)],
                "truncated": True}
    return _clip(str(value), limit)


def _selected_notebook(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    latest = value.get("latest_cell")
    compact = {
        key: value.get(key)
        for key in ("notebook_id", "name", "dataset_kind", "processed_dataset_id", "cell_count")
        if value.get(key) is not None
    }
    if not isinstance(latest, dict):
        compact["latest_cell"] = None
        return compact
    execution = latest.get("last_execution")
    evidence = None
    if isinstance(execution, dict):
        evidence = {
            key: execution.get(key)
            for key in ("success", "expression_kind", "executed_at", "row_count")
            if execution.get(key) is not None
        }
        if execution.get("output") is not None:
            evidence["output"] = _clip(str(execution["output"]), 500)
        if isinstance(execution.get("columns"), list):
            evidence["columns"] = [str(col)[:70] for col in execution["columns"][:12]]
        if isinstance(execution.get("preview_rows"), list):
            evidence["preview_rows"] = _bounded(execution["preview_rows"][:2], 500)
    compact["latest_cell"] = {
        "cell_id": latest.get("cell_id"),
        "code": _clip(str(latest.get("code") or ""), 1100),
        "last_execution": evidence,
        "execution_evidence": "persisted Notebook observation; source/code version match not independently verified",
    }
    # Promote bounded evidence from earlier cells and saved human review notes.
    # These observations are not proof that the full dataset was verified.
    checks = value.get("quality_checks") or []
    if isinstance(checks, list):
        compact["quality_checks"] = [
            {
                "title": _clip(str(x.get("title") or ""), 90),
                "note": _clip(str(x.get("note") or ""), 420),
                "result_summary": _clip(str(x.get("result_summary") or ""), 240),
                "status": x.get("status"),
                "sample_row_count": x.get("sample_row_count"),
            }
            for x in checks[:3] if isinstance(x, dict)
        ]
    recent = value.get("recent_cells") or []
    if isinstance(recent, list):
        compact["recent_cells"] = [
            {
                "cell_id": x.get("cell_id"),
                "code": _clip(str(x.get("code") or ""), 320),
                "output": _clip(str((x.get("last_execution") or {}).get("output") or ""), 260),
                "preview_rows": _bounded(
                    ((x.get("last_execution") or {}).get("preview_rows") or [])[:1], 280
                ),
                "executed_at": (x.get("last_execution") or {}).get("executed_at"),
            }
            for x in recent[:5]
            if isinstance(x, dict) and isinstance(x.get("last_execution"), dict)
        ]
    return compact


def compact_mentor_workspace_context(source: dict | None) -> dict:
    """Keep dataset/stage/scope and latest executed cell ahead of optional artifacts."""
    if not isinstance(source, dict):
        return {}
    basic_limits = {
        "workspace_id": 120, "title": 130, "task_brief": 340,
        "desired_outcome": 220, "project_type": 100,
        "dataset_filename": 160, "development_sample_size": 40,
    }
    result = {
        key: _clip(source[key], limit)
        for key, limit in basic_limits.items()
        if source.get(key) is not None
    }
    for key, limit in (
        ("mentor_setup", 450),
        ("dataset_profile_summary", 900),
        ("sampling_context", 400),
        ("verified_action_evidence", 500),
        ("local_investigation", 450),
        ("current_step", 400),
        ("checkpoint", 300),
        ("mentor_execution_context", 700),
    ):
        if source.get(key) is not None:
            result[key] = _bounded(source[key], limit)

    ui = source.get("ui_context")
    if isinstance(ui, dict):
        result["ui_context"] = {
            key: _clip(ui[key], 90)
            for key in (
                "active_workspace_stage", "active_prepare_stage", "workbench_view",
                "selected_notebook_id", "selected_notebook_dataset_kind",
                "selected_workbench_column",
            )
            if ui.get(key) is not None
        }

    artifacts = source.get("artifacts")
    if isinstance(artifacts, dict):
        important = ("selected_notebook", "dataset_profile", "dataset_analysis")
        reduced = {}
        if "selected_notebook" in artifacts:
            reduced["selected_notebook"] = _selected_notebook(artifacts["selected_notebook"])
        for key in ("dataset_profile", "dataset_analysis"):
            if artifacts.get(key) is not None:
                reduced[key] = _bounded(artifacts[key], 650)
        # Stage summaries, not full model/operations/dashboard payloads.
        for key, value in artifacts.items():
            if key not in important and value is not None:
                reduced[key] = _bounded(value, 250)
        result["artifacts"] = reduced

    if len(_json(result)) > MAX_WORKSPACE_CHARS:
        # Preserve selected Notebook evidence while discarding secondary
        # stage summaries. Never produce an invalid partial JSON blob.
        if "artifacts" in result:
            result["artifacts"] = {
                key: value for key, value in result["artifacts"].items()
                if key in {"selected_notebook", "dataset_profile"}
            }
        result.pop("verified_action_evidence", None)
        result.pop("mentor_execution_context", None)
    if len(_json(result)) > MAX_WORKSPACE_CHARS:
        notebook = (result.get("artifacts") or {}).get("selected_notebook")
        if isinstance(notebook, dict):
            notebook["recent_cells"] = notebook.get("recent_cells", [])[:3]
            notebook["quality_checks"] = notebook.get("quality_checks", [])[:2]
    if len(_json(result)) > MAX_WORKSPACE_CHARS:
        for key in ("task_brief", "desired_outcome", "mentor_setup",
                    "dataset_profile_summary", "current_step", "checkpoint"):
            result.pop(key, None)
            if len(_json(result)) <= MAX_WORKSPACE_CHARS:
                break
    if len(_json(result)) > MAX_WORKSPACE_CHARS:
        notebook = (result.get("artifacts") or {}).get("selected_notebook")
        if isinstance(notebook, dict):
            notebook.pop("recent_cells", None)
            notebook.pop("quality_checks", None)
    return result


def compact_mentor_history(items: list[dict] | None, count: int = 4) -> list[dict]:
    return [
        {
            "role": str(item.get("role") or "user"),
            "content": str(item.get("content") or "")[-MAX_HISTORY_ITEM_CHARS:],
        }
        for item in (items or [])[-count:]
        if isinstance(item, dict)
    ]


def mentor_provider_overload_reply(workspace_context: dict | None) -> str:
    """Truthful no-LLM fallback for provider-side 413, with no invented data."""
    compact = compact_mentor_workspace_context(workspace_context)
    notebook = (compact.get("artifacts") or {}).get("selected_notebook")
    sentence = (
        "AI sağlayıcısı bu isteği boyut/token sınırı nedeniyle kabul etmedi. "
        "Bu yanıt yapay zekâ tarafından üretilmedi; kayıtlı çalışma bağlamından oluşturuldu."
    )
    if isinstance(notebook, dict) and isinstance(notebook.get("latest_cell"), dict):
        cell = notebook["latest_cell"]
        run = cell.get("last_execution")
        if isinstance(run, dict) and run.get("success") is True:
            output = run.get("output")
            code = cell.get("code") or ""
            detail = f" Son kaydedilmiş Notebook hücresi: {str(code)[-230:]}."
            if output is not None:
                detail += f" Kaydedilmiş çıktı: {str(output)[:180]}."
            return sentence + detail + (
                " Bu sonuç yalnızca Notebook kapsamındadır; tam kaynak veri doğrulanmadı. "
                "Kodun veya verinin sonradan değişip değişmediğini doğrulayamadım."
            )
    return sentence + (
        " Bu nedenle güncel Notebook sonucunu doğruladığımı söyleyemem. "
        "Yeni AI çağrıları yapmadan önce bağlam sınırının kontrol edilmesi gerekiyor."
    )
