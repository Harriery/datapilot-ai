import {
  useEffect,
  useMemo,
  useState,
} from "react";

import AnalysisWorkspace from "./AnalysisWorkspace";

import type {
  DataModelStudioData,
} from "./DataModelCanvas";

import type {
  PersonalKpiData,
} from "./PersonalKpiCandidates";

type AnalysisPlanData = {
  measure_candidates: string[];
  dimension_candidates: string[];
  time_candidates: string[];
  suggested_questions: string[];
  source: "local";
};

export type AnalysisResultData = {
  analysis_id: string | null;
  measure: string;
  dimension: string | null;

  kpi_code?: string | null;
  dimension_table?: string | null;
  aggregation?:
    | "count"
    | "sum"
    | "mean"
    | "min"
    | "max"
    | "custom"
    | null;

  overall: {
    count: number;
    metric_value?: number | null;
    mean: number | null;
    min: number | null;
    max: number | null;
  };

  grouped_results: {
    value:
      | string
      | number
      | boolean
      | null;

    count: number;
    metric_value?: number | null;
    mean: number | null;
    min: number | null;
    max: number | null;
  }[];

  source: "local";
};

type Props = {
  analysisPlan: AnalysisPlanData;

  dataModelStudio?:
    | DataModelStudioData
    | null;

  kpiDefinitions?:
    PersonalKpiData[];

  analysisResult?:
    | AnalysisResultData
    | null;

  analysisResults?: AnalysisResultData[];

  loading: boolean;

  error:
    | string
    | null;

  onRunAnalysis: (
    measure: string,
    dimension: string | null,
    kpiCode?: string | null,
    dimensionTable?: string | null,
  ) => void;

  onDeleteAnalysis: (
    analysisId: string
  ) => void;
};

type SemanticDimensionOption = {
  key: string;
  table: string;
  column: string;
  label: string;
  isTime: boolean;
};

function PersonalAnalysisPlan({
  analysisPlan,
  dataModelStudio = null,
  kpiDefinitions = [],
  analysisResult,
  analysisResults = [],
  loading,
  error,
  onRunAnalysis,
  onDeleteAnalysis,
}: Props) {
  const semanticMode =
    Boolean(
      dataModelStudio &&
      kpiDefinitions.length > 0
    );

  const semanticDimensions =
    useMemo<
      SemanticDimensionOption[]
    >(
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
                    key:
                      table.name +
                      "." +
                      column.name,
                    table:
                      table.name,
                    column:
                      column.name,
                    label:
                      column.name,
                    isTime:
                      column.role ===
                        "time" ||
                      column.derivation
                        ?.type ===
                        "date_part",
                  })
                )
          );
      },
      [dataModelStudio]
    );

  const [
    selectedKpiCode,
    setSelectedKpiCode,
  ] = useState(
    kpiDefinitions[0]?.code ?? ""
  );

  const selectedKpi =
    kpiDefinitions.find(
      (item) =>
        item.code === selectedKpiCode
    ) ??
    kpiDefinitions[0] ??
    null;

  const defaultSemanticDimension =
    useMemo(
      () => {
        if (
          selectedKpi
            ?.dimension_table &&
          selectedKpi.dimension
        ) {
          return (
            selectedKpi
              .dimension_table +
            "." +
            selectedKpi.dimension
          );
        }

        return (
          semanticDimensions[0]?.key ??
          ""
        );
      },
      [
        selectedKpi,
        semanticDimensions,
      ]
    );

  const [
    selectedSemanticDimension,
    setSelectedSemanticDimension,
  ] = useState(
    defaultSemanticDimension
  );

  const [
    selectedMeasure,
    setSelectedMeasure,
  ] = useState(
    analysisPlan
      .measure_candidates[0] ?? ""
  );

  const [
    selectedDimension,
    setSelectedDimension,
  ] = useState(
    analysisPlan
      .dimension_candidates[0] ?? ""
  );

  useEffect(() => {
    if (
      semanticMode &&
      !kpiDefinitions.some(
        (item) =>
          item.code ===
          selectedKpiCode
      )
    ) {
      setSelectedKpiCode(
        kpiDefinitions[0]?.code ??
        ""
      );
    }
  }, [
    semanticMode,
    kpiDefinitions,
    selectedKpiCode,
  ]);

  useEffect(() => {
    if (!semanticMode) {
      return;
    }

    setSelectedSemanticDimension(
      defaultSemanticDimension
    );
  }, [
    semanticMode,
    selectedKpiCode,
    defaultSemanticDimension,
  ]);

  useEffect(() => {
    if (
      !analysisPlan
        .measure_candidates
        .includes(
          selectedMeasure
        )
    ) {
      setSelectedMeasure(
        analysisPlan
          .measure_candidates[0] ??
        ""
      );
    }

    if (
      selectedDimension &&
      !analysisPlan
        .dimension_candidates
        .includes(
          selectedDimension
        )
    ) {
      setSelectedDimension(
        analysisPlan
          .dimension_candidates[0] ??
        ""
      );
    }
  }, [
    analysisPlan,
    selectedMeasure,
    selectedDimension,
  ]);

  const suggestedSemanticQuestions =
    useMemo(
      () => {
        if (!semanticMode) {
          return [];
        }

        const questions: string[] = [];

        for (
          const definition
          of kpiDefinitions
        ) {
          if (
            definition.dimension
          ) {
            questions.push(
              "How does " +
              definition.title +
              " vary by " +
              definition.dimension +
              "?"
            );
          }

          if (questions.length >= 3) {
            break;
          }
        }

        if (
          questions.length < 3 &&
          kpiDefinitions[0] &&
          semanticDimensions[0]
        ) {
          questions.push(
            "How does " +
            kpiDefinitions[0].title +
            " vary by " +
            semanticDimensions[0]
              .label +
            "?"
          );
        }

        return Array.from(
          new Set(
            questions
          )
        ).slice(0, 3);
      },
      [
        semanticMode,
        kpiDefinitions,
        semanticDimensions,
      ]
    );

  const savedAnalysisResults =
    analysisResults.length > 0
      ? analysisResults
      : analysisResult
        ? [analysisResult]
        : [];

  const selectedSemanticDimensionOption =
    semanticDimensions.find(
      (item) =>
        item.key ===
        selectedSemanticDimension
    ) ?? null;

  return (
    <section className="personal-analysis-plan">
      <div className="personal-analysis-plan-header">
        <div>
          <span className="workspace-overview-label">
            ANALYSIS
          </span>

          <h2>
            {semanticMode
              ? "Semantic analysis"
              : "Analysis plan"}
          </h2>

          <p>
            {semanticMode
              ? (
                  "Analyze the KPI definitions and dimensions " +
                  "confirmed in the BI semantic model."
                )
              : (
                  "DataPilot identified possible measures, " +
                  "dimensions and analysis questions from " +
                  "the validated dataset."
                )}
          </p>
        </div>

        <span className="personal-analysis-plan-source">
          {semanticMode
            ? "Semantic model"
            : "Local analysis"}
        </span>
      </div>

      {semanticMode ? (
        <>
          <div className="personal-analysis-plan-grid">
            <div className="personal-analysis-plan-group">
              <span className="personal-analysis-plan-label">
                Measures / KPIs
              </span>

              <div className="personal-analysis-plan-tags">
                {kpiDefinitions.map(
                  (item) => (
                    <span
                      key={item.code}
                      className="personal-analysis-plan-tag"
                    >
                      {item.title}
                    </span>
                  )
                )}
              </div>
            </div>

            <div className="personal-analysis-plan-group">
              <span className="personal-analysis-plan-label">
                Dimensions
              </span>

              <div className="personal-analysis-plan-tags">
                {semanticDimensions
                  .filter(
                    (item) =>
                      !item.isTime
                  )
                  .map(
                    (item) => (
                      <span
                        key={item.key}
                        className="personal-analysis-plan-tag"
                      >
                        {item.label}
                      </span>
                    )
                  )}
              </div>
            </div>

            <div className="personal-analysis-plan-group">
              <span className="personal-analysis-plan-label">
                Time
              </span>

              <div className="personal-analysis-plan-tags">
                {semanticDimensions
                  .filter(
                    (item) =>
                      item.isTime
                  )
                  .map(
                    (item) => (
                      <span
                        key={item.key}
                        className="personal-analysis-plan-tag"
                      >
                        {item.label}
                      </span>
                    )
                  )}

                {!semanticDimensions.some(
                  (item) =>
                    item.isTime
                ) && (
                  <span className="personal-analysis-plan-empty">
                    No semantic time field detected.
                  </span>
                )}
              </div>
            </div>
          </div>

          {suggestedSemanticQuestions.length > 0 && (
            <div className="personal-analysis-questions">
              <span className="personal-analysis-plan-label">
                Suggested analysis questions
              </span>

              <ul>
                {suggestedSemanticQuestions.map(
                  (question) => (
                    <li key={question}>
                      {question}
                    </li>
                  )
                )}
              </ul>
            </div>
          )}

          <div className="personal-analysis-run">
            <span className="personal-analysis-plan-label">
              Run semantic analysis
            </span>

            <div className="personal-analysis-controls">
              <label>
                <span>
                  Measure / KPI
                </span>

                <select
                  value={selectedKpiCode}
                  onChange={(event) =>
                    setSelectedKpiCode(
                      event.target.value
                    )
                  }
                >
                  {kpiDefinitions.map(
                    (item) => (
                      <option
                        key={item.code}
                        value={item.code}
                      >
                        {item.title}
                      </option>
                    )
                  )}
                </select>
              </label>

              <label>
                <span>
                  Dimension
                </span>

                <select
                  value={
                    selectedSemanticDimension
                  }
                  onChange={(event) =>
                    setSelectedSemanticDimension(
                      event.target.value
                    )
                  }
                >
                  <option value="">
                    No dimension
                  </option>

                  {semanticDimensions.map(
                    (item) => (
                      <option
                        key={item.key}
                        value={item.key}
                      >
                        {item.label}
                      </option>
                    )
                  )}
                </select>
              </label>

              <button
                type="button"
                className="new-workspace-button"
                disabled={
                  loading ||
                  !selectedKpi
                }
                onClick={() =>
                  onRunAnalysis(
                    selectedKpi?.title ??
                      "",
                    selectedSemanticDimensionOption
                      ?.column ??
                      null,
                    selectedKpi?.code ??
                      null,
                    selectedSemanticDimensionOption
                      ?.table ??
                      null,
                  )
                }
              >
                {loading
                  ? "Running analysis..."
                  : "Run analysis"}
              </button>
            </div>

            {selectedKpi && (
              <div className="semantic-analysis-selection">
                <span>
                  Formula
                </span>

                <code>
                  {selectedKpi.formula ??
                    "No formula"}
                </code>
              </div>
            )}

            {error && (
              <p className="personal-analysis-error">
                {error}
              </p>
            )}
          </div>
        </>
      ) : (
        <>
          <div className="personal-analysis-plan-grid">
            <div className="personal-analysis-plan-group">
              <span className="personal-analysis-plan-label">
                Measures
              </span>

              <div className="personal-analysis-plan-tags">
                {analysisPlan.measure_candidates.map(
                  (item) => (
                    <span
                      key={item}
                      className="personal-analysis-plan-tag"
                    >
                      {item}
                    </span>
                  )
                )}
              </div>
            </div>

            <div className="personal-analysis-plan-group">
              <span className="personal-analysis-plan-label">
                Dimensions
              </span>

              <div className="personal-analysis-plan-tags">
                {analysisPlan.dimension_candidates.map(
                  (item) => (
                    <span
                      key={item}
                      className="personal-analysis-plan-tag"
                    >
                      {item}
                    </span>
                  )
                )}
              </div>
            </div>

            <div className="personal-analysis-plan-group">
              <span className="personal-analysis-plan-label">
                Time
              </span>

              <div className="personal-analysis-plan-tags">
                {analysisPlan.time_candidates.map(
                  (item) => (
                    <span
                      key={item}
                      className="personal-analysis-plan-tag"
                    >
                      {item}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>

          {analysisPlan.suggested_questions.length > 0 && (
            <div className="personal-analysis-questions">
              <span className="personal-analysis-plan-label">
                Suggested analysis questions
              </span>

              <ul>
                {analysisPlan.suggested_questions.map(
                  (question) => (
                    <li key={question}>
                      {question}
                    </li>
                  )
                )}
              </ul>
            </div>
          )}

          <div className="personal-analysis-run">
            <span className="personal-analysis-plan-label">
              Run analysis
            </span>

            <div className="personal-analysis-controls">
              <label>
                <span>Measure</span>

                <select
                  value={selectedMeasure}
                  onChange={(event) =>
                    setSelectedMeasure(
                      event.target.value
                    )
                  }
                >
                  {analysisPlan.measure_candidates.map(
                    (measure) => (
                      <option
                        key={measure}
                        value={measure}
                      >
                        {measure}
                      </option>
                    )
                  )}
                </select>
              </label>

              <label>
                <span>Dimension</span>

                <select
                  value={selectedDimension}
                  onChange={(event) =>
                    setSelectedDimension(
                      event.target.value
                    )
                  }
                >
                  <option value="">
                    No dimension
                  </option>

                  {analysisPlan.dimension_candidates.map(
                    (dimension) => (
                      <option
                        key={dimension}
                        value={dimension}
                      >
                        {dimension}
                      </option>
                    )
                  )}
                </select>
              </label>

              <button
                type="button"
                className="new-workspace-button"
                disabled={
                  loading ||
                  !selectedMeasure
                }
                onClick={() =>
                  onRunAnalysis(
                    selectedMeasure,
                    selectedDimension || null,
                  )
                }
              >
                {loading
                  ? "Running analysis..."
                  : "Run analysis"}
              </button>
            </div>

            {error && (
              <p className="personal-analysis-error">
                {error}
              </p>
            )}
          </div>
        </>
      )}

      <AnalysisWorkspace
        results={savedAnalysisResults}
        onDeleteAnalysis={
          onDeleteAnalysis
        }
      />
    </section>
  );
}

export default PersonalAnalysisPlan;
