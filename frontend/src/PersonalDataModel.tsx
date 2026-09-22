import DataModelCanvas from "./DataModelCanvas";

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
      | "max"
      | null;

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

  dataModelStudio:
    | PersonalDataModelStudio
    | null
    | undefined;

  loading: boolean;
  error: string | null;

  onBuild: () => void;
};

type PersonalDataModelStudio = {
  tables: {
    name: string;

    table_type:
      | "fact"
      | "dimension"
      | "bridge";

    columns: {
      name: string;
      source_column: string | null;

      role:
        | "key"
        | "foreign_key"
        | "dimension"
        | "measure"
        | "attribute"
        | "time";

      aggregation:
        | "count"
        | "sum"
        | "mean"
        | "min"
        | "max"
        | null;
    }[];
  }[];

  relationships: {
    from_table: string;
    from_column: string;

    to_table: string;
    to_column: string;

    cardinality:
      | "many_to_one"
      | "one_to_many"
      | "one_to_one";

    active: boolean;
  }[];

  source: "local" | "user";
};

function PersonalDataModel({
  dataModelPlan,
  dataModelStudio,
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
            Create a local analytical model from
            the validated dataset and analysis
            structure before defining final KPIs.
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
                        {measure.aggregation ??
                         "Source measure"}
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

          {dataModelStudio ? (
            <div className="personal-data-model-studio">
              <div className="personal-data-model-studio-header">

                <div>
                  <span className="personal-analysis-plan-source">
                    MODEL STUDIO
                  </span>
                    
                  <h3>
                    Tables and relationships
                  </h3>
                    
                  <p>
                    This is the logical analytical model
                    built from the validated dataset and
                    analysis structure.
                  </p>
                </div>
              </div>
              
              <DataModelCanvas
                studio={dataModelStudio}
              />
                    
              <div className="personal-data-model-studio-tables">
                {dataModelStudio.tables.map(
                  (table) => (
                    <article
                      key={table.name}
                      className="personal-data-model-studio-table"
                    >
                      <div className="personal-data-model-studio-table-header">
                        <strong>
                          {table.name}
                        </strong>
                  
                        <span>
                          {table.table_type}
                        </span>
                      </div>
                  
                      <div className="personal-data-model-studio-columns">
                        {table.columns.map(
                          (column) => (
                            <div
                              key={
                                `${table.name}-${column.name}`
                              }
                              className="personal-data-model-studio-column"
                            >
                              <span>
                                {column.name}
                              </span>
                            
                              <small>
                                {column.role}
                              </small>
                            </div>
                          )
                        )}
                      </div>
                    </article>
                  )
                )}
              </div>
              
              <div className="personal-data-model-studio-relationships">
                <h3>Relationships</h3>
              
                {dataModelStudio.relationships.length >
                0 ? (
                  dataModelStudio.relationships.map(
                    (relationship) => (
                      <div
                        key={
                          `${relationship.from_table}-${relationship.from_column}-${relationship.to_table}-${relationship.to_column}`
                        }
                        className="personal-data-model-studio-relationship"
                      >
                        <strong>
                          {relationship.from_table}.
                          {relationship.from_column}
                        </strong>
                      
                        <span>
                          →
                        </span>
                      
                        <strong>
                          {relationship.to_table}.
                          {relationship.to_column}
                        </strong>
                      
                        <small>
                          {relationship.cardinality}
                        </small>
                      </div>
                    )
                  )
                ) : (
                  <p>
                    No relationships are defined yet.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="personal-data-model-studio-empty">
              <div>
                <strong>
                  Data Model Studio is not initialized yet.
                </strong>
          
                <p>
                  Initialize it from the existing data
                  model plan.
                </p>
              </div>
          
              <button
                type="button"
                className="new-workspace-button"
                disabled={loading}
                onClick={onBuild}
              >
                {loading
                  ? "Initializing..."
                  : "Initialize model studio"}
              </button>
            </div>
          )}

          {dataModelStudio && (
            <div className="personal-data-model-ready">
              ✓ Data model and model studio created
              locally. Ready for the next stage.
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default PersonalDataModel;