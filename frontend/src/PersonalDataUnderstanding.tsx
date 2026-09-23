type ColumnIntelligence = {
  name: string;
  data_type: string;
  null_count: number;
  null_percentage: number;
  distinct_count: number;
  cardinality_ratio: number;
  examples: string[];
  minimum: number | null;
  maximum: number | null;
  role_candidates: (
    | "key"
    | "numeric"
    | "dimension"
    | "time"
  )[];
  confidence:
    | "low"
    | "medium"
    | "high";
  reasoning: string[];
};

type DataUnderstandingPlan = {
  measure_candidates: string[];
  numeric_candidates?: string[];
  key_candidates?: string[];
  dimension_candidates: string[];
  time_candidates: string[];
  column_intelligence?: ColumnIntelligence[];
  model_discovery?: {
    grain: string;
    fact_table_candidate: string;
    dimension_table_candidates: string[];
    confidence:
      | "low"
      | "medium"
      | "high";
    reasoning: string[];
  } | null;
  suggested_questions: string[];
  source: "local";
};

type Props = {
  plan: DataUnderstandingPlan;
};

function CandidateGroup({
  label,
  items,
  emptyText,
}: {
  label: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div className="understanding-candidate-group">
      <span className="personal-analysis-plan-label">
        {label}
      </span>

      <div className="personal-analysis-plan-tags">
        {items.length > 0 ? (
          items.map((item) => (
            <span
              key={item}
              className="personal-analysis-plan-tag"
            >
              {item}
            </span>
          ))
        ) : (
          <span className="personal-analysis-plan-empty">
            {emptyText}
          </span>
        )}
      </div>
    </div>
  );
}

function PersonalDataUnderstanding({
  plan,
}: Props) {
  const numericCandidates =
    plan.numeric_candidates ??
    plan.measure_candidates;

  const keyCandidates =
    plan.key_candidates ?? [];

  const columnIntelligence =
    plan.column_intelligence ?? [];

  const discovery =
    plan.model_discovery ?? null;

  return (
    <section className="personal-analysis-plan understanding-card">
      <div className="personal-analysis-plan-header">
        <div>
          <span className="workspace-overview-label">
            MODEL DISCOVERY
          </span>

          <h2>
            Understand the validated dataset
          </h2>

          <p>
            Inspect technical column evidence before
            deciding the logical model. These are
            candidates and recommendations, not final
            semantic definitions.
          </p>
        </div>

        <span className="personal-analysis-plan-source">
          Deterministic profiling
        </span>
      </div>

      {discovery && (
        <div className="understanding-model-summary">
          <div className="understanding-model-summary-main">
            <span className="personal-analysis-plan-label">
              Suggested model shape
            </span>

            <strong>
              {discovery.fact_table_candidate}
            </strong>

            <p>
              {discovery.grain}
            </p>
          </div>

          <div className="understanding-confidence">
            <span>
              Confidence
            </span>

            <strong
              className={
                `confidence-${discovery.confidence}`
              }
            >
              {discovery.confidence}
            </strong>
          </div>

          <div className="understanding-dimension-suggestions">
            <span className="personal-analysis-plan-label">
              Possible dimensions
            </span>

            <div className="personal-analysis-plan-tags">
              {discovery.dimension_table_candidates.length > 0 ? (
                discovery.dimension_table_candidates.map(
                  (table) => (
                    <span
                      key={table}
                      className="personal-analysis-plan-tag"
                    >
                      {table}
                    </span>
                  )
                )
              ) : (
                <span className="personal-analysis-plan-empty">
                  No dimension table suggested yet.
                </span>
              )}
            </div>
          </div>

          <ul className="understanding-reasoning">
            {discovery.reasoning.map(
              (reason) => (
                <li key={reason}>
                  {reason}
                </li>
              )
            )}
          </ul>
        </div>
      )}

      <div className="understanding-candidate-grid">
        <CandidateGroup
          label="Key candidates"
          items={keyCandidates}
          emptyText="No reliable unique key detected."
        />

        <CandidateGroup
          label="Numeric candidates"
          items={numericCandidates}
          emptyText="No numeric candidates detected."
        />

        <CandidateGroup
          label="Dimension candidates"
          items={plan.dimension_candidates}
          emptyText="No dimension candidates detected."
        />

        <CandidateGroup
          label="Time candidates"
          items={plan.time_candidates}
          emptyText="No time candidate detected."
        />
      </div>

      {columnIntelligence.length > 0 && (
        <div className="understanding-columns">
          <div className="understanding-section-header">
            <div>
              <span className="personal-analysis-plan-label">
                Column intelligence
              </span>

              <strong>
                {columnIntelligence.length} columns profiled
              </strong>
            </div>

            <span>
              nulls · cardinality · role evidence
            </span>
          </div>

          <div className="understanding-column-list">
            {columnIntelligence.map(
              (column) => (
                <article
                  key={column.name}
                  className="understanding-column-row"
                >
                  <div className="understanding-column-identity">
                    <strong>
                      {column.name}
                    </strong>

                    <span>
                      {column.data_type}
                    </span>
                  </div>

                  <div className="understanding-column-metrics">
                    <span>
                      Null {column.null_percentage}%
                    </span>

                    <span>
                      {column.distinct_count} distinct
                    </span>

                    <span>
                      Cardinality {
                        Math.round(
                          column.cardinality_ratio * 100
                        )
                      }%
                    </span>
                  </div>

                  <div className="understanding-column-roles">
                    {column.role_candidates.length > 0 ? (
                      column.role_candidates.map(
                        (role) => (
                          <span
                            key={role}
                            className="understanding-role"
                          >
                            {role}
                          </span>
                        )
                      )
                    ) : (
                      <span className="understanding-role muted-role">
                        unclassified
                      </span>
                    )}
                  </div>

                  <div className="understanding-column-evidence">
                    {column.examples.length > 0 && (
                      <span>
                        Examples: {column.examples.join(", ")}
                      </span>
                    )}

                    {column.minimum !== null &&
                      column.maximum !== null && (
                        <span>
                          Range: {column.minimum} → {column.maximum}
                        </span>
                      )}

                    <span>
                      {column.reasoning[0]}
                    </span>
                  </div>

                  <span
                    className={
                      `understanding-column-confidence confidence-${column.confidence}`
                    }
                  >
                    {column.confidence}
                  </span>
                </article>
              )
            )}
          </div>
        </div>
      )}

      {plan.suggested_questions.length > 0 && (
        <div className="personal-analysis-questions">
          <span className="personal-analysis-plan-label">
            Model requirements to support later
          </span>

          <ul>
            {plan.suggested_questions.map(
              (question) => (
                <li key={question}>
                  {question}
                </li>
              )
            )}
          </ul>
        </div>
      )}

      <div className="data-understanding-note">
        <strong>
          Next: Data Model
        </strong>

        <span>
          Use these technical suggestions as a starting
          point. The Data Model stage remains editable;
          no dataset values are changed here.
        </span>
      </div>
    </section>
  );
}

export default PersonalDataUnderstanding;
