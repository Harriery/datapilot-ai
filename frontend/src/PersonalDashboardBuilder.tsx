import {
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
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
  | "chronological"
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
  auto_title?: boolean;
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

  grid_column?: number | null;

  canvas_x?: number | null;
  canvas_y?: number | null;
  canvas_width?: number | null;
  canvas_height?: number | null;

  title_alignment?: "left" | "center" | "right";

  kpi_label?: string | null;
  kpi_label_font_size?: number;
  kpi_label_bold?: boolean;
  kpi_label_color?: string | null;
  kpi_show_secondary?: boolean;
  kpi_value_alignment?: "left" | "center" | "right";
  kpi_vertical_alignment?: "top" | "center" | "bottom";

  title_font_size?: number;
  title_bold?: boolean;
  title_color?: string | null;

  subtitle_font_size?: number;
  subtitle_bold?: boolean;
  subtitle_color?: string | null;

  category_label_font_size?: number;
  category_label_bold?: boolean;
  category_label_color?: string | null;

  value_label_font_size?: number;
  value_label_bold?: boolean;
  value_label_color?: string | null;

  axis_label_font_size?: number;
  axis_label_bold?: boolean;
  axis_label_color?: string | null;

  legend_label_font_size?: number;
  legend_label_bold?: boolean;
  legend_label_color?: string | null;
};

export type DashboardFilterData = {
  filter_id: string;
  table: string;
  column: string;
  label: string;
  value: string | null;
  values?: string[];
};

type DashboardCrossFilterData =
  DashboardFilterData & {
    source_visual_id: string;
  };

type Props = {
  analyses: AnalysisResultData[];
  kpiDefinitions: PersonalKpiData[];
  dataModelStudio: DataModelStudioData | null;
  savedVisuals: DashboardVisualData[];
  savedTitle: string;
  savedSubtitle: string | null;
  savedTheme: DashboardTheme;
  savedFilters: DashboardFilterData[];
  loading: boolean;
  error: string | null;

  onPreview: (
    kpiCode: string,
    dimensionTable: string | null,
    dimension: string | null,
    filters?: DashboardFilterData[],
  ) => Promise<AnalysisResultData>;

  onLoadFilterValues: (
    table: string,
    column: string,
  ) => Promise<string[]>;

  onSave: (
    visuals: DashboardVisualData[],
    title: string,
    subtitle: string | null,
    theme: DashboardTheme,
    filters: DashboardFilterData[],
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
    (
      visualType === "line" ||
      visualType === "area"
    ) &&
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
    (
      visualType === "bar" ||
      visualType === "column"
    ) &&
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
    (
      visualType === "bar" ||
      visualType === "column"
    ) &&
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
    bar: "Horizontal bar",
    column: "Column chart",
    line: "Line chart",
    area: "Area chart",
    pie: "Pie chart",
    donut: "Donut chart",
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

const DASHBOARD_GRID_SIZE = 8;
const DASHBOARD_CANVAS_MIN_WIDTH = 1040;
const DASHBOARD_CANVAS_MIN_HEIGHT = 620;
const DASHBOARD_VISUAL_GAP = 16;
const DASHBOARD_VISUAL_MIN_WIDTH = 240;
const DASHBOARD_VISUAL_MIN_HEIGHT = 180;
const DASHBOARD_KPI_MIN_WIDTH = 160;
const DASHBOARD_KPI_MIN_HEIGHT = 112;

function visualMinWidth(
  visual: DashboardVisualData
) {
  return visual.visual_type === "kpi"
    ? DASHBOARD_KPI_MIN_WIDTH
    : DASHBOARD_VISUAL_MIN_WIDTH;
}

function visualMinHeight(
  visual: DashboardVisualData
) {
  return visual.visual_type === "kpi"
    ? DASHBOARD_KPI_MIN_HEIGHT
    : DASHBOARD_VISUAL_MIN_HEIGHT;
}

function defaultVisualCanvasSize(
  visual: DashboardVisualData
) {
  if (visual.visual_type === "kpi") {
    return { width: 240, height: 160 };
  }

  return {
    compact: { width: 320, height: 220 },
    small: { width: 400, height: 260 },
    medium: { width: 480, height: 300 },
    large: { width: 992, height: 320 },
  }[visual.size];
}

function normalizeVisualLayouts(
  source: DashboardVisualData[]
): DashboardVisualData[] {
  let cursorX = 0;
  let cursorY = 0;
  let rowHeight = 0;

  return source.map((visual) => {
    const defaults =
      defaultVisualCanvasSize(visual);

    const width =
      visual.canvas_width ??
      defaults.width;
    const height =
      visual.canvas_height ??
      defaults.height;

    const hasSavedLayout =
      visual.canvas_x !== null &&
      visual.canvas_x !== undefined &&
      visual.canvas_y !== null &&
      visual.canvas_y !== undefined &&
      visual.canvas_width !== null &&
      visual.canvas_width !== undefined &&
      visual.canvas_height !== null &&
      visual.canvas_height !== undefined;

    if (hasSavedLayout) {
      return {
        ...visual,
        canvas_width: width,
        canvas_height: height,
        value_label_font_size:
          visual.visual_type === "kpi" &&
          (visual.value_label_font_size ?? 8) <= 8
            ? 30
            : visual.value_label_font_size,
      };
    }

    if (
      cursorX > 0 &&
      cursorX + width >
        DASHBOARD_CANVAS_MIN_WIDTH
    ) {
      cursorX = 0;
      cursorY +=
        rowHeight +
        DASHBOARD_VISUAL_GAP;
      rowHeight = 0;
    }

    let x = cursorX;

    if (visual.grid_column) {
      const legacyX =
        Math.round(
          (
            (visual.grid_column - 1) /
            12
          ) *
          DASHBOARD_CANVAS_MIN_WIDTH
        );

      x = Math.min(
        legacyX,
        Math.max(
          0,
          DASHBOARD_CANVAS_MIN_WIDTH -
            width
        )
      );
    }

    const normalized = {
      ...visual,
      canvas_x: x,
      canvas_y: cursorY,
      canvas_width: width,
      canvas_height: height,
      value_label_font_size:
        visual.visual_type === "kpi"
          ? (
              visual.value_label_font_size &&
              visual.value_label_font_size > 8
                ? visual.value_label_font_size
                : 30
            )
          : visual.value_label_font_size,
    };

    cursorX =
      x +
      width +
      DASHBOARD_VISUAL_GAP;
    rowHeight =
      Math.max(
        rowHeight,
        height
      );

    return normalized;
  });
}

function snapCanvasValue(
  value: number,
  enabled: boolean
) {
  if (!enabled) {
    return Math.round(value);
  }

  return (
    Math.round(
      value /
        DASHBOARD_GRID_SIZE
    ) *
    DASHBOARD_GRID_SIZE
  );
}


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

  const [
    search,
    setSearch,
  ] = useState("");

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
          {options.length > 10 && (
            <input
              className="dashboard-select-search"
              type="search"
              value={search}
              placeholder="Search..."
              onClick={(event) =>
                event.stopPropagation()
              }
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
            />
          )}

          {options
            .filter(
              (option) =>
                option.label
                  .toLowerCase()
                  .includes(
                    search
                      .trim()
                      .toLowerCase()
                  )
            )
            .map(
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

function DashboardMultiSelect({
  values,
  selected,
  onChange,
}: {
  values: string[];
  selected: string[];
  onChange: (
    values: string[]
  ) => void;
}) {
  const [
    open,
    setOpen,
  ] = useState(false);

  const [
    search,
    setSearch,
  ] = useState("");

  const visible =
    values.filter(
      (value) =>
        value
          .toLowerCase()
          .includes(
            search
              .trim()
              .toLowerCase()
          )
    );

  const allSelected =
    values.length > 0 &&
    selected.length ===
      values.length;

  return (
    <div
      className={
        "dashboard-multi-select" +
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
      >
        <span>
          {selected.length === 0
            ? "All"
            : (
                selected.length === 1
                  ? selected[0]
                  : (
                      selected.length +
                      " selected"
                    )
              )}
        </span>

        <span>
          ▾
        </span>
      </button>

      {open && (
        <div className="dashboard-multi-select-menu">
          <input
            type="search"
            value={search}
            placeholder="Search values"
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
          />

          <div className="dashboard-multi-select-actions">
            <button
              type="button"
              onClick={() =>
                onChange(
                  allSelected
                    ? []
                    : [...values]
                )
              }
            >
              {allSelected
                ? "Clear all"
                : "Select all"}
            </button>

            <button
              type="button"
              onClick={() =>
                onChange([])
              }
            >
              All
            </button>
          </div>

          <div className="dashboard-multi-select-options">
            {visible.map(
              (value) => {
                const checked =
                  selected.includes(
                    value
                  );

                return (
                  <label
                    key={value}
                  >
                    <input
                      type="checkbox"
                      checked={
                        checked
                      }
                      onChange={() =>
                        onChange(
                          checked
                            ? selected.filter(
                                (item) =>
                                  item !==
                                  value
                              )
                            : [
                                ...selected,
                                value,
                              ]
                        )
                      }
                    />

                    <span>
                      {value}
                    </span>
                  </label>
                );
              }
            )}
          </div>
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
        "alphabetical" ||
        sortMode ===
        "chronological"
      ) {
        return String(
          left.value ?? ""
        ).localeCompare(
          String(
            right.value ?? ""
          ),
          undefined,
          {
            numeric:
              sortMode ===
              "chronological",
          }
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

function buildDashboardTooltip(
  template: string | null | undefined,
  analysis: AnalysisResultData,
  row: AnalysisResultData["grouped_results"][number],
): string {
  const semantic =
    Boolean(
      analysis.kpi_code
    );

  const value =
    semantic
      ? row.metric_value
      : row.mean;

  const fallback =
    "{category}\n{measure}: {value}\nRecords: {count}";

  return (
    template ||
    fallback
  )
    .replaceAll(
      "{category}",
      String(
        row.value ??
        "Missing"
      )
    )
    .replaceAll(
      "{measure}",
      analysis.measure
    )
    .replaceAll(
      "{value}",
      formatNumber(
        value
      )
    )
    .replaceAll(
      "{count}",
      formatNumber(
        row.count
      )
    );
}


function DashboardKpiVisual({
  analysis,
  accentColor,
  label,
  showSecondary,
  labelFontSize,
  labelBold,
  labelColor,
  valueAlignment,
  verticalAlignment,
}: {
  analysis: AnalysisResultData;
  accentColor: string;
  label: string | null;
  showSecondary: boolean;
  labelFontSize: number;
  labelBold: boolean;
  labelColor: string;
  valueAlignment: "left" | "center" | "right";
  verticalAlignment: "top" | "center" | "bottom";
}) {
  const secondary =
    analysis.dimension
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
        );

  return (
    <div
      className={
        "dashboard-kpi-visual align-" +
        valueAlignment +
        " valign-" +
        verticalAlignment
      }
      style={{
        "--dashboard-accent":
          accentColor,
        "--dashboard-kpi-label-size":
          labelFontSize + "px",
        "--dashboard-kpi-label-weight":
          labelBold ? 700 : 500,
        "--dashboard-kpi-label-color":
          labelColor,
      } as CSSProperties}
    >
      <strong data-format-target="value">
        {formatNumber(
          getMetricValue(
            analysis
          )
        )}
      </strong>

      {label && (
        <span
          className="dashboard-kpi-label"
        >
          {label}
        </span>
      )}

      {showSecondary && (
        <small className="dashboard-kpi-secondary">
          {secondary}
        </small>
      )}
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
  tooltipTemplate,
  selectedValue,
  onSelect,
  containerWidth,
  containerHeight,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  accentColor: string;
  xAxisTitle: string | null;
  yAxisTitle: string | null;
  showValues: boolean;
  tooltipTemplate?: string | null;
  selectedValue?: string | null;
  onSelect?: (
    value: unknown
  ) => void;
  containerWidth: number;
  containerHeight: number;
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

  const compact =
    containerWidth < 360 ||
    containerHeight < 220;

  const veryCompact =
    containerWidth < 290 ||
    containerHeight < 185;

  return (
    <div
      className={
        "dashboard-bar-chart" +
        (compact ? " compact" : "") +
        (veryCompact ? " very-compact" : "")
      }
      style={{
        "--dashboard-accent":
          accentColor,
        "--dashboard-bar-row-gap":
          Math.max(
            3,
            Math.min(
              7,
              Math.floor(
                containerHeight /
                Math.max(
                  rows.length + 3,
                  1
                ) /
                3
              )
            )
          ) + "px",
      } as CSSProperties}
    >
      {!veryCompact &&
        (xAxisTitle || yAxisTitle) && (
        <div className="dashboard-axis-summary">
          {xAxisTitle && (
            <span data-format-target="axis">
              Category: {xAxisTitle}
            </span>
          )}

          {yAxisTitle && (
            <span data-format-target="axis">
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
              className={
                "dashboard-bar-row" +
                (
                  selectedValue ===
                  String(
                    row.value
                  )
                    ? " selected"
                    : ""
                )
              }
              onClick={() =>
                onSelect?.(
                  row.value
                )
              }
              title={
                buildDashboardTooltip(
                  tooltipTemplate,
                  analysis,
                  row,
                )
              }
            >
              <span
                data-format-target="category"
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
                <strong data-format-target="value">
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
  showGridlines,
  tooltipTemplate,
  selectedValue,
  onSelect,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  accentColor: string;
  xAxisTitle: string | null;
  yAxisTitle: string | null;
  showValues: boolean;
  showGridlines: boolean;
  tooltipTemplate?: string | null;
  selectedValue?: string | null;
  onSelect?: (
    value: unknown
  ) => void;
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
          row,
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
      className={
        "dashboard-line-chart" +
        (
          showGridlines
            ? " with-gridlines"
            : ""
        )
      }
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
              r={
                selectedValue ===
                String(
                  point.row.value
                )
                  ? "2.6"
                  : "1.6"
              }
              className={
                selectedValue ===
                String(
                  point.row.value
                )
                  ? "selected"
                  : ""
              }
              onClick={() =>
                onSelect?.(
                  point.row.value
                )
              }
              vectorEffect="non-scaling-stroke"
            >
              <title>
                {buildDashboardTooltip(
                  tooltipTemplate,
                  analysis,
                  point.row,
                )}
              </title>
            </circle>
          )
        )}
      </svg>

      <div
        className="dashboard-line-axis"
        data-format-target="axis"
      >
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
        <div
          className="dashboard-line-measure-label"
          data-format-target="axis"
        >
          {yAxisTitle}
        </div>
      )}

      {showValues && points.length > 0 && (
        <div
          className="dashboard-line-value-summary"
          data-format-target="value"
        >
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

function DashboardColumnVisual({
  analysis,
  rows,
  accentColor,
  showValues,
  showGridlines,
  tooltipTemplate,
  selectedValue,
  onSelect,
  containerWidth,
  containerHeight,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  accentColor: string;
  showValues: boolean;
  showGridlines: boolean;
  tooltipTemplate?: string | null;
  selectedValue?: string | null;
  onSelect?: (
    value: unknown
  ) => void;
  containerWidth: number;
  containerHeight: number;
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
      ...values.map(
        (value) =>
          Math.abs(value)
      ),
      1
    );

  const compact =
    containerWidth < 360 ||
    containerHeight < 230;

  const veryCompact =
    containerWidth < 290 ||
    containerHeight < 190;

  return (
    <div
      className={
        "dashboard-column-chart" +
        (
          showGridlines
            ? " with-gridlines"
            : ""
        )
      }
      style={{
        "--dashboard-accent":
          accentColor,
        "--dashboard-column-height":
          Math.max(
            72,
            containerHeight - 82
          ) + "px",
      } as CSSProperties}
    >
      {rows.map(
        (row, index) => {
          const value =
            values[index];

          const height =
            Math.max(
              3,
              (
                Math.abs(value) /
                maxValue
              ) * 100
            );

          return (
            <div
              key={
                String(row.value) +
                "-" +
                index
              }
              className={
                "dashboard-column-item dashboard-tooltip-host" +
                (compact ? " compact" : "") +
                (veryCompact ? " very-compact" : "") +
                (
                  selectedValue ===
                  String(
                    row.value
                  )
                    ? " selected"
                    : ""
                )
              }
              onClick={() =>
                onSelect?.(
                  row.value
                )
              }
              data-tooltip={
                buildDashboardTooltip(
                  tooltipTemplate,
                  analysis,
                  row,
                )
              }
            >
              {showValues && (
                <strong data-format-target="value">
                  {formatNumber(
                    value
                  )}
                </strong>
              )}

              <div className="dashboard-column-track">
                <div
                  className="dashboard-column-value"
                  style={{
                    height:
                      height + "%",
                  }}
                />
              </div>

              <span data-format-target="category">
                {String(
                  row.value ??
                  "Missing"
                )}
              </span>
            </div>
          );
        }
      )}
    </div>
  );
}


function DashboardAreaVisual({
  analysis,
  rows,
  accentColor,
  showValues,
  showGridlines,
  tooltipTemplate,
  selectedValue,
  onSelect,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  accentColor: string;
  showValues: boolean;
  showGridlines: boolean;
  tooltipTemplate?: string | null;
  selectedValue?: string | null;
  onSelect?: (
    value: unknown
  ) => void;
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
      (row, index) => ({
        row,
        x:
          orderedRows.length <= 1
            ? 50
            : (
                index /
                (
                  orderedRows.length -
                  1
                )
              ) * 100,
        y:
          88 -
          (
            (
              values[index] - min
            ) /
            range
          ) * 76,
        value:
          values[index],
      })
    );

  const polygon =
    [
      "0,92",
      ...points.map(
        (point) =>
          point.x +
          "," +
          point.y
      ),
      "100,92",
    ].join(" ");

  return (
    <div
      className={
        "dashboard-area-chart" +
        (
          showGridlines
            ? " with-gridlines"
            : ""
        )
      }
      style={{
        "--dashboard-accent":
          accentColor,
      } as CSSProperties}
    >
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <polygon
          points={polygon}
          className="dashboard-area-fill"
        />

        <polyline
          points={
            points
              .map(
                (point) =>
                  point.x +
                  "," +
                  point.y
              )
              .join(" ")
          }
          fill="none"
          vectorEffect="non-scaling-stroke"
        />

        {points.map(
          (point, index) => (
            <circle
              key={index}
              cx={point.x}
              cy={point.y}
              r={
                selectedValue ===
                String(
                  point.row.value
                )
                  ? "2.6"
                  : "1.6"
              }
              className={
                selectedValue ===
                String(
                  point.row.value
                )
                  ? "selected"
                  : ""
              }
              onClick={() =>
                onSelect?.(
                  point.row.value
                )
              }
              vectorEffect="non-scaling-stroke"
            >
              <title>
                {buildDashboardTooltip(
                  tooltipTemplate,
                  analysis,
                  point.row,
                )}
              </title>
            </circle>
          )
        )}
      </svg>

      <div
        className="dashboard-line-axis"
        data-format-target="axis"
      >
        <span>
          {String(
            orderedRows[0]
              ?.value ?? ""
          )}
        </span>

        <span>
          {String(
            orderedRows[
              orderedRows.length - 1
            ]?.value ?? ""
          )}
        </span>
      </div>

      {showValues &&
        points.length > 0 && (
        <div
          className="dashboard-line-value-summary"
          data-format-target="value"
        >
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


function DashboardPieVisual({
  analysis,
  rows,
  accentColor,
  donut,
  showValues,
  showLegend,
  tooltipTemplate,
  selectedValue,
  onSelect,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  accentColor: string;
  donut: boolean;
  showValues: boolean;
  showLegend: boolean;
  tooltipTemplate?: string | null;
  selectedValue?: string | null;
  onSelect?: (
    value: unknown
  ) => void;
}) {
  const [
    hoveredSegment,
    setHoveredSegment,
  ] = useState<number | null>(
    null
  );

  const semantic =
    Boolean(
      analysis.kpi_code
    );

  const palette = [
    accentColor,
    "#7c5ce6",
    "#e8873a",
    "#0f9f8f",
    "#52677f",
    "#d95f76",
    "#e0b43c",
    "#5d8fd8",
  ];

  const values =
    rows.map(
      (row) =>
        Math.max(
          0,
          (
            semantic
              ? row.metric_value
              : row.mean
          ) ?? 0
        )
    );

  const total =
    values.reduce(
      (sum, value) =>
        sum + value,
      0
    ) || 1;

  let cursor = 0;

  const segments =
    rows.map(
      (row, index) => {
        const start =
          cursor;

        const percent =
          (
            values[index] /
            total
          ) * 100;

        cursor += percent;

        return {
          row,
          color:
            palette[
              index %
              palette.length
            ],
          start,
          end:
            cursor,
          percent,
        };
      }
    );

  const gradient =
    segments
      .map(
        (segment) =>
          segment.color +
          " " +
          segment.start +
          "% " +
          segment.end +
          "%"
      )
      .join(", ");

  return (
    <div className="dashboard-pie-layout">
      <div
        className={
          (
            donut
              ? "dashboard-pie-chart donut"
              : "dashboard-pie-chart"
          ) +
          (
            selectedValue
              ? " has-selection"
              : ""
          )
        }
        style={{
          background:
            "conic-gradient(" +
            gradient +
            ")",
        }}
        onMouseMove={(event) => {
          const rect =
            event.currentTarget
              .getBoundingClientRect();

          const centerX =
            rect.left +
            rect.width / 2;

          const centerY =
            rect.top +
            rect.height / 2;

          const x =
            event.clientX -
            centerX;

          const y =
            event.clientY -
            centerY;

          const radius =
            Math.sqrt(
              x * x +
              y * y
            );

          if (
            donut &&
            radius <
              rect.width *
              0.24
          ) {
            setHoveredSegment(
              null
            );

            return;
          }

          const angle =
            (
              Math.atan2(
                y,
                x
              ) *
              180 /
              Math.PI +
              450
            ) % 360;

          const percent =
            angle /
            360 *
            100;

          const index =
            segments.findIndex(
              (segment) =>
                percent >=
                  segment.start &&
                percent <
                  segment.end
            );

          setHoveredSegment(
            index >= 0
              ? index
              : null
          );
        }}
        onMouseLeave={() =>
          setHoveredSegment(
            null
          )
        }
        onClick={() => {
          if (
            hoveredSegment === null
          ) {
            return;
          }

          onSelect?.(
            segments[
              hoveredSegment
            ].row.value
          );
        }}
      >
        {hoveredSegment !== null && (
          <div className="dashboard-pie-tooltip">
            {buildDashboardTooltip(
              tooltipTemplate,
              analysis,
              segments[
                hoveredSegment
              ].row,
            )}
          </div>
        )}

        {donut && (
          <div className="dashboard-donut-hole">
            <strong>
              {formatNumber(
                total
              )}
            </strong>
          </div>
        )}
      </div>

      {showLegend && (
        <div className="dashboard-pie-legend">
          {segments.map(
            (segment, index) => (
              <div
                key={
                  String(
                    segment.row.value
                  ) +
                  "-" +
                  index
                }
                className={
                  "dashboard-tooltip-host" +
                  (
                    selectedValue ===
                    String(
                      segment.row.value
                    )
                      ? " selected"
                      : ""
                  )
                }
                onClick={() =>
                  onSelect?.(
                    segment.row.value
                  )
                }
                data-tooltip={
                  buildDashboardTooltip(
                    tooltipTemplate,
                    analysis,
                    segment.row,
                  )
                }
              >
                <i
                  style={{
                    background:
                      segment.color,
                  }}
                />

                <span data-format-target="legend">
                  {String(
                    segment.row.value ??
                    "Missing"
                  )}
                </span>

                {showValues && (
                  <strong data-format-target="value">
                    {
                      segment.percent
                        .toFixed(1)
                    }%
                  </strong>
                )}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}


function DashboardTableVisual({
  analysis,
  rows,
  selectedValue,
  onSelect,
}: {
  analysis: AnalysisResultData;
  rows: AnalysisResultData[
    "grouped_results"
  ];
  selectedValue?: string | null;
  onSelect?: (
    value: unknown
  ) => void;
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
                className={
                  selectedValue ===
                  String(
                    row.value
                  )
                    ? "selected"
                    : ""
                }
                onClick={() =>
                  onSelect?.(
                    row.value
                  )
                }
              >
                <td data-format-target="category">
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

                <td data-format-target="value">
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
  savedFilters,
  loading,
  error,
  onPreview,
  onLoadFilterValues,
  onSave,
}: Props) {
  const [
    visuals,
    setVisuals,
  ] = useState<
    DashboardVisualData[]
  >(
    normalizeVisualLayouts(
      savedVisuals
    )
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
    dashboardFilters,
    setDashboardFilters,
  ] = useState<
    DashboardFilterData[]
  >(
    savedFilters
  );


  const [
    crossFilters,
    setCrossFilters,
  ] = useState<
    DashboardCrossFilterData[]
  >([]);

  const [
    filterValues,
    setFilterValues,
  ] = useState<
    Record<
      string,
      string[]
    >
  >({});

  const [
    pendingFilterKey,
    setPendingFilterKey,
  ] = useState(
    ""
  );

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

  const [
    propertiesPanelOpen,
    setPropertiesPanelOpen,
  ] = useState(false);


  const [
    dashboardMode,
    setDashboardMode,
  ] = useState<
    "interact" | "edit"
  >("interact");

  const [
    formatTarget,
    setFormatTarget,
  ] = useState<
    | "visual"
    | "title"
    | "subtitle"
    | "category"
    | "value"
    | "axis"
    | "legend"
  >("visual");

  const [
    showCanvasGrid,
    setShowCanvasGrid,
  ] = useState(true);

  const savedVisualsSignature =
    JSON.stringify(
      savedVisuals
    );

  const savedFiltersSignature =
    JSON.stringify(
      savedFilters
    );

  useEffect(
    () => {
      setVisuals(
        normalizeVisualLayouts(
          savedVisuals
        )
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

      setDashboardFilters(
        savedFilters
      );
    },
    [
      savedVisualsSignature,
      savedTitle,
      savedSubtitle,
      savedTheme,
      savedFiltersSignature,
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
      ? (
          previewResults[
            editingVisual.visual_id
          ] ??
          analyses.find(
            (analysis) =>
              analysis.analysis_id ===
              editingVisual.analysis_id
          ) ??
          null
        )
      : null;


  const editingKpiDefinition =
    editingVisual
      ? kpiDefinitions.find(
          (item) =>
            item.code ===
            (
              editingVisual.kpi_code ??
              editingAnalysis?.kpi_code
            )
        ) ?? null
      : null;

  const editingDimension =
    editingVisual?.dimension ??
    editingAnalysis?.dimension ??
    null;

  const editingIsTime =
    isTimeDimension(
      editingDimension
    );

  const editingHasAxes =
    Boolean(
      editingVisual &&
      [
        "bar",
        "column",
        "line",
        "area",
      ].includes(
        editingVisual.visual_type
      )
    );

  const editingIsPie =
    Boolean(
      editingVisual &&
      [
        "pie",
        "donut",
      ].includes(
        editingVisual.visual_type
      )
    );

  const editingHasGroups =
    Boolean(
      editingAnalysis &&
      editingAnalysis.grouped_results.length > 0
    );

  const editingNonAdditivePie =
    Boolean(
      editingIsPie &&
      editingKpiDefinition &&
      ![
        "sum",
        "count",
      ].includes(
        editingKpiDefinition.aggregation ??
        ""
      )
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


  const dimensionOptions =
    useMemo(
      () => {
        if (!dataModelStudio) {
          return [];
        }

        return dataModelStudio.tables
          .filter(
            (table) =>
              table.table_type ===
              "dimension"
          )
          .flatMap(
            (table) =>
              table.columns
                .filter(
                  (column) =>
                    [
                      "key",
                      "dimension",
                      "attribute",
                      "time",
                    ].includes(
                      column.role
                    )
                )
                .map(
                  (column) => ({
                    value:
                      table.name +
                      "." +
                      column.name,
                    table:
                      table.name,
                    column:
                      column.name,
                    label:
                      column.name +
                      " · " +
                      table.name,
                  })
                )
          );
      },
      [dataModelStudio]
    );


  useEffect(
    () => {
      let cancelled =
        false;

      async function restoreFilters() {
        for (
          const filter
          of savedFilters
        ) {
          try {
            const values =
              await onLoadFilterValues(
                filter.table,
                filter.column,
              );

            if (cancelled) {
              return;
            }

            setFilterValues(
              (previous) => ({
                ...previous,
                [filter.filter_id]:
                  values,
              })
            );
          } catch {
            // Keep the dashboard usable if one slicer
            // cannot load its distinct values.
          }
        }

        if (
          savedFilters.some(
            (filter) =>
              (
                  filter.value !== null ||
                  (filter.values?.length ?? 0) > 0
                )
          )
        ) {
          for (
            const visual
            of savedVisuals
          ) {
            const sourceAnalysis =
              visual.analysis_id
                ? analyses.find(
                    (analysis) =>
                      analysis.analysis_id ===
                      visual.analysis_id
                  )
                : undefined;

            const kpiCode =
              visual.kpi_code ??
              sourceAnalysis?.kpi_code;

            if (!kpiCode) {
              continue;
            }

            try {
              const result =
                await onPreview(
                  kpiCode,
                  visual.dimension_table ??
                    sourceAnalysis?.dimension_table ??
                    null,
                  visual.dimension ??
                    sourceAnalysis?.dimension ??
                    null,
                  savedFilters,
                );

              if (cancelled) {
                return;
              }

              setPreviewResults(
                (previous) => ({
                  ...previous,
                  [visual.visual_id]:
                    result,
                })
              );
            } catch {
              // Per-visual errors remain available when
              // the user changes a slicer interactively.
            }
          }
        }
      }

      void restoreFilters();

      return () => {
        cancelled = true;
      };
    },
    [
      savedFilters,
      savedVisuals,
      analyses,
      onLoadFilterValues,
      onPreview,
    ]
  );

  async function refreshVisualPreview(
    visualId: string,
    kpiCode: string,
    dimensionTable: string | null,
    dimension: string | null,
    filters?: DashboardFilterData[],
  ) {
    const effectiveFilters =
      filters ??
      [
        ...dashboardFilters,
        ...crossFilters
          .filter(
            (filter) =>
              filter.source_visual_id !==
              visualId
          )
          .map(
            (filter) => ({
              filter_id:
                filter.filter_id,
              table:
                filter.table,
              column:
                filter.column,
              label:
                filter.label,
              value:
                filter.value,
            })
          ),
      ];
    setPreviewErrors(
      (previous) => ({
        ...previous,
        [visualId]: "",
      })
    );

    try {
      const result =
        await onPreview(
          kpiCode,
          dimensionTable,
          dimension,
          effectiveFilters,
        );

      setPreviewResults(
        (previous) => ({
          ...previous,
          [visualId]: result,
        })
      );

      return result;

    } catch (error) {
      setPreviewErrors(
        (previous) => ({
          ...previous,
          [visualId]:
            error instanceof Error
              ? error.message
              : "Preview could not be refreshed.",
        })
      );

      return null;
    }
  }

  async function ensureFilterValues(
    filter:
      DashboardFilterData
  ) {
    if (
      filterValues[
        filter.filter_id
      ]
    ) {
      return;
    }

    const values =
      await onLoadFilterValues(
        filter.table,
        filter.column,
      );

    setFilterValues(
      (previous) => ({
        ...previous,
        [filter.filter_id]:
          values,
      })
    );
  }

  async function refreshAllVisuals(
    nextFilters:
      DashboardFilterData[],
    nextCrossFilters:
      DashboardCrossFilterData[] =
        crossFilters,
  ) {
    await Promise.all(
      visuals.map(
        async (visual) => {
          const sourceAnalysis =
            previewResults[
              visual.visual_id
            ] ??
            (
              visual.analysis_id
                ? analysesById.get(
                    visual.analysis_id
                  )
                : undefined
            );

          const kpiCode =
            visual.kpi_code ??
            sourceAnalysis?.kpi_code;

          if (!kpiCode) {
            return;
          }

          const interactionFilters:
            DashboardFilterData[] =
              nextCrossFilters
                .filter(
                  (filter) =>
                    filter.source_visual_id !==
                    visual.visual_id
                )
                .map(
                  (filter) => ({
                    filter_id:
                      filter.filter_id,
                    table:
                      filter.table,
                    column:
                      filter.column,
                    label:
                      filter.label,
                    value:
                      filter.value,
                  })
                );

          await refreshVisualPreview(
            visual.visual_id,
            kpiCode,
            visual.dimension_table ??
              sourceAnalysis?.dimension_table ??
              null,
            visual.dimension ??
              sourceAnalysis?.dimension ??
              null,
            [
              ...nextFilters,
              ...interactionFilters,
            ],
          );
        }
      )
    );
  }

  async function addDashboardFilter() {
    const option =
      dimensionOptions.find(
        (item) =>
          item.value ===
          pendingFilterKey
      );

    if (!option) {
      return;
    }

    const existing =
      dashboardFilters.find(
        (item) =>
          item.table ===
            option.table &&
          item.column ===
            option.column
      );

    if (existing) {
      await ensureFilterValues(
        existing
      );

      return;
    }

    const filter:
      DashboardFilterData = {
        filter_id:
          (
            globalThis.crypto
              ?.randomUUID?.()
          ) ??
          (
            "filter-" +
            Date.now()
          ),
        table:
          option.table,
        column:
          option.column,
        label:
          option.column,
        value:
          null,
        values: [],
      };

    const nextFilters = [
      ...dashboardFilters,
      filter,
    ];

    setDashboardFilters(
      nextFilters
    );

    setPendingFilterKey(
      ""
    );

    await ensureFilterValues(
      filter
    );
  }

  async function setDashboardFilterValues(
    filterId: string,
    values: string[],
  ) {
    const nextFilters =
      dashboardFilters.map(
        (filter) =>
          filter.filter_id ===
          filterId
            ? {
                ...filter,
                values,
                value:
                  values.length === 1
                    ? values[0]
                    : null,
              }
            : filter
      );

    setDashboardFilters(
      nextFilters
    );

    await refreshAllVisuals(
      nextFilters
    );
  }

  async function removeDashboardFilter(
    filterId: string
  ) {
    const nextFilters =
      dashboardFilters.filter(
        (filter) =>
          filter.filter_id !==
          filterId
      );

    setDashboardFilters(
      nextFilters
    );

    await refreshAllVisuals(
      nextFilters
    );
  }

  async function clearDashboardFilters() {
    const nextFilters =
      dashboardFilters.map(
        (filter) => ({
          ...filter,
          value: null,
          values: [],
        })
      );

    setDashboardFilters(
      nextFilters
    );

    setCrossFilters(
      []
    );

    await refreshAllVisuals(
      nextFilters,
      [],
    );
  }

  async function toggleCrossFilter(
    sourceVisualId: string,
    table: string | null | undefined,
    column: string | null | undefined,
    value: unknown,
  ) {
    if (
      !table ||
      !column ||
      value === null ||
      value === undefined
    ) {
      return;
    }

    const normalizedValue =
      String(value);

    const current =
      crossFilters.find(
        (filter) =>
          filter.source_visual_id ===
          sourceVisualId
      );

    const nextCrossFilters =
      (
        current &&
        current.table === table &&
        current.column === column &&
        current.value ===
          normalizedValue
      )
        ? crossFilters.filter(
            (filter) =>
              filter.source_visual_id !==
              sourceVisualId
          )
        : [
            ...crossFilters.filter(
              (filter) =>
                filter.source_visual_id !==
                sourceVisualId
            ),
            {
              filter_id:
                "cross-" +
                sourceVisualId,
              source_visual_id:
                sourceVisualId,
              table,
              column,
              label:
                column,
              value:
                normalizedValue,
            },
          ];

    setCrossFilters(
      nextCrossFilters
    );

    await refreshAllVisuals(
      dashboardFilters,
      nextCrossFilters,
    );
  }

  async function removeCrossFilter(
    sourceVisualId: string
  ) {
    const nextCrossFilters =
      crossFilters.filter(
        (filter) =>
          filter.source_visual_id !==
          sourceVisualId
      );

    setCrossFilters(
      nextCrossFilters
    );

    await refreshAllVisuals(
      dashboardFilters,
      nextCrossFilters,
    );
  }

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
      kpi_code:
        analysis.kpi_code ??
        null,
      dimension_table:
        analysis.dimension_table ??
        null,
      dimension:
        analysis.dimension ??
        null,
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
      auto_title: true,
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
      show_legend: true,
      show_gridlines: true,
      animate: true,
      title_alignment: "left",
      kpi_label: null,
      kpi_label_font_size: 10,
      kpi_label_bold: false,
      kpi_label_color: null,
      kpi_show_secondary: false,
      kpi_value_alignment: "center",
      kpi_vertical_alignment: "center",
      tooltip_template:
        "{category}\n{measure}: {value}\nRecords: {count}",
      grid_column: null,
      title_font_size: 10,
      title_bold: true,
      title_color: null,
      subtitle_font_size: 7,
      subtitle_bold: false,
      subtitle_color: null,
      category_label_font_size: 8,
      category_label_bold: false,
      category_label_color: null,
      value_label_font_size:
        visualType === "kpi"
          ? 30
          : 8,
      value_label_bold: true,
      value_label_color: null,
      axis_label_font_size: 8,
      axis_label_bold: false,
      axis_label_color: null,
      legend_label_font_size: 8,
      legend_label_bold: false,
      legend_label_color: null,
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
      (previous) =>
        normalizeVisualLayouts(
          [
            ...previous,
            visual,
          ]
        )
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
          (analysis) =>
            createVisual(
              analysis
            )
        )
        .filter(
          (
            visual,
          ): visual is
            DashboardVisualData =>
              visual !== null
        );

    setVisuals(
      normalizeVisualLayouts(
        next
      )
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

  async function removeVisual(
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
      setPropertiesPanelOpen(
        false
      );
    }

    if (
      crossFilters.some(
        (filter) =>
          filter.source_visual_id ===
          visualId
      )
    ) {
      const nextCrossFilters =
        crossFilters.filter(
          (filter) =>
            filter.source_visual_id !==
            visualId
        );

      setCrossFilters(
        nextCrossFilters
      );

      await refreshAllVisuals(
        dashboardFilters,
        nextCrossFilters,
      );
    }
  }

  function resizeVisual(
    visual:
      DashboardVisualData,
    direction:
      "smaller" | "larger",
  ) {
    const step =
      direction === "larger"
        ? 48
        : -48;

    updateVisual(
      visual.visual_id,
      {
        canvas_width:
          snapCanvasValue(
            Math.max(
              visualMinWidth(
                visual
              ),
              (visual.canvas_width ?? 480) +
                step
            ),
            showCanvasGrid
          ),
        canvas_height:
          snapCanvasValue(
            Math.max(
              visualMinHeight(
                visual
              ),
              (visual.canvas_height ?? 300) +
                step
            ),
            showCanvasGrid
          ),
      }
    );
  }

  function duplicateVisual(
    visual:
      DashboardVisualData
  ) {
    const offset = 24;

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
          canvas_x:
            (visual.canvas_x ?? 0) +
            offset,
          canvas_y:
            (visual.canvas_y ?? 0) +
            offset,
        },
      ]
    );
  }

  function updateFormatTargetStyle(
    patch: {
      fontSize?: number;
      bold?: boolean;
      color?: string | null;
    }
  ) {
    if (!editingVisual) {
      return;
    }

    const clamp = (
      value: number,
      min: number,
      max: number,
    ) =>
      Math.max(
        min,
        Math.min(
          max,
          value
        )
      );

    if (
      formatTarget ===
      "title"
    ) {
      updateVisual(
        editingVisual.visual_id,
        {
          title_font_size:
            patch.fontSize ===
            undefined
              ? editingVisual.title_font_size
              : clamp(
                  patch.fontSize,
                  7,
                  28,
                ),
          title_bold:
            patch.bold ??
            editingVisual.title_bold,
          title_color:
            patch.color ===
            undefined
              ? editingVisual.title_color
              : patch.color,
        }
      );
    }

    if (
      formatTarget ===
      "subtitle"
    ) {
      updateVisual(
        editingVisual.visual_id,
        {
          subtitle_font_size:
            patch.fontSize ===
            undefined
              ? editingVisual.subtitle_font_size
              : clamp(
                  patch.fontSize,
                  6,
                  20,
                ),
          subtitle_bold:
            patch.bold ??
            editingVisual.subtitle_bold,
          subtitle_color:
            patch.color ===
            undefined
              ? editingVisual.subtitle_color
              : patch.color,
        }
      );
    }

    if (
      formatTarget ===
      "category"
    ) {
      updateVisual(
        editingVisual.visual_id,
        {
          category_label_font_size:
            patch.fontSize ===
            undefined
              ? editingVisual.category_label_font_size
              : clamp(
                  patch.fontSize,
                  6,
                  22,
                ),
          category_label_bold:
            patch.bold ??
            editingVisual.category_label_bold,
          category_label_color:
            patch.color ===
            undefined
              ? editingVisual.category_label_color
              : patch.color,
        }
      );
    }

    if (
      formatTarget ===
      "value"
    ) {
      updateVisual(
        editingVisual.visual_id,
        {
          value_label_font_size:
            patch.fontSize ===
            undefined
              ? editingVisual.value_label_font_size
              : clamp(
                  patch.fontSize,
                  6,
                  editingVisual.visual_type === "kpi"
                    ? 64
                    : 22,
                ),
          value_label_bold:
            patch.bold ??
            editingVisual.value_label_bold,
          value_label_color:
            patch.color ===
            undefined
              ? editingVisual.value_label_color
              : patch.color,
        }
      );
    }

    if (
      formatTarget ===
      "axis"
    ) {
      updateVisual(
        editingVisual.visual_id,
        {
          axis_label_font_size:
            patch.fontSize ===
            undefined
              ? editingVisual.axis_label_font_size
              : clamp(
                  patch.fontSize,
                  6,
                  20,
                ),
          axis_label_bold:
            patch.bold ??
            editingVisual.axis_label_bold,
          axis_label_color:
            patch.color ===
            undefined
              ? editingVisual.axis_label_color
              : patch.color,
        }
      );
    }

    if (
      formatTarget ===
      "legend"
    ) {
      updateVisual(
        editingVisual.visual_id,
        {
          legend_label_font_size:
            patch.fontSize ===
            undefined
              ? editingVisual.legend_label_font_size
              : clamp(
                  patch.fontSize,
                  6,
                  20,
                ),
          legend_label_bold:
            patch.bold ??
            editingVisual.legend_label_bold,
          legend_label_color:
            patch.color ===
            undefined
              ? editingVisual.legend_label_color
              : patch.color,
        }
      );
    }
  }

  function currentFormatStyle() {
    if (!editingVisual) {
      return {
        fontSize: 8,
        bold: false,
        color: "#213854",
      };
    }

    if (
      formatTarget ===
      "title"
    ) {
      return {
        fontSize:
          editingVisual.title_font_size ??
          10,
        bold:
          editingVisual.title_bold ??
          true,
        color:
          editingVisual.title_color ??
          editingVisual.text_color,
      };
    }

    if (
      formatTarget ===
      "subtitle"
    ) {
      return {
        fontSize:
          editingVisual.subtitle_font_size ??
          7,
        bold:
          editingVisual.subtitle_bold ??
          false,
        color:
          editingVisual.subtitle_color ??
          editingVisual.text_color,
      };
    }

    if (
      formatTarget ===
      "category"
    ) {
      return {
        fontSize:
          editingVisual.category_label_font_size ??
          8,
        bold:
          editingVisual.category_label_bold ??
          false,
        color:
          editingVisual.category_label_color ??
          editingVisual.text_color,
      };
    }

    if (
      formatTarget ===
      "value"
    ) {
      return {
        fontSize:
          editingVisual.value_label_font_size ??
          8,
        bold:
          editingVisual.value_label_bold ??
          true,
        color:
          editingVisual.value_label_color ??
          editingVisual.text_color,
      };
    }

    if (
      formatTarget ===
      "axis"
    ) {
      return {
        fontSize:
          editingVisual.axis_label_font_size ??
          8,
        bold:
          editingVisual.axis_label_bold ??
          false,
        color:
          editingVisual.axis_label_color ??
          editingVisual.text_color,
      };
    }

    return {
      fontSize:
        editingVisual.legend_label_font_size ??
        8,
      bold:
        editingVisual.legend_label_bold ??
        false,
      color:
        editingVisual.legend_label_color ??
        editingVisual.text_color,
    };
  }

  function beginVisualMove(
    event:
      ReactPointerEvent<HTMLElement>,
    visual:
      DashboardVisualData
  ) {
    if (dashboardMode !== "edit") {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    setEditingVisualId(
      visual.visual_id
    );
    setFormatTarget("visual");

    const canvas =
      event.currentTarget.closest(
        ".dashboard-visual-grid"
      ) as HTMLElement | null;

    const canvasWidth =
      canvas?.clientWidth ??
      DASHBOARD_CANVAS_MIN_WIDTH;

    const pointerX = event.clientX;
    const pointerY = event.clientY;
    const startX =
      visual.canvas_x ?? 0;
    const startY =
      visual.canvas_y ?? 0;
    const width =
      visual.canvas_width ?? 480;

    const move = (
      moveEvent: PointerEvent
    ) => {
      const maxX =
        Math.max(
          0,
          canvasWidth - width
        );

      const nextX =
        Math.min(
          maxX,
          Math.max(
            0,
            snapCanvasValue(
              startX +
                moveEvent.clientX -
                pointerX,
              showCanvasGrid
            )
          )
        );

      const nextY =
        Math.max(
          0,
          snapCanvasValue(
            startY +
              moveEvent.clientY -
              pointerY,
            showCanvasGrid
          )
        );

      updateVisual(
        visual.visual_id,
        {
          canvas_x: nextX,
          canvas_y: nextY,
        }
      );
    };

    const stop = () => {
      globalThis.removeEventListener(
        "pointermove",
        move
      );
      globalThis.removeEventListener(
        "pointerup",
        stop
      );
    };

    globalThis.addEventListener(
      "pointermove",
      move
    );
    globalThis.addEventListener(
      "pointerup",
      stop
    );
  }

  function beginVisualResize(
    event:
      ReactPointerEvent<HTMLButtonElement>,
    visual:
      DashboardVisualData
  ) {
    if (dashboardMode !== "edit") {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    setEditingVisualId(
      visual.visual_id
    );
    setFormatTarget("visual");

    const canvas =
      event.currentTarget.closest(
        ".dashboard-visual-grid"
      ) as HTMLElement | null;

    const canvasWidth =
      canvas?.clientWidth ??
      DASHBOARD_CANVAS_MIN_WIDTH;

    const pointerX = event.clientX;
    const pointerY = event.clientY;
    const startWidth =
      visual.canvas_width ?? 480;
    const startHeight =
      visual.canvas_height ?? 300;
    const x =
      visual.canvas_x ?? 0;

    const move = (
      moveEvent: PointerEvent
    ) => {
      const minimumWidth =
        visualMinWidth(
          visual
        );
      const minimumHeight =
        visualMinHeight(
          visual
        );

      const maxWidth =
        Math.max(
          minimumWidth,
          canvasWidth - x
        );

      const nextWidth =
        Math.min(
          maxWidth,
          Math.max(
            minimumWidth,
            snapCanvasValue(
              startWidth +
                moveEvent.clientX -
                pointerX,
              showCanvasGrid
            )
          )
        );

      const nextHeight =
        Math.max(
          minimumHeight,
          snapCanvasValue(
            startHeight +
              moveEvent.clientY -
              pointerY,
            showCanvasGrid
          )
        );

      updateVisual(
        visual.visual_id,
        {
          canvas_width:
            nextWidth,
          canvas_height:
            nextHeight,
        }
      );
    };

    const stop = () => {
      globalThis.removeEventListener(
        "pointermove",
        move
      );
      globalThis.removeEventListener(
        "pointerup",
        stop
      );
    };

    globalThis.addEventListener(
      "pointermove",
      move
    );
    globalThis.addEventListener(
      "pointerup",
      stop
    );
  }

  function handleVisualKeyDown(
    event:
      KeyboardEvent<HTMLElement>,
    visual:
      DashboardVisualData
  ) {
    if (dashboardMode !== "edit") {
      return;
    }

    const delta =
      event.shiftKey
        ? 10
        : 1;

    const directions:
      Record<
        string,
        [number, number]
      > = {
        ArrowLeft: [-delta, 0],
        ArrowRight: [delta, 0],
        ArrowUp: [0, -delta],
        ArrowDown: [0, delta],
      };

    const direction =
      directions[event.key];

    if (!direction) {
      return;
    }

    event.preventDefault();

    const canvas =
      event.currentTarget.closest(
        ".dashboard-visual-grid"
      ) as HTMLElement | null;

    const canvasWidth =
      canvas?.clientWidth ??
      DASHBOARD_CANVAS_MIN_WIDTH;
    const width =
      visual.canvas_width ?? 480;
    const maxX =
      Math.max(
        0,
        canvasWidth - width
      );

    updateVisual(
      visual.visual_id,
      {
        canvas_x:
          Math.min(
            maxX,
            Math.max(
              0,
              (visual.canvas_x ?? 0) +
                direction[0]
            )
          ),
        canvas_y:
          Math.max(
            0,
            (visual.canvas_y ?? 0) +
              direction[1]
          ),
      }
    );
  }

  const canvasHeight =
    Math.max(
      DASHBOARD_CANVAS_MIN_HEIGHT,
      ...visuals.map(
        (visual) =>
          (visual.canvas_y ?? 0) +
          (visual.canvas_height ?? 300) +
          32
      )
    );

  const activeFormatStyle =
    currentFormatStyle();

  return (
    <section
      className={
        "personal-dashboard-builder mode-" +
        dashboardMode
      }
    >
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
                dashboardFilters,
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


      </div>

      <div
        className={
          "dashboard-slicer-toolbar mode-" +
          dashboardMode
        }
      >
        <div className="dashboard-slicer-heading">
          <div>
            <span className="workspace-overview-label">
              FILTERS / SLICERS
            </span>

            <strong>
              Filter the whole dashboard
            </strong>
          </div>

          <button
            type="button"
            className="dashboard-reset-button"
            disabled={
              !dashboardFilters.some(
                (filter) =>
                  (
                  filter.value !== null ||
                  (filter.values?.length ?? 0) > 0
                )
              ) &&
              crossFilters.length === 0
            }
            onClick={
              clearDashboardFilters
            }
          >
            Clear filters
          </button>
        </div>

        {dashboardMode === "edit" && (
        <div className="dashboard-slicer-builder">
          <DashboardSelect
            value={
              pendingFilterKey
            }
            options={[
              {
                value: "",
                label:
                  "Choose dimension",
              },
              ...dimensionOptions
                .filter(
                  (option) =>
                    !dashboardFilters.some(
                      (filter) =>
                        filter.table ===
                          option.table &&
                        filter.column ===
                          option.column
                    )
                )
                .map(
                  (option) => ({
                    value:
                      option.value,
                    label:
                      option.label,
                  })
                ),
            ]}
            onChange={
              setPendingFilterKey
            }
          />

          <button
            type="button"
            className="secondary-button"
            disabled={
              !pendingFilterKey
            }
            onClick={
              addDashboardFilter
            }
          >
            + Add slicer
          </button>
        </div>
        )}

        {dashboardFilters.length > 0 && (
          <div className="dashboard-slicer-list">
            {dashboardFilters.map(
              (filter) => (
                <div
                  key={
                    filter.filter_id
                  }
                  className={
                    "dashboard-slicer-card" +
                    (
                      (
                  filter.value !== null ||
                  (filter.values?.length ?? 0) > 0
                )
                        ? " active"
                        : ""
                    )
                  }
                >
                  <span>
                    {filter.label}
                  </span>

                  <DashboardMultiSelect
                    values={
                      filterValues[
                        filter.filter_id
                      ] ?? []
                    }
                    selected={
                      (
                        filter.values &&
                        filter.values.length > 0
                      )
                        ? filter.values
                        : (
                            filter.value !== null
                              ? [
                                  filter.value,
                                ]
                              : []
                          )
                    }
                    onChange={(values) =>
                      setDashboardFilterValues(
                        filter.filter_id,
                        values,
                      )
                    }
                  />

                  <button
                    type="button"
                    className="dashboard-slicer-remove"
                    title="Remove slicer"
                    onClick={() =>
                      removeDashboardFilter(
                        filter.filter_id
                      )
                    }
                  >
                    ×
                  </button>
                </div>
              )
            )}
          </div>
        )}

        {crossFilters.length > 0 && (
          <div className="dashboard-cross-filter-list">
            <span className="dashboard-cross-filter-label">
              Visual selections
            </span>

            {crossFilters.map(
              (filter) => (
                <button
                  key={
                    filter.filter_id
                  }
                  type="button"
                  className="dashboard-cross-filter-chip"
                  title="Remove visual filter"
                  onClick={() =>
                    removeCrossFilter(
                      filter.source_visual_id
                    )
                  }
                >
                  <span>
                    {filter.label}
                  </span>

                  <strong>
                    {filter.value}
                  </strong>

                  <i>
                    ×
                  </i>
                </button>
              )
            )}
          </div>
        )}
      </div>

      <div
        className={
          "dashboard-builder-layout" +
          (
            dashboardMode ===
              "edit" &&
            editingVisual &&
            propertiesPanelOpen
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

                const isAdded =
                  visuals.some(
                    (visual) =>
                      (
                        visual.analysis_id ===
                        analysis.analysis_id
                      ) ||
                      (
                        visual.kpi_code ===
                          analysis.kpi_code &&
                        visual.dimension_table ===
                          analysis.dimension_table &&
                        visual.dimension ===
                          analysis.dimension
                      )
                  );

                return (
                  <div
                    key={
                      analysis.analysis_id ??
                      index
                    }
                    className={
                      "dashboard-analysis-item" +
                      (
                        isAdded
                          ? " added"
                          : ""
                      )
                    }
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
                      className={
                        isAdded
                          ? "dashboard-added-button"
                          : "secondary-button"
                      }
                      disabled={
                        !analysis.analysis_id ||
                        isAdded
                      }
                      onClick={() =>
                        addAnalysis(
                          analysis
                        )
                      }
                    >
                      {isAdded
                        ? "Added"
                        : "Add"}
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

        {dashboardMode === "edit" &&
          editingVisual &&
          propertiesPanelOpen && (
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
                  setPropertiesPanelOpen(
                    false
                  )
                }
                title="Close properties"
                aria-label="Close visual properties"
              >
                ×
              </button>
            </div>

            <div className="dashboard-properties-body">
              <div className="dashboard-property-section dashboard-format-target-section">
                <strong>
                  FORMAT TARGET
                </strong>

                <div className="dashboard-format-targets">
                  {[
                    ["visual", "Visual"],
                    ["title", "Title"],
                    ["subtitle", "Subtitle"],
                    ["category", "Category labels"],
                    ["value", "Value labels"],
                    ["axis", "Axis labels"],
                    ["legend", "Legend"],
                  ].map(
                    ([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        className={
                          formatTarget ===
                          value
                            ? "active"
                            : ""
                        }
                        onClick={() =>
                          setFormatTarget(
                            value as
                              | "visual"
                              | "title"
                              | "subtitle"
                              | "category"
                              | "value"
                              | "axis"
                              | "legend"
                          )
                        }
                      >
                        {label}
                      </button>
                    )
                  )}
                </div>

                {formatTarget !== "visual" && (
                  <div className="dashboard-format-controls">
                    <div className="dashboard-font-stepper">
                      <span>
                        Font size
                      </span>

                      <button
                        type="button"
                        onClick={() =>
                          updateFormatTargetStyle(
                            {
                              fontSize:
                                activeFormatStyle.fontSize -
                                1,
                            }
                          )
                        }
                      >
                        −
                      </button>

                      <strong>
                        {activeFormatStyle.fontSize}
                      </strong>

                      <button
                        type="button"
                        onClick={() =>
                          updateFormatTargetStyle(
                            {
                              fontSize:
                                activeFormatStyle.fontSize +
                                1,
                            }
                          )
                        }
                      >
                        +
                      </button>
                    </div>

                    <label className="dashboard-property-check">
                      <input
                        type="checkbox"
                        checked={
                          activeFormatStyle.bold
                        }
                        onChange={(event) =>
                          updateFormatTargetStyle(
                            {
                              bold:
                                event.target.checked,
                            }
                          )
                        }
                      />

                      <span>
                        Bold
                      </span>
                    </label>

                    <label className="dashboard-format-color">
                      <span>
                        Color
                      </span>

                      <input
                        type="color"
                        value={
                          activeFormatStyle.color
                        }
                        onChange={(event) =>
                          updateFormatTargetStyle(
                            {
                              color:
                                event.target.value,
                            }
                          )
                        }
                      />
                    </label>
                  </div>
                )}

                <small className="dashboard-property-hint">
                  In Edit mode, click a title, label or value inside the visual to select its formatting group. In Interact mode, data marks filter the other visuals.
                </small>
              </div>

              <div className="dashboard-property-section">
                <strong>
                  POSITION & SIZE
                </strong>

                <div className="dashboard-layout-fields">
                  {[
                    ["X", "canvas_x", 0],
                    ["Y", "canvas_y", 0],
                    [
                      "W",
                      "canvas_width",
                      visualMinWidth(
                        editingVisual
                      ),
                    ],
                    [
                      "H",
                      "canvas_height",
                      visualMinHeight(
                        editingVisual
                      ),
                    ],
                  ].map(
                    ([label, key, minimum]) => (
                      <label
                        key={String(key)}
                        className="dashboard-property-field"
                      >
                        <span>
                          {String(label)}
                        </span>

                        <input
                          type="number"
                          min={Number(minimum)}
                          value={
                            Number(
                              editingVisual[
                                key as
                                  | "canvas_x"
                                  | "canvas_y"
                                  | "canvas_width"
                                  | "canvas_height"
                              ] ?? 0
                            )
                          }
                          onChange={(event) =>
                            updateVisual(
                              editingVisual.visual_id,
                              {
                                [key]:
                                  Math.max(
                                    Number(minimum),
                                    Number(
                                      event.target.value
                                    ) || 0
                                  ),
                              }
                            )
                          }
                        />
                      </label>
                    )
                  )}
                </div>

                <small className="dashboard-property-hint">
                  Drag the handle to move. Drag the bottom-right corner to resize. Arrow keys move 1 px; Shift + Arrow moves 10 px.
                </small>
              </div>

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
                        auto_title:
                          false,
                      }
                    )
                  }
                />
              </label>

              <div className="dashboard-property-section dashboard-inline-property-section">
                <strong>
                  Title alignment
                </strong>

                <div className="dashboard-segmented-control">
                  {[
                    ["left", "Left"],
                    ["center", "Center"],
                    ["right", "Right"],
                  ].map(
                    ([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        className={
                          (editingVisual.title_alignment ?? "left") === value
                            ? "active"
                            : ""
                        }
                        onClick={() =>
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              title_alignment:
                                value as
                                  | "left"
                                  | "center"
                                  | "right",
                            }
                          )
                        }
                      >
                        {label}
                      </button>
                    )
                  )}
                </div>
              </div>

              <label className="dashboard-property-check">
                <input
                  type="checkbox"
                  checked={
                    editingVisual.auto_title !== false
                  }
                  onChange={(event) => {
                    const autoTitle =
                      event.target.checked;

                    updateVisual(
                      editingVisual.visual_id,
                      {
                        auto_title:
                          autoTitle,
                        title:
                          (
                            autoTitle &&
                            editingAnalysis
                          )
                            ? defaultVisualTitle(
                                editingAnalysis,
                                editingVisual.visual_type,
                                editingVisual.sort_mode,
                                editingVisual.top_n,
                              )
                            : editingVisual.title,
                      }
                    );
                  }}
                />

                <span>
                  Auto-update title from data binding
                </span>
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

              {editingVisual.visual_type === "kpi" && (
                <div className="dashboard-property-section dashboard-kpi-property-section">
                  <strong>
                    KPI card
                  </strong>

                  <label className="dashboard-property-field">
                    <span>
                      Label
                    </span>

                    <input
                      type="text"
                      value={
                        editingVisual.kpi_label ??
                        ""
                      }
                      placeholder="Optional label"
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            kpi_label:
                              event.target.value ||
                              null,
                          }
                        )
                      }
                    />
                  </label>

                  <div className="dashboard-layout-fields">
                    <label className="dashboard-property-field">
                      <span>
                        Label size
                      </span>

                      <input
                        type="number"
                        min="6"
                        max="32"
                        value={
                          editingVisual.kpi_label_font_size ??
                          10
                        }
                        onChange={(event) =>
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              kpi_label_font_size:
                                Math.max(
                                  6,
                                  Math.min(
                                    32,
                                    Number(
                                      event.target.value
                                    ) || 10
                                  )
                                ),
                            }
                          )
                        }
                      />
                    </label>

                    <label className="dashboard-format-color">
                      <span>
                        Label color
                      </span>

                      <input
                        type="color"
                        value={
                          editingVisual.kpi_label_color ??
                          editingVisual.text_color
                        }
                        onChange={(event) =>
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              kpi_label_color:
                                event.target.value,
                            }
                          )
                        }
                      />
                    </label>
                  </div>

                  <label className="dashboard-property-check">
                    <input
                      type="checkbox"
                      checked={
                        editingVisual.kpi_label_bold ??
                        false
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            kpi_label_bold:
                              event.target.checked,
                          }
                        )
                      }
                    />

                    <span>
                      Bold label
                    </span>
                  </label>

                  <label className="dashboard-property-check">
                    <input
                      type="checkbox"
                      checked={
                        editingVisual.kpi_show_secondary ??
                        false
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            kpi_show_secondary:
                              event.target.checked,
                          }
                        )
                      }
                    />

                    <span>
                      Show records / groups
                    </span>
                  </label>

                  <div className="dashboard-property-field">
                    <span>
                      Horizontal alignment
                    </span>

                    <div className="dashboard-segmented-control">
                      {[
                        ["left", "Left"],
                        ["center", "Center"],
                        ["right", "Right"],
                      ].map(
                        ([value, label]) => (
                          <button
                            key={value}
                            type="button"
                            className={
                              (editingVisual.kpi_value_alignment ?? "center") === value
                                ? "active"
                                : ""
                            }
                            onClick={() =>
                              updateVisual(
                                editingVisual.visual_id,
                                {
                                  kpi_value_alignment:
                                    value as
                                      | "left"
                                      | "center"
                                      | "right",
                                }
                              )
                            }
                          >
                            {label}
                          </button>
                        )
                      )}
                    </div>
                  </div>

                  <div className="dashboard-property-field">
                    <span>
                      Vertical alignment
                    </span>

                    <div className="dashboard-segmented-control">
                      {[
                        ["top", "Top"],
                        ["center", "Center"],
                        ["bottom", "Bottom"],
                      ].map(
                        ([value, label]) => (
                          <button
                            key={value}
                            type="button"
                            className={
                              (editingVisual.kpi_vertical_alignment ?? "center") === value
                                ? "active"
                                : ""
                            }
                            onClick={() =>
                              updateVisual(
                                editingVisual.visual_id,
                                {
                                  kpi_vertical_alignment:
                                    value as
                                      | "top"
                                      | "center"
                                      | "bottom",
                                }
                              )
                            }
                          >
                            {label}
                          </button>
                        )
                      )}
                    </div>
                  </div>

                  <small className="dashboard-property-hint">
                    Use the Value format target above to change the KPI number size, weight and color.
                  </small>
                </div>
              )}

              <div className="dashboard-property-section">
                <strong>
                  Semantic data
                </strong>

                <label className="dashboard-property-field">
                  <span>
                    Measure / KPI
                  </span>

                  <DashboardSelect
                    value={
                      editingVisual.kpi_code ??
                      editingAnalysis?.kpi_code ??
                      ""
                    }
                    options={
                      kpiDefinitions.map(
                        (item) => ({
                          value:
                            item.code,
                          label:
                            item.title,
                        })
                      )
                    }
                    onChange={async (
                      kpiCode
                    ) => {
                      const definition =
                        kpiDefinitions.find(
                          (item) =>
                            item.code ===
                            kpiCode
                        );

                      const dimensionTable =
                        editingVisual.dimension_table ??
                        editingAnalysis?.dimension_table ??
                        null;

                      const dimension =
                        editingVisual.dimension ??
                        editingAnalysis?.dimension ??
                        null;

                      const nextSort =
                        (
                          isTimeDimension(
                            dimension
                          ) &&
                          [
                            "line",
                            "area",
                          ].includes(
                            editingVisual.visual_type
                          )
                        )
                          ? "chronological"
                          : (
                              editingVisual.sort_mode ===
                              "chronological"
                                ? (
                                    [
                                      "line",
                                      "area",
                                    ].includes(
                                      editingVisual.visual_type
                                    )
                                      ? "alphabetical"
                                      : "top_value"
                                  )
                                : editingVisual.sort_mode
                            );

                      updateVisual(
                        editingVisual.visual_id,
                        {
                          analysis_id:
                            null,
                          kpi_code:
                            kpiCode,
                          y_axis_title:
                            definition?.title ??
                            editingVisual.y_axis_title,
                          sort_mode:
                            nextSort,
                        }
                      );

                      const result =
                        await refreshVisualPreview(
                          editingVisual.visual_id,
                          kpiCode,
                          dimensionTable,
                          dimension,
                        );

                      if (
                        result &&
                        editingVisual.auto_title !== false
                      ) {
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            title:
                              defaultVisualTitle(
                                result,
                                editingVisual.visual_type,
                                nextSort,
                                editingVisual.top_n,
                              ),
                          }
                        );
                      }
                    }}
                  />
                </label>

                <label className="dashboard-property-field">
                  <span>
                    Category / Dimension
                  </span>

                  <DashboardSelect
                    value={
                      editingVisual.dimension_table &&
                      editingVisual.dimension
                        ? (
                            editingVisual.dimension_table +
                            "." +
                            editingVisual.dimension
                          )
                        : editingAnalysis?.dimension_table &&
                          editingAnalysis?.dimension
                          ? (
                              editingAnalysis.dimension_table +
                              "." +
                              editingAnalysis.dimension
                            )
                          : ""
                    }
                    options={[
                      {
                        value: "",
                        label:
                          "No dimension",
                      },
                      ...dimensionOptions.map(
                        (item) => ({
                          value:
                            item.value,
                          label:
                            item.label,
                        })
                      ),
                    ]}
                    onChange={async (
                      dimensionKey
                    ) => {
                      if (
                        crossFilters.some(
                          (filter) =>
                            filter.source_visual_id ===
                            editingVisual.visual_id
                        )
                      ) {
                        await removeCrossFilter(
                          editingVisual.visual_id
                        );
                      }

                      const selected =
                        dimensionOptions.find(
                          (item) =>
                            item.value ===
                            dimensionKey
                        );

                      const dimensionTable =
                        selected?.table ??
                        null;

                      const dimension =
                        selected?.column ??
                        null;

                      const kpiCode =
                        editingVisual.kpi_code ??
                        editingAnalysis?.kpi_code;

                      const nextSort =
                        (
                          isTimeDimension(
                            dimension
                          ) &&
                          [
                            "line",
                            "area",
                          ].includes(
                            editingVisual.visual_type
                          )
                        )
                          ? "chronological"
                          : (
                              editingVisual.sort_mode ===
                              "chronological"
                                ? (
                                    [
                                      "line",
                                      "area",
                                    ].includes(
                                      editingVisual.visual_type
                                    )
                                      ? "alphabetical"
                                      : "top_value"
                                  )
                                : editingVisual.sort_mode
                            );

                      updateVisual(
                        editingVisual.visual_id,
                        {
                          analysis_id:
                            null,
                          dimension_table:
                            dimensionTable,
                          dimension,
                          x_axis_title:
                            dimension,
                          sort_mode:
                            nextSort,
                        }
                      );

                      if (kpiCode) {
                        const result =
                          await refreshVisualPreview(
                            editingVisual.visual_id,
                            kpiCode,
                            dimensionTable,
                            dimension,
                          );

                        if (
                          result &&
                          editingVisual.auto_title !== false
                        ) {
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              title:
                                defaultVisualTitle(
                                  result,
                                  editingVisual.visual_type,
                                  nextSort,
                                  editingVisual.top_n,
                                ),
                            }
                          );
                        }
                      }
                    }}
                  />
                </label>

                {previewErrors[
                  editingVisual.visual_id
                ] && (
                  <p className="dashboard-property-error">
                    {
                      previewErrors[
                        editingVisual.visual_id
                      ]
                    }
                  </p>
                )}

                <small className="dashboard-property-hint">
                  Data binding controls the real semantic query.
                  Axis titles below only change the displayed labels.
                </small>
              </div>

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
                        label: "Horizontal bar",
                      },
                      {
                        value: "column",
                        label: "Column chart",
                      },
                      {
                        value: "line",
                        label: "Line chart",
                      },
                      {
                        value: "area",
                        label: "Area chart",
                      },
                      {
                        value: "pie",
                        label: "Pie chart",
                      },
                      {
                        value: "donut",
                        label: "Donut chart",
                      },
                      {
                        value: "table",
                        label: "Table",
                      },
                    ]}
                    onChange={(visualType) => {
                      const nextSort =
                        (
                          editingIsTime &&
                          [
                            "line",
                            "area",
                          ].includes(
                            visualType
                          )
                        )
                          ? "chronological"
                          : (
                              editingVisual.sort_mode ===
                              "chronological"
                                ? (
                                    [
                                      "line",
                                      "area",
                                    ].includes(
                                      visualType
                                    )
                                      ? "alphabetical"
                                      : "top_value"
                                  )
                                : editingVisual.sort_mode
                            );

                      updateVisual(
                        editingVisual.visual_id,
                        {
                          visual_type:
                            visualType,
                          sort_mode:
                            nextSort,
                          title:
                            (
                              editingVisual.auto_title !== false &&
                              editingAnalysis
                            )
                              ? defaultVisualTitle(
                                  editingAnalysis,
                                  visualType,
                                  nextSort,
                                  editingVisual.top_n,
                                )
                              : editingVisual.title,
                        }
                      );
                    }}
                  />
                </label>

                {editingNonAdditivePie && (
                  <div className="dashboard-property-warning">
                    <strong>
                      Check this chart choice
                    </strong>

                    <span>
                      Pie and donut charts show part-to-whole relationships.
                      This KPI uses {
                        editingKpiDefinition?.aggregation ??
                        "a non-additive calculation"
                      }, so percentages can be misleading. A bar or column chart
                      is usually clearer.
                    </span>
                  </div>
                )}

                {editingHasGroups &&
                  editingVisual.visual_type !== "kpi" && (
                  <>
                    <label className="dashboard-property-field">
                      <span>
                        Sort
                      </span>

                      <DashboardSelect
                        value={
                          editingVisual.sort_mode
                        }
                        options={
                          (
                            editingIsTime &&
                            [
                              "line",
                              "area",
                            ].includes(
                              editingVisual.visual_type
                            )
                          )
                            ? [
                                {
                                  value: "chronological",
                                  label: "Chronological",
                                },
                              ]
                            : [
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
                              ]
                        }
                        onChange={(sortMode) =>
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              sort_mode:
                                sortMode,
                              title:
                                (
                                  editingVisual.auto_title !== false &&
                                  editingAnalysis
                                )
                                  ? defaultVisualTitle(
                                      editingAnalysis,
                                      editingVisual.visual_type,
                                      sortMode,
                                      editingVisual.top_n,
                                    )
                                  : editingVisual.title,
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
                        onChange={(event) => {
                          const topN =
                            Math.max(
                              1,
                              Math.min(
                                50,
                                Number(
                                  event.target.value
                                ) || 1
                              )
                            );

                          updateVisual(
                            editingVisual.visual_id,
                            {
                              top_n:
                                topN,
                              title:
                                (
                                  editingVisual.auto_title !== false &&
                                  editingAnalysis
                                )
                                  ? defaultVisualTitle(
                                      editingAnalysis,
                                      editingVisual.visual_type,
                                      editingVisual.sort_mode,
                                      topN,
                                    )
                                  : editingVisual.title,
                            }
                          );
                        }}
                      />
                    </label>
                  </>
                )}
              </div>

              <div className="dashboard-property-section">
                <strong>
                  Labels & interaction
                </strong>

                {editingHasAxes && (
                  <>
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
                  </>
                )}

                {editingVisual.visual_type !== "table" && (
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
                )}

                {editingIsPie && (
                  <label className="dashboard-property-check">
                    <input
                      type="checkbox"
                      checked={
                        editingVisual.show_legend ??
                        true
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            show_legend:
                              event.target.checked,
                          }
                        )
                      }
                    />

                    <span>
                      Show legend
                    </span>
                  </label>
                )}

                {[
                  "column",
                  "line",
                  "area",
                ].includes(
                  editingVisual.visual_type
                ) && (
                  <label className="dashboard-property-check">
                    <input
                      type="checkbox"
                      checked={
                        editingVisual.show_gridlines ??
                        true
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            show_gridlines:
                              event.target.checked,
                          }
                        )
                      }
                    />

                    <span>
                      Show gridlines
                    </span>
                  </label>
                )}

                {![
                  "kpi",
                  "table",
                ].includes(
                  editingVisual.visual_type
                ) && (
                  <label className="dashboard-property-check">
                    <input
                      type="checkbox"
                      checked={
                        editingVisual.animate ??
                        true
                      }
                      onChange={(event) =>
                        updateVisual(
                          editingVisual.visual_id,
                          {
                            animate:
                              event.target.checked,
                          }
                        )
                      }
                    />

                    <span>
                      Animate
                    </span>
                  </label>
                )}

                {![
                  "kpi",
                  "table",
                ].includes(
                  editingVisual.visual_type
                ) && (
                  <>
                    <label className="dashboard-property-field">
                      <span>
                        Tooltip template
                      </span>

                      <textarea
                        rows={4}
                        value={
                          editingVisual.tooltip_template ??
                          "{category}\n{measure}: {value}\nRecords: {count}"
                        }
                        onChange={(event) =>
                          updateVisual(
                            editingVisual.visual_id,
                            {
                              tooltip_template:
                                event.target.value ||
                                null,
                            }
                          )
                        }
                      />
                    </label>

                    <small className="dashboard-property-hint">
                      Available placeholders: {"{category}"}, {"{measure}"}, {"{value}"}, {"{count}"}.
                    </small>
                  </>
                )}
              </div>
            </div>
          </aside>
        )}

        {dashboardMode === "edit" &&
          editingVisual &&
          !propertiesPanelOpen && (
          <button
            type="button"
            className="dashboard-properties-rail-toggle"
            onClick={() =>
              setPropertiesPanelOpen(
                true
              )
            }
            title="Open visual properties"
            aria-label="Open visual properties"
          >
            <span aria-hidden="true">⚙</span>
            <strong>Properties</strong>
          </button>
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

            <div className="dashboard-canvas-mode-controls">
              <div className="dashboard-mode-toggle">
                <button
                  type="button"
                  className={
                    dashboardMode ===
                    "interact"
                      ? "active"
                      : ""
                  }
                  onClick={() => {
                    setDashboardMode(
                      "interact"
                    );
                    setFormatTarget(
                      "visual"
                    );
                    setEditingVisualId(
                      null
                    );
                    setPropertiesPanelOpen(
                      false
                    );
                  }}
                >
                  Interact
                </button>

                <button
                  type="button"
                  className={
                    dashboardMode ===
                    "edit"
                      ? "active"
                      : ""
                  }
                  onClick={() =>
                    setDashboardMode(
                      "edit"
                    )
                  }
                >
                  Edit
                </button>
              </div>

              {dashboardMode === "edit" && (
                <button
                  type="button"
                  className={
                    "dashboard-properties-toolbar-button" +
                    (
                      propertiesPanelOpen
                        ? " active"
                        : ""
                    )
                  }
                  disabled={
                    !editingVisual
                  }
                  onClick={() =>
                    setPropertiesPanelOpen(
                      (previous) =>
                        !previous
                    )
                  }
                  title={
                    editingVisual
                      ? "Show or hide visual properties"
                      : "Select a visual first"
                  }
                >
                  Properties
                </button>
              )}

              {dashboardMode === "edit" && (
                <label className="dashboard-grid-toggle">
                  <input
                    type="checkbox"
                    checked={
                      showCanvasGrid
                    }
                    onChange={(event) =>
                      setShowCanvasGrid(
                        event.target.checked
                      )
                    }
                  />

                  <span>
                    Grid
                  </span>
                </label>
              )}
            </div>

            {dashboardMode === "edit" && (
              <button
                type="button"
                className="dashboard-reset-button"
                disabled={
                  visuals.length === 0
                }
                onClick={() => {
                  setVisuals([]);
                  setCrossFilters([]);
                }}
              >
                Reset canvas
              </button>
            )}
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

          <div
            className={
              "dashboard-visual-grid" +
              (
                showCanvasGrid &&
                dashboardMode ===
                  "edit"
                  ? " show-grid"
                  : ""
              ) +
              (
                dashboardMode ===
                "edit"
                  ? " edit-mode"
                  : " interact-mode"
              )
            }
            style={{
              minHeight:
                canvasHeight +
                "px",
            }}
          >
            {visuals.map(
              (visual) => {
                const analysis =
                  previewResults[
                    visual.visual_id
                  ] ??
                  (
                    visual.analysis_id
                      ? analysesById.get(
                          visual.analysis_id
                        )
                      : undefined
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

                const visualDimensionTable =
                  visual.dimension_table ??
                  analysis.dimension_table ??
                  null;

                const visualDimension =
                  visual.dimension ??
                  analysis.dimension ??
                  null;

                const selectedCrossFilter =
                  crossFilters.find(
                    (filter) =>
                      filter.source_visual_id ===
                      visual.visual_id
                  );

                const selectedValue =
                  selectedCrossFilter?.value ??
                  null;

                const visualIsFiltered =
                  dashboardFilters.some(
                    (filter) =>
                      (
                        filter.value !== null ||
                        (filter.values?.length ?? 0) > 0
                      )
                  ) ||
                  crossFilters.some(
                    (filter) =>
                      filter.source_visual_id !==
                      visual.visual_id
                  );

                const selectCategory = (
                  value: unknown
                ) =>
                  toggleCrossFilter(
                    visual.visual_id,
                    visualDimensionTable,
                    visualDimension,
                    value,
                  );

                return (
                  <article
                    key={
                      visual.visual_id
                    }
                    className={
                      "dashboard-visual-card mode-" +
                      dashboardMode +
                      " size-" +
                      visual.size +
                      (
                        visual.animate === false
                          ? " no-animation"
                          : ""
                      ) +
                      (
                        dashboardMode ===
                        "edit" &&
                        editingVisualId ===
                        visual.visual_id
                          ? " selected"
                          : ""
                      )
                    }
                    style={{
                      background:
                        visual.background_color,
                      color:
                        visual.text_color,
                      left:
                        (visual.canvas_x ?? 0) +
                        "px",
                      top:
                        (visual.canvas_y ?? 0) +
                        "px",
                      width:
                        (visual.canvas_width ?? 480) +
                        "px",
                      height:
                        (visual.canvas_height ?? 300) +
                        "px",
                      "--dashboard-title-size":
                        (visual.title_font_size ?? 10) + "px",
                      "--dashboard-title-weight":
                        visual.title_bold === false
                          ? 400
                          : 800,
                      "--dashboard-title-color":
                        visual.title_color ??
                        visual.text_color,
                      "--dashboard-title-align":
                        visual.title_alignment ??
                        "left",
                      "--dashboard-subtitle-size":
                        (visual.subtitle_font_size ?? 7) + "px",
                      "--dashboard-subtitle-weight":
                        visual.subtitle_bold
                          ? 700
                          : 400,
                      "--dashboard-subtitle-color":
                        visual.subtitle_color ??
                        visual.text_color,
                      "--dashboard-category-size":
                        (visual.category_label_font_size ?? 8) + "px",
                      "--dashboard-category-weight":
                        visual.category_label_bold
                          ? 700
                          : 400,
                      "--dashboard-category-color":
                        visual.category_label_color ??
                        visual.text_color,
                      "--dashboard-value-size":
                        (visual.value_label_font_size ?? 8) + "px",
                      "--dashboard-value-weight":
                        visual.value_label_bold === false
                          ? 400
                          : 700,
                      "--dashboard-value-color":
                        visual.value_label_color ??
                        visual.text_color,
                      "--dashboard-axis-size":
                        (visual.axis_label_font_size ?? 8) + "px",
                      "--dashboard-axis-weight":
                        visual.axis_label_bold
                          ? 700
                          : 400,
                      "--dashboard-axis-color":
                        visual.axis_label_color ??
                        visual.text_color,
                      "--dashboard-legend-size":
                        (visual.legend_label_font_size ?? 8) + "px",
                      "--dashboard-legend-weight":
                        visual.legend_label_bold
                          ? 700
                          : 400,
                      "--dashboard-legend-color":
                        visual.legend_label_color ??
                        visual.text_color,
                    } as CSSProperties}
                    onClick={(event) => {
                      if (
                        dashboardMode !==
                        "edit"
                      ) {
                        return;
                      }

                      setEditingVisualId(
                        visual.visual_id
                      );

                      const target =
                        (
                          event.target as HTMLElement
                        ).closest(
                          "[data-format-target]"
                        ) as HTMLElement | null;

                      const nextTarget =
                        target?.dataset
                          .formatTarget;

                      if (
                        nextTarget &&
                        [
                          "title",
                          "subtitle",
                          "category",
                          "value",
                          "axis",
                          "legend",
                        ].includes(
                          nextTarget
                        )
                      ) {
                        setFormatTarget(
                          nextTarget as
                            | "title"
                            | "subtitle"
                            | "category"
                            | "value"
                            | "axis"
                            | "legend"
                        );
                      } else {
                        setFormatTarget(
                          "visual"
                        );
                      }
                    }}
                    tabIndex={
                      dashboardMode ===
                      "edit"
                        ? 0
                        : -1
                    }
                    onKeyDown={(event) =>
                      handleVisualKeyDown(
                        event,
                        visual
                      )
                    }
                  >
                    <header className="dashboard-visual-header">
                      {dashboardMode === "edit" && (
                        <span
                          className="dashboard-visual-drag"
                          title="Drag visual"
                          onPointerDown={(event) =>
                            beginVisualMove(
                              event,
                              visual
                            )
                          }
                        >
                          ⋮⋮
                        </span>
                      )}

                      <div className="dashboard-visual-title-block">
                        <strong data-format-target="title">
                          {visual.title}
                        </strong>

                        {visual.subtitle && (
                          <span data-format-target="subtitle">
                            {visual.subtitle}
                          </span>
                        )}
                      </div>

                      <div
                        className="dashboard-visual-actions"
                        onClick={(event) =>
                          event.stopPropagation()
                        }
                      >
                        {visualIsFiltered && (
                          <span className="dashboard-filtered-badge">
                            Filtered
                          </span>
                        )}
                        {dashboardMode === "edit" && (
                          <>
                          <button
                            type="button"
                            className={
                              editingVisualId ===
                              visual.visual_id
                                ? "active"
                                : ""
                            }
                            onClick={() => {
                              setDashboardMode(
                                "edit"
                              );
  
                              setFormatTarget(
                                "visual"
                              );
  
                              setEditingVisualId(
                                visual.visual_id
                              );
                              setPropertiesPanelOpen(
                                true
                              );
                            }}
                            title="Edit visual"
                          >
                            ⚙
                          </button>
  
                          <button
                            type="button"
                            disabled={
                              (visual.canvas_width ?? 480) <=
                                visualMinWidth(
                                  visual
                                ) &&
                              (visual.canvas_height ?? 300) <=
                                visualMinHeight(
                                  visual
                                )
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
  
                          </>
                        )}
                      </div>
                    </header>

                    {dashboardMode === "edit" && (
                      <button
                        type="button"
                        className="dashboard-visual-resize-handle"
                        aria-label="Resize visual"
                        title="Drag to resize"
                        onPointerDown={(event) =>
                          beginVisualResize(
                            event,
                            visual
                          )
                        }
                      />
                    )}

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
                          label={
                            visual.kpi_label ??
                            null
                          }
                          showSecondary={
                            visual.kpi_show_secondary ??
                            false
                          }
                          labelFontSize={
                            visual.kpi_label_font_size ??
                            10
                          }
                          labelBold={
                            visual.kpi_label_bold ??
                            false
                          }
                          labelColor={
                            visual.kpi_label_color ??
                            visual.text_color
                          }
                          valueAlignment={
                            visual.kpi_value_alignment ??
                            "center"
                          }
                          verticalAlignment={
                            visual.kpi_vertical_alignment ??
                            "center"
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
                          tooltipTemplate={
                            visual.tooltip_template
                          }
                          selectedValue={
                            selectedValue
                          }
                          onSelect={
                            dashboardMode ===
                            "interact"
                              ? selectCategory
                              : undefined
                          }
                          containerWidth={
                            visual.canvas_width ?? 480
                          }
                          containerHeight={
                            visual.canvas_height ?? 300
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
                          showGridlines={
                            visual.show_gridlines ??
                            true
                          }
                          tooltipTemplate={
                            visual.tooltip_template
                          }
                          selectedValue={
                            selectedValue
                          }
                          onSelect={
                            dashboardMode ===
                            "interact"
                              ? selectCategory
                              : undefined
                          }
                        />
                      )}

                      {visual.visual_type ===
                        "column" && (
                        <DashboardColumnVisual
                          analysis={
                            analysis
                          }
                          rows={rows}
                          accentColor={
                            visual.accent_color
                          }
                          showValues={
                            visual.show_values
                          }
                          showGridlines={
                            visual.show_gridlines ??
                            true
                          }
                          tooltipTemplate={
                            visual.tooltip_template
                          }
                          selectedValue={
                            selectedValue
                          }
                          onSelect={
                            dashboardMode ===
                            "interact"
                              ? selectCategory
                              : undefined
                          }
                          containerWidth={
                            visual.canvas_width ?? 480
                          }
                          containerHeight={
                            visual.canvas_height ?? 300
                          }
                        />
                      )}

                      {visual.visual_type ===
                        "area" && (
                        <DashboardAreaVisual
                          analysis={
                            analysis
                          }
                          rows={rows}
                          accentColor={
                            visual.accent_color
                          }
                          showValues={
                            visual.show_values
                          }
                          showGridlines={
                            visual.show_gridlines ??
                            true
                          }
                          tooltipTemplate={
                            visual.tooltip_template
                          }
                          selectedValue={
                            selectedValue
                          }
                          onSelect={
                            dashboardMode ===
                            "interact"
                              ? selectCategory
                              : undefined
                          }
                        />
                      )}

                      {(visual.visual_type ===
                        "pie" ||
                        visual.visual_type ===
                          "donut") && (
                        <DashboardPieVisual
                          analysis={
                            analysis
                          }
                          rows={rows}
                          accentColor={
                            visual.accent_color
                          }
                          donut={
                            visual.visual_type ===
                            "donut"
                          }
                          showValues={
                            visual.show_values
                          }
                          showLegend={
                            visual.show_legend ??
                            true
                          }
                          tooltipTemplate={
                            visual.tooltip_template
                          }
                          selectedValue={
                            selectedValue
                          }
                          onSelect={
                            dashboardMode ===
                            "interact"
                              ? selectCategory
                              : undefined
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
                          selectedValue={
                            selectedValue
                          }
                          onSelect={
                            dashboardMode ===
                            "interact"
                              ? selectCategory
                              : undefined
                          }
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
