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


# Detailed controls/options are stored centrally and retrieved selectively.
PRODUCT_REGISTRY["prepare.workbench"]["controls"].extend([
    {
        "id": "artifact.new_notebook",
        "label": "New notebook",
        "type": "button",
        "effect": "Creates a Python notebook artifact.",
        "mutates_data": False,
    },
    {
        "id": "artifact.lineage",
        "label": "Lineage",
        "type": "view",
        "effect": "Shows data-flow lineage.",
        "mutates_data": False,
    },
    {
        "id": "workbench.add_transformation",
        "label": "Add transformation",
        "type": "modal",
        "fields": [
            "title",
            "goal",
            "operation_type",
            "source_columns",
            "expected_columns",
        ],
        "operation_type_options": [
            "clean",
            "transform",
            "schema",
            "business_rule",
            "enrichment",
            "custom",
        ],
        "effect": "Defines a candidate Workbench operation.",
        "mutates_data": False,
    },
])

PRODUCT_REGISTRY["prepare.workbench.pipeline"]["controls"].extend([
    {
        "id": "pipeline.action_type",
        "label": "Pipeline action",
        "type": "select",
        "options": [
            "rename",
            "remove",
            "change_type",
            "fill_missing",
            "replace_values",
            "derived",
        ],
        "effect": "Chooses the deterministic transformation action.",
        "mutates_data": False,
    },
    {
        "id": "pipeline.change_type",
        "label": "Target data type",
        "type": "select",
        "options": ["string", "integer", "float", "datetime"],
        "effect": "Sets the target type for change_type.",
        "mutates_data": False,
    },
    {
        "id": "pipeline.fill_strategy",
        "label": "Fill strategy",
        "type": "select",
        "options": ["value", "mean", "median", "mode", "zero", "mapping"],
        "effect": "Sets missing-value treatment after the treatment is justified.",
        "mutates_data": False,
    },
    {
        "id": "pipeline.derived_operation",
        "label": "Derived operation",
        "type": "select",
        "options": ["copy", "uppercase", "lowercase", "add", "multiply"],
        "effect": "Defines a supported derived-column operation.",
        "mutates_data": False,
    },
])

PRODUCT_REGISTRY["data_model"]["controls"].extend([
    {
        "id": "model.table_type",
        "label": "Table type",
        "type": "select",
        "options": ["fact", "dimension", "bridge"],
        "effect": "Sets the semantic role of a model table.",
        "mutates_data": False,
    },
    {
        "id": "model.column_role",
        "label": "Column role",
        "type": "select",
        "options": [
            "key",
            "foreign_key",
            "dimension",
            "measure",
            "attribute",
            "time",
        ],
        "effect": "Sets a model column's semantic role.",
        "mutates_data": False,
    },
    {
        "id": "model.aggregation",
        "label": "Aggregation",
        "type": "select",
        "options": ["count", "sum", "mean", "min", "max", "none"],
        "effect": "Sets default aggregation where semantically valid.",
        "mutates_data": False,
    },
    {
        "id": "model.relationship_cardinality",
        "label": "Cardinality",
        "type": "select",
        "options": ["many_to_one", "one_to_many", "one_to_one"],
        "effect": "Defines relationship cardinality.",
        "mutates_data": False,
    },
    {
        "id": "model.relationship_active",
        "label": "Active relationship",
        "type": "toggle",
        "effect": "Enables/disables the relationship.",
        "mutates_data": False,
    },
    {
        "id": "model.derivation_type",
        "label": "Derived column type",
        "type": "select",
        "options": [
            "date_part",
            "numeric",
            "text",
            "multi_column",
            "mapping",
            "bucketing",
        ],
        "effect": "Chooses a supported semantic/model derivation family.",
        "mutates_data": False,
    },
])

PRODUCT_REGISTRY["kpis"]["controls"].extend([
    {
        "id": "kpi.dimension_table",
        "label": "Dimension table",
        "type": "select",
        "effect": "Selects a related dimension table.",
        "mutates_data": False,
    },
    {
        "id": "kpi.dimension_column",
        "label": "Dimension column",
        "type": "select",
        "effect": "Selects the grouping dimension.",
        "mutates_data": False,
    },
    {
        "id": "kpi.filter_value",
        "label": "Optional filter value",
        "type": "input",
        "effect": "Adds an optional KPI filter value.",
        "mutates_data": False,
    },
    {
        "id": "kpi.title",
        "label": "KPI title",
        "type": "input",
        "effect": "Sets the KPI display title.",
        "mutates_data": False,
    },
    {
        "id": "kpi.custom_formula_functions",
        "label": "Supported custom functions",
        "type": "reference",
        "options": [
            "SUM",
            "MEAN",
            "COUNT",
            "COUNT_ROWS",
            "MIN",
            "MAX",
            "SAFE_DIVIDE",
        ],
        "effect": "Constrains declarative custom KPI formulas.",
        "mutates_data": False,
    },
    {
        "id": "kpi.add_definition",
        "label": "Add KPI definition",
        "type": "button",
        "effect": "Adds the current definition to the KPI library.",
        "mutates_data": False,
    },
])

PRODUCT_REGISTRY["dashboard"]["controls"].extend([
    {
        "id": "dashboard.theme",
        "label": "Theme",
        "type": "select",
        "options": ["ocean", "teal", "violet", "sunset", "slate"],
        "effect": "Changes dashboard-level visual theme.",
        "mutates_data": False,
    },
    {
        "id": "dashboard.sort",
        "label": "Sort",
        "type": "select",
        "options": [
            "top_value",
            "bottom_value",
            "alphabetical",
            "chronological",
            "highest_count",
            "lowest_count",
        ],
        "effect": "Changes visual category ordering.",
        "mutates_data": False,
    },
    {
        "id": "dashboard.top_n",
        "label": "Top N",
        "type": "input",
        "effect": "Limits grouped visual results.",
        "mutates_data": False,
    },
    {
        "id": "dashboard.visual_size",
        "label": "Visual size",
        "type": "select",
        "options": ["compact", "small", "medium", "large"],
        "effect": "Sets a visual's preset size.",
        "mutates_data": False,
    },
    {
        "id": "dashboard.display_toggles",
        "label": "Display options",
        "type": "toggles",
        "options": ["show_values", "show_legend", "show_gridlines", "animate"],
        "effect": "Controls visual display elements.",
        "mutates_data": False,
    },
    {
        "id": "dashboard.canvas_layout",
        "label": "Canvas position / size",
        "type": "editor",
        "fields": ["canvas_x", "canvas_y", "canvas_width", "canvas_height"],
        "effect": "Positions and resizes a visual on the dashboard canvas.",
        "mutates_data": False,
    },
    {
        "id": "dashboard.label_style",
        "label": "Independent label/font style",
        "type": "editor",
        "fields": [
            "title_font_size",
            "title_bold",
            "title_color",
            "subtitle_font_size",
            "subtitle_bold",
            "subtitle_color",
            "category_label_font_size",
            "category_label_bold",
            "category_label_color",
            "value_label_font_size",
            "value_label_bold",
            "value_label_color",
            "axis_label_font_size",
            "axis_label_bold",
            "axis_label_color",
            "legend_label_font_size",
            "legend_label_bold",
            "legend_label_color",
        ],
        "effect": "Styles independent dashboard text elements.",
        "mutates_data": False,
    },
    {
        "id": "dashboard.kpi_layout",
        "label": "KPI card layout",
        "type": "editor",
        "fields": [
            "kpi_label",
            "kpi_label_font_size",
            "kpi_label_bold",
            "kpi_label_color",
            "kpi_show_secondary",
            "kpi_value_alignment",
            "kpi_vertical_alignment",
            "kpi_stat",
        ],
        "effect": "Controls KPI card label/value presentation.",
        "mutates_data": False,
    },
])

PRODUCT_REGISTRY["insights"]["controls"].extend([
    {
        "id": "insights.confirm",
        "label": "Confirm insights",
        "type": "button",
        "effect": "Confirms evidence-backed insight findings.",
        "mutates_data": False,
    },
    {
        "id": "insights.show_all",
        "label": "Show all / Show fewer",
        "type": "button",
        "effect": "Expands or collapses the insight list.",
        "mutates_data": False,
    },
])

PRODUCT_REGISTRY["docs"]["controls"].extend([
    {
        "id": "docs.copy_markdown",
        "label": "Copy Markdown",
        "type": "button",
        "effect": "Copies generated project documentation as Markdown.",
        "mutates_data": False,
    },
    {
        "id": "docs.download_markdown",
        "label": "Download .md",
        "type": "button",
        "effect": "Downloads the generated project handoff Markdown.",
        "mutates_data": False,
    },
    {
        "id": "docs.complete_project",
        "label": "Complete project",
        "type": "button",
        "effect": "Marks the documented project as complete when available.",
        "mutates_data": False,
    },
])

WORKSPACE_STAGE_ORDER = [
    "source",
    "prepare",
    "data_model",
    "kpis",
    "bi_dataset",
    "analysis",
    "dashboard",
    "insights",
    "docs",
]

PREPARE_STAGE_ORDER = ["profile", "workbench", "validate", "understand"]

_STAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "source": ("source", "raw source", "ham kaynak", "kaynak", "bron"),
    "prepare.profile": ("profile", "profil", "data quality", "veri kalitesi"),
    "prepare.workbench": ("workbench", "explorer"),
    "prepare.workbench.notebook": (
        "notebook", "python cell", "python hücre", "python hucre",
    ),
    "prepare.workbench.pipeline": (
        "pipeline", "transformation", "dönüşüm", "donusum",
    ),
    "prepare.validate": ("validate", "validation", "doğrulama", "dogrulama"),
    "prepare.understand": ("understand", "model discovery", "veriyi anla"),
    "data_model": (
        "data model", "model studio", "fact", "dimension",
        "relationship", "veri modeli", "ilişki", "iliski",
    ),
    "kpis": ("kpi", "measure", "aggregation", "ölçü", "olcu"),
    "bi_dataset": ("bi model", "semantic model", "semantik model"),
    "analysis": ("analysis", "analiz", "saved analyses"),
    "dashboard": ("dashboard", "visual", "grafik", "slicer", "canvas"),
    "insights": ("insight", "insights", "bulgu", "bulgular"),
    "docs": (
        "docs", "documentation", "dokümantasyon", "dokumantasyon",
        "markdown", "handoff",
    ),
}


def _entry_for_path(path: str) -> dict:
    entry = PRODUCT_REGISTRY.get(path, {})

    return {
        "path": path,
        "label": entry.get("label"),
        "purpose": entry.get("purpose"),
        "dataset_role": entry.get("dataset_role"),
        "views": entry.get("views", []),
        "controls": entry.get("controls", []),
        "limits": entry.get("limits", []),
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



def retrieve_product_context(
    *,
    ui_context: dict | None,
    message: str,
    max_referenced: int = 2,
) -> dict:
    """
    Return the current product slice plus only stages explicitly relevant to
    the user's message. This bounds prompt size as the guide grows.
    """
    current = resolve_product_context(
        ui_context
    )
    normalized = message.casefold()
    referenced = []
    current_path = current.get("path")

    for path, aliases in _STAGE_ALIASES.items():
        if path == current_path:
            continue

        if any(
            alias.casefold() in normalized
            for alias in aliases
        ):
            referenced.append(
                _entry_for_path(path)
            )

        if len(referenced) >= max_referenced:
            break

    return {
        "current": current,
        "referenced": referenced,
        "workspace_stage_order": WORKSPACE_STAGE_ORDER,
        "prepare_stage_order": PREPARE_STAGE_ORDER,
    }



# Learning-support areas outside the workspace stage rail.
PRODUCT_REGISTRY.update({
    "practice": {
        "label": "Practice V2",
        "purpose": "Close diagnosed skill gaps through evidence-based practice.",
        "controls": [
            {
                "id": "practice.recommended",
                "label": "Recommended practice",
                "type": "button",
                "effect": "Starts practice based on current learner priority.",
                "mutates_data": False,
            },
            {
                "id": "practice.topic",
                "label": "Topic",
                "type": "selection",
                "effect": "Chooses the skill family to practice.",
                "mutates_data": False,
            },
            {
                "id": "practice.focus_area",
                "label": "Focus area",
                "type": "select",
                "effect": "Chooses a subtopic/focus area.",
                "mutates_data": False,
            },
            {
                "id": "practice.mode",
                "label": "Practice mode",
                "type": "select",
                "effect": "Chooses an available mode such as code or theory.",
                "mutates_data": False,
            },
            {
                "id": "practice.difficulty",
                "label": "Difficulty",
                "type": "select",
                "options": ["easy", "medium", "hard"],
                "effect": "Sets practice difficulty.",
                "mutates_data": False,
            },
            {
                "id": "practice.start",
                "label": "Start practice",
                "type": "button",
                "effect": "Loads the selected practice exercise/check.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "Practice should target diagnosed gaps, not random question quotas.",
            "Mastery is evidence-based.",
        ],
    },
    "progress": {
        "label": "Progress",
        "purpose": "Show skill performance, independence, misconceptions and readiness.",
        "controls": [
            {
                "id": "progress.skill_performance",
                "label": "Skill Performance",
                "type": "panel",
                "effect": "Shows attempts/success by skill.",
                "mutates_data": False,
            },
            {
                "id": "progress.independence",
                "label": "Mentor Support & Independence",
                "type": "panel",
                "effect": "Shows assistance/dependency trend.",
                "mutates_data": False,
            },
            {
                "id": "progress.skill_details",
                "label": "Skill Details",
                "type": "panel",
                "effect": "Shows phase counts, priority and misconception details.",
                "mutates_data": False,
            },
        ],
        "limits": [
            "Observed Mentor V2 signals do not inflate assessed attempt counts.",
        ],
    },
    "tasks": {
        "label": "Tasks",
        "purpose": "Review workspace task status and open the relevant workspace.",
        "controls": [
            {
                "id": "tasks.refresh",
                "label": "Refresh",
                "type": "button",
                "effect": "Reloads task status.",
                "mutates_data": False,
            },
            {
                "id": "tasks.open_workspace",
                "label": "Open workspace",
                "type": "button",
                "effect": "Opens the workspace for that task.",
                "mutates_data": False,
            },
        ],
        "limits": [],
    },
})

_STAGE_ALIASES.update({
    "practice": (
        "practice", "pratik", "exercise", "egzersiz",
    ),
    "progress": (
        "progress", "ilerleme", "independence", "bağımsızlık", "bagimsizlik",
    ),
    "tasks": (
        "tasks", "görevler", "gorevler", "task list",
    ),
})
