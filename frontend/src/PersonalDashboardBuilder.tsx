import {
  useEffect,
  useMemo,
  useState,
  type DragEvent,
  type CSSProperties,
} from "react";

import type {
  AnalysisResultData,
} from "./PersonalAnalysisPlan";

import type {
  PersonalKpiData,
} from "./PersonalKpiCandidates";

import type {
  DataModelStudioData,
} from "./DataModelCanvas";


export type DashboardVisualType =
  | "kpi"
  | "bar"
  | "column"
  | "line"
  | "area"
  | "pie"
  | "donut"
  | "table";

export type DashboardSortMode =
  | "top_value"
  | "bottom_value"
  | "alphabetical"
  | "highest_count"
  | "lowest_count";

export type DashboardTheme =
  | "ocean"
  | "teal"
  | "violet"
  | "sunset"
  | "slate";

export type DashboardVisualData = {
  visual_id: string;
  analysis_id: string | null;

  kpi_code?: string | null;
  dimension_table?: string | null;
  dimension?: string | null;

  visual_type: DashboardVisualType;
  title: string;
  subtitle: string | null;
  size:
    | "compact"
    | "small"
    | "medium"
    | "large";
  sort_mode: DashboardSortMode;
  top_n: number;
  accent_color: string;
  background_color: string;
  text_color: string;
  x_axis_title: string | null;
  y_axis_title: string | null;
  show_values: boolean;

  show_legend?: boolean;
  show_gridlines?: boolean;
  animate?: boolean;

  tooltip_template?: string | null;
};

type Props = {
  analyses: AnalysisResultData[];
  kpiDefinitions: PersonalKpiData[];
  dataModelStudio: DataModelStudioData | null;
  savedVisuals: DashboardVisualData[];
  savedTitle: string;
  savedSubtitle: string | null;
  savedTheme: DashboardTheme;
  loading: boolean;
  error: string | null;

  onPreview: (
    kpiCode: string,
    dimensionTable: string | null,
    dimension: string | null,
  ) => Promise<AnalysisResultData>;

  onSave: (
    visuals: DashboardVisualData[],
    title: string,
    subtitle: string | null,
    theme: DashboardTheme,
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

function defaultVisualTitle(
  analysis: AnalysisResultData,
  visualType: DashboardVisualType,
  sortMode: DashboardSortMode,
  topN: number,
): string {
  const base =
    analysis.measure;

  if (!analysis.dimension) {
    return base;
  }

  if (
    visualType === "line" &&
    isTimeDimension(
      analysis.dimension
    )
  ) {
    return (
      base +
      " over " +
      analysis.dimension
    );
  }

  if (
    visualType === "bar" &&
    sortMode === "top_value"
  ) {
    return (
      "Top " +
      topN +
      " " +
      analysis.dimension +
      " by " +
      base
    );
  }

  if (
    visualType === "bar" &&
    sortMode === "bottom_value"
  ) {
    return (
      "Bottom " +
      topN +
      " " +
      analysis.dimension +
      " by " +
      base
    );
  }

  return (
    base +
    " by " +
    analysis.dimension
  );
}

function defaultVisualSubtitle(
  analysis: AnalysisResultData,
): string | null {
  if (!analysis.dimension) {
    return "Overall semantic KPI";
  }

  return (
    "Based on saved analysis: " +
    analysis.measure +
    " by " +
    analysis.dimension
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

  return "bar";
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


const DASHBOARD_THEMES: Record<
  DashboardTheme,
  {
    label: string;
    accent: string;
    background: string;
    text: string;
  }
> = {
  ocean: {
    label: "Ocean",
    accent: "#2f80ed",
    background: "#ffffff",
    text: "#213854",
  },
  teal: {
    label: "Teal",
    accent: "#0f9f8f",
    background: "#fbfffe",
    text: "#183f3a",
  },
  violet: {
    label: "Violet",
    accent: "#7c5ce6",
    background: "#fdfcff",
    text: "#302650",
  },
  sunset: {
    label: "Sunset",
    accent: "#e8873a",
    background: "#fffdf9",
    text: "#51311f",
  },
  slate: {
    label: "Slate",
    accent: "#52677f",
    background: "#fbfcfd",
    text: "#26384a",
  },
};


function DashboardSelect<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: {
    value: T;
    label: string;
  }[];
  onChange: (
    value: T
  ) => void;
}) {
  const [
    open,
    setOpen,
  ] = useState(false);

  const selected =
    options.find(
      (option) =>
        option.value === value
    );

  return (
    <div
      className={
        "dashboard-select" +
        (
          open
            ? " open"
            : ""
        )
      }
    >
      <button
        type="button"
        className="dashboard-select-trigger"
        onClick={() =>
          setOpen(
            (previous) =>
              !previous
          )
        }
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span>
          {selected?.label ??
            value}
        </span>

        <span aria-hidden="true">
          ▾
        </span>
      </button>

      {open && (
        <div
          className="dashboard-select-menu"
          role="listbox"
        >
          {options.map(
            (option) => (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={
                  option.value ===
                  value
                }
                className={
                  option.value ===
                  value
                    ? "dashboard-select-option selected"
                    : "dashboard-select-option"
                }
                onClick={() => {
                  onChange(
                    option.value
                  );

                  setOpen(false);
                }}
              >
                {option.label}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
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
  accentColor,
}: {
  analysis: AnalysisResultData;
  accentColor: string;
}) {
  return (
    <div
      className="dashboard-kpi-visual"
      style={{
        "--dashboard-accent":
          accentColor,
      } as CSSProperties}
    >
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
  accentColor,
  xAxisTitle,
  yAxisTitle,
  showValues,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  accentColor: string;
  xAxisTitle: string | null;
  yAxisTitle: string | null;
  showValues: boolean;
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
    <div
      className="dashboard-bar-chart"
      style={{
        "--dashboard-accent":
          accentColor,
      } as CSSProperties}
    >
      {(xAxisTitle || yAxisTitle) && (
        <div className="dashboard-axis-summary">
          {xAxisTitle && (
            <span>
              Category: {xAxisTitle}
            </span>
          )}

          {yAxisTitle && (
            <span>
              Measure: {yAxisTitle}
            </span>
          )}
        </div>
      )}

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

              {showValues ? (
                <strong>
                  {formatNumber(
                    value
                  )}
                </strong>
              ) : (
                <span
                  className="dashboard-bar-value-hidden"
                  aria-hidden="true"
                />
              )}
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
  accentColor,
  xAxisTitle,
  yAxisTitle,
  showValues,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  accentColor: string;
  xAxisTitle: string | null;
  yAxisTitle: string | null;
  showValues: boolean;
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
    <div
      className="dashboard-line-chart"
      style={{
        "--dashboard-accent":
          accentColor,
      } as CSSProperties}
    >
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

        {xAxisTitle && (
          <strong>
            {xAxisTitle}
          </strong>
        )}

        <span>
          {
            points[
              points.length - 1
            ]?.label ?? ""
          }
        </span>
      </div>

      {yAxisTitle && (
        <div className="dashboard-line-measure-label">
          {yAxisTitle}
        </div>
      )}

      {showValues && points.length > 0 && (
        <div className="dashboard-line-value-summary">
          <span>
            First: {
              formatNumber(
                points[0].value
              )
            }
          </span>

          <span>
            Last: {
              formatNumber(
                points[
                  points.length - 1
                ].value
              )
            }
          </span>
        </div>
      )}
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
  kpiDefinitions,
  dataModelStudio,
  savedVisuals,
  savedTitle,
  savedSubtitle,
  savedTheme,
  loading,
  error,
  onPreview,
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
    dashboardTitle,
    setDashboardTitle,
  ] = useState(
    savedTitle
  );

  const [
    dashboardSubtitle,
    setDashboardSubtitle,
  ] = useState(
    savedSubtitle ?? ""
  );

  const [
    dashboardTheme,
    setDashboardTheme,
  ] = useState<
    DashboardTheme
  >(
    savedTheme
  );

  const [
    draggingId,
    setDraggingId,
  ] = useState<
    string | null
  >(null);


  const [
    previewResults,
    setPreviewResults,
  ] = useState<
    Record<
      string,
      AnalysisResultData
    >
  >({});

  const [
    previewErrors,
    setPreviewErrors,
  ] = useState<
    Record<
      string,
      string
    >
  >({});


  const [
    editingVisualId,
    setEditingVisualId,
  ] = useState<
    string | null
  >(null);

  useEffect(
    () => {
      setVisuals(
        savedVisuals
      );

      setDashboardTitle(
        savedTitle
      );

      setDashboardSubtitle(
        savedSubtitle ?? ""
      );

      setDashboardTheme(
        savedTheme
      );
    },
    [
      savedVisuals,
      savedTitle,
      savedSubtitle,
      savedTheme,
    ]
  );

  const editingVisual =
    visuals.find(
      (visual) =>
        visual.visual_id ===
        editingVisualId
    ) ?? null;

  const editingAnalysis =
    editingVisual
      ? analyses.find(
          (analysis) =>
            analysis.analysis_id ===
            editingVisual.analysis_id
        ) ?? null
      : null;

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
        defaultVisualTitle(
          analysis,
          visualType,
          isTimeDimension(
            analysis.dimension
          )
            ? "alphabetical"
            : "top_value",
          visualType === "line"
            ? 20
            : 10,
        ),
      subtitle:
        defaultVisualSubtitle(
          analysis
        ),
      size:
        visualType === "kpi"
          ? "compact"
          : "medium",
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
      accent_color:
        DASHBOARD_THEMES[
          dashboardTheme
        ].accent,
      background_color:
        DASHBOARD_THEMES[
          dashboardTheme
        ].background,
      text_color:
        DASHBOARD_THEMES[
          dashboardTheme
        ].text,
      x_axis_title:
        analysis.dimension,
      y_axis_title:
        analysis.measure,
      show_values: true,
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

    if (
      editingVisualId ===
      visualId
    ) {
      setEditingVisualId(
        null
      );
    }
  }

  function resizeVisual(
    visual:
      DashboardVisualData,
    direction:
      "smaller" | "larger",
  ) {
    const order:
      DashboardVisualData["size"][] = [
        "compact",
        "small",
        "medium",
        "large",
      ];

    const currentIndex =
      order.indexOf(
        visual.size
      );

    const nextIndex =
      direction === "larger"
        ? Math.min(
            order.length - 1,
            currentIndex + 1
          )
        : Math.max(
            0,
            currentIndex - 1
          );

    updateVisual(
      visual.visual_id,
      {
        size:
          order[nextIndex],
      }
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
                visuals,
                dashboardTitle.trim() || "Dashboard",
                dashboardSubtitle.trim() || null,
                dashboardTheme,
              )
            }
          >
            {loading
              ? "Saving..."
              : "Save dashboard"}
          </button>
        </div>
      </div>

      <div className="dashboard-style-toolbar">
        <label>
          <span>
            Dashboard title
          </span>

          <input
            value={
              dashboardTitle
            }
            onChange={(event) =>
              setDashboardTitle(
                event.target.value
              )
            }
          />
        </label>

        <label>
          <span>
            Subtitle
          </span>

          <input
            value={
              dashboardSubtitle
            }
            placeholder="Optional"
            onChange={(event) =>
              setDashboardSubtitle(
                event.target.value
              )
            }
          />
        </label>

        <label>
          <span>
            Theme
          </span>

          <DashboardSelect
            value={
              dashboardTheme
            }
            options={
              (
                Object.entries(
                  DASHBOARD_THEMES
                ) as [
                  DashboardTheme,
                  {
                    label: string;
                  },
                ][]
              ).map(
                ([
                  value,
                  theme,
                ]) => ({
                  value,
                  label:
                    theme.label,
                })
              )
            }
            onChange={(
              theme
            ) => {
              setDashboardTheme(
                theme
              );

              const palette =
                DASHBOARD_THEMES[
                  theme
                ];

              setVisuals(
                (previous) =>
                  previous.map(
                    (visual) => ({
                      ...visual,
                      accent_color:
                        palette.accent,
                      background_color:
                        palette.background,
                      text_color:
                        palette.text,
                    })
                  )
              );
            }}
          />
        </label>

        <div className="dashboard-theme-swatches">
          {(
            Object.entries(
              DASHBOARD_THEMES
            ) as [
              DashboardTheme,
              {
                label: string;
                accent: string;
              },
            ][]
          ).map(
            ([
              themeKey,
              theme,
            ]) => (
              <button
                key={
                  themeKey
                }
                type="button"
                title={
                  theme.label
                }
                className={
                  themeKey ===
                  dashboardTheme
                    ? "active"
                    : ""
                }
                style={{
                  background:
                    theme.accent,
                }}
                onClick={() => {
                  setDashboardTheme(
                    themeKey
                  );

                  const palette =
                    DASHBOARD_THEMES[
                      themeKey
                    ];

                  setVisuals(
                    (previous) =>
                      previous.map(
                        (visual) => ({
                          ...visual,
                          accent_color:
                            palette.accent,
                          background_color:
                            palette.background,
                          text_color:
                            palette.text,
                        })
                      )
                  );
                }}
              />
            )
          )}
        </div>
      </div>

      <div
        className={
          "dashboard-builder-layout" +
          (
            editingVisual
              ? " properties-open"
              : ""
          )
        }
      >
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

                      {visuals
                        .filter(
                          (visual) =>
                            visual.analysis_id ===
                            analysis.analysis_id
                        )
                        .slice(0, 2)
                        .map(
                          (visual) => (
                            <small
                              key={
                                visual.visual_id
                              }
                              title={
                                visual.title
                              }
                            >
                              Dashboard: {
                                visual.title
                              }
                            </small>
                          )
                        )}
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

        {editingVisual && (
          <aside className="dashboard-properties-panel">
            <div className="dashboard-properties-header">
              <div>
                <span className="workspace-overview-label">
                  VISUAL PROPERTIES
                </span>

                <strong>
                  Edit visual
                </strong>

                {editingAnalysis && (
                  <small>
                    Source: {
                      editingAnalysis.measure
                    }{
                      editingAnalysis.dimension
                        ? (
                            " by " +
                            editingAnalysis.dimension
                          )
                        : ""
                    }
                  </small>
                )}
              </div>

              <button
                type="button"
                onClick={() =>
                  setEditingVisualId(
                    null
                  )
                }
                title="Close properties"
              >
                ×
              </button>
            </div>

            <div className="dashboard-properties-body">
              <label className="dashboard-property-field">
                <span>
                  Chart title
                </span>

                <input
                  type="text"
                  value={
                    editingVisual.title
                  }
                  onChange={(event) =>
                    updateVisual(
                      editingVisual.visual_id,
                      {
                        title:
                          event.target.value,
                      }
                    )
                  }
                />
              </label>

              <label className="dashboard-property-field">
                <span>
                  Subtitle
                </span>

                <textarea
                  rows={3}
                  value={
                    editingVisual.subtitle ??
                    ""
                  }
                  placeholder="What does this visual tell the reader?"
                  onChange={(event) =>
                    updateVisual(
                      editingVisual.visual_id,
                      {
                        subtitle:
                          event.target.value ||
                          null,
                      }
                    )
                  }
                />
              </label>

              <div className="dashboard-property-section">
                <strong>
                  Appearance
                </strong>

                <div className="dashboard-property-colors">
                  <label>
                    <span>
                      Accent
                    </span>

                    <input
                      type="color"
                      value={
                        editingVisual.accent_color
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            accent_color:
                              event.target.value,
                          }
                        )
                      }
                    />
                  </label>

                  <label>
                    <span>
                      Card
                    </span>

                    <input
                      type="color"
                      value={
                        editingVisual.background_color
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            background_color:
                              event.target.value,
                          }
                        )
                      }
                    />
                  </label>

                  <label>
                    <span>
                      Text
                    </span>

                    <input
                      type="color"
                      value={
                        editingVisual.text_color
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            text_color:
                              event.target.value,
                          }
                        )
                      }
                    />
                  </label>
                </div>
              </div>

              <div className="dashboard-property-section">
                <strong>
                  Visual
                </strong>

                <label className="dashboard-property-field">
                  <span>
                    Type
                  </span>

                  <DashboardSelect
                    value={
                      editingVisual.visual_type
                    }
                    options={[
                      {
                        value: "kpi",
                        label: "KPI card",
                      },
                      {
                        value: "bar",
                        label: "Bar chart",
                      },
                      {
                        value: "line",
                        label: "Line chart",
                      },
                      {
                        value: "table",
                        label: "Table",
                      },
                    ]}
                    onChange={(visualType) =>
                      updateVisual(
                        editingVisual.visual_id,
                        {
                          visual_type:
                            visualType,
                        }
                      )
                    }
                  />
                </label>

                {editingAnalysis &&
                  editingAnalysis.grouped_results.length > 0 && (
                  <>
                    <label className="dashboard-property-field">
                      <span>
                        Sort
                      </span>

                      <DashboardSelect
                        value={
                          editingVisual.sort_mode
                        }
                        options={[
                          {
                            value: "top_value",
                            label: "Top value",
                          },
                          {
                            value: "bottom_value",
                            label: "Bottom value",
                          },
                          {
                            value: "alphabetical",
                            label: "Alphabetical",
                          },
                          {
                            value: "highest_count",
                            label: "Highest count",
                          },
                          {
                            value: "lowest_count",
                            label: "Lowest count",
                          },
                        ]}
                        onChange={(sortMode) =>
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              sort_mode:
                                sortMode,
                            }
                          )
                        }
                      />
                    </label>

                    <label className="dashboard-property-field">
                      <span>
                        Top N
                      </span>

                      <input
                        type="number"
                        min="1"
                        max="50"
                        value={
                          editingVisual.top_n
                        }
                        onChange={(event) =>
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              top_n:
                                Math.max(
                                  1,
                                  Math.min(
                                    50,
                                    Number(
                                      event.target.value
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

              <div className="dashboard-property-section">
                <strong>
                  Labels & axes
                </strong>

                <label className="dashboard-property-field">
                  <span>
                    X-axis title
                  </span>

                  <input
                    type="text"
                    value={
                      editingVisual.x_axis_title ??
                      ""
                    }
                    onChange={(event) =>
                      updateVisual(
                        editingVisual.visual_id,
                        {
                          x_axis_title:
                            event.target.value ||
                            null,
                        }
                      )
                    }
                  />
                </label>

                <label className="dashboard-property-field">
                  <span>
                    Y-axis title
                  </span>

                  <input
                    type="text"
                    value={
                      editingVisual.y_axis_title ??
                      ""
                    }
                    onChange={(event) =>
                      updateVisual(
                        editingVisual.visual_id,
                        {
                          y_axis_title:
                            event.target.value ||
                            null,
                        }
                      )
                    }
                  />
                </label>

                <label className="dashboard-property-check">
                  <input
                    type="checkbox"
                    checked={
                      editingVisual.show_values
                    }
                    onChange={(event) =>
                      updateVisual(
                        editingVisual.visual_id,
                        {
                          show_values:
                            event.target.checked,
                        }
                      )
                    }
                  />

                  <span>
                    Show values
                  </span>
                </label>
              </div>
            </div>
          </aside>
        )}

        <main
          className="dashboard-canvas"
          style={{
            "--dashboard-theme-accent":
              DASHBOARD_THEMES[
                dashboardTheme
              ].accent,
          } as CSSProperties}
        >
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

          <div className="dashboard-report-heading">
            <div>
              <h3>
                {dashboardTitle.trim() ||
                  "Dashboard"}
              </h3>

              {dashboardSubtitle.trim() && (
                <p>
                  {dashboardSubtitle}
                </p>
              )}
            </div>

            <span>
              {DASHBOARD_THEMES[
                dashboardTheme
              ].label}
            </span>
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
                    style={{
                      background:
                        visual.background_color,
                      color:
                        visual.text_color,
                    }}
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

                      <div className="dashboard-visual-title-block">
                        <strong>
                          {visual.title}
                        </strong>

                        {visual.subtitle && (
                          <span>
                            {visual.subtitle}
                          </span>
                        )}
                      </div>

                      <div className="dashboard-visual-actions">
                        <button
                          type="button"
                          className={
                            editingVisualId ===
                            visual.visual_id
                              ? "active"
                              : ""
                          }
                          onClick={() =>
                            setEditingVisualId(
                              (previous) =>
                                previous ===
                                visual.visual_id
                                  ? null
                                  : visual.visual_id
                            )
                          }
                          title="Edit visual"
                        >
                          ⚙
                        </button>

                        <button
                          type="button"
                          disabled={
                            visual.size ===
                            "compact"
                          }
                          onClick={() =>
                            resizeVisual(
                              visual,
                              "smaller",
                            )
                          }
                          title="Make smaller"
                        >
                          −
                        </button>

                        <button
                          type="button"
                          disabled={
                            visual.size ===
                            "large"
                          }
                          onClick={() =>
                            resizeVisual(
                              visual,
                              "larger",
                            )
                          }
                          title="Make larger"
                        >
                          +
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

                    <div className="dashboard-visual-content">
                      {visual.visual_type ===
                        "kpi" && (
                        <DashboardKpiVisual
                          analysis={
                            analysis
                          }
                          accentColor={
                            visual.accent_color
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
                          accentColor={
                            visual.accent_color
                          }
                          xAxisTitle={
                            visual.x_axis_title
                          }
                          yAxisTitle={
                            visual.y_axis_title
                          }
                          showValues={
                            visual.show_values
                          }
                        />
                      )}

                      {visual.visual_type ===
                        "line" && (
                        <DashboardLineVisual
                          analysis={
                            analysis
                          }
                          rows={rows}
                          accentColor={
                            visual.accent_color
                          }
                          xAxisTitle={
                            visual.x_axis_title
                          }
                          yAxisTitle={
                            visual.y_axis_title
                          }
                          showValues={
                            visual.show_values
                          }
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
