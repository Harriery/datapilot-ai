import {
  useMemo,
  useState,
} from "react";

import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Lightbulb,
  Trophy,
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

type Props = {
  analyses: AnalysisResultData[];
  dataModelStudio?:
    | DataModelStudioData
    | null;
  kpiDefinitions?: PersonalKpiData[];
  onConfirm?: () => Promise<void>;
};

type InsightKind =
  | "top"
  | "bottom"
  | "trend"
  | "distribution";

type Insight = {
  id: string;
  kind: InsightKind;
  title: string;
  summary: string;
  evidence: string;
  dimension: string;
  value?: number | null;
};

type InsightCandidate = {
  row:
    AnalysisResultData["grouped_results"][number];
  metric: number;
};

const MONTH_LABELS = [
  "",
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const HIGH_CARDINALITY_THRESHOLD = 20;
const DEFAULT_VISIBLE_FINDINGS = 12;

function metricValue(
  row:
    AnalysisResultData["grouped_results"][number],
  aggregation:
    AnalysisResultData["aggregation"],
): number | null {
  if (row.metric_value != null) {
    return Number(row.metric_value);
  }

  if (aggregation === "count") {
    return Number(row.count);
  }

  if (aggregation === "min") {
    return row.min == null
      ? null
      : Number(row.min);
  }

  if (aggregation === "max") {
    return row.max == null
      ? null
      : Number(row.max);
  }

  return row.mean == null
    ? null
    : Number(row.mean);
}

function formatValue(
  value: number | null | undefined,
) {
  if (
    value == null ||
    !Number.isFinite(value)
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 2,
    },
  ).format(value);
}

function labelForAnalysis(
  analysis: AnalysisResultData,
  kpis: PersonalKpiData[],
) {
  const kpi =
    analysis.kpi_code
      ? kpis.find(
          (item) =>
            item.code === analysis.kpi_code,
        )
      : undefined;

  return (
    kpi?.title ??
    analysis.measure
  );
}

function dimensionMeta(
  analysis: AnalysisResultData,
  studio?:
    | DataModelStudioData
    | null,
) {
  if (
    !analysis.dimension ||
    !studio
  ) {
    return null;
  }

  for (
    const table
    of studio.tables
  ) {
    if (
      analysis.dimension_table &&
      table.name !==
        analysis.dimension_table
    ) {
      continue;
    }

    const column =
      table.columns.find(
        (item) =>
          item.name ===
          analysis.dimension,
      );

    if (column) {
      return column;
    }
  }

  for (
    const table
    of studio.tables
  ) {
    const column =
      table.columns.find(
        (item) =>
          item.name ===
          analysis.dimension,
      );

    if (column) {
      return column;
    }
  }

  return null;
}

function semanticAnalysisKey(
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
      "no-dimension",
  ].join("::");
}

function deduplicateAnalyses(
  analyses: AnalysisResultData[],
) {
  const bySemanticBinding =
    new Map<
      string,
      AnalysisResultData
    >();

  for (
    const analysis
    of analyses
  ) {
    bySemanticBinding.set(
      semanticAnalysisKey(
        analysis,
      ),
      analysis,
    );
  }

  return [
    ...bySemanticBinding.values(),
  ];
}

function isTimeAnalysis(
  analysis: AnalysisResultData,
  studio?:
    | DataModelStudioData
    | null,
) {
  const column =
    dimensionMeta(
      analysis,
      studio,
    );

  return (
    column?.role === "time" ||
    column?.derivation?.type ===
      "date_part"
  );
}

function derivationOperation(
  analysis: AnalysisResultData,
  studio?:
    | DataModelStudioData
    | null,
) {
  return (
    dimensionMeta(
      analysis,
      studio,
    )?.derivation?.operation ??
    null
  );
}

function formatDimensionValue(
  value:
    | string
    | number
    | boolean
    | null,
  analysis: AnalysisResultData,
  studio?:
    | DataModelStudioData
    | null,
) {
  if (value == null) {
    return "Unknown";
  }

  const operation =
    derivationOperation(
      analysis,
      studio,
    );

  if (
    operation === "month" ||
    operation === "month_number"
  ) {
    const month =
      Number(value);

    if (
      Number.isInteger(month) &&
      month >= 1 &&
      month <= 12
    ) {
      return MONTH_LABELS[month];
    }
  }

  if (
    operation === "quarter"
  ) {
    const raw =
      String(value)
        .trim()
        .replace(/^q/i, "");

    const quarter =
      Number(raw);

    if (
      Number.isInteger(quarter) &&
      quarter >= 1 &&
      quarter <= 4
    ) {
      return `Q${quarter}`;
    }
  }

  return String(value);
}

function orderedTrendRows(
  analysis: AnalysisResultData,
  studio?:
    | DataModelStudioData
    | null,
) {
  const rows =
    analysis.grouped_results.filter(
      (row) =>
        row.value != null,
    );

  const operation =
    derivationOperation(
      analysis,
      studio,
    );

  const numericRank = (
    value: unknown,
  ) => {
    const normalized =
      String(value)
        .trim()
        .replace(/^q/i, "");

    const parsed =
      Number(normalized);

    return Number.isFinite(parsed)
      ? parsed
      : Number.POSITIVE_INFINITY;
  };

  return [
    ...rows,
  ].sort(
    (a, b) => {
      if (
        operation === "quarter" ||
        operation === "month" ||
        operation === "month_number" ||
        operation === "year" ||
        operation === "day"
      ) {
        return (
          numericRank(a.value) -
          numericRank(b.value)
        );
      }

      if (
        typeof a.value ===
          "number" &&
        typeof b.value ===
          "number"
      ) {
        return (
          a.value -
          b.value
        );
      }

      return String(
        a.value,
      ).localeCompare(
        String(b.value),
      );
    },
  );
}

function minimumSampleSize(
  analysis: AnalysisResultData,
) {
  const total =
    Number(
      analysis.overall.count ??
        0,
    );

  if (
    !Number.isFinite(total) ||
    total <= 0
  ) {
    return 2;
  }

  return Math.max(
    2,
    Math.ceil(
      Math.sqrt(total) /
        10,
    ),
  );
}

function usableCandidates(
  analysis: AnalysisResultData,
) {
  return (
    analysis.grouped_results
      .map(
        (row) => ({
          row,
          metric:
            metricValue(
              row,
              analysis.aggregation,
            ),
        }),
      )
      .filter(
        (
          item,
        ): item is InsightCandidate =>
          item.metric != null &&
          Number.isFinite(
            item.metric,
          ) &&
          item.row.value != null,
      )
  );
}

function rankingCandidates(
  analysis: AnalysisResultData,
  candidates: InsightCandidate[],
) {
  if (
    analysis.aggregation !==
      "mean" &&
    analysis.aggregation !==
      "custom"
  ) {
    return candidates;
  }

  const minSample =
    minimumSampleSize(
      analysis,
    );

  const qualified =
    candidates.filter(
      (item) =>
        item.row.count >=
        minSample,
    );

  return (
    qualified.length >= 2
      ? qualified
      : candidates
  );
}

function buildInsights(
  analyses: AnalysisResultData[],
  studio:
    | DataModelStudioData
    | null
    | undefined,
  kpis: PersonalKpiData[],
): Insight[] {
  const insights: Insight[] = [];

  const uniqueAnalyses =
    deduplicateAnalyses(
      analyses,
    );

  for (
    const analysis
    of uniqueAnalyses
  ) {
    if (
      !analysis.dimension ||
      analysis.grouped_results.length <
        2
    ) {
      continue;
    }

    const measureLabel =
      labelForAnalysis(
        analysis,
        kpis,
      );

    const dimensionLabel =
      analysis.dimension;

    const usable =
      usableCandidates(
        analysis,
      );

    if (
      usable.length < 2
    ) {
      continue;
    }

    const rankingPool =
      rankingCandidates(
        analysis,
        usable,
      );

    if (
      rankingPool.length < 2
    ) {
      continue;
    }

    const sorted = [
      ...rankingPool,
    ].sort(
      (a, b) =>
        b.metric -
        a.metric,
    );

    const top =
      sorted[0];

    const bottom =
      sorted[
        sorted.length - 1
      ];

    const topLabel =
      formatDimensionValue(
        top.row.value,
        analysis,
        studio,
      );

    const bottomLabel =
      formatDimensionValue(
        bottom.row.value,
        analysis,
        studio,
      );

    const evidence =
      `${measureLabel} by ${dimensionLabel}`;

    insights.push({
      id:
        `${semanticAnalysisKey(analysis)}-top`,
      kind: "top",
      title:
        `Highest ${measureLabel}`,
      summary:
        `${topLabel} has the highest ${measureLabel} ` +
        `at ${formatValue(top.metric)}.`,
      evidence,
      dimension:
        dimensionLabel,
      value:
        top.metric,
    });

    const suppressBottom =
      (
        analysis.aggregation ===
          "count" ||
        analysis.aggregation ===
          "sum"
      ) &&
      usable.length >
        HIGH_CARDINALITY_THRESHOLD;

    if (
      !suppressBottom
    ) {
      insights.push({
        id:
          `${semanticAnalysisKey(analysis)}-bottom`,
        kind: "bottom",
        title:
          `Lowest ${measureLabel}`,
        summary:
          `${bottomLabel} has the lowest ${measureLabel} ` +
          `at ${formatValue(bottom.metric)}.`,
        evidence,
        dimension:
          dimensionLabel,
        value:
          bottom.metric,
      });
    }

    if (
      analysis.aggregation ===
        "count" ||
      analysis.aggregation ===
        "sum"
    ) {
      const total =
        usable.reduce(
          (
            sum,
            item,
          ) =>
            sum +
            item.metric,
          0,
        );

      if (
        total > 0
      ) {
        const share =
          (
            top.metric /
            total
          ) *
          100;

        insights.push({
          id:
            `${semanticAnalysisKey(analysis)}-distribution`,
          kind:
            "distribution",
          title:
            `Largest ${dimensionLabel} share`,
          summary:
            `${topLabel} represents ` +
            `${share.toFixed(1)}% of the grouped ${measureLabel}.`,
          evidence,
          dimension:
            dimensionLabel,
          value:
            share,
        });
      }
    }

    if (
      isTimeAnalysis(
        analysis,
        studio,
      )
    ) {
      const trendRows =
        orderedTrendRows(
          analysis,
          studio,
        )
          .map(
            (row) => ({
              row,
              metric:
                metricValue(
                  row,
                  analysis.aggregation,
                ),
            }),
          )
          .filter(
            (
              item,
            ): item is InsightCandidate =>
              item.metric != null &&
              Number.isFinite(
                item.metric,
              ),
          );

      if (
        trendRows.length >= 2
      ) {
        const first =
          trendRows[0];

        const last =
          trendRows[
            trendRows.length - 1
          ];

        const delta =
          last.metric -
          first.metric;

        const percent =
          first.metric !== 0
            ? (
                delta /
                Math.abs(
                  first.metric,
                )
              ) *
              100
            : null;

        const firstLabel =
          formatDimensionValue(
            first.row.value,
            analysis,
            studio,
          );

        const lastLabel =
          formatDimensionValue(
            last.row.value,
            analysis,
            studio,
          );

        insights.push({
          id:
            `${semanticAnalysisKey(analysis)}-trend`,
          kind: "trend",
          title:
            `${measureLabel} trend`,
          summary:
            `From ${firstLabel} to ${lastLabel}, ` +
            `${measureLabel} ${delta >= 0 ? "increased" : "decreased"} ` +
            `by ${formatValue(Math.abs(delta))}` +
            `${percent == null ? "" : ` (${Math.abs(percent).toFixed(1)}%)`}.`,
          evidence,
          dimension:
            dimensionLabel,
          value:
            delta,
        });
      }
    }
  }

  const kindOrder:
    Record<
      InsightKind,
      number
    > = {
      trend: 0,
      distribution: 1,
      top: 2,
      bottom: 3,
    };

  return insights.sort(
    (a, b) =>
      kindOrder[a.kind] -
      kindOrder[b.kind],
  );
}

function selectExecutiveSummary(
  insights: Insight[],
) {
  const selected: Insight[] = [];
  const usedEvidence =
    new Set<string>();

  const takeFirst = (
    kind: InsightKind,
  ) => {
    const match =
      insights.find(
        (insight) =>
          insight.kind ===
            kind &&
          !usedEvidence.has(
            insight.evidence,
          ),
      );

    if (match) {
      selected.push(
        match,
      );
      usedEvidence.add(
        match.evidence,
      );
    }
  };

  takeFirst("trend");
  takeFirst("distribution");

  for (
    const insight
    of insights
  ) {
    if (
      selected.length >= 5
    ) {
      break;
    }

    if (
      insight.kind !== "top" ||
      usedEvidence.has(
        insight.evidence,
      )
    ) {
      continue;
    }

    selected.push(
      insight,
    );

    usedEvidence.add(
      insight.evidence,
    );
  }

  if (
    selected.length < 4
  ) {
    for (
      const insight
      of insights
    ) {
      if (
        selected.length >= 4
      ) {
        break;
      }

      if (
        selected.some(
          (item) =>
            item.id ===
            insight.id,
        )
      ) {
        continue;
      }

      selected.push(
        insight,
      );
    }
  }

  return selected.slice(
    0,
    4,
  );
}

function kindLabel(
  kind: InsightKind,
) {
  if (kind === "trend") {
    return "Trend";
  }

  if (kind === "distribution") {
    return "Distribution";
  }

  if (kind === "top") {
    return "Top performer";
  }

  return "Lower-end";
}

function insightValueLabel(
  insight: Insight,
) {
  if (
    insight.value == null ||
    !Number.isFinite(
      insight.value,
    )
  ) {
    return null;
  }

  if (
    insight.kind ===
    "distribution"
  ) {
    return `${insight.value.toFixed(1)}%`;
  }

  if (
    insight.kind ===
    "trend"
  ) {
    const prefix =
      insight.value >= 0
        ? "+"
        : "−";

    return (
      prefix +
      formatValue(
        Math.abs(
          insight.value,
        ),
      )
    );
  }

  return formatValue(
    insight.value,
  );
}

function iconForInsight(
  kind: InsightKind,
) {
  if (
    kind === "top"
  ) {
    return (
      <Trophy size={18} />
    );
  }

  if (
    kind === "trend"
  ) {
    return (
      <ArrowUpRight
        size={18}
      />
    );
  }

  if (
    kind === "bottom"
  ) {
    return (
      <ArrowDownRight
        size={18}
      />
    );
  }

  return (
    <BarChart3
      size={18}
    />
  );
}

function sectionLabel(
  kind: InsightKind,
) {
  if (
    kind === "trend"
  ) {
    return "Trends";
  }

  if (
    kind ===
    "distribution"
  ) {
    return "Distribution";
  }

  if (
    kind === "top"
  ) {
    return "Top performers";
  }

  return "Lower-end findings";
}

export default function PersonalInsights({
  analyses,
  dataModelStudio,
  kpiDefinitions = [],
  onConfirm,
}: Props) {
  const [
    confirming,
    setConfirming,
  ] = useState(false);

  const [
    confirmError,
    setConfirmError,
  ] = useState<
    string | null
  >(null);

  const [
    showAll,
    setShowAll,
  ] = useState(false);

  const insights =
    useMemo(
      () =>
        buildInsights(
          analyses,
          dataModelStudio,
          kpiDefinitions,
        ),
      [
        analyses,
        dataModelStudio,
        kpiDefinitions,
      ],
    );

  const summary =
    useMemo(
      () =>
        selectExecutiveSummary(
          insights,
        ),
      [insights],
    );

  const visibleInsights =
    showAll
      ? insights
      : insights.slice(
          0,
          DEFAULT_VISIBLE_FINDINGS,
        );

  const groupedVisible =
    useMemo(
      () => {
        const groups =
          new Map<
            InsightKind,
            Insight[]
          >();

        for (
          const insight
          of visibleInsights
        ) {
          const existing =
            groups.get(
              insight.kind,
            ) ?? [];

          existing.push(
            insight,
          );

          groups.set(
            insight.kind,
            existing,
          );
        }

        return [
          ...groups.entries(),
        ];
      },
      [visibleInsights],
    );

  const uniqueAnalysisCount =
    useMemo(
      () =>
        deduplicateAnalyses(
          analyses,
        ).length,
      [analyses],
    );

  return (
    <section className="personal-insights">
      <header className="personal-insights-header">
        <div>
          <span className="personal-insights-eyebrow">
            INSIGHTS
          </span>

          <h2>
            Evidence-based insights
          </h2>

          <p>
            Deterministic findings generated from saved semantic analyses.
            Duplicate semantic bindings are consolidated, small-sample
            averages are guarded, and no missing values are invented.
          </p>
        </div>

        <div className="personal-insights-header-actions">
          <span className="personal-insights-badge">
            {insights.length} findings · {uniqueAnalysisCount} analyses
          </span>

          {onConfirm &&
            insights.length > 0 && (
              <button
                type="button"
                className="personal-insights-confirm"
                disabled={confirming}
                onClick={async () => {
                  setConfirming(true);
                  setConfirmError(null);

                  try {
                    await onConfirm();
                  } catch (error) {
                    setConfirmError(
                      error instanceof Error
                        ? error.message
                        : "Insights could not be confirmed.",
                    );
                  } finally {
                    setConfirming(false);
                  }
                }}
              >
                {confirming
                  ? "Confirming..."
                  : "Confirm insights"}
              </button>
            )}
        </div>
      </header>

      {confirmError && (
        <div
          className="personal-insights-error"
          role="alert"
        >
          {confirmError}
        </div>
      )}

      {analyses.length === 0 ||
      insights.length === 0 ? (
        <div className="personal-insights-empty">
          <Lightbulb
            size={22}
          />

          <div>
            <strong>
              No insight-ready analyses yet
            </strong>

            <p>
              Save grouped analyses with at least two valid groups to
              generate deterministic findings.
            </p>
          </div>
        </div>
      ) : (
        <>
          <section className="personal-insights-summary">
            <div className="personal-insights-section-title">
              <span>
                Executive summary
              </span>

              <small>
                Diverse evidence selected from the current semantic model
              </small>
            </div>

            <div className="personal-insights-summary-grid">
              {summary.map(
                (insight) => {
                  const valueLabel =
                    insightValueLabel(
                      insight,
                    );

                  return (
                    <article
                      key={
                        insight.id
                      }
                      className="personal-insight-summary-card"
                    >
                      <div className="personal-insight-summary-top">
                        <div className="personal-insight-icon">
                          {iconForInsight(
                            insight.kind,
                          )}
                        </div>

                        <span className="personal-insight-kind">
                          {kindLabel(
                            insight.kind,
                          )}
                        </span>
                      </div>

                      <div className="personal-insight-summary-main">
                        <div>
                          <strong>
                            {insight.title}
                          </strong>

                          <span className="personal-insight-dimension">
                            By {insight.dimension}
                          </span>
                        </div>

                        {valueLabel && (
                          <span className="personal-insight-metric">
                            {valueLabel}
                          </span>
                        )}
                      </div>

                      <p>
                        {insight.summary}
                      </p>

                      <small>
                        Source:{" "}
                        {insight.evidence}
                      </small>
                    </article>
                  );
                },
              )}
            </div>
          </section>

          <section className="personal-insights-detail">
            <div className="personal-insights-section-title">
              <div>
                <span>
                  Key findings
                </span>

                <small>
                  Quality-filtered evidence grouped by analytical pattern
                </small>
              </div>

              {insights.length >
                DEFAULT_VISIBLE_FINDINGS && (
                <button
                  type="button"
                  className="personal-insights-show-all personal-insights-show-all-inline"
                  onClick={() =>
                    setShowAll(
                      (current) =>
                        !current,
                    )
                  }
                >
                  {showAll
                    ? "Show fewer"
                    : `Show all (${insights.length})`}
                </button>
              )}
            </div>

            {groupedVisible.map(
              ([
                kind,
                group,
              ]) => (
                <div
                  key={kind}
                  className="personal-insights-group"
                >
                  <div className="personal-insights-group-title">
                    {sectionLabel(
                      kind,
                    )}
                  </div>

                  <div className="personal-insights-list">
                    {group.map(
                      (
                        insight,
                      ) => (
                        <article
                          key={
                            insight.id
                          }
                          className="personal-insight-row"
                        >
                          <div className="personal-insight-icon">
                            {iconForInsight(
                              insight.kind,
                            )}
                          </div>

                          <div className="personal-insight-copy">
                            <div className="personal-insight-row-heading">
                              <span className="personal-insight-kind">
                                {kindLabel(
                                  insight.kind,
                                )}
                              </span>

                              <span className="personal-insight-dimension">
                                By {insight.dimension}
                              </span>
                            </div>

                            <strong>
                              {insight.title}
                            </strong>

                            <p>
                              {insight.summary}
                            </p>

                            <small className="personal-insight-source">
                              Source: {insight.evidence}
                            </small>
                          </div>

                          {insightValueLabel(
                            insight,
                          ) && (
                            <span className="personal-insight-row-metric">
                              {insightValueLabel(
                                insight,
                              )}
                            </span>
                          )}
                        </article>
                      ),
                    )}
                  </div>
                </div>
              ),
            )}


          </section>
        </>
      )}
    </section>
  );
}
