import DataModelCanvas, {
  type DataModelStudioData,
} from "./DataModelCanvas";

type PersonalDataModelPlan = {
  model_type:
    | "single_table"
    | "star_schema_candidate";

  base_table: string;
  grain: string;
};

type PersonalDataModelProps = {
  dataModelPlan:
    | PersonalDataModelPlan
    | null
    | undefined;

  dataModelStudio:
    | DataModelStudioData
    | null
    | undefined;

  loading: boolean;
  error: string | null;

  onBuild: () => void;

  onSaveStudio: (
    studio: DataModelStudioData
  ) => Promise<void>;

  onExport: () => void;

  studioSaving: boolean;
};

function PersonalDataModel({
  dataModelPlan,
  dataModelStudio,
  loading,
  error,
  onBuild,
  onSaveStudio,
  onExport,
  studioSaving,
}: PersonalDataModelProps) {
  const tableCount =
    dataModelStudio?.tables.length ?? 0;

  const factCount =
    dataModelStudio?.tables.filter(
      (table) =>
        table.table_type === "fact"
    ).length ?? 0;

  const dimensionCount =
    dataModelStudio?.tables.filter(
      (table) =>
        table.table_type === "dimension"
    ).length ?? 0;

  const bridgeCount =
    dataModelStudio?.tables.filter(
      (table) =>
        table.table_type === "bridge"
    ).length ?? 0;

  const activeRelationshipCount =
    dataModelStudio?.relationships.filter(
      (relationship) =>
        relationship.active
    ).length ?? 0;

  return (
    <section className="personal-data-model-card">
      <div className="personal-data-model-header">
        <div>
          <span className="personal-analysis-plan-source">
            DATA MODEL
          </span>

          <h2>
            Design the logical data model
          </h2>

          <p>
            Define tables, roles and relationships.
            This stage changes model metadata only;
            dataset values remain untouched.
          </p>
        </div>

        <div className="personal-data-model-header-actions">
          {dataModelStudio && (
            <button
              type="button"
              className="secondary-button"
              onClick={onExport}
            >
              Export JSON
            </button>
          )}

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
              <span>Tables</span>
              <strong>
                {tableCount}
              </strong>
            </div>

            <div>
              <span>Fact / Dim / Bridge</span>
              <strong>
                {factCount} / {dimensionCount} / {bridgeCount}
              </strong>
            </div>

            <div>
              <span>Active relationships</span>
              <strong>
                {activeRelationshipCount}
              </strong>
            </div>

            <div>
              <span>Grain</span>
              <strong>
                {dataModelPlan.grain}
              </strong>
            </div>
          </div>

          {dataModelStudio ? (
            <div className="personal-data-model-studio">
              <div className="personal-data-model-studio-header">
                <div>
                  <span className="personal-analysis-plan-source">
                    MODEL STUDIO
                  </span>

                  <h3>
                    Logical model canvas
                  </h3>

                  <p>
                    The summary above is generated from
                    the current editable studio state.
                  </p>
                </div>
              </div>

              <DataModelCanvas
                studio={dataModelStudio}
                onSaveStudio={onSaveStudio}
                saving={studioSaving}
              />
            </div>
          ) : (
            <div className="personal-data-model-studio-empty">
              <div>
                <strong>
                  Data Model Studio is not initialized yet.
                </strong>

                <p>
                  Initialize it from the current
                  model-discovery result.
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
              ✓ Logical model is persisted and ready
              for KPI definition.
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default PersonalDataModel;
