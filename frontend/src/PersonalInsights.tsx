import { useMemo } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Lightbulb,
  Trophy,
} from "lucide-react";

import type { AnalysisResultData } from "./PersonalAnalysisPlan";
import type { DataModelStudioData } from "./DataModelCanvas";
import type { PersonalKpiData } from "./PersonalKpiCandidates";

type Props = {
  analyses: AnalysisResultData[];
  dataModelStudio?: DataModelStudioData | null;
  kpiDefinitions?: PersonalKpiData[];
};

type Insight = {
  id: string;
  kind: "top" | "bottom" | "trend" | "distribution";
  title: string;
  summary: string;
  evidence: string;
  value?: number | null;
};

function metricValue(
  row: AnalysisResultData["grouped_results"][number],
  aggregation: AnalysisResultData["aggregation"],
): number | null {
  if (row.metric_value != null) {
    return Number(row.metric_value);
  }

  if (aggregation === "count") {
    return Number(row.count);
  }

  if (aggregation === "min") {
    return row.min == null ? null : Number(row.min);
  }

  if (aggregation === "max") {
    return row.max == null ? null : Number(row.max);
  }

  return row.mean == null ? null : Number(row.mean);
}

function formatValue(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
  }).format(value);
}

function labelForAnalysis(
  analysis: AnalysisResultData,
  kpis: PersonalKpiData[],
) {
  const kpi = analysis.kpi_code
    ? kpis.find((item) => item.code === analysis.kpi_code)
    : undefined;

  return kpi?.title ?? analysis.measure;
}

function dimensionMeta(
  analysis: AnalysisResultData,
  studio?: DataModelStudioData | null,
) {
  if (!analysis.dimension || !studio) {
    return null;
  }

  for (const table of studio.tables) {
    if (
      analysis.dimension_table &&
      table.name !== analysis.dimension_table
    ) {
      continue;
    }

    const column = table.columns.find(
      (item) => item.name === analysis.dimension,
    );

    if (column) {
      return column;
    }
  }

  for (const table of studio.tables) {
    const column = table.columns.find(
      (item) => item.name === analysis.dimension,
    );

    if (column) {
      return column;
    }
  }

  return null;
}

function isTimeAnalysis(
  analysis: AnalysisResultData,
  studio?: DataModelStudioData | null,
) {
  const column = dimensionMeta(analysis, studio);

  return (
    column?.role === "time" ||
    column?.derivation?.type === "date_part"
  );
}

function orderedTrendRows(
  analysis: AnalysisResultData,
  studio?: DataModelStudioData | null,
) {
  const rows = analysis.grouped_results.filter(
    (row) => row.value != null,
  );

  const operation =
    dimensionMeta(analysis, studio)?.derivation?.operation;

  const rankQuarter = (value: unknown) => {
    const normalized = String(value).toLowerCase().replace("q", "");
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 999;
  };

  return [...rows].sort((a, b) => {
    if (operation === "quarter") {
      return rankQuarter(a.value) - rankQuarter(b.value);
    }

    if (
      operation === "month" ||
      operation === "year" ||
      operation === "day" ||
      typeof a.value === "number"
    ) {
      const left = Number(a.value);
      const right = Number(b.value);

      if (Number.isFinite(left) && Number.isFinite(right)) {
        return left - right;
      }
    }

    return String(a.value).localeCompare(String(b.value));
  });
}

function buildInsights(
  analyses: AnalysisResultData[],
  studio: DataModelStudioData | null | undefined,
  kpis: PersonalKpiData[],
): Insight[] {
  const insights: Insight[] = [];

  for (const analysis of analyses) {
    if (
      !analysis.dimension ||
      analysis.grouped_results.length < 2
    ) {
      continue;
    }

    const measureLabel = labelForAnalysis(analysis, kpis);
    const dimensionLabel = analysis.dimension;
    const usable = analysis.grouped_results
      .map((row) => ({
        row,
        metric: metricValue(row, analysis.aggregation),
      }))
      .filter(
        (
          item,
        ): item is {
          row: AnalysisResultData["grouped_results"][number];
          metric: number;
        } =>
          item.metric != null &&
          Number.isFinite(item.metric) &&
          item.row.value != null,
      );

    if (usable.length < 2) {
      continue;
    }

    const sorted = [...usable].sort(
      (a, b) => b.metric - a.metric,
    );
    const top = sorted[0];
    const bottom = sorted[sorted.length - 1];

    insights.push({
      id: `${analysis.analysis_id ?? measureLabel}-top`,
      kind: "top",
      title: `Highest ${measureLabel} by ${dimensionLabel}`,
      summary:
        `${String(top.row.value)} has the highest ${measureLabel} ` +
        `at ${formatValue(top.metric)}.`,
      evidence: `${measureLabel} by ${dimensionLabel}`,
      value: top.metric,
    });

    insights.push({
      id: `${analysis.analysis_id ?? measureLabel}-bottom`,
      kind: "bottom",
      title: `Lowest ${measureLabel} by ${dimensionLabel}`,
      summary:
        `${String(bottom.row.value)} has the lowest ${measureLabel} ` +
        `at ${formatValue(bottom.metric)}.`,
      evidence: `${measureLabel} by ${dimensionLabel}`,
      value: bottom.metric,
    });

    if (
      analysis.aggregation === "count" ||
      analysis.aggregation === "sum"
    ) {
      const total = usable.reduce(
        (sum, item) => sum + item.metric,
        0,
      );

      if (total > 0) {
        const share = (top.metric / total) * 100;

        insights.push({
          id: `${analysis.analysis_id ?? measureLabel}-distribution`,
          kind: "distribution",
          title: `Largest share by ${dimensionLabel}`,
          summary:
            `${String(top.row.value)} represents ` +
            `${share.toFixed(1)}% of the grouped ${measureLabel}.`,
          evidence: `${measureLabel} by ${dimensionLabel}`,
          value: share,
        });
      }
    }

    if (isTimeAnalysis(analysis, studio)) {
      const trendRows = orderedTrendRows(analysis, studio)
        .map((row) => ({
          row,
          metric: metricValue(row, analysis.aggregation),
        }))
        .filter(
          (
            item,
          ): item is {
            row: AnalysisResultData["grouped_results"][number];
            metric: number;
          } =>
            item.metric != null &&
            Number.isFinite(item.metric),
        );

      if (trendRows.length >= 2) {
        const first = trendRows[0];
        const last = trendRows[trendRows.length - 1];
        const delta = last.metric - first.metric;
        const percent =
          first.metric !== 0
            ? (delta / Math.abs(first.metric)) * 100
            : null;

        insights.push({
          id: `${analysis.analysis_id ?? measureLabel}-trend`,
          kind: "trend",
          title: `${measureLabel} trend over ${dimensionLabel}`,
          summary:
            `From ${String(first.row.value)} to ${String(last.row.value)}, ` +
            `${measureLabel} ${delta >= 0 ? "increased" : "decreased"} ` +
            `by ${formatValue(Math.abs(delta))}` +
            `${percent == null ? "" : ` (${Math.abs(percent).toFixed(1)}%)`}.`,
          evidence: `${measureLabel} by ${dimensionLabel}`,
          value: delta,
        });
      }
    }
  }

  const kindOrder: Record<Insight["kind"], number> = {
    trend: 0,
    distribution: 1,
    top: 2,
    bottom: 3,
  };

  return insights.sort(
    (a, b) => kindOrder[a.kind] - kindOrder[b.kind],
  );
}

function iconForInsight(kind: Insight["kind"]) {
  if (kind === "top") {
    return <Trophy size={18} />;
  }

  if (kind === "trend") {
    return <ArrowUpRight size={18} />;
  }

  if (kind === "bottom") {
    return <ArrowDownRight size={18} />;
  }

  return <BarChart3 size={18} />;
}

export default function PersonalInsights({
  analyses,
  dataModelStudio,
  kpiDefinitions = [],
}: Props) {
  const insights = useMemo(
    () =>
      buildInsights(
        analyses,
        dataModelStudio,
        kpiDefinitions,
      ),
    [analyses, dataModelStudio, kpiDefinitions],
  );

  const summary = insights.slice(0, 4);

  return (
    <section className="personal-insights">
      <header className="personal-insights-header">
        <div>
          <span className="personal-insights-eyebrow">
            INSIGHTS
          </span>
          <h2>Evidence-based insights</h2>
          <p>
            Deterministic findings generated from saved semantic analyses.
            No LLM is used and no missing values are invented.
          </p>
        </div>

        <span className="personal-insights-badge">
          {insights.length} findings
        </span>
      </header>

      {analyses.length === 0 || insights.length === 0 ? (
        <div className="personal-insights-empty">
          <Lightbulb size={22} />
          <div>
            <strong>No insight-ready analyses yet</strong>
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
              <span>Executive summary</span>
              <small>Top evidence from the current semantic model</small>
            </div>

            <div className="personal-insights-summary-grid">
              {summary.map((insight) => (
                <article
                  key={insight.id}
                  className="personal-insight-summary-card"
                >
                  <div className="personal-insight-icon">
                    {iconForInsight(insight.kind)}
                  </div>
                  <strong>{insight.title}</strong>
                  <p>{insight.summary}</p>
                  <small>Source: {insight.evidence}</small>
                </article>
              ))}
            </div>
          </section>

          <section className="personal-insights-detail">
            <div className="personal-insights-section-title">
              <span>All findings</span>
              <small>
                Top/bottom, distribution and time-trend rules
              </small>
            </div>

            <div className="personal-insights-list">
              {insights.map((insight) => (
                <article
                  key={insight.id}
                  className="personal-insight-row"
                >
                  <div className="personal-insight-icon">
                    {iconForInsight(insight.kind)}
                  </div>

                  <div className="personal-insight-copy">
                    <strong>{insight.title}</strong>
                    <p>{insight.summary}</p>
                  </div>

                  <span className="personal-insight-evidence">
                    {insight.evidence}
                  </span>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </section>
  );
}
