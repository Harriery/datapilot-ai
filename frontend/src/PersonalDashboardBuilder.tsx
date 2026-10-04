import {
  useEffect,
  useMemo,
  useRef,
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
  kpi_stat?:
    | "metric"
    | "count"
    | "min"
    | "max";

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
  draftKey: string;
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
  ) => Promise<void>;
};

type DashboardDraftData = {
  visuals: DashboardVisualData[];
  title: string;
  subtitle: string;
  theme: DashboardTheme;
  filters: DashboardFilterData[];
  updated_at: string;
};

function loadDashboardDraft(
  draftKey: string,
): DashboardDraftData | null {
  try {
    const raw =
      window.localStorage.getItem(
        draftKey,
      );

    if (!raw) {
      return null;
    }

    const parsed =
      JSON.parse(
        raw,
      ) as DashboardDraftData;

    if (
      !Array.isArray(
        parsed.visuals,
      ) ||
      !Array.isArray(
        parsed.filters,
      ) ||
      typeof parsed.title !== "string"
    ) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

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

function isSemanticTimeDimension(
  dataModelStudio:
    DataModelStudioData | null | undefined,
  tableName: string | null | undefined,
  columnName: string | null | undefined,
): boolean {
  if (
    !dataModelStudio ||
    !columnName
  ) {
    return false;
  }

  const tables =
    tableName
      ? dataModelStudio.tables.filter(
          (table) =>
            table.name === tableName
        )
      : dataModelStudio.tables;

  const matches =
    tables.flatMap(
      (table) =>
        table.columns.filter(
          (column) =>
            column.name ===
            columnName
        )
    );

  return (
    matches.length === 1 &&
    (
      matches[0].role === "time" ||
      matches[0].derivation?.type ===
        "date_part"
    )
  );
}

function getSemanticDateOperation(
  dataModelStudio:
    DataModelStudioData | null | undefined,
  tableName: string | null | undefined,
  columnName: string | null | undefined,
): string | null {
  if (
    !dataModelStudio ||
    !columnName
  ) {
    return null;
  }

  const tables =
    tableName
      ? dataModelStudio.tables.filter(
          (table) =>
            table.name === tableName
        )
      : dataModelStudio.tables;

  const matches =
    tables.flatMap(
      (table) =>
        table.columns.filter(
          (column) =>
            column.name ===
            columnName
        )
    );

  if (
    matches.length !== 1 ||
    matches[0].derivation?.type !==
      "date_part"
  ) {
    return null;
  }

  return (
    matches[0].derivation
      ?.operation ??
    null
  );
}

function defaultVisualTitle(
  analysis: AnalysisResultData,
  visualType: DashboardVisualType,
  sortMode: DashboardSortMode,
  topN: number,
  isTimeDimension: boolean = false,
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
    isTimeDimension
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
  analysis: AnalysisResultData,
  isTimeDimension: boolean = false,
): DashboardVisualType {
  if (
    !analysis.dimension ||
    analysis.grouped_results.length === 0
  ) {
    return "kpi";
  }

  if (isTimeDimension) {
    return (
      analysis.grouped_results.length <= 3
        ? "column"
        : "line"
    );
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
const DASHBOARD_PAGE_WIDTH = 1600;
const DASHBOARD_PAGE_HEIGHT = 900;
const DASHBOARD_CANVAS_MIN_WIDTH = DASHBOARD_PAGE_WIDTH;
const DASHBOARD_CANVAS_MIN_HEIGHT = 680;
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
  placeholder,
}: {
  value: T;
  options: {
    value: T;
    label: string;
  }[];
  onChange: (
    value: T
  ) => void;
  placeholder?: string;
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
            (
              value ||
              placeholder ||
              ""
            )}
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

  const rootRef =
    useRef<HTMLDivElement | null>(
      null
    );

  const closeTimerRef =
    useRef<number | null>(
      null
    );

  useEffect(
    () => {
      if (!open) {
        return;
      }

      const handlePointerDown = (
        event: PointerEvent
      ) => {
        if (
          rootRef.current &&
          !rootRef.current.contains(
            event.target as Node
          )
        ) {
          setOpen(false);
        }
      };

      const handleKeyDown = (
        event: globalThis.KeyboardEvent
      ) => {
        if (event.key === "Escape") {
          setOpen(false);
        }
      };

      document.addEventListener(
        "pointerdown",
        handlePointerDown
      );

      document.addEventListener(
        "keydown",
        handleKeyDown
      );

      return () => {
        document.removeEventListener(
          "pointerdown",
          handlePointerDown
        );

        document.removeEventListener(
          "keydown",
          handleKeyDown
        );
      };
    },
    [open]
  );

  useEffect(
    () => () => {
      if (
        closeTimerRef.current !== null
      ) {
        window.clearTimeout(
          closeTimerRef.current
        );
      }
    },
    []
  );

  const scheduleClose = () => {
    if (
      closeTimerRef.current !== null
    ) {
      window.clearTimeout(
        closeTimerRef.current
      );
    }

    closeTimerRef.current =
      window.setTimeout(
        () => {
          setOpen(false);
          closeTimerRef.current =
            null;
        },
        350
      );
  };

  const cancelClose = () => {
    if (
      closeTimerRef.current !== null
    ) {
      window.clearTimeout(
        closeTimerRef.current
      );
      closeTimerRef.current =
        null;
    }
  };

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
      ref={rootRef}
      className={
        "dashboard-multi-select" +
        (
          open
            ? " open"
            : ""
        )
      }
      onMouseEnter={
        cancelClose
      }
      onMouseLeave={
        scheduleClose
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
  stat,
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
  stat:
    | "metric"
    | "count"
    | "min"
    | "max";
}) {
  const value =
    stat === "count"
      ? analysis.overall.count
      : stat === "min"
        ? analysis.overall.min
        : stat === "max"
          ? analysis.overall.max
          : getMetricValue(
              analysis
            );

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
          value
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
  dateOperation,
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
  dateOperation?: string | null;
}) {
  const semantic =
    Boolean(
      analysis.kpi_code
    );

  const formatTimeLabel = (
    value: unknown
  ) => {
    if (
      dateOperation ===
      "month"
    ) {
      const month =
        Number(value);

      if (
        Number.isInteger(month) &&
        month >= 1 &&
        month <= 12
      ) {
        return new Intl.DateTimeFormat(
          undefined,
          {
            month: "short",
          }
        ).format(
          new Date(
            2000,
            month - 1,
            1
          )
        );
      }
    }

    return String(
      value ?? ""
    );
  };

  const orderedRows =
    dateOperation === "month"
      ? Array.from(
          {
            length: 12,
          },
          (_, index) => {
            const month =
              index + 1;

            const existing =
              rows.find(
                (row) =>
                  Number(
                    row.value
                  ) === month
              );

            if (existing) {
              return existing;
            }

            const emptyRow:
              AnalysisResultData[
                "grouped_results"
              ][number] = {
                value: month,
                count: 0,
                metric_value: null,
                mean: null,
                min: null,
                max: null,
              };

            return emptyRow;
          }
        )
      : [
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

  const points =
    orderedRows.map(
      (row, index) => {
        const raw =
          semantic
            ? row.metric_value
            : row.mean;

        const numeric =
          raw === null ||
          raw === undefined
            ? null
            : Number(raw);

        return {
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
          value:
            numeric !== null &&
            Number.isFinite(
              numeric
            )
              ? numeric
              : null,
          label:
            formatTimeLabel(
              row.value
            ),
        };
      }
    );

  const validValues =
    points
      .map(
        (point) =>
          point.value
      )
      .filter(
        (
          value,
        ): value is number =>
          value !== null
      );

  const rawMin =
    validValues.length > 0
      ? Math.min(
          ...validValues
        )
      : 0;

  const rawMax =
    validValues.length > 0
      ? Math.max(
          ...validValues
        )
      : 1;

  const rawRange =
    rawMax - rawMin;

  const padding =
    rawRange > 0
      ? rawRange * 0.12
      : Math.max(
          Math.abs(rawMax) * 0.05,
          1
        );

  const min =
    rawMin - padding;

  const max =
    rawMax + padding;

  const range =
    max - min || 1;

  const plottedPoints =
    points.map(
      (point) => ({
        ...point,
        y:
          point.value === null
            ? null
            : (
                88 -
                (
                  (
                    point.value - min
                  ) /
                  range
                ) * 76
              ),
      })
    );

  const validPoints =
    plottedPoints.filter(
      (
        point,
      ): point is typeof point & {
        y: number;
        value: number;
      } =>
        point.y !== null &&
        point.value !== null
    );

  let penDown = false;

  const path =
    plottedPoints
      .map(
        (point) => {
          if (
            point.y === null ||
            point.value === null
          ) {
            penDown = false;
            return "";
          }

          const command =
            penDown
              ? "L "
              : "M ";

          penDown = true;

          return (
            command +
            point.x +
            " " +
            point.y
          );
        }
      )
      .filter(Boolean)
      .join(" ");

  const labelStep =
    plottedPoints.length <= 12
      ? 1
      : Math.ceil(
          plottedPoints.length /
          8
        );

  const axisLabels =
    plottedPoints.filter(
      (_, index) =>
        plottedPoints.length <= 12 ||
        index === 0 ||
        index ===
          plottedPoints.length - 1 ||
        index % labelStep === 0
    );

  const yTicks =
    Array.from(
      {
        length: 5,
      },
      (_, index) => {
        const ratio =
          index / 4;

        return {
          value:
            max -
            range * ratio,
          top:
            12 +
            76 * ratio,
        };
      }
    );

  const showPointValues =
    showValues &&
    validPoints.length <= 12;

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
      <div className="dashboard-line-plot">
        <div
          className="dashboard-line-y-axis"
          data-format-target="axis"
        >
          {yTicks.map(
            (tick, index) => (
              <span
                key={index}
                style={{
                  top:
                    tick.top + "%",
                }}
              >
                {formatNumber(
                  tick.value
                )}
              </span>
            )
          )}
        </div>

        <div className="dashboard-line-plot-body">
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-label={
              analysis.measure +
              " trend"
            }
          >
        <path
          d={path}
          fill="none"
          vectorEffect="non-scaling-stroke"
        />

        {validPoints.map(
          (point, index) => (
            <circle
              key={
                point.label +
                "-" +
                index
              }
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

          {showPointValues && (
            <div
              className="dashboard-line-point-values"
              data-format-target="value"
            >
              {validPoints.map(
                (point, index) => (
                  <span
                    key={
                      point.label +
                      "-value-" +
                      index
                    }
                    style={{
                      left:
                        point.x + "%",
                      top:
                        point.y + "%",
                    }}
                  >
                    {formatNumber(
                      point.value
                    )}
                  </span>
                )
              )}
            </div>
          )}
        </div>
      </div>

      <div
        className="dashboard-line-axis dashboard-line-axis-detailed"
        data-format-target="axis"
      >
        <div className="dashboard-line-ticks">
          {axisLabels.map(
            (point, index) => (
              <span
                key={
                  point.label +
                  "-" +
                  index
                }
                style={{
                  left:
                    point.x + "%",
                }}
              >
                {point.label}
              </span>
            )
          )}
        </div>

        {xAxisTitle && (
          <strong>
            {xAxisTitle}
          </strong>
        )}
      </div>

      {yAxisTitle && (
        <div
          className="dashboard-line-measure-label"
          data-format-target="axis"
        >
          {yAxisTitle}
        </div>
      )}

      {showValues &&
        validPoints.length > 0 &&
        !showPointValues && (
        <div
          className="dashboard-line-value-summary"
          data-format-target="value"
        >
          <span>
            First: {
              formatNumber(
                validPoints[0].value
              )
            }
          </span>

          <span>
            Last: {
              formatNumber(
                validPoints[
                  validPoints.length - 1
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

  const rawMin =
    Math.min(
      ...values
    );

  const rawMax =
    Math.max(
      ...values
    );

  const rawRange =
    rawMax - rawMin;

  const padding =
    rawRange > 0
      ? rawRange * 0.12
      : Math.max(
          Math.abs(rawMax) * 0.05,
          1
        );

  const min =
    rawMin - padding;

  const max =
    rawMax + padding;

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
  draftKey,
  loading,
  error,
  onPreview,
  onLoadFilterValues,
  onSave,
}: Props) {
  const initialDraftRef =
    useRef<
      DashboardDraftData | null
    >(
      loadDashboardDraft(
        draftKey,
      )
    );

  const [
    draftRecovered,
    setDraftRecovered,
  ] = useState(
    initialDraftRef.current !== null
  );

  const [
    visuals,
    setVisuals,
  ] = useState<
    DashboardVisualData[]
  >(
    normalizeVisualLayouts(
      initialDraftRef.current?.visuals ??
        savedVisuals
    )
  );


  const [
    dashboardTitle,
    setDashboardTitle,
  ] = useState(
    initialDraftRef.current?.title ??
      savedTitle
  );

  const [
    dashboardSubtitle,
    setDashboardSubtitle,
  ] = useState(
    initialDraftRef.current?.subtitle ??
      savedSubtitle ??
      ""
  );

  const [
    dashboardTheme,
    setDashboardTheme,
  ] = useState<
    DashboardTheme
  >(
    initialDraftRef.current?.theme ??
      savedTheme
  );


  const [
    dashboardFilters,
    setDashboardFilters,
  ] = useState<
    DashboardFilterData[]
  >(
    initialDraftRef.current?.filters ??
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
    slicerPickerOpen,
    setSlicerPickerOpen,
  ] = useState(false);

  const [
    pendingVisualKpiCode,
    setPendingVisualKpiCode,
  ] = useState(
    ""
  );

  const [
    pendingVisualDimensionKey,
    setPendingVisualDimensionKey,
  ] = useState(
    ""
  );

  const [
    pendingVisualType,
    setPendingVisualType,
  ] = useState<
    "auto" | DashboardVisualType
  >("auto");

  const [
    creatingVisual,
    setCreatingVisual,
  ] = useState(false);

  const [
    createVisualError,
    setCreateVisualError,
  ] = useState("");

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
    selectedVisualIds,
    setSelectedVisualIds,
  ] = useState<string[]>([]);

  const [
    snapGuides,
    setSnapGuides,
  ] = useState<{
    x: number | null;
    y: number | null;
  }>({
    x: null,
    y: null,
  });

  const [
    propertiesPanelOpen,
    setPropertiesPanelOpen,
  ] = useState(false);

  const [
    analysisLibraryOpen,
    setAnalysisLibraryOpen,
  ] = useState(true);


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

  const canvasSurfaceRef =
    useRef<HTMLDivElement | null>(
      null
    );

  const pageViewportRef =
    useRef<HTMLDivElement | null>(
      null
    );

  const [
    interactScale,
    setInteractScale,
  ] = useState(1);

  useEffect(
    () => {
      const viewport =
        pageViewportRef.current;

      if (!viewport) {
        return;
      }

      const updateScale = () => {
        if (
          dashboardMode !==
          "interact"
        ) {
          setInteractScale(1);
          return;
        }

        const availableWidth =
          Math.max(
            320,
            viewport.clientWidth - 24
          );

        setInteractScale(
          Math.min(
            1,
            availableWidth /
              DASHBOARD_PAGE_WIDTH
          )
        );
      };

      updateScale();

      const observer =
        new ResizeObserver(
          updateScale
        );

      observer.observe(
        viewport
      );

      window.addEventListener(
        "resize",
        updateScale
      );

      return () => {
        observer.disconnect();

        window.removeEventListener(
          "resize",
          updateScale
        );
      };
    },
    [dashboardMode]
  );

  const savedVisualsSignature =
    JSON.stringify(
      savedVisuals
    );

  const savedFiltersSignature =
    JSON.stringify(
      savedFilters
    );

  const skippedInitialSavedSyncRef =
    useRef(
      initialDraftRef.current !== null
    );

  useEffect(
    () => {
      if (
        skippedInitialSavedSyncRef.current
      ) {
        skippedInitialSavedSyncRef.current =
          false;

        return;
      }

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

      setDraftRecovered(
        false
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

  useEffect(
    () => {
      const draft:
        DashboardDraftData = {
          visuals,
          title:
            dashboardTitle,
          subtitle:
            dashboardSubtitle,
          theme:
            dashboardTheme,
          filters:
            dashboardFilters,
          updated_at:
            new Date().toISOString(),
        };

      try {
        window.localStorage.setItem(
          draftKey,
          JSON.stringify(
            draft,
          ),
        );
      } catch {
        // Keep dashboard editing usable when
        // local storage is unavailable.
      }
    },
    [
      draftKey,
      visuals,
      dashboardTitle,
      dashboardSubtitle,
      dashboardTheme,
      dashboardFilters,
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
    isSemanticTimeDimension(
      dataModelStudio,
      editingVisual?.dimension_table ??
        editingAnalysis?.dimension_table ??
        null,
      editingDimension,
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
                    role:
                      column.role === "time" ||
                      column.derivation?.type ===
                        "date_part"
                        ? "time"
                        : column.role,
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

  const reusableKpiDefinitions =
    useMemo(
      () =>
        kpiDefinitions.filter(
          (item) =>
            !item.dimension &&
            !item.dimension_table
        ),
      [kpiDefinitions]
    );

  const pendingDimensionOption =
    dimensionOptions.find(
      (option) =>
        option.value ===
        pendingVisualDimensionKey
    ) ?? null;

  const pendingKpiDefinition =
    reusableKpiDefinitions.find(
      (item) =>
        item.code ===
        pendingVisualKpiCode
    ) ?? null;

  const pendingDimensionIsTime =
    pendingDimensionOption?.role ===
    "time";

  const pendingKpiIsAdditive =
    Boolean(
      pendingKpiDefinition &&
      [
        "sum",
        "count",
      ].includes(
        pendingKpiDefinition.aggregation ??
        ""
      )
    );

  const directVisualTypeOptions =
    !pendingDimensionOption
      ? [
          {
            value: "auto",
            label:
              "Auto · KPI card",
          },
          {
            value: "kpi",
            label:
              "KPI card",
          },
        ]
      : [
          {
            value: "auto",
            label:
              pendingDimensionIsTime
                ? "Auto · Time chart"
                : "Auto · Horizontal bar",
          },
          ...(pendingDimensionIsTime
            ? [
                {
                  value: "line",
                  label:
                    "Line chart",
                },
                {
                  value: "area",
                  label:
                    "Area chart",
                },
                {
                  value: "column",
                  label:
                    "Column chart",
                },
                {
                  value: "table",
                  label:
                    "Table",
                },
              ]
            : [
                {
                  value: "bar",
                  label:
                    "Horizontal bar",
                },
                {
                  value: "column",
                  label:
                    "Column chart",
                },
                ...(pendingKpiIsAdditive
                  ? [
                      {
                        value: "pie",
                        label:
                          "Pie chart",
                      },
                      {
                        value: "donut",
                        label:
                          "Donut chart",
                      },
                    ]
                  : []),
                {
                  value: "table",
                  label:
                    "Table",
                },
              ]),
        ];


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

  async function addDashboardFilterByKey(
    filterKey: string
  ) {
    const option =
      dimensionOptions.find(
        (item) =>
          item.value ===
          filterKey
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

    setDashboardFilters(
      (previous) => [
        ...previous,
        filter,
      ]
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
      AnalysisResultData,
    visualTypeOverride?:
      DashboardVisualType,
  ): DashboardVisualData | null {
    if (
      !analysis.analysis_id &&
      !analysis.kpi_code
    ) {
      return null;
    }

    const analysisIsTime =
      isSemanticTimeDimension(
        dataModelStudio,
        analysis.dimension_table ??
          null,
        analysis.dimension,
      );

    const visualType =
      visualTypeOverride ??
      recommendedVisual(
        analysis,
        analysisIsTime,
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
        analysis.analysis_id ??
        null,
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
          analysisIsTime
            ? "alphabetical"
            : "top_value",
          visualType === "line"
            ? 20
            : 10,
          analysisIsTime,
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
        analysisIsTime
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
      kpi_stat: "metric",
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
      (previous) => [
        ...previous,
        placeVisualInFreeSlot(
          previous,
          visual
        ),
      ]
    );
  }

  async function addDirectVisual() {
    if (!pendingVisualKpiCode) {
      return;
    }

    const dimensionOption =
      dimensionOptions.find(
        (option) =>
          option.value ===
          pendingVisualDimensionKey
      );

    const dimensionTable =
      dimensionOption?.table ??
      null;

    const dimension =
      dimensionOption?.column ??
      null;

    setCreatingVisual(true);
    setCreateVisualError("");

    try {
      const preview =
        await onPreview(
          pendingVisualKpiCode,
          dimensionTable,
          dimension,
          dashboardFilters,
        );

      const kpiDefinition =
        kpiDefinitions.find(
          (item) =>
            item.code ===
            pendingVisualKpiCode
        );

      const analysis:
        AnalysisResultData = {
          ...preview,
          analysis_id: null,
          kpi_code:
            pendingVisualKpiCode,
          dimension_table:
            dimensionTable,
          dimension,
          measure:
            preview.measure ||
            kpiDefinition?.title ||
            pendingVisualKpiCode,
        };

      const allowedTypes =
        new Set(
          directVisualTypeOptions.map(
            (option) =>
              option.value
          )
        );

      const normalizedSelection =
        allowedTypes.has(
          pendingVisualType
        )
          ? pendingVisualType
          : "auto";

      const visualType =
        normalizedSelection ===
        "auto"
          ? undefined
          : normalizedSelection as
              DashboardVisualType;

      const visual =
        createVisual(
          analysis,
          visualType,
        );

      if (!visual) {
        setCreateVisualError(
          "Could not create this visual."
        );
        return;
      }

      setVisuals(
        (previous) => [
          ...previous,
          placeVisualInFreeSlot(
            previous,
            visual
          ),
        ]
      );

      setPreviewResults(
        (previous) => ({
          ...previous,
          [visual.visual_id]:
            analysis,
        })
      );

      setEditingVisualId(
        visual.visual_id
      );
      setSelectedVisualIds(
        [
          visual.visual_id,
        ]
      );
    } catch (error) {
      setCreateVisualError(
        error instanceof Error
          ? error.message
          : "Could not create this visual."
      );
    } finally {
      setCreatingVisual(false);
    }
  }

  async function addSuggestedDashboard() {
    setCreatingVisual(true);
    setCreateVisualError("");

    try {
      const suggested:
        DashboardVisualData[] = [];

      const suggestedResults:
        Record<
          string,
          AnalysisResultData
        > = {};

      const baseKpi =
        reusableKpiDefinitions[0] ??
        null;

      if (baseKpi) {
        const preview =
          await onPreview(
            baseKpi.code,
            null,
            null,
            dashboardFilters,
          );

        const baseAnalysis:
          AnalysisResultData = {
          ...preview,
          analysis_id: null,
          kpi_code:
            baseKpi.code,
          dimension_table: null,
          dimension: null,
          measure:
            preview.measure ||
            baseKpi.title ||
            baseKpi.code,
        };

        const kpiSpecs:
          Array<{
            stat:
              | "metric"
              | "count"
              | "min"
              | "max";
            title: string;
          }> = [
          {
            stat: "metric",
            title:
              baseKpi.title,
          },
          {
            stat: "count",
            title:
              "Records",
          },
          {
            stat: "min",
            title:
              "Minimum " +
              baseAnalysis.measure,
          },
          {
            stat: "max",
            title:
              "Maximum " +
              baseAnalysis.measure,
          },
        ];

        kpiSpecs.forEach(
          (spec) => {
            const visual =
              createVisual(
                baseAnalysis,
                "kpi",
              );

            if (!visual) {
              return;
            }

            const configured = {
              ...visual,
              title:
                spec.title,
              subtitle: null,
              auto_title: false,
              kpi_stat:
                spec.stat,
              kpi_show_secondary:
                spec.stat ===
                "metric",
              kpi_value_alignment:
                "left" as const,
            };

            suggested.push(
              configured
            );

            suggestedResults[
              configured.visual_id
            ] =
              baseAnalysis;
          }
        );
      }

      const dimensionAnalyses =
        analyses.filter(
          (analysis) =>
            Boolean(
              analysis.dimension
            ) &&
            analysis.grouped_results
              .length > 0
        );

      const timeAnalyses =
        dimensionAnalyses.filter(
          (analysis) =>
            isSemanticTimeDimension(
              dataModelStudio,
              analysis.dimension_table ??
                null,
              analysis.dimension,
            )
        );

      const categoricalAnalyses =
        dimensionAnalyses.filter(
          (analysis) =>
            !isSemanticTimeDimension(
              dataModelStudio,
              analysis.dimension_table ??
                null,
              analysis.dimension,
            )
        );

      const usedAnalysisIds =
        new Set<string>();

      const addFromAnalysis = (
        analysis:
          AnalysisResultData | undefined,
        visualType:
          DashboardVisualType
      ) => {
        if (!analysis) {
          return;
        }

        const visual =
          createVisual(
            analysis,
            visualType,
          );

        if (!visual) {
          return;
        }

        suggested.push(
          visual
        );

        if (
          analysis.analysis_id
        ) {
          usedAnalysisIds.add(
            analysis.analysis_id
          );
        }
      };

      addFromAnalysis(
        timeAnalyses[0],
        "line",
      );

      addFromAnalysis(
        categoricalAnalyses[0],
        "bar",
      );

      addFromAnalysis(
        categoricalAnalyses[1] ??
          categoricalAnalyses[0],
        "column",
      );

      const additiveCategorical =
        categoricalAnalyses.find(
          (analysis) => {
            const definition =
              kpiDefinitions.find(
                (item) =>
                  item.code ===
                  analysis.kpi_code
              );

            return [
              "sum",
              "count",
            ].includes(
              definition?.aggregation ??
              ""
            );
          }
        );

      addFromAnalysis(
        additiveCategorical,
        "donut",
      );

      const tableAnalysis =
        dimensionAnalyses.find(
          (analysis) =>
            !analysis.analysis_id ||
            !usedAnalysisIds.has(
              analysis.analysis_id
            )
        ) ??
        dimensionAnalyses[0];

      addFromAnalysis(
        tableAnalysis,
        "table",
      );

      if (suggested.length === 0) {
        setCreateVisualError(
          "Create at least one KPI or saved analysis before building a suggested dashboard."
        );
        return;
      }

      const canvasWidth =
        Math.max(
          DASHBOARD_CANVAS_MIN_WIDTH,
          canvasSurfaceRef.current
            ?.clientWidth ??
            DASHBOARD_CANVAS_MIN_WIDTH
        );

      const padding = 16;
      const gap = 16;
      const availableWidth =
        canvasWidth -
        padding * 2;

      const kpis =
        suggested.filter(
          (visual) =>
            visual.visual_type ===
            "kpi"
        );

      const line =
        suggested.find(
          (visual) =>
            visual.visual_type ===
            "line" ||
            visual.visual_type ===
            "area"
        ) ??
        null;

      const donut =
        suggested.find(
          (visual) =>
            visual.visual_type ===
            "donut" ||
            visual.visual_type ===
            "pie"
        ) ??
        null;

      const comparisons =
        suggested.filter(
          (visual) =>
            visual.visual_type ===
              "bar" ||
            visual.visual_type ===
              "column"
        );

      const table =
        suggested.find(
          (visual) =>
            visual.visual_type ===
            "table"
        ) ??
        null;

      const arranged =
        new Map<
          string,
          DashboardVisualData
        >();

      let y = padding;

      if (kpis.length > 0) {
        const columns =
          Math.min(
            4,
            kpis.length
          );

        const width =
          Math.floor(
            (
              availableWidth -
              gap *
                (columns - 1)
            ) /
            columns
          );

        kpis.forEach(
          (visual, index) => {
            arranged.set(
              visual.visual_id,
              {
                ...visual,
                canvas_x:
                  padding +
                  index *
                    (
                      width +
                      gap
                    ),
                canvas_y: y,
                canvas_width:
                  width,
                canvas_height:
                  136,
              }
            );
          }
        );

        y += 152;
      }

      if (line && donut) {
        const rowWidth =
          availableWidth -
          gap;

        const lineWidth =
          Math.floor(
            rowWidth *
            0.66
          );

        arranged.set(
          line.visual_id,
          {
            ...line,
            canvas_x: padding,
            canvas_y: y,
            canvas_width:
              lineWidth,
            canvas_height: 320,
          }
        );

        arranged.set(
          donut.visual_id,
          {
            ...donut,
            canvas_x:
              padding +
              lineWidth +
              gap,
            canvas_y: y,
            canvas_width:
              rowWidth -
              lineWidth,
            canvas_height: 320,
          }
        );

        y += 336;
      } else if (line) {
        arranged.set(
          line.visual_id,
          {
            ...line,
            canvas_x: padding,
            canvas_y: y,
            canvas_width:
              availableWidth,
            canvas_height: 320,
          }
        );

        y += 336;
      } else if (donut) {
        arranged.set(
          donut.visual_id,
          {
            ...donut,
            canvas_x: padding,
            canvas_y: y,
            canvas_width:
              Math.min(
                420,
                availableWidth
              ),
            canvas_height: 300,
          }
        );

        y += 316;
      }

      if (
        comparisons.length > 0
      ) {
        const columns =
          Math.min(
            2,
            comparisons.length
          );

        const width =
          Math.floor(
            (
              availableWidth -
              gap *
                (columns - 1)
            ) /
            columns
          );

        comparisons.forEach(
          (visual, index) => {
            arranged.set(
              visual.visual_id,
              {
                ...visual,
                canvas_x:
                  padding +
                  index *
                    (
                      width +
                      gap
                    ),
                canvas_y: y,
                canvas_width:
                  width,
                canvas_height:
                  280,
              }
            );
          }
        );

        y += 296;
      }

      if (table) {
        arranged.set(
          table.visual_id,
          {
            ...table,
            canvas_x: padding,
            canvas_y: y,
            canvas_width:
              availableWidth,
            canvas_height: 300,
          }
        );
      }

      const nextVisuals =
        suggested.map(
          (visual) =>
            arranged.get(
              visual.visual_id
            ) ??
            placeVisualInFreeSlot(
              [],
              visual
            )
        );

      setPreviewResults(
        (previous) => ({
          ...previous,
          ...suggestedResults,
        })
      );

      setVisuals(
        nextVisuals
      );

      setSelectedVisualIds(
        []
      );

      setEditingVisualId(
        null
      );
    } catch (error) {
      setCreateVisualError(
        error instanceof Error
          ? error.message
          : "Could not build the suggested dashboard."
      );
    } finally {
      setCreatingVisual(false);
    }
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

    setSelectedVisualIds(
      (previous) =>
        previous.filter(
          (id) =>
            id !== visualId
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

  function placeVisualInFreeSlot(
    previous:
      DashboardVisualData[],
    visual:
      DashboardVisualData
  ): DashboardVisualData {
    const defaults =
      defaultVisualCanvasSize(
        visual
      );

    const width =
      visual.canvas_width ??
      defaults.width;

    const height =
      visual.canvas_height ??
      defaults.height;

    const canvasWidth =
      Math.max(
        DASHBOARD_CANVAS_MIN_WIDTH,
        canvasSurfaceRef.current
          ?.clientWidth ??
          DASHBOARD_CANVAS_MIN_WIDTH
      );

    const gap =
      DASHBOARD_VISUAL_GAP;

    const overlaps = (
      x: number,
      y: number
    ) =>
      previous.some(
        (item) => {
          const itemDefaults =
            defaultVisualCanvasSize(
              item
            );

          const itemX =
            item.canvas_x ?? 0;
          const itemY =
            item.canvas_y ?? 0;
          const itemW =
            item.canvas_width ??
            itemDefaults.width;
          const itemH =
            item.canvas_height ??
            itemDefaults.height;

          return !(
            x + width + gap <=
              itemX ||
            x >=
              itemX +
                itemW +
                gap ||
            y + height + gap <=
              itemY ||
            y >=
              itemY +
                itemH +
                gap
          );
        }
      );

    const step =
      Math.max(
        DASHBOARD_GRID_SIZE,
        16
      );

    for (
      let y = 0;
      y < 5000;
      y += step
    ) {
      for (
        let x = 0;
        x + width <=
          canvasWidth;
        x += step
      ) {
        if (!overlaps(x, y)) {
          return {
            ...visual,
            canvas_x: x,
            canvas_y: y,
            canvas_width:
              width,
            canvas_height:
              height,
          };
        }
      }
    }

    const bottom =
      previous.reduce(
        (max, item) => {
          const defaults =
            defaultVisualCanvasSize(
              item
            );

          return Math.max(
            max,
            (item.canvas_y ?? 0) +
              (
                item.canvas_height ??
                defaults.height
              )
          );
        },
        0
      );

    return {
      ...visual,
      canvas_x: 0,
      canvas_y:
        bottom + gap,
      canvas_width:
        width,
      canvas_height:
        height,
    };
  }

  function alignSelectedVisuals(
    action:
      | "left"
      | "right"
      | "top"
      | "bottom"
      | "same-width"
      | "same-height"
      | "distribute-horizontal"
      | "distribute-vertical"
  ) {
    if (
      selectedVisualIds.length <
      2
    ) {
      return;
    }

    setVisuals(
      (previous) => {
        const selected =
          previous.filter(
            (visual) =>
              selectedVisualIds.includes(
                visual.visual_id
              )
          );

        if (
          selected.length < 2
        ) {
          return previous;
        }

        const anchor =
          selected.find(
            (visual) =>
              visual.visual_id ===
              editingVisualId
          ) ??
          selected[0];

        const anchorDefaults =
          defaultVisualCanvasSize(
            anchor
          );

        const anchorX =
          anchor.canvas_x ?? 0;
        const anchorY =
          anchor.canvas_y ?? 0;
        const anchorWidth =
          anchor.canvas_width ??
          anchorDefaults.width;
        const anchorHeight =
          anchor.canvas_height ??
          anchorDefaults.height;

        if (
          action ===
          "distribute-horizontal" &&
          selected.length >= 3
        ) {
          const ordered =
            [...selected].sort(
              (left, right) =>
                (left.canvas_x ?? 0) -
                (right.canvas_x ?? 0)
            );

          const leftEdge =
            ordered[0].canvas_x ?? 0;

          const last =
            ordered[
              ordered.length - 1
            ];

          const lastDefaults =
            defaultVisualCanvasSize(
              last
            );

          const rightEdge =
            (last.canvas_x ?? 0) +
            (
              last.canvas_width ??
              lastDefaults.width
            );

          const totalWidth =
            ordered.reduce(
              (sum, visual) => {
                const defaults =
                  defaultVisualCanvasSize(
                    visual
                  );

                return (
                  sum +
                  (
                    visual.canvas_width ??
                    defaults.width
                  )
                );
              },
              0
            );

          const gap =
            Math.max(
              0,
              (
                rightEdge -
                leftEdge -
                totalWidth
              ) /
              (ordered.length - 1)
            );

          const positions =
            new Map<
              string,
              number
            >();

          let cursor =
            leftEdge;

          ordered.forEach(
            (visual) => {
              positions.set(
                visual.visual_id,
                cursor
              );

              const defaults =
                defaultVisualCanvasSize(
                  visual
                );

              cursor +=
                (
                  visual.canvas_width ??
                  defaults.width
                ) +
                gap;
            }
          );

          return previous.map(
            (visual) =>
              positions.has(
                visual.visual_id
              )
                ? {
                    ...visual,
                    canvas_x:
                      positions.get(
                        visual.visual_id
                      )!,
                  }
                : visual
          );
        }

        if (
          action ===
          "distribute-vertical" &&
          selected.length >= 3
        ) {
          const ordered =
            [...selected].sort(
              (left, right) =>
                (left.canvas_y ?? 0) -
                (right.canvas_y ?? 0)
            );

          const topEdge =
            ordered[0].canvas_y ?? 0;

          const last =
            ordered[
              ordered.length - 1
            ];

          const lastDefaults =
            defaultVisualCanvasSize(
              last
            );

          const bottomEdge =
            (last.canvas_y ?? 0) +
            (
              last.canvas_height ??
              lastDefaults.height
            );

          const totalHeight =
            ordered.reduce(
              (sum, visual) => {
                const defaults =
                  defaultVisualCanvasSize(
                    visual
                  );

                return (
                  sum +
                  (
                    visual.canvas_height ??
                    defaults.height
                  )
                );
              },
              0
            );

          const gap =
            Math.max(
              0,
              (
                bottomEdge -
                topEdge -
                totalHeight
              ) /
              (ordered.length - 1)
            );

          const positions =
            new Map<
              string,
              number
            >();

          let cursor =
            topEdge;

          ordered.forEach(
            (visual) => {
              positions.set(
                visual.visual_id,
                cursor
              );

              const defaults =
                defaultVisualCanvasSize(
                  visual
                );

              cursor +=
                (
                  visual.canvas_height ??
                  defaults.height
                ) +
                gap;
            }
          );

          return previous.map(
            (visual) =>
              positions.has(
                visual.visual_id
              )
                ? {
                    ...visual,
                    canvas_y:
                      positions.get(
                        visual.visual_id
                      )!,
                  }
                : visual
          );
        }

        return previous.map(
          (visual) => {
            if (
              !selectedVisualIds.includes(
                visual.visual_id
              )
            ) {
              return visual;
            }

            if (action === "left") {
              return {
                ...visual,
                canvas_x:
                  anchorX,
              };
            }

            if (action === "right") {
              const defaults =
                defaultVisualCanvasSize(
                  visual
                );

              const width =
                visual.canvas_width ??
                defaults.width;

              return {
                ...visual,
                canvas_x:
                  anchorX +
                  anchorWidth -
                  width,
              };
            }

            if (action === "top") {
              return {
                ...visual,
                canvas_y:
                  anchorY,
              };
            }

            if (action === "bottom") {
              const defaults =
                defaultVisualCanvasSize(
                  visual
                );

              const height =
                visual.canvas_height ??
                defaults.height;

              return {
                ...visual,
                canvas_y:
                  anchorY +
                  anchorHeight -
                  height,
              };
            }

            if (
              action ===
              "same-width"
            ) {
              return {
                ...visual,
                canvas_width:
                  Math.max(
                    visualMinWidth(
                      visual
                    ),
                    anchorWidth
                  ),
              };
            }

            return {
              ...visual,
              canvas_height:
                Math.max(
                  visualMinHeight(
                    visual
                  ),
                  anchorHeight
                ),
            };
          }
        );
      }
    );
  }

  function arrangeProfessionalDashboard() {
    const padding = 16;
    const gap = 16;

    const measuredWidth =
      canvasSurfaceRef.current
        ?.clientWidth ??
      DASHBOARD_CANVAS_MIN_WIDTH;

    const canvasWidth =
      Math.max(
        DASHBOARD_CANVAS_MIN_WIDTH,
        measuredWidth
      );

    const availableWidth =
      canvasWidth -
      padding * 2;

    setVisuals(
      (previous) => {
        const kpis =
          previous.filter(
            (visual) =>
              visual.visual_type ===
              "kpi"
          );

        const charts =
          previous.filter(
            (visual) =>
              visual.visual_type !==
              "kpi"
          );

        const arranged =
          new Map<
            string,
            DashboardVisualData
          >();

        let nextY = padding;

        if (kpis.length > 0) {
          const cardHeight = 136;

          if (kpis.length === 1) {
            const cardWidth =
              Math.min(
                340,
                Math.max(
                  260,
                  Math.floor(
                    availableWidth *
                    0.28
                  )
                )
              );

            arranged.set(
              kpis[0].visual_id,
              {
                ...kpis[0],
                canvas_x: padding,
                canvas_y: nextY,
                canvas_width:
                  cardWidth,
                canvas_height:
                  cardHeight,
              }
            );

            nextY +=
              cardHeight +
              gap;
          } else {
            const perRow =
              Math.min(
                4,
                kpis.length
              );

            const cardWidth =
              Math.floor(
                (
                  availableWidth -
                  gap *
                    (perRow - 1)
                ) /
                perRow
              );

            kpis.forEach(
              (visual, index) => {
                const row =
                  Math.floor(
                    index /
                    perRow
                  );

                const column =
                  index %
                  perRow;

                arranged.set(
                  visual.visual_id,
                  {
                    ...visual,
                    canvas_x:
                      padding +
                      column *
                        (
                          cardWidth +
                          gap
                        ),
                    canvas_y:
                      nextY +
                      row *
                        (
                          cardHeight +
                          gap
                        ),
                    canvas_width:
                      cardWidth,
                    canvas_height:
                      cardHeight,
                  }
                );
              }
            );

            nextY +=
              Math.ceil(
                kpis.length /
                perRow
              ) *
                (
                  cardHeight +
                  gap
                );
          }
        }

        if (charts.length === 1) {
          arranged.set(
            charts[0].visual_id,
            {
              ...charts[0],
              canvas_x: padding,
              canvas_y: nextY,
              canvas_width:
                availableWidth,
              canvas_height: 320,
            }
          );

          nextY += 336;
        }

        if (charts.length >= 2) {
          const rowWidth =
            availableWidth -
            gap;

          const primaryWidth =
            Math.floor(
              rowWidth *
              0.62
            );

          const secondaryWidth =
            rowWidth -
            primaryWidth;

          arranged.set(
            charts[0].visual_id,
            {
              ...charts[0],
              canvas_x: padding,
              canvas_y: nextY,
              canvas_width:
                primaryWidth,
              canvas_height: 320,
            }
          );

          arranged.set(
            charts[1].visual_id,
            {
              ...charts[1],
              canvas_x:
                padding +
                primaryWidth +
                gap,
              canvas_y: nextY,
              canvas_width:
                secondaryWidth,
              canvas_height: 320,
            }
          );

          nextY += 336;
        }

        if (charts.length === 3) {
          arranged.set(
            charts[2].visual_id,
            {
              ...charts[2],
              canvas_x: padding,
              canvas_y: nextY,
              canvas_width:
                availableWidth,
              canvas_height: 280,
            }
          );

          nextY += 296;
        }

        const remaining =
          charts.length === 3
            ? []
            : charts.slice(2);

        if (remaining.length > 0) {
          const columns =
            canvasWidth >= 1250
              ? 3
              : 2;

          const cardWidth =
            Math.floor(
              (
                availableWidth -
                gap *
                  (columns - 1)
              ) /
              columns
            );

          remaining.forEach(
            (visual, index) => {
              const column =
                index %
                columns;

              const row =
                Math.floor(
                  index /
                  columns
                );

              arranged.set(
                visual.visual_id,
                {
                  ...visual,
                  canvas_x:
                    padding +
                    column *
                      (
                        cardWidth +
                        gap
                      ),
                  canvas_y:
                    nextY +
                    row *
                      276,
                  canvas_width:
                    cardWidth,
                  canvas_height:
                    260,
                }
              );
            }
          );
        }

        return previous.map(
          (visual) =>
            arranged.get(
              visual.visual_id
            ) ??
            visual
        );
      }
    );
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
    setSelectedVisualIds(
      (previous) =>
        previous.includes(
          visual.visual_id
        )
          ? previous
          : [
              visual.visual_id,
            ]
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
    const height =
      visual.canvas_height ?? 300;

    const move = (
      moveEvent: PointerEvent
    ) => {
      const maxX =
        Math.max(
          0,
          canvasWidth - width
        );

      let nextX =
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

      const maxY =
        Math.max(
          0,
          DASHBOARD_CANVAS_MIN_HEIGHT -
            height
        );

      let nextY =
        Math.min(
          maxY,
          Math.max(
            0,
            snapCanvasValue(
              startY +
                moveEvent.clientY -
                pointerY,
              showCanvasGrid
            )
          )
        );

      const tolerance = 6;

      let guideX:
        number | null = null;
      let guideY:
        number | null = null;

      const otherVisuals =
        visuals.filter(
          (item) =>
            item.visual_id !==
            visual.visual_id
        );

      const xCandidates:
        Array<{
          snap: number;
          guide: number;
        }> = [];

      const yCandidates:
        Array<{
          snap: number;
          guide: number;
        }> = [];

      otherVisuals.forEach(
        (item) => {
          const defaults =
            defaultVisualCanvasSize(
              item
            );

          const itemX =
            item.canvas_x ?? 0;
          const itemY =
            item.canvas_y ?? 0;
          const itemWidth =
            item.canvas_width ??
            defaults.width;
          const itemHeight =
            item.canvas_height ??
            defaults.height;

          const itemCenterX =
            itemX +
            itemWidth / 2;
          const itemCenterY =
            itemY +
            itemHeight / 2;

          const movingCenterX =
            width / 2;
          const movingCenterY =
            height / 2;

          [
            {
              snap: itemX,
              guide: itemX,
            },
            {
              snap:
                itemCenterX -
                movingCenterX,
              guide:
                itemCenterX,
            },
            {
              snap:
                itemX +
                itemWidth -
                width,
              guide:
                itemX +
                itemWidth,
            },
          ].forEach(
            (candidate) =>
              xCandidates.push(
                candidate
              )
          );

          [
            {
              snap: itemY,
              guide: itemY,
            },
            {
              snap:
                itemCenterY -
                movingCenterY,
              guide:
                itemCenterY,
            },
            {
              snap:
                itemY +
                itemHeight -
                height,
              guide:
                itemY +
                itemHeight,
            },
          ].forEach(
            (candidate) =>
              yCandidates.push(
                candidate
              )
          );
        }
      );

      const xMatch =
        xCandidates
          .map(
            (candidate) => ({
              ...candidate,
              distance:
                Math.abs(
                  candidate.snap -
                  nextX
                ),
            })
          )
          .filter(
            (candidate) =>
              candidate.distance <=
              tolerance
          )
          .sort(
            (left, right) =>
              left.distance -
              right.distance
          )[0];

      if (xMatch) {
        nextX =
          Math.min(
            maxX,
            Math.max(
              0,
              xMatch.snap
            )
          );
        guideX =
          xMatch.guide;
      }

      const yMatch =
        yCandidates
          .map(
            (candidate) => ({
              ...candidate,
              distance:
                Math.abs(
                  candidate.snap -
                  nextY
                ),
            })
          )
          .filter(
            (candidate) =>
              candidate.distance <=
              tolerance
          )
          .sort(
            (left, right) =>
              left.distance -
              right.distance
          )[0];

      if (yMatch) {
        nextY =
          Math.min(
            maxY,
            Math.max(
              0,
              yMatch.snap
            )
          );
        guideY =
          yMatch.guide;
      }

      setSnapGuides({
        x: guideX,
        y: guideY,
      });

      updateVisual(
        visual.visual_id,
        {
          canvas_x: nextX,
          canvas_y: nextY,
        }
      );
    };

    const stop = () => {
      setSnapGuides({
        x: null,
        y: null,
      });

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
    setSelectedVisualIds(
      (previous) =>
        previous.includes(
          visual.visual_id
        )
          ? previous
          : [
              visual.visual_id,
            ]
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
    const y =
      visual.canvas_y ?? 0;

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

      const maxHeight =
        Math.max(
          minimumHeight,
          DASHBOARD_CANVAS_MIN_HEIGHT -
            y
        );

      const nextHeight =
        Math.min(
          maxHeight,
          Math.max(
            minimumHeight,
            snapCanvasValue(
              startHeight +
                moveEvent.clientY -
                pointerY,
              showCanvasGrid
            )
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
    DASHBOARD_CANVAS_MIN_HEIGHT;

  const activeFormatStyle =
    currentFormatStyle();

  return (
    <section
      className={
        "personal-dashboard-builder mode-" +
        dashboardMode
      }
    >
      {draftRecovered && (
        <div className="dashboard-draft-recovered">
          <strong>Unsaved dashboard draft restored.</strong>
          <span>
            Your latest local canvas was recovered. Save the dashboard to persist it to the workspace.
          </span>
        </div>
      )}

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
              (
                analyses.length === 0 &&
                reusableKpiDefinitions.length === 0
              ) ||
              creatingVisual
            }
            onClick={() =>
              void addSuggestedDashboard()
            }
          >
            {creatingVisual
              ? "Building dashboard..."
              : "Build suggested dashboard"}
          </button>

          <button
            type="button"
            className="new-workspace-button"
            disabled={
              loading ||
              visuals.length === 0
            }
            onClick={() =>
              void onSave(
                visuals,
                dashboardTitle.trim() || "Dashboard",
                dashboardSubtitle.trim() || null,
                dashboardTheme,
                dashboardFilters,
              ).then(() => {
                try {
                  window.localStorage.removeItem(
                    draftKey,
                  );
                } catch {
                  // Saving to the server already succeeded.
                }

                setDraftRecovered(
                  false
                );
              })
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
          "dashboard-builder-layout" +
          (
            dashboardMode ===
              "edit" &&
            editingVisual &&
            propertiesPanelOpen
              ? " properties-open"
              : ""
          ) +
          (
            dashboardMode ===
              "edit" &&
            !analysisLibraryOpen
              ? " analysis-library-collapsed"
              : ""
          )
        }
      >
        <aside
          className={
            "dashboard-analysis-library" +
            (
              analysisLibraryOpen
                ? ""
                : " collapsed"
            )
          }
        >
          <div className="dashboard-panel-heading">
            <div>
              <span className="workspace-overview-label">
                DASHBOARD CONTENT
              </span>

              <strong>
                Add visual
              </strong>
            </div>

            {dashboardMode === "edit" && (
              <button
                type="button"
                className="dashboard-analysis-library-toggle"
                onClick={() =>
                  setAnalysisLibraryOpen(
                    false
                  )
                }
                title="Hide saved analyses"
                aria-label="Hide saved analyses"
              >
                ‹
              </button>
            )}
          </div>

          <div className="dashboard-create-visual-panel">
            <span className="dashboard-create-visual-eyebrow">
              CREATE VISUAL
            </span>

            <label className="dashboard-create-visual-field">
              <span>
                Measure / KPI
              </span>

              <DashboardSelect
                value={
                  pendingVisualKpiCode
                }
                options={
                  reusableKpiDefinitions.map(
                    (item) => ({
                      value:
                        item.code,
                      label:
                        item.title,
                    })
                  )
                }
                onChange={
                  setPendingVisualKpiCode
                }
                placeholder="Select measure"
              />
            </label>

            <label className="dashboard-create-visual-field">
              <span>
                Dimension
              </span>

              <DashboardSelect
                value={
                  pendingVisualDimensionKey
                }
                options={[
                  {
                    value: "",
                    label:
                      "None · KPI card",
                  },
                  ...dimensionOptions.map(
                    (option) => ({
                      value:
                        option.value,
                      label:
                        option.label,
                    })
                  ),
                ]}
                onChange={(value) => {
                  setPendingVisualDimensionKey(
                    value
                  );
                  setPendingVisualType(
                    "auto"
                  );
                }}
                placeholder="Optional"
              />
            </label>

            <label className="dashboard-create-visual-field">
              <span>
                Visual type
              </span>

              <DashboardSelect
                value={
                  pendingVisualType
                }
                options={
                  directVisualTypeOptions
                }
                onChange={(value) =>
                  setPendingVisualType(
                    value as
                      | "auto"
                      | DashboardVisualType
                  )
                }
              />
            </label>

            <button
              type="button"
              className="dashboard-create-visual-button"
              disabled={
                !pendingVisualKpiCode ||
                creatingVisual
              }
              onClick={() =>
                void addDirectVisual()
              }
            >
              {creatingVisual
                ? "Adding..."
                : "+ Add to dashboard"}
            </button>

            {createVisualError && (
              <small className="dashboard-create-visual-error">
                {createVisualError}
              </small>
            )}

            <div className="dashboard-create-visual-auto-hint">
              <strong>
                Auto:
              </strong>

              <span>
                {!pendingDimensionOption
                  ? "KPI card"
                  : pendingDimensionIsTime
                    ? "Time chart. Auto uses columns for a few time periods and a line for a longer series."
                    : "Horizontal bar because the selected field is a categorical dimension."}
              </span>
            </div>

            {!pendingDimensionOption &&
              pendingVisualKpiCode && (
              <small className="dashboard-create-visual-hint">
                Select a dimension only when you want to break this measure down into categories or time.
              </small>
            )}

            {pendingDimensionOption &&
              !pendingKpiIsAdditive && (
              <small className="dashboard-create-visual-hint">
                Pie and donut are hidden because this measure is not marked as additive (sum/count).
              </small>
            )}
          </div>

          <div className="dashboard-saved-analysis-divider">
            <span>
              SAVED ANALYSES
            </span>
          </div>

          <div className="dashboard-analysis-list">
            {analyses.map(
              (analysis, index) => {
                const recommendation =
                  recommendedVisual(
                    analysis,
                    isSemanticTimeDimension(
                      dataModelStudio,
                      analysis.dimension_table ??
                        null,
                      analysis.dimension,
                    )
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
              No saved analyses yet. You can still create visuals directly above.
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
                                editingIsTime,
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
                          isSemanticTimeDimension(
                            dataModelStudio,
                            dimensionTable,
                            dimension,
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
                                isSemanticTimeDimension(
                                  dataModelStudio,
                                  dimensionTable,
                                  dimension,
                                ),
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
                          isSemanticTimeDimension(
                            dataModelStudio,
                            dimensionTable,
                            dimension,
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
                                isSemanticTimeDimension(
                                  dataModelStudio,
                                  dimensionTable,
                                  dimension,
                                ),
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
                                  editingIsTime,
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
                                      editingIsTime,
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
                                      editingIsTime,
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
          ref={pageViewportRef}
          style={{
            "--dashboard-theme-accent":
              DASHBOARD_THEMES[
                dashboardTheme
              ].accent,
            "--dashboard-page-scale":
              interactScale,
            "--dashboard-page-width":
              DASHBOARD_PAGE_WIDTH + "px",
            "--dashboard-page-height":
              DASHBOARD_PAGE_HEIGHT + "px",
          } as CSSProperties}
        >
          <div className="dashboard-canvas-heading">
            <div>
              {dashboardMode === "edit" &&
                !analysisLibraryOpen && (
                <button
                  type="button"
                  className="dashboard-analysis-reopen-button"
                  onClick={() =>
                    setAnalysisLibraryOpen(
                      true
                    )
                  }
                  title="Open saved analyses"
                >
                  › Analyses
                </button>
              )}

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
                    setSelectedVisualIds(
                      []
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
                  className="dashboard-auto-layout-button"
                  disabled={
                    visuals.length === 0
                  }
                  onClick={
                    arrangeProfessionalDashboard
                  }
                  title="Arrange visuals into a professional dashboard layout"
                >
                  Auto arrange
                </button>
              )}

              {dashboardMode === "edit" && (
                <div
                  className="dashboard-align-toolbar"
                  aria-label="Visual alignment tools"
                >
                  <div className="dashboard-align-group">
                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 2
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "left"
                        )
                      }
                      title="Align left"
                      aria-label="Align left"
                    >
                      ↤
                    </button>

                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 2
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "right"
                        )
                      }
                      title="Align right"
                      aria-label="Align right"
                    >
                      ↦
                    </button>

                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 2
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "top"
                        )
                      }
                      title="Align top"
                      aria-label="Align top"
                    >
                      ↥
                    </button>

                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 2
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "bottom"
                        )
                      }
                      title="Align bottom"
                      aria-label="Align bottom"
                    >
                      ↧
                    </button>
                  </div>

                  <div className="dashboard-align-group">
                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 2
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "same-width"
                        )
                      }
                      title="Same width"
                      aria-label="Same width"
                    >
                      W
                    </button>

                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 2
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "same-height"
                        )
                      }
                      title="Same height"
                      aria-label="Same height"
                    >
                      H
                    </button>
                  </div>

                  <div className="dashboard-align-group">
                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 3
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "distribute-horizontal"
                        )
                      }
                      title="Distribute horizontally"
                      aria-label="Distribute horizontally"
                    >
                      ↔
                    </button>

                    <button
                      type="button"
                      disabled={
                        selectedVisualIds.length < 3
                      }
                      onClick={() =>
                        alignSelectedVisuals(
                          "distribute-vertical"
                        )
                      }
                      title="Distribute vertically"
                      aria-label="Distribute vertically"
                    >
                      ↕
                    </button>
                  </div>
                </div>
              )}

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

              <div
                className={
                  "dashboard-slicer-toolbar dashboard-report-slicers mode-" +
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
                    <div className="dashboard-slicer-picker">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() =>
                          setSlicerPickerOpen(
                            (previous) =>
                              !previous
                          )
                        }
                        aria-expanded={
                          slicerPickerOpen
                        }
                      >
                        + Add slicer
                      </button>

                      {slicerPickerOpen && (
                        <div className="dashboard-slicer-picker-menu">
                          {dimensionOptions
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
                              (option) => (
                                <button
                                  key={
                                    option.value
                                  }
                                  type="button"
                                  onClick={() => {
                                    setSlicerPickerOpen(
                                      false
                                    );
                                    void addDashboardFilterByKey(
                                      option.value
                                    );
                                  }}
                                >
                                  <span>
                                    {option.column}
                                  </span>

                                  <small>
                                    {option.table}
                                  </small>
                                </button>
                              )
                            )}

                          {dimensionOptions.filter(
                            (option) =>
                              !dashboardFilters.some(
                                (filter) =>
                                  filter.table ===
                                    option.table &&
                                  filter.column ===
                                    option.column
                              )
                          ).length === 0 && (
                            <p>
                              All available dimensions are already added.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
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
            ref={
              canvasSurfaceRef
            }
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
            {dashboardMode === "edit" &&
              snapGuides.x !== null && (
                <div
                  className="dashboard-snap-guide vertical"
                  style={{
                    left:
                      snapGuides.x +
                      "px",
                  }}
                />
              )}

            {dashboardMode === "edit" &&
              snapGuides.y !== null && (
                <div
                  className="dashboard-snap-guide horizontal"
                  style={{
                    top:
                      snapGuides.y +
                      "px",
                  }}
                />
              )}

            {visuals.map(
              (visual) => {
                const visualWidth =
                  visual.canvas_width ??
                  480;

                const visualHeight =
                  visual.canvas_height ??
                  300;

                const fitBaselineWidth =
                  visual.visual_type ===
                  "kpi"
                    ? 260
                    : 480;

                const fitBaselineHeight =
                  visual.visual_type ===
                  "kpi"
                    ? 150
                    : 300;

                const visualFitScale =
                  Math.max(
                    0.62,
                    Math.min(
                      1,
                      visualWidth /
                        fitBaselineWidth,
                      visualHeight /
                        fitBaselineHeight,
                    )
                  );

                const visualCompact =
                  visualWidth < 360 ||
                  visualHeight < 220;

                const visualVeryCompact =
                  visualWidth < 290 ||
                  visualHeight < 180;

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
                      " visual-" +
                      visual.visual_type +
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
                        selectedVisualIds.includes(
                          visual.visual_id
                        )
                          ? " selected"
                          : ""
                      ) +
                      (
                        visualCompact
                          ? " compact-visual"
                          : ""
                      ) +
                      (
                        visualVeryCompact
                          ? " very-compact-visual"
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
                      "--dashboard-fit-scale":
                        visualFitScale,
                    } as CSSProperties}
                    onClick={(event) => {
                      if (
                        dashboardMode !==
                        "edit"
                      ) {
                        return;
                      }

                      const additive =
                        event.ctrlKey ||
                        event.metaKey;

                      setEditingVisualId(
                        visual.visual_id
                      );

                      setSelectedVisualIds(
                        (previous) => {
                          if (!additive) {
                            return [
                              visual.visual_id,
                            ];
                          }

                          return previous.includes(
                            visual.visual_id
                          )
                            ? previous.filter(
                                (id) =>
                                  id !==
                                  visual.visual_id
                              )
                            : [
                                ...previous,
                                visual.visual_id,
                              ];
                        }
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
                          stat={
                            visual.kpi_stat ??
                            "metric"
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
                          dateOperation={
                            getSemanticDateOperation(
                              dataModelStudio,
                              visualDimensionTable,
                              visualDimension,
                            )
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
