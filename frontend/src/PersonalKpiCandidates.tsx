import {
  useEffect,
  useMemo,
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


  const [
    activeCode,
    setActiveCode,
  ] = useState<string | null>(
    null
  );


  useEffect(() => {
    setSelectedCodes(
      selectedDefinitions.map(
        (item) => item.code
      )
    );
  }, [selectedDefinitions]);


  useEffect(() => {
    if (candidates.length === 0) {
      setActiveCode(null);
      return;
    }

    if (
      activeCode &&
      candidates.some(
        (candidate) =>
          candidate.code === activeCode
      )
    ) {
      return;
    }

    const firstSelected =
      candidates.find(
        (candidate) =>
          selectedCodes.includes(
            candidate.code
          )
      );

    setActiveCode(
      firstSelected?.code ??
      candidates[0].code
    );
  }, [
    candidates,
    selectedCodes,
    activeCode,
  ]);


  const activeCandidate =
    useMemo(
      () =>
        candidates.find(
          (candidate) =>
            candidate.code === activeCode
        ) ?? null,
      [
        candidates,
        activeCode,
      ]
    );


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
            Review KPI candidates and select the
            metrics that are meaningful for this
            project.
          </p>
        </div>

        <span className="personal-analysis-plan-source">
          Local candidates
        </span>

      </div>


      <div className="personal-kpi-workspace">

        {/* =========================================
            LEFT: KPI LIST
            ========================================= */}

        <div className="personal-kpi-master">

          <div className="personal-kpi-master-header">

            <div>
              <span className="workspace-overview-label">
                CANDIDATES
              </span>

              <strong>
                {candidates.length} KPIs
              </strong>
            </div>

            <span className="personal-kpi-selected-count">
              {selectedCodes.length} selected
            </span>

          </div>


          <div className="personal-kpi-compact-list">

            {candidates.map(
              (candidate) => {

                const selected =
                  selectedCodes.includes(
                    candidate.code
                  );

                const active =
                  candidate.code ===
                  activeCode;


                return (
                  <div
                    key={candidate.code}
                    className={
                      `personal-kpi-compact-item ${
                        active
                          ? "active"
                          : ""
                      } ${
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
                      aria-label={
                        `Select ${candidate.title}`
                      }
                    />


                    <button
                      type="button"
                      className="personal-kpi-compact-open"
                      onClick={() =>
                        setActiveCode(
                          candidate.code
                        )
                      }
                    >

                      <span className="personal-kpi-compact-title">
                        {candidate.title}
                      </span>

                      <span className="personal-kpi-compact-type">
                        {
                          candidate
                            .aggregation
                            .toUpperCase()
                        }
                      </span>

                    </button>

                  </div>
                );
              }
            )}

          </div>

        </div>


        {/* =========================================
            RIGHT: KPI DETAIL
            ========================================= */}

        <div className="personal-kpi-detail">

          {activeCandidate ? (
            <>

              <div className="personal-kpi-detail-header">

                <div>
                  <span className="workspace-overview-label">
                    KPI DETAILS
                  </span>

                  <h3>
                    {activeCandidate.title}
                  </h3>
                </div>


                <span className="personal-kpi-detail-aggregation">
                  {
                    activeCandidate
                      .aggregation
                      .toUpperCase()
                  }
                </span>

              </div>


              <p className="personal-kpi-detail-description">
                {activeCandidate.description}
              </p>


              <div className="personal-kpi-detail-grid">

                <div>
                  <span>
                    Measure
                  </span>

                  <strong>
                    {
                      activeCandidate.measure ??
                      "—"
                    }
                  </strong>
                </div>


                <div>
                  <span>
                    Dimension
                  </span>

                  <strong>
                    {
                      activeCandidate.dimension ??
                      "None"
                    }
                  </strong>
                </div>


                <div>
                  <span>
                    Aggregation
                  </span>

                  <strong>
                    {
                      activeCandidate
                        .aggregation
                        .toUpperCase()
                    }
                  </strong>
                </div>


                <div>
                  <span>
                    Source
                  </span>

                  <strong>
                    {
                      activeCandidate.source ===
                      "local"
                        ? "Local analysis"
                        : "User defined"
                    }
                  </strong>
                </div>

              </div>


              <div className="personal-kpi-detail-selection">

                <span>
                  {
                    selectedCodes.includes(
                      activeCandidate.code
                    )
                      ? "Selected for project"
                      : "Not selected"
                  }
                </span>

                <button
                  type="button"
                  className={
                    selectedCodes.includes(
                      activeCandidate.code
                    )
                      ? "secondary-button"
                      : "new-workspace-button"
                  }
                  onClick={() =>
                    toggleKpi(
                      activeCandidate.code
                    )
                  }
                >
                  {
                    selectedCodes.includes(
                      activeCandidate.code
                    )
                      ? "Remove KPI"
                      : "Select KPI"
                  }
                </button>

              </div>

            </>
          ) : (
            <div className="personal-kpi-detail-empty">

              <strong>
                No KPI selected
              </strong>

              <p>
                Choose a KPI candidate to review
                its details.
              </p>

            </div>
          )}

        </div>

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