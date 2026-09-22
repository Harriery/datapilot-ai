import {
  useEffect,
  useState,
} from "react";

import AnalysisWorkspace from "./AnalysisWorkspace";

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

  overall: {
    count: number;
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
    mean: number | null;
    min: number | null;
    max: number | null;
  }[];

  source: "local";
};


type Props = {
  analysisPlan: AnalysisPlanData;

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
  ) => void;

  onDeleteAnalysis: (
    analysisId: string
  ) => void;
};


function PersonalAnalysisPlan({
  analysisPlan,
  analysisResult,
  analysisResults = [],
  loading,
  error,
  onRunAnalysis,
  onDeleteAnalysis,
}: Props) {

  const [
    selectedMeasure,
    setSelectedMeasure,
  ] = useState(
    analysisPlan.measure_candidates[0] ?? ""
  );

  const [
    selectedDimension,
    setSelectedDimension,
  ] = useState(
    analysisPlan.dimension_candidates[0] ?? ""
  );


  useEffect(() => {
    if (
      !analysisPlan.measure_candidates.includes(
        selectedMeasure
      )
    ) {
      setSelectedMeasure(
        analysisPlan.measure_candidates[0] ?? ""
      );
    }
  
    if (
      selectedDimension &&
      !analysisPlan.dimension_candidates.includes(
        selectedDimension
      )
    ) {
      setSelectedDimension(
        analysisPlan.dimension_candidates[0] ?? ""
      );
    }
  }, [
    analysisPlan,
    selectedMeasure,
    selectedDimension,
  ]);

  const savedAnalysisResults =
    analysisResults.length > 0
      ? analysisResults
      : analysisResult
        ? [analysisResult]
        : [];

  return (
    <section className="personal-analysis-plan">
      <div className="personal-analysis-plan-header">
        <div>
          <span className="workspace-overview-label">
            ANALYSIS
          </span>

          <h2>Analysis plan</h2>

          <p>
            DataPilot identified possible measures,
            dimensions and analysis questions from
            the validated dataset.
          </p>
        </div>

        <span className="personal-analysis-plan-source">
          Local analysis
        </span>
      </div>


      <div className="personal-analysis-plan-grid">

        <div className="personal-analysis-plan-group">
          <span className="personal-analysis-plan-label">
            Measures
          </span>

          <div className="personal-analysis-plan-tags">
            {analysisPlan.measure_candidates.length > 0 ? (
              analysisPlan.measure_candidates.map(
                (item) => (
                  <span
                    key={item}
                    className="personal-analysis-plan-tag"
                  >
                    {item}
                  </span>
                )
              )
            ) : (
              <span className="personal-analysis-plan-empty">
                No measure candidates detected.
              </span>
            )}
          </div>
        </div>


        <div className="personal-analysis-plan-group">
          <span className="personal-analysis-plan-label">
            Dimensions
          </span>

          <div className="personal-analysis-plan-tags">
            {analysisPlan.dimension_candidates.length > 0 ? (
              analysisPlan.dimension_candidates.map(
                (item) => (
                  <span
                    key={item}
                    className="personal-analysis-plan-tag"
                  >
                    {item}
                  </span>
                )
              )
            ) : (
              <span className="personal-analysis-plan-empty">
                No dimension candidates detected.
              </span>
            )}
          </div>
        </div>


        <div className="personal-analysis-plan-group">
          <span className="personal-analysis-plan-label">
            Time
          </span>

          <div className="personal-analysis-plan-tags">
            {analysisPlan.time_candidates.length > 0 ? (
              analysisPlan.time_candidates.map(
                (item) => (
                  <span
                    key={item}
                    className="personal-analysis-plan-tag"
                  >
                    {item}
                  </span>
                )
              )
            ) : (
              <span className="personal-analysis-plan-empty">
                No time column detected.
              </span>
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