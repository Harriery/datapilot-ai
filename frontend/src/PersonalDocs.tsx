import {
  useMemo,
  useState,
} from "react";

import {
  CheckCircle2,
  Clipboard,
  Download,
  FileText,
  Network,
  Sigma,
  SlidersHorizontal,
} from "lucide-react";

import type {
  AnalysisResultData,
} from "./PersonalAnalysisPlan";

import type {
  DataModelStudioData,
} from "./DataModelCanvas";

import type {
  PersonalKpiData,
} from "./PersonalKpiCandidates";

import type {
  DashboardFilterData,
  DashboardTheme,
  DashboardVisualData,
} from "./PersonalDashboardBuilder";

type ValidationData = {
  passed: boolean;
  source_row_count: number;
  working_row_count: number;
  checks: {
    name: string;
    status:
      | "passed"
      | "failed"
      | "warning";
    message: string;
  }[];
};

type WorkbenchOperationData = {
  operation_id: string;
  title: string;
  goal: string;
  operation_type: string;
  origin:
    | "data_quality"
    | "project_requirement"
    | "user";
  status:
    | "pending"
    | "active"
    | "completed";
};

type Props = {
  projectTitle: string;
  datasetFilename?: string | null;
  taskBrief?: string | null;
  desiredOutcome?: string | null;
  validationResult?: ValidationData | null;
  workbenchOperations?: WorkbenchOperationData[];
  dataModelStudio?: DataModelStudioData | null;
  kpiDefinitions?: PersonalKpiData[];
  analyses?: AnalysisResultData[];
  dashboardConfig?: {
    title: string;
    subtitle: string | null;
    theme: DashboardTheme;
    visuals: DashboardVisualData[];
    filters: DashboardFilterData[];
  } | null;
  onComplete?: () => Promise<void>;
};

function analysisKey(
  analysis: AnalysisResultData,
) {
  return [
    analysis.kpi_code ??
      analysis.measure,
    analysis.aggregation ??
      "unknown",
    analysis.dimension_table ??
      "no-table",
    analysis.dimension ??
      "overall",
  ].join("::");
}

function dedupeAnalyses(
  analyses: AnalysisResultData[],
) {
  const unique =
    new Map<
      string,
      AnalysisResultData
    >();

  for (
    const analysis
    of analyses
  ) {
    unique.set(
      analysisKey(
        analysis,
      ),
      analysis,
    );
  }

  return [
    ...unique.values(),
  ];
}

function kpiTitle(
  analysis: AnalysisResultData,
  kpis: PersonalKpiData[],
) {
  const definition =
    analysis.kpi_code
      ? kpis.find(
          (item) =>
            item.code ===
            analysis.kpi_code,
        )
      : undefined;

  return (
    definition?.title ??
    analysis.measure
  );
}

function formulaLabel(
  kpi: PersonalKpiData,
) {
  if (
    kpi.formula?.trim()
  ) {
    return kpi.formula;
  }

  if (
    kpi.formula_mode ===
    "row_count"
  ) {
    return `COUNT_ROWS(${kpi.fact_table ?? "fact"})`;
  }

  if (
    kpi.measure &&
    kpi.aggregation
  ) {
    return (
      `${kpi.aggregation.toUpperCase()}(` +
      `${kpi.fact_table ?? "fact"}.${kpi.measure})`
    );
  }

  return "Semantic definition";
}

function buildMarkdown(
  props: Props,
) {
  const {
    projectTitle,
    datasetFilename,
    taskBrief,
    desiredOutcome,
    validationResult,
    workbenchOperations = [],
    dataModelStudio,
    kpiDefinitions = [],
    analyses = [],
    dashboardConfig,
  } = props;

  const uniqueAnalyses =
    dedupeAnalyses(
      analyses,
    );

  const lines: string[] = [
    `# ${projectTitle}`,
    "",
    "## Project Overview",
    "",
    `- Dataset: ${datasetFilename ?? "Not specified"}`,
    `- Goal: ${taskBrief ?? "Not specified"}`,
    `- Expected outcome: ${desiredOutcome ?? "Not specified"}`,
    "",
    "## Data Preparation",
    "",
  ];

  const completedOperations =
    workbenchOperations.filter(
      (item) =>
        item.status ===
        "completed",
    );

  if (
    completedOperations.length
  ) {
    for (
      const operation
      of completedOperations
    ) {
      lines.push(
        `- ${operation.title}: ${operation.goal}`,
      );
    }
  } else {
    lines.push(
      "- No completed preparation operations were recorded.",
    );
  }

  lines.push(
    "",
    "## Validation",
    "",
  );

  if (
    validationResult
  ) {
    lines.push(
      `- Overall status: ${validationResult.passed ? "Passed" : "Not passed"}`,
      `- Source rows: ${validationResult.source_row_count}`,
      `- Working rows: ${validationResult.working_row_count}`,
    );

    for (
      const check
      of validationResult.checks
    ) {
      lines.push(
        `- ${check.name}: ${check.status} — ${check.message}`,
      );
    }
  } else {
    lines.push(
      "- No validation result was recorded.",
    );
  }

  lines.push(
    "",
    "## Data Model",
    "",
  );

  if (
    dataModelStudio
  ) {
    for (
      const table
      of dataModelStudio.tables
    ) {
      lines.push(
        `### ${table.name} (${table.table_type})`,
        "",
      );

      for (
        const column
        of table.columns
      ) {
        lines.push(
          `- ${column.name}: ${column.role}${column.aggregation ? ` / ${column.aggregation}` : ""}`,
        );
      }

      lines.push("");
    }

    lines.push(
      "### Relationships",
      "",
    );

    for (
      const relationship
      of dataModelStudio.relationships
    ) {
      lines.push(
        `- ${relationship.from_table}.${relationship.from_column} → ` +
        `${relationship.to_table}.${relationship.to_column} (${relationship.cardinality})`,
      );
    }
  } else {
    lines.push(
      "- No semantic model was recorded.",
    );
  }

  lines.push(
    "",
    "## KPI Definitions",
    "",
  );

  for (
    const kpi
    of kpiDefinitions
  ) {
    lines.push(
      `- **${kpi.title}** — ${formulaLabel(kpi)}`,
    );
  }

  lines.push(
    "",
    "## Semantic Analyses",
    "",
  );

  for (
    const analysis
    of uniqueAnalyses
  ) {
    const title =
      kpiTitle(
        analysis,
        kpiDefinitions,
      );

    lines.push(
      `- ${title}${analysis.dimension ? ` by ${analysis.dimension}` : " (overall)"}`,
    );
  }

  lines.push(
    "",
    "## Dashboard",
    "",
  );

  if (
    dashboardConfig
  ) {
    lines.push(
      `- Title: ${dashboardConfig.title}`,
      `- Theme: ${dashboardConfig.theme}`,
      `- Visuals: ${dashboardConfig.visuals.length}`,
      `- Filters: ${dashboardConfig.filters.length}`,
    );

    for (
      const visual
      of dashboardConfig.visuals
    ) {
      lines.push(
        `- Visual: ${visual.visual_type}${visual.dimension ? ` by ${visual.dimension}` : ""}`,
      );
    }

    for (
      const filter
      of dashboardConfig.filters
    ) {
      lines.push(
        `- Filter: ${filter.label || filter.column}`,
      );
    }
  } else {
    lines.push(
      "- No dashboard configuration was recorded.",
    );
  }

  lines.push(
    "",
    "## Technical Notes",
    "",
    "- The semantic layer separates measures from dimensions.",
    "- Dashboard visuals are bound to saved semantic KPIs or analyses.",
    "- Insight generation is deterministic and does not invent missing values.",
    "- Time behavior is driven by semantic derivation metadata rather than dataset-specific column names.",
    "- The workflow is dataset-agnostic: project logic is derived from schema, roles, relationships and saved workspace metadata.",
    "",
  );

  return lines.join("\n");
}

function Stat({
  label,
  value,
}: {
  label: string;
  value:
    | string
    | number;
}) {
  return (
    <div className="personal-docs-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function PersonalDocs(
  props: Props,
) {
  const {
    projectTitle,
    datasetFilename,
    taskBrief,
    desiredOutcome,
    validationResult,
    workbenchOperations = [],
    dataModelStudio,
    kpiDefinitions = [],
    analyses = [],
    dashboardConfig,
    onComplete,
  } = props;

  const [
    copied,
    setCopied,
  ] = useState(false);

  const [
    completing,
    setCompleting,
  ] = useState(false);

  const [
    completeError,
    setCompleteError,
  ] = useState<
    string | null
  >(null);

  const uniqueAnalyses =
    useMemo(
      () =>
        dedupeAnalyses(
          analyses,
        ),
      [analyses],
    );

  const completedOperations =
    useMemo(
      () =>
        workbenchOperations.filter(
          (item) =>
            item.status ===
            "completed",
        ),
      [workbenchOperations],
    );

  const markdown =
    useMemo(
      () =>
        buildMarkdown(
          props,
        ),
      [
        projectTitle,
        datasetFilename,
        taskBrief,
        desiredOutcome,
        validationResult,
        workbenchOperations,
        dataModelStudio,
        kpiDefinitions,
        analyses,
        dashboardConfig,
      ],
    );

  function downloadMarkdown() {
    const blob =
      new Blob(
        [markdown],
        {
          type:
            "text/markdown;charset=utf-8",
        },
      );

    const url =
      URL.createObjectURL(
        blob,
      );

    const anchor =
      document.createElement(
        "a",
      );

    anchor.href = url;
    anchor.download =
      `${projectTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "project"}-documentation.md`;

    document.body.appendChild(
      anchor,
    );

    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(
      url,
    );
  }

  async function copyMarkdown() {
    await navigator.clipboard.writeText(
      markdown,
    );

    setCopied(true);

    window.setTimeout(
      () =>
        setCopied(false),
      1800,
    );
  }

  const factCount =
    dataModelStudio?.tables.filter(
      (table) =>
        table.table_type ===
        "fact",
    ).length ?? 0;

  const dimensionCount =
    dataModelStudio?.tables.filter(
      (table) =>
        table.table_type ===
        "dimension",
    ).length ?? 0;

  return (
    <section className="personal-docs">
      <header className="personal-docs-header">
        <div>
          <span className="personal-docs-eyebrow">
            PROJECT DOCUMENTATION
          </span>

          <h2>
            Final project handoff
          </h2>

          <p>
            A workspace-derived summary of the prepared data, semantic
            model, KPIs, analyses and dashboard configuration.
          </p>
        </div>

        <div className="personal-docs-actions">
          <button
            type="button"
            className="personal-docs-secondary"
            onClick={
              copyMarkdown
            }
          >
            <Clipboard
              size={15}
            />
            {copied
              ? "Copied"
              : "Copy Markdown"}
          </button>

          <button
            type="button"
            className="personal-docs-secondary"
            onClick={
              downloadMarkdown
            }
          >
            <Download
              size={15}
            />
            Download .md
          </button>

          {onComplete && (
            <button
              type="button"
              className="personal-docs-primary"
              disabled={
                completing
              }
              onClick={async () => {
                setCompleting(
                  true,
                );

                setCompleteError(
                  null,
                );

                try {
                  await onComplete();
                } catch (error) {
                  setCompleteError(
                    error instanceof Error
                      ? error.message
                      : "Documentation could not be completed.",
                  );
                } finally {
                  setCompleting(
                    false,
                  );
                }
              }}
            >
              <CheckCircle2
                size={15}
              />
              {completing
                ? "Completing..."
                : "Complete project"}
            </button>
          )}
        </div>
      </header>

      {completeError && (
        <div
          className="personal-docs-error"
          role="alert"
        >
          {completeError}
        </div>
      )}

      <section className="personal-docs-summary">
        <div className="personal-docs-project-copy">
          <span>
            PROJECT
          </span>

          <h3>
            {projectTitle}
          </h3>

          <p>
            {taskBrief ??
              "No project goal was provided."}
          </p>

          {desiredOutcome && (
            <small>
              Expected outcome:{" "}
              {desiredOutcome}
            </small>
          )}
        </div>

        <div className="personal-docs-stats">
          <Stat
            label="Dataset"
            value={
              datasetFilename ??
              "—"
            }
          />

          <Stat
            label="Model"
            value={
              `${factCount} fact · ${dimensionCount} dimensions`
            }
          />

          <Stat
            label="KPIs"
            value={
              kpiDefinitions.length
            }
          />

          <Stat
            label="Analyses"
            value={
              uniqueAnalyses.length
            }
          />

          <Stat
            label="Visuals"
            value={
              dashboardConfig?.visuals.length ??
              0
            }
          />

          <Stat
            label="Validation"
            value={
              validationResult?.passed
                ? "Passed"
                : "Not confirmed"
            }
          />
        </div>
      </section>

      <div className="personal-docs-grid">
        <article className="personal-docs-card">
          <div className="personal-docs-card-title">
            <FileText
              size={18}
            />

            <div>
              <strong>
                Data preparation
              </strong>

              <small>
                Completed workspace operations
              </small>
            </div>
          </div>

          <div className="personal-docs-list">
            {completedOperations.length ? (
              completedOperations.map(
                (operation) => (
                  <div
                    key={
                      operation.operation_id
                    }
                    className="personal-docs-list-row"
                  >
                    <strong>
                      {operation.title}
                    </strong>

                    <span>
                      {operation.goal}
                    </span>
                  </div>
                ),
              )
            ) : (
              <p className="personal-docs-muted">
                No completed preparation operations were recorded.
              </p>
            )}
          </div>
        </article>

        <article className="personal-docs-card">
          <div className="personal-docs-card-title">
            <Network
              size={18}
            />

            <div>
              <strong>
                Semantic model
              </strong>

              <small>
                Tables and relationships
              </small>
            </div>
          </div>

          <div className="personal-docs-chip-list">
            {dataModelStudio?.tables.map(
              (table) => (
                <span
                  key={
                    table.name
                  }
                >
                  {table.name}
                  <small>
                    {table.table_type}
                  </small>
                </span>
              ),
            )}
          </div>

          <div className="personal-docs-relationship-count">
            {dataModelStudio?.relationships.length ??
              0}{" "}
            relationships
          </div>
        </article>

        <article className="personal-docs-card">
          <div className="personal-docs-card-title">
            <Sigma
              size={18}
            />

            <div>
              <strong>
                KPI definitions
              </strong>

              <small>
                Reusable semantic measures
              </small>
            </div>
          </div>

          <div className="personal-docs-list">
            {kpiDefinitions.map(
              (kpi) => (
                <div
                  key={
                    kpi.code
                  }
                  className="personal-docs-list-row"
                >
                  <strong>
                    {kpi.title}
                  </strong>

                  <code>
                    {formulaLabel(
                      kpi,
                    )}
                  </code>
                </div>
              ),
            )}
          </div>
        </article>

        <article className="personal-docs-card">
          <div className="personal-docs-card-title">
            <SlidersHorizontal
              size={18}
            />

            <div>
              <strong>
                Dashboard
              </strong>

              <small>
                Report configuration
              </small>
            </div>
          </div>

          <div className="personal-docs-stats compact">
            <Stat
              label="Visuals"
              value={
                dashboardConfig?.visuals.length ??
                0
              }
            />

            <Stat
              label="Filters"
              value={
                dashboardConfig?.filters.length ??
                0
              }
            />

            <Stat
              label="Theme"
              value={
                dashboardConfig?.theme ??
                "—"
              }
            />
          </div>

          <div className="personal-docs-chip-list">
            {dashboardConfig?.visuals.map(
              (visual) => (
                <span
                  key={
                    visual.visual_id
                  }
                >
                  {visual.visual_type}
                  <small>
                    {visual.dimension ??
                      "overall"}
                  </small>
                </span>
              ),
            )}
          </div>
        </article>
      </div>

      <section className="personal-docs-card personal-docs-analysis-card">
        <div className="personal-docs-card-title">
          <FileText
            size={18}
          />

          <div>
            <strong>
              Semantic analyses
            </strong>

            <small>
              Unique measure and dimension bindings
            </small>
          </div>
        </div>

        <div className="personal-docs-analysis-grid">
          {uniqueAnalyses.map(
            (analysis) => (
              <div
                key={
                  analysisKey(
                    analysis,
                  )
                }
                className="personal-docs-analysis-item"
              >
                <strong>
                  {kpiTitle(
                    analysis,
                    kpiDefinitions,
                  )}
                </strong>

                <span>
                  {analysis.dimension
                    ? `By ${analysis.dimension}`
                    : "Overall"}
                </span>
              </div>
            ),
          )}
        </div>
      </section>

      <section className="personal-docs-card personal-docs-notes">
        <div className="personal-docs-card-title">
          <CheckCircle2
            size={18}
          />

          <div>
            <strong>
              Technical notes
            </strong>

            <small>
              Architecture and reliability principles
            </small>
          </div>
        </div>

        <ul>
          <li>
            Measures and dimensions are separated in the semantic layer.
          </li>
          <li>
            Dashboard visuals are bound to saved semantic KPIs or analyses.
          </li>
          <li>
            Insight generation is deterministic and does not invent missing values.
          </li>
          <li>
            Time behavior is driven by semantic derivation metadata.
          </li>
          <li>
            The workflow is dataset-agnostic and driven by schema, roles,
            relationships and workspace metadata.
          </li>
        </ul>
      </section>
    </section>
  );
}
