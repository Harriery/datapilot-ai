type PersonalDataModelPlan = {
  model_type:
    | "single_table"
    | "star_schema_candidate";

  base_table: string;
  grain: string;

  dimensions: string[];

  time_dimension: string | null;

  measures: {
    code: string;
    title: string;
    column: string | null;

    aggregation:
      | "count"
      | "sum"
      | "mean"
      | "min"
      | "max";

    dimension: string | null;
  }[];

  recommended_dimension_tables: string[];

  source: "local";
};

type PersonalDataModelProps = {
  dataModelPlan:
    | PersonalDataModelPlan
    | null
    | undefined;

  loading: boolean;
  error: string | null;

  onBuild: () => void;
};

function PersonalDataModel({
  dataModelPlan,
  loading,
  error,
  onBuild,
}: PersonalDataModelProps) {
  return (
    <section className="personal-data-model-card">
      <div className="personal-data-model-header">
        <div>
          <span className="personal-analysis-plan-source">
            DATA MODEL
          </span>

          <h2>
            Build analytical data model
          </h2>

          <p>
            Create a local model recommendation
            from the validated dataset and your
            confirmed KPI definitions.
          </p>
        </div>

        {!dataModelPlan && (
          <button
            type="button"
            className="new-workspace-button"
            disabled={loading}
            onClick={onBuild}
          >
            {loading
              ? "Building model..."
              : "Build data model"}
          </button>
        )}
      </div>

      {error && (
        <div className="personal-analysis-error">
          {error}
        </div>
      )}

      {dataModelPlan && (
        <div className="personal-data-model-result">
          <div className="personal-data-model-summary">
            <div>
              <span>Model type</span>
              <strong>
                {dataModelPlan.model_type ===
                "star_schema_candidate"
                  ? "Star schema candidate"
                  : "Single table"}
              </strong>
            </div>

            <div>
              <span>Base table</span>
              <strong>
                {dataModelPlan.base_table}
              </strong>
            </div>

            <div>
              <span>Grain</span>
              <strong>
                {dataModelPlan.grain}
              </strong>
            </div>
          </div>

          <div className="personal-data-model-section">
            <h3>Dimensions</h3>

            {dataModelPlan.dimensions.length >
            0 ? (
              <div className="personal-analysis-tags">
                {dataModelPlan.dimensions.map(
                  (dimension) => (
                    <span key={dimension}>
                      {dimension}
                    </span>
                  )
                )}
              </div>
            ) : (
              <p>
                No dimensions selected from the
                confirmed KPIs.
              </p>
            )}
          </div>

          {dataModelPlan.time_dimension && (
            <div className="personal-data-model-section">
              <h3>Time dimension</h3>

              <div className="personal-analysis-tags">
                <span>
                  {
                    dataModelPlan.time_dimension
                  }
                </span>
              </div>
            </div>
          )}

          <div className="personal-data-model-section">
            <h3>Measures</h3>

            <div className="personal-data-model-measures">
              {dataModelPlan.measures.map(
                (measure) => (
                  <div
                    key={measure.code}
                    className="personal-data-model-measure"
                  >
                    <div>
                      <strong>
                        {measure.title}
                      </strong>

                      <span>
                        {measure.aggregation}
                      </span>
                    </div>

                    <p>
                      Column:{" "}
                      {measure.column ?? "—"}
                    </p>

                    {measure.dimension && (
                      <p>
                        Dimension:{" "}
                        {measure.dimension}
                      </p>
                    )}
                  </div>
                )
              )}
            </div>
          </div>

          <div className="personal-data-model-section">
            <h3>
              Recommended dimension tables
            </h3>

            {dataModelPlan
              .recommended_dimension_tables
              .length > 0 ? (
              <div className="personal-analysis-tags">
                {dataModelPlan
                  .recommended_dimension_tables
                  .map((table) => (
                    <span key={table}>
                      {table}
                    </span>
                  ))}
              </div>
            ) : (
              <p>
                No separate dimension tables are
                currently recommended.
              </p>
            )}
          </div>

          <div className="personal-data-model-ready">
            ✓ Data model plan created locally.
            Ready for the Power BI-ready dataset
            stage.
          </div>
        </div>
      )}
    </section>
  );
}

export default PersonalDataModel;