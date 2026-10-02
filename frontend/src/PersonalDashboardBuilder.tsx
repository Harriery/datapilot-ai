import {
  useEffect,
  useMemo,
  useState,
  type DragEvent,
} from "react";

import type {
  AnalysisResultData,
} from "./PersonalAnalysisPlan";


export type DashboardVisualType =
  | "kpi"
  | "bar"
  | "line"
  | "table";

export type DashboardSortMode =
  | "top_value"
  | "bottom_value"
  | "alphabetical"
  | "highest_count"
  | "lowest_count";

export type DashboardVisualData = {
  visual_id: string;
  analysis_id: string;
  visual_type: DashboardVisualType;
  title: string;
  size: "small" | "large";
  sort_mode: DashboardSortMode;
  top_n: number;
};

type Props = {
  analyses: AnalysisResultData[];
  savedVisuals: DashboardVisualData[];
  loading: boolean;
  error: string | null;
  onSave: (
    visuals: DashboardVisualData[]
  ) => void;
};

function formatNumber(
  value: number | null | undefined
): string {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 2,
    }
  ).format(value);
}

function isTimeDimension(
  dimension: string | null
): boolean {
  if (!dimension) {
    return false;
  }

  return [
    "date",
    "year",
    "quarter",
    "month",
    "monthname",
    "week",
    "day",
  ].includes(
    dimension
      .replace(/[^a-z]/gi, "")
      .toLowerCase()
  );
}

function recommendedVisual(
  analysis: AnalysisResultData
): DashboardVisualType {
  if (
    !analysis.dimension ||
    analysis.grouped_results.length === 0
  ) {
    return "kpi";
  }

  if (
    isTimeDimension(
      analysis.dimension
    )
  ) {
    return "line";
  }

  if (
    analysis.grouped_results.length <= 20
  ) {
    return "bar";
  }

  return "table";
}

function recommendationLabel(
  type: DashboardVisualType
): string {
  return {
    kpi: "KPI card",
    bar: "Bar chart",
    line: "Line chart",
    table: "Table",
  }[type];
}

function sortRows(
  analysis: AnalysisResultData,
  sortMode: DashboardSortMode,
) {
  const semantic =
    Boolean(
      analysis.kpi_code
    );

  return [
    ...analysis.grouped_results,
  ].sort(
    (left, right) => {
      if (
        sortMode ===
        "alphabetical"
      ) {
        return String(
          left.value ?? ""
        ).localeCompare(
          String(
            right.value ?? ""
          )
        );
      }

      if (
        sortMode ===
        "highest_count"
      ) {
        return (
          right.count -
          left.count
        );
      }

      if (
        sortMode ===
        "lowest_count"
      ) {
        return (
          left.count -
          right.count
        );
      }

      const leftValue =
        semantic
          ? left.metric_value
          : left.mean;

      const rightValue =
        semantic
          ? right.metric_value
          : right.mean;

      const safeLeft =
        leftValue ??
        Number.NEGATIVE_INFINITY;

      const safeRight =
        rightValue ??
        Number.NEGATIVE_INFINITY;

      return (
        sortMode ===
        "bottom_value"
          ? safeLeft - safeRight
          : safeRight - safeLeft
      );
    }
  );
}

function getMetricValue(
  analysis: AnalysisResultData,
) {
  return analysis.kpi_code
    ? analysis.overall.metric_value
    : analysis.overall.mean;
}

function DashboardKpiVisual({
  analysis,
}: {
  analysis: AnalysisResultData;
}) {
  return (
    <div className="dashboard-kpi-visual">
      <strong>
        {formatNumber(
          getMetricValue(
            analysis
          )
        )}
      </strong>

      <span>
        {analysis.dimension
          ? (
              String(
                analysis.grouped_results.length
              ) +
              " groups"
            )
          : (
              formatNumber(
                analysis.overall.count
              ) +
              " records"
            )}
      </span>
    </div>
  );
}

function DashboardBarVisual({
  analysis,
  rows,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
}) {
  const semantic =
    Boolean(
      analysis.kpi_code
    );

  const values =
    rows.map(
      (row) =>
        (
          semantic
            ? row.metric_value
            : row.mean
        ) ?? 0
    );

  const maxValue =
    Math.max(
      ...values,
      1
    );

  return (
    <div className="dashboard-bar-chart">
      {rows.map(
        (row, index) => {
          const value =
            values[index];

          const width =
            Math.max(
              2,
              (
                Math.abs(value) /
                Math.abs(maxValue)
              ) * 100
            );

          return (
            <div
              key={
                String(row.value) +
                "-" +
                index
              }
              className="dashboard-bar-row"
            >
              <span
                title={
                  String(
                    row.value ??
                    "Missing"
                  )
                }
              >
                {String(
                  row.value ??
                  "Missing"
                )}
              </span>

              <div className="dashboard-bar-track">
                <div
                  className="dashboard-bar-value"
                  style={{
                    width:
                      width + "%",
                  }}
                />
              </div>

              <strong>
                {formatNumber(
                  value
                )}
              </strong>
            </div>
          );
        }
      )}
    </div>
  );
}

function DashboardLineVisual({
  analysis,
  rows,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
}) {
  const semantic =
    Boolean(
      analysis.kpi_code
    );

  const orderedRows = [
    ...rows,
  ].sort(
    (left, right) =>
      String(
        left.value ?? ""
      ).localeCompare(
        String(
          right.value ?? ""
        ),
        undefined,
        {
          numeric: true,
        }
      )
  );

  const values =
    orderedRows.map(
      (row) =>
        (
          semantic
            ? row.metric_value
            : row.mean
        ) ?? 0
    );

  const min =
    Math.min(
      ...values,
      0
    );

  const max =
    Math.max(
      ...values,
      1
    );

  const range =
    max - min || 1;

  const points =
    orderedRows.map(
      (row, index) => {
        const x =
          orderedRows.length <= 1
            ? 50
            : (
                index /
                (
                  orderedRows.length -
                  1
                )
              ) * 100;

        const value =
          values[index];

        const y =
          88 -
          (
            (
              value - min
            ) /
            range
          ) * 76;

        return {
          x,
          y,
          value,
          label:
            String(
              row.value ?? ""
            ),
        };
      }
    );

  const path =
    points
      .map(
        (point) =>
          point.x +
          "," +
          point.y
      )
      .join(" ");

  return (
    <div className="dashboard-line-chart">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-label={
          analysis.measure +
          " trend"
        }
      >
        <polyline
          points={path}
          fill="none"
          vectorEffect="non-scaling-stroke"
        />

        {points.map(
          (point, index) => (
            <circle
              key={index}
              cx={point.x}
              cy={point.y}
              r="1.6"
              vectorEffect="non-scaling-stroke"
            >
              <title>
                {point.label +
                  ": " +
                  formatNumber(
                    point.value
                  )}
              </title>
            </circle>
          )
        )}
      </svg>

      <div className="dashboard-line-axis">
        <span>
          {points[0]?.label ??
            ""}
        </span>

        <span>
          {
            points[
              points.length - 1
            ]?.label ?? ""
          }
        </span>
      </div>
    </div>
  );
}

function DashboardTableVisual({
  analysis,
  rows,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
}) {
  const semantic =
    Boolean(
      analysis.kpi_code
    );

  return (
    <div className="dashboard-table-wrap">
      <table className="dashboard-table">
        <thead>
          <tr>
            <th>
              {analysis.dimension ??
                "Value"}
            </th>

            <th>
              Count
            </th>

            <th>
              KPI value
            </th>
          </tr>
        </thead>

        <tbody>
          {rows.map(
            (row, index) => (
              <tr
                key={
                  String(
                    row.value
                  ) +
                  "-" +
                  index
                }
              >
                <td>
                  {String(
                    row.value ??
                    "Missing"
                  )}
                </td>

                <td>
                  {formatNumber(
                    row.count
                  )}
                </td>

                <td>
                  {formatNumber(
                    semantic
                      ? row.metric_value
                      : row.mean
                  )}
                </td>
              </tr>
            )
          )}
        </tbody>
      </table>
    </div>
  );
}

function PersonalDashboardBuilder({
  analyses,
  savedVisuals,
  loading,
  error,
  onSave,
}: Props) {
  const [
    visuals,
    setVisuals,
  ] = useState<
    DashboardVisualData[]
  >(
    savedVisuals
  );

  const [
    draggingId,
    setDraggingId,
  ] = useState<
    string | null
  >(null);

  useEffect(
    () => {
      setVisuals(
        savedVisuals
      );
    },
    [savedVisuals]
  );

  const analysesById =
    useMemo(
      () =>
        new Map(
          analyses
            .filter(
              (analysis) =>
                analysis.analysis_id
            )
            .map(
              (analysis) => [
                analysis.analysis_id!,
                analysis,
              ]
            )
        ),
      [analyses]
    );

  function createVisual(
    analysis:
      AnalysisResultData
  ): DashboardVisualData | null {
    if (!analysis.analysis_id) {
      return null;
    }

    const visualType =
      recommendedVisual(
        analysis
      );

    return {
      visual_id:
        (
          globalThis.crypto
            ?.randomUUID?.()
        ) ??
        (
          "visual-" +
          Date.now() +
          "-" +
          Math.random()
            .toString(36)
            .slice(2)
        ),
      analysis_id:
        analysis.analysis_id,
      visual_type:
        visualType,
      title:
        analysis.measure +
        (
          analysis.dimension
            ? (
                " by " +
                analysis.dimension
              )
            : ""
        ),
      size:
        visualType === "kpi"
          ? "small"
          : "large",
      sort_mode:
        isTimeDimension(
          analysis.dimension
        )
          ? "alphabetical"
          : "top_value",
      top_n:
        visualType === "line"
          ? 20
          : 10,
    };
  }

  function addAnalysis(
    analysis:
      AnalysisResultData
  ) {
    const visual =
      createVisual(
        analysis
      );

    if (!visual) {
      return;
    }

    setVisuals(
      (previous) => [
        ...previous,
        visual,
      ]
    );
  }

  function addSuggestedDashboard() {
    const next =
      analyses
        .filter(
          (analysis) =>
            analysis.analysis_id
        )
        .slice(0, 8)
        .map(
          createVisual
        )
        .filter(
          (
            visual,
          ): visual is
            DashboardVisualData =>
              visual !== null
        );

    setVisuals(
      next
    );
  }

  function updateVisual(
    visualId: string,
    update:
      Partial<
        DashboardVisualData
      >
  ) {
    setVisuals(
      (previous) =>
        previous.map(
          (visual) =>
            visual.visual_id ===
            visualId
              ? {
                  ...visual,
                  ...update,
                }
              : visual
        )
    );
  }

  function removeVisual(
    visualId: string
  ) {
    setVisuals(
      (previous) =>
        previous.filter(
          (visual) =>
            visual.visual_id !==
            visualId
        )
    );
  }

  function duplicateVisual(
    visual:
      DashboardVisualData
  ) {
    setVisuals(
      (previous) => [
        ...previous,
        {
          ...visual,
          visual_id:
            (
              globalThis.crypto
                ?.randomUUID?.()
            ) ??
            (
              "visual-" +
              Date.now()
            ),
          title:
            visual.title +
            " copy",
        },
      ]
    );
  }

  function handleDrop(
    targetId: string
  ) {
    if (
      !draggingId ||
      draggingId ===
        targetId
    ) {
      setDraggingId(
        null
      );
      return;
    }

    setVisuals(
      (previous) => {
        const next = [
          ...previous,
        ];

        const from =
          next.findIndex(
            (item) =>
              item.visual_id ===
              draggingId
          );

        const to =
          next.findIndex(
            (item) =>
              item.visual_id ===
              targetId
          );

        if (
          from < 0 ||
          to < 0
        ) {
          return previous;
        }

        const [moved] =
          next.splice(
            from,
            1
          );

        next.splice(
          to,
          0,
          moved
        );

        return next;
      }
    );

    setDraggingId(
      null
    );
  }

  return (
    <section className="personal-dashboard-builder">
      <div className="dashboard-builder-header">
        <div>
          <span className="workspace-overview-label">
            DASHBOARD BUILDER
          </span>

          <h2>
            Build the report canvas
          </h2>

          <p>
            Turn saved semantic analyses into reusable
            KPI cards, charts and tables. Visual settings
            stay linked to the saved analysis results.
          </p>
        </div>

        <div className="dashboard-builder-header-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={
              analyses.length === 0
            }
            onClick={
              addSuggestedDashboard
            }
          >
            Build suggested dashboard
          </button>

          <button
            type="button"
            className="new-workspace-button"
            disabled={
              loading ||
              visuals.length === 0
            }
            onClick={() =>
              onSave(
                visuals
              )
            }
          >
            {loading
              ? "Saving..."
              : "Save dashboard"}
          </button>
        </div>
      </div>

      <div className="dashboard-builder-layout">
        <aside className="dashboard-analysis-library">
          <div className="dashboard-panel-heading">
            <span className="workspace-overview-label">
              SAVED ANALYSES
            </span>

            <strong>
              Add visual
            </strong>
          </div>

          <div className="dashboard-analysis-list">
            {analyses.map(
              (analysis, index) => {
                const recommendation =
                  recommendedVisual(
                    analysis
                  );

                return (
                  <div
                    key={
                      analysis.analysis_id ??
                      index
                    }
                    className="dashboard-analysis-item"
                  >
                    <div>
                      <strong>
                        {analysis.measure}
                        {analysis.dimension
                          ? (
                              " by " +
                              analysis.dimension
                            )
                          : ""}
                      </strong>

                      <span>
                        Recommended: {
                          recommendationLabel(
                            recommendation
                          )
                        }
                      </span>
                    </div>

                    <button
                      type="button"
                      className="secondary-button"
                      disabled={
                        !analysis.analysis_id
                      }
                      onClick={() =>
                        addAnalysis(
                          analysis
                        )
                      }
                    >
                      Add
                    </button>
                  </div>
                );
              }
            )}
          </div>

          {analyses.length === 0 && (
            <p className="dashboard-empty-copy">
              Run and save analyses before building a dashboard.
            </p>
          )}
        </aside>

        <main className="dashboard-canvas">
          <div className="dashboard-canvas-heading">
            <div>
              <span className="workspace-overview-label">
                CANVAS
              </span>

              <strong>
                {visuals.length} visual
                {visuals.length === 1
                  ? ""
                  : "s"}
              </strong>
            </div>

            <button
              type="button"
              className="dashboard-reset-button"
              disabled={
                visuals.length === 0
              }
              onClick={() =>
                setVisuals([])
              }
            >
              Reset canvas
            </button>
          </div>

          {visuals.length === 0 && (
            <div className="dashboard-canvas-empty">
              <strong>
                Your dashboard is empty
              </strong>

              <p>
                Add a saved analysis or build the suggested
                dashboard to start.
              </p>
            </div>
          )}

          <div className="dashboard-visual-grid">
            {visuals.map(
              (visual) => {
                const analysis =
                  analysesById.get(
                    visual.analysis_id
                  );

                if (!analysis) {
                  return null;
                }

                const rows =
                  sortRows(
                    analysis,
                    visual.sort_mode
                  ).slice(
                    0,
                    visual.top_n
                  );

                return (
                  <article
                    key={
                      visual.visual_id
                    }
                    className={
                      "dashboard-visual-card size-" +
                      visual.size
                    }
                    draggable
                    onDragStart={(
                      event:
                        DragEvent<HTMLElement>
                    ) => {
                      setDraggingId(
                        visual.visual_id
                      );

                      event
                        .dataTransfer
                        .setData(
                          "text/plain",
                          visual.visual_id
                        );
                    }}
                    onDragOver={(
                      event
                    ) =>
                      event
                        .preventDefault()
                    }
                    onDrop={() =>
                      handleDrop(
                        visual.visual_id
                      )
                    }
                    onDragEnd={() =>
                      setDraggingId(
                        null
                      )
                    }
                  >
                    <header className="dashboard-visual-header">
                      <span
                        className="dashboard-visual-drag"
                        title="Drag to reorder"
                      >
                        ⋮⋮
                      </span>

                      <input
                        value={
                          visual.title
                        }
                        onChange={(
                          event
                        ) =>
                          updateVisual(
                            visual.visual_id,
                            {
                              title:
                                event
                                  .target
                                  .value,
                            }
                          )
                        }
                        aria-label="Visual title"
                      />

                      <div className="dashboard-visual-actions">
                        <button
                          type="button"
                          onClick={() =>
                            updateVisual(
                              visual.visual_id,
                              {
                                size:
                                  visual.size ===
                                  "small"
                                    ? "large"
                                    : "small",
                              }
                            )
                          }
                          title="Toggle size"
                        >
                          {visual.size ===
                          "small"
                            ? "L"
                            : "S"}
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            duplicateVisual(
                              visual
                            )
                          }
                          title="Duplicate visual"
                        >
                          ⧉
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            removeVisual(
                              visual.visual_id
                            )
                          }
                          title="Remove visual"
                        >
                          ×
                        </button>
                      </div>
                    </header>

                    <div className="dashboard-visual-settings">
                      <label>
                        <span>
                          Visual
                        </span>

                        <select
                          value={
                            visual.visual_type
                          }
                          onChange={(
                            event
                          ) =>
                            updateVisual(
                              visual.visual_id,
                              {
                                visual_type:
                                  event
                                    .target
                                    .value as
                                    DashboardVisualType,
                              }
                            )
                          }
                        >
                          <option value="kpi">
                            KPI card
                          </option>
                          <option value="bar">
                            Bar chart
                          </option>
                          <option value="line">
                            Line chart
                          </option>
                          <option value="table">
                            Table
                          </option>
                        </select>
                      </label>

                      {analysis.grouped_results.length > 0 && (
                        <>
                          <label>
                            <span>
                              Sort
                            </span>

                            <select
                              value={
                                visual.sort_mode
                              }
                              onChange={(
                                event
                              ) =>
                                updateVisual(
                                  visual.visual_id,
                                  {
                                    sort_mode:
                                      event
                                        .target
                                        .value as
                                        DashboardSortMode,
                                  }
                                )
                              }
                            >
                              <option value="top_value">
                                Top value
                              </option>
                              <option value="bottom_value">
                                Bottom value
                              </option>
                              <option value="alphabetical">
                                Alphabetical
                              </option>
                              <option value="highest_count">
                                Highest count
                              </option>
                              <option value="lowest_count">
                                Lowest count
                              </option>
                            </select>
                          </label>

                          <label>
                            <span>
                              Top N
                            </span>

                            <input
                              type="number"
                              min="1"
                              max="50"
                              value={
                                visual.top_n
                              }
                              onChange={(
                                event
                              ) =>
                                updateVisual(
                                  visual.visual_id,
                                  {
                                    top_n:
                                      Math.max(
                                        1,
                                        Math.min(
                                          50,
                                          Number(
                                            event
                                              .target
                                              .value
                                          ) || 1
                                        )
                                      ),
                                  }
                                )
                              }
                            />
                          </label>
                        </>
                      )}
                    </div>

                    <div className="dashboard-visual-content">
                      {visual.visual_type ===
                        "kpi" && (
                        <DashboardKpiVisual
                          analysis={
                            analysis
                          }
                        />
                      )}

                      {visual.visual_type ===
                        "bar" && (
                        <DashboardBarVisual
                          analysis={
                            analysis
                          }
                          rows={rows}
                        />
                      )}

                      {visual.visual_type ===
                        "line" && (
                        <DashboardLineVisual
                          analysis={
                            analysis
                          }
                          rows={rows}
                        />
                      )}

                      {visual.visual_type ===
                        "table" && (
                        <DashboardTableVisual
                          analysis={
                            analysis
                          }
                          rows={rows}
                        />
                      )}
                    </div>
                  </article>
                );
              }
            )}
          </div>
        </main>
      </div>

      {error && (
        <p className="personal-analysis-error">
          {error}
        </p>
      )}
    </section>
  );
}

export default PersonalDashboardBuilder;
