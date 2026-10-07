from __future__ import annotations

"""
Structured DataPilot product knowledge for Mentor V2.

The LLM must not guess what the DataPilot UI can do. It receives only the
relevant slice of this registry plus live UI state.
"""

PRODUCT_REGISTRY: dict[str, dict] = {
    "source": {
        "label": "Source",
        "purpose": "Inspect immutable raw source data before transformations.",
        "dataset_role": "raw",
        "controls": [
            {
                "id": "raw_preview.search",
                "label": "Search preview",
                "type": "text_search",
                "effect": "Narrows visible preview rows only.",
                "mutates_data": False,
            },
            {
                "id": "raw_preview.filters",
                "label": "Filters",
                "type": "filter_builder",
                "operators": [
                    "is_missing", "is_not_missing", "is_blank",
                    "is_not_blank", "equals", "not_equals", "contains",
                    "not_contains", "starts_with", "ends_with",
                    "greater_than", "greater_than_or_equal", "less_than",
                    "less_than_or_equal", "between", "before", "after",
                    "date_between", "in", "not_in", "is_duplicate",
                    "is_unique",
                ],
                "effect": "Read-only row filtering in preview.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "Column headers are not clickable.",
            "No grouping or aggregation.",
            "No transformations.",
            "Filtering changes only the preview, never raw data.",
        ],
    },
    "prepare.profile": {
        "label": "Prepare / Profile",
        "purpose": "Review profile statistics and data-quality findings.",
        "dataset_role": "raw",
        "controls": [
            {
                "id": "finding.learn_with_mentor",
                "label": "Learn with Mentor",
                "type": "button",
                "effect": "Starts/resumes the guided learning loop for a finding.",
                "mutates_data": False,
            },
            {
                "id": "execution_plan.build",
                "label": "Build execution plan",
                "type": "button",
                "effect": "Creates a guided workflow from the current profile.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "This stage is for observation/reasoning, not permanent cleaning.",
        ],
    },
    "prepare.workbench": {
        "label": "Prepare / Workbench",
        "purpose": "Inspect, experiment, and build replayable transformations.",
        "dataset_role": "working_or_selected_notebook_dataset",
        "views": ["explorer", "notebook", "pipeline"],
        "controls": [
            {
                "id": "workbench.explorer",
                "label": "Explorer",
                "type": "view",
                "effect": "Shows working-dataset preview and column actions.",
                "mutates_data": False,
            },
            {
                "id": "workbench.notebook",
                "label": "Notebook",
                "type": "view",
                "effect": "Runs Python inspection/experimentation against selected dataset.",
                "mutates_data": False,
            },
            {
                "id": "workbench.pipeline",
                "label": "Pipeline",
                "type": "view",
                "effect": "Reviews replayable transformation operations.",
                "mutates_data": False,
            },
            {
                "id": "workbench.column",
                "label": "Working preview column",
                "type": "button",
                "effect": "Opens column inspector for the working dataset.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "Working data may already contain applied cleaning steps.",
            "Use a raw-backed notebook to investigate original missing rows.",
        ],
    },
    "prepare.workbench.notebook": {
        "label": "Prepare / Workbench / Notebook",
        "purpose": "Run inspection or experimental Python with visible outputs.",
        "controls": [
            {
                "id": "notebook.dataset",
                "label": "Dataset",
                "type": "select",
                "options": ["working", "raw", "processed:<dataset_id>"],
                "effect": "Changes which dataset is loaded into df for notebook execution.",
                "mutates_data": False,
            },
            {
                "id": "notebook.run_cell",
                "label": "Run cell",
                "type": "button",
                "effect": "Executes the selected Python cell and captures output/error.",
                "mutates_data": False,
            },
            {
                "id": "notebook.run_all",
                "label": "Run all",
                "type": "button",
                "effect": "Executes notebook cells sequentially.",
                "mutates_data": False,
            },
            {
                "id": "notebook.reset",
                "label": "Reset",
                "type": "button",
                "effect": "Clears current notebook execution results.",
                "mutates_data": False,
            },
            {
                "id": "notebook.add_cell",
                "label": "Add Python cell",
                "type": "button",
                "effect": "Adds a new Python cell.",
                "mutates_data": False,
            },
            {
                "id": "notebook.send_pipeline",
                "label": "Send to pipeline",
                "type": "button",
                "effect": "Promotes transformation-like code into a replayable pipeline draft.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "Notebook analysis does not mutate raw source.",
            "Inspection code should stay in the notebook.",
            "Only transformation code should be promoted to the pipeline.",
        ],
    },
    "prepare.workbench.pipeline": {
        "label": "Prepare / Workbench / Pipeline",
        "purpose": "Build and review deterministic replayable transformations.",
        "controls": [
            {
                "id": "pipeline.apply",
                "label": "Apply",
                "type": "button",
                "effect": "Applies the prepared transformation to working data.",
                "mutates_data": True,
            },
            {
                "id": "pipeline.operation",
                "label": "Operation",
                "type": "item",
                "effect": "Represents one replayable transformation step.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "Raw source remains immutable.",
            "A transformation should be justified before Apply.",
        ],
    },
    "prepare.validate": {
        "label": "Prepare / Validate",
        "purpose": "Validate transformed working data and replay safety.",
        "controls": [
            {
                "id": "validation.run",
                "label": "Run validation",
                "type": "button",
                "effect": "Checks integrity, schema, pipeline replay, duplicates and missing values.",
                "mutates_data": False,
            },
            {
                "id": "validation.save_processed",
                "label": "Save processed dataset",
                "type": "button",
                "effect": "Creates a named validated dataset snapshot.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "Validation confirms outcomes; it is not a substitute for reasoning.",
        ],
    },
    "prepare.understand": {
        "label": "Prepare / Understand",
        "purpose": "Review the validated data before modeling.",
        "controls": [
            {
                "id": "understand.preview",
                "label": "Processed dataset sample",
                "type": "preview",
                "effect": "Shows the validated working dataset used downstream.",
                "mutates_data": False,
            }
        ],
        "limits": [],
    },
    "data_model": {
        "label": "Data Model",
        "purpose": "Design fact/dimension tables, columns, derived fields and relationships.",
        "controls": [
            {"id": "model.table_add", "label": "Add table", "type": "button", "effect": "Adds a model table.", "mutates_data": False},
            {"id": "model.column_add", "label": "Add column", "type": "button", "effect": "Adds/maps a model column.", "mutates_data": False},
            {"id": "model.relationship", "label": "Relationship", "type": "editor", "effect": "Defines table relationships/cardinality.", "mutates_data": False},
            {"id": "model.derived", "label": "Derived column", "type": "editor", "effect": "Defines semantic/model derivations.", "mutates_data": False},
        ],
        "limits": [
            "Model decisions must preserve grain and valid keys.",
            "Do not invent dimensions only to normalize mechanically.",
        ],
    },
    "kpis": {
        "label": "KPIs",
        "purpose": "Define reusable business measures from the data model.",
        "controls": [
            {"id": "kpi.mode", "label": "Guided / Custom", "type": "select", "options": ["guided", "custom"], "effect": "Chooses KPI authoring mode.", "mutates_data": False},
            {"id": "kpi.fact_table", "label": "Fact table", "type": "select", "effect": "Selects KPI fact source.", "mutates_data": False},
            {"id": "kpi.measure", "label": "Measure", "type": "select", "effect": "Selects measure column.", "mutates_data": False},
            {"id": "kpi.aggregation", "label": "Aggregation", "type": "select", "options": ["count", "sum", "mean", "min", "max"], "effect": "Sets aggregation semantics.", "mutates_data": False},
            {"id": "kpi.custom_formula", "label": "Custom formula", "type": "input", "effect": "Defines a supported KPI formula.", "mutates_data": False},
            {"id": "kpi.save", "label": "Save", "type": "button", "effect": "Persists selected KPI definitions.", "mutates_data": False},
        ],
        "limits": [
            "Aggregation must match the metric's semantics.",
            "Non-additive measures should not be summed blindly.",
        ],
    },
    "bi_dataset": {
        "label": "BI Model",
        "purpose": "Review semantic-model readiness before analysis.",
        "controls": [
            {"id": "bi.confirm", "label": "Confirm semantic model", "type": "button", "effect": "Completes semantic-model review and unlocks Analysis.", "mutates_data": False},
        ],
        "limits": [
            "Required semantic checks must pass before confirmation.",
        ],
    },
    "analysis": {
        "label": "Analysis",
        "purpose": "Create and save analyses from model/KPI definitions.",
        "controls": [
            {"id": "analysis.add", "label": "Add", "type": "button", "effect": "Adds a suggested analysis to the definition.", "mutates_data": False},
            {"id": "analysis.sort", "label": "Sort", "type": "select", "options": ["top_value", "bottom_value", "alphabetical", "chronological", "highest_count", "lowest_count"], "effect": "Controls grouped-result ordering.", "mutates_data": False},
            {"id": "analysis.top_n", "label": "Top N", "type": "input", "effect": "Limits grouped result count.", "mutates_data": False},
        ],
        "limits": [
            "Analysis must use saved semantic definitions, not raw-column guesses.",
        ],
    },
    "dashboard": {
        "label": "Dashboard",
        "purpose": "Build interactive visual layouts from saved analyses/KPIs.",
        "controls": [
            {"id": "dashboard.visual_type", "label": "Visual type", "type": "select", "options": ["kpi", "bar", "column", "line", "area", "pie", "donut", "table"], "effect": "Changes visual representation.", "mutates_data": False},
            {"id": "dashboard.measure", "label": "Measure", "type": "select", "effect": "Binds visual measure.", "mutates_data": False},
            {"id": "dashboard.dimension", "label": "Dimension", "type": "select", "effect": "Binds visual dimension.", "mutates_data": False},
            {"id": "dashboard.filters", "label": "Slicers / filters", "type": "editor", "effect": "Adds interactive dashboard filtering.", "mutates_data": False},
            {"id": "dashboard.grid", "label": "Grid", "type": "toggle", "effect": "Shows/hides alignment grid.", "mutates_data": False},
            {"id": "dashboard.snap", "label": "Snap to grid", "type": "toggle", "effect": "Snaps visual positions to grid.", "mutates_data": False},
            {"id": "dashboard.properties", "label": "Visual properties", "type": "panel", "effect": "Edits visual title, labels, fonts, colors and layout.", "mutates_data": False},
        ],
        "limits": [
            "Visual choice should match measure/dimension semantics.",
            "Pie/donut should not imply additivity for non-additive KPIs.",
        ],
    },
    "insights": {
        "label": "Insights",
        "purpose": "Review interpreted results and noteworthy findings.",
        "controls": [],
        "limits": ["Insights should be traceable to saved analyses/KPIs."],
    },
    "docs": {
        "label": "Docs",
        "purpose": "Document project decisions, outputs and handoff context.",
        "controls": [],
        "limits": ["Documentation should reflect validated project state."],
    },
}


def resolve_product_context(ui_context: dict | None) -> dict:
    ui_context = ui_context or {}
    stage = ui_context.get("active_workspace_stage")
    prepare_stage = ui_context.get("active_prepare_stage")
    workbench_view = ui_context.get("workbench_view")

    path = str(stage or "source")

    if stage == "prepare" and isinstance(prepare_stage, str):
        path = f"prepare.{prepare_stage}"

        if (
            prepare_stage == "workbench"
            and workbench_view in {"notebook", "pipeline"}
        ):
            detailed = f"{path}.{workbench_view}"
            if detailed in PRODUCT_REGISTRY:
                path = detailed

    entry = PRODUCT_REGISTRY.get(
        path,
        PRODUCT_REGISTRY.get(str(stage), {}),
    )

    return {
        "path": path,
        "label": entry.get("label"),
        "purpose": entry.get("purpose"),
        "dataset_role": entry.get("dataset_role"),
        "views": entry.get("views", []),
        "controls": entry.get("controls", []),
        "limits": entry.get("limits", []),
    }
