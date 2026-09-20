import {
  useEffect,
  useState,
} from "react";


export type PersonalKpiData = {
  code: string;
  title: string;

  measure: string | null;

  aggregation:
    | "count"
    | "sum"
    | "mean"
    | "min"
    | "max";

  dimension: string | null;

  description: string;

  source:
    | "local"
    | "user";
};


type Props = {
  candidates: PersonalKpiData[];

  selectedDefinitions: PersonalKpiData[];

  loading: boolean;

  error: string | null;

  onSave: (
    codes: string[]
  ) => void;
};


function PersonalKpiCandidates({
  candidates,
  selectedDefinitions,
  loading,
  error,
  onSave,
}: Props) {

  const [
    selectedCodes,
    setSelectedCodes,
  ] = useState<string[]>([]);


  useEffect(() => {
    setSelectedCodes(
      selectedDefinitions.map(
        (item) => item.code
      )
    );
  }, [selectedDefinitions]);


  function toggleKpi(
    code: string,
  ) {
    setSelectedCodes(
      (previous) =>
        previous.includes(code)
          ? previous.filter(
              (item) =>
                item !== code
            )
          : [
              ...previous,
              code,
            ]
    );
  }


  return (
    <section className="personal-kpi-card">

      <div className="personal-kpi-header">
        <div>
          <span className="workspace-overview-label">
            KPI DEFINITIONS
          </span>

          <h2>
            Choose project KPIs
          </h2>

          <p>
            DataPilot generated KPI candidates
            from the validated analysis result.
            Select the metrics that are meaningful
            for this project.
          </p>
        </div>

        <span className="personal-analysis-plan-source">
          Local candidates
        </span>
      </div>


      <div className="personal-kpi-list">

        {candidates.map(
          (candidate) => {

            const selected =
              selectedCodes.includes(
                candidate.code
              );

            return (
              <label
                key={candidate.code}
                className={
                  `personal-kpi-item ${
                    selected
                      ? "selected"
                      : ""
                  }`
                }
              >

                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() =>
                    toggleKpi(
                      candidate.code
                    )
                  }
                />

                <div className="personal-kpi-content">

                  <div className="personal-kpi-title-row">
                    <strong>
                      {candidate.title}
                    </strong>

                    <span className="personal-kpi-aggregation">
                      {candidate.aggregation}
                    </span>
                  </div>

                  <p>
                    {candidate.description}
                  </p>

                  <div className="personal-kpi-meta">

                    {candidate.measure && (
                      <span>
                        Measure:{" "}
                        {candidate.measure}
                      </span>
                    )}

                    {candidate.dimension && (
                      <span>
                        Dimension:{" "}
                        {candidate.dimension}
                      </span>
                    )}

                  </div>

                </div>

              </label>
            );
          }
        )}

      </div>


      {error && (
        <p className="personal-analysis-error">
          {error}
        </p>
      )}


      <div className="personal-kpi-actions">

        <span>
          {selectedCodes.length} KPI
          {selectedCodes.length === 1
            ? ""
            : "s"}{" "}
          selected
        </span>

        <button
          type="button"
          className="new-workspace-button"
          disabled={
            loading ||
            selectedCodes.length === 0
          }
          onClick={() =>
            onSave(
              selectedCodes
            )
          }
        >
          {loading
            ? "Saving KPIs..."
            : "Confirm KPIs"}
        </button>

      </div>

    </section>
  );
}


export default PersonalKpiCandidates;