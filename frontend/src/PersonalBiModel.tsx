import type {
  DataModelStudioData,
} from "./DataModelCanvas";

import type {
  PersonalKpiData,
} from "./PersonalKpiCandidates";

type Props = {
  studio: DataModelStudioData;
  definitions: PersonalKpiData[];
  loading: boolean;
  error: string | null;
  onConfirm: () => void;
};

function PersonalBiModel({
  studio,
  definitions,
  loading,
  error,
  onConfirm,
}: Props) {
  const activeRelationships =
    studio.relationships.filter(
      (relationship) =>
        relationship.active
    );

  const factTables =
    studio.tables.filter(
      (table) =>
        table.table_type === "fact"
    );

  const dimensionTables =
    studio.tables.filter(
      (table) =>
        table.table_type === "dimension"
    );

  const customMeasures =
    definitions.filter(
      (definition) =>
        definition.formula_mode === "custom"
    );

  const dateTables =
    studio.tables.filter(
      (table) =>
        table.columns.some(
          (column) =>
            column.role === "time" ||
            column.derivation?.type === "date_part"
        )
    );

  const checks = [
    {
      label: "Fact table",
      passed: factTables.length > 0,
      detail:
        factTables.length > 0
          ? String(factTables.length) + " fact table ready"
          : "No fact table found",
    },
    {
      label: "Dimensions",
      passed: true,
      detail:
        dimensionTables.length > 0
          ? String(dimensionTables.length) + " dimension tables ready"
          : "Single-table model — no dimensions required",
    },
    {
      label: "Relationships",
      passed:
        dimensionTables.length === 0 ||
        activeRelationships.length > 0,
      detail:
        dimensionTables.length === 0
          ? "Not required for a single-table model"
          : activeRelationships.length > 0
            ? String(activeRelationships.length) + " active relationships"
            : "Dimension tables need an active relationship",
    },
    {
      label: "Measures",
      passed: definitions.length > 0,
      detail:
        definitions.length > 0
          ? String(definitions.length) + " KPI / measures ready"
          : "No KPI definitions found",
    },
    {
      label: "Time analysis",
      passed: dateTables.length > 0,
      detail:
        dateTables.length > 0
          ? String(dateTables.length) + " time-aware table ready"
          : "No time-aware dimension detected",
    },
  ];

  const requiredReady =
    checks
      .slice(0, 4)
      .every(
        (check) =>
          check.passed
      );

  return (
    <section className="personal-bi-model">
      <div className="personal-bi-model-header">
        <div>
          <span className="workspace-overview-label">
            BI SEMANTIC MODEL
          </span>

          <h2>
            Review the report-ready semantic layer
          </h2>

          <p>
            Combine the logical model, relationships
            and KPI definitions into the reusable
            semantic layer that will feed analysis
            and dashboards.
          </p>
        </div>

        <span
          className={
            requiredReady
              ? "bi-model-readiness ready"
              : "bi-model-readiness warning"
          }
        >
          {requiredReady
            ? "Ready for review"
            : "Needs attention"}
        </span>
      </div>

      <div className="bi-model-summary-grid">
        <div>
          <strong>
            {studio.tables.length}
          </strong>
          <span>Tables</span>
        </div>

        <div>
          <strong>
            {activeRelationships.length}
          </strong>
          <span>Relationships</span>
        </div>

        <div>
          <strong>
            {definitions.length}
          </strong>
          <span>Measures</span>
        </div>

        <div>
          <strong>
            {customMeasures.length}
          </strong>
          <span>Custom formulas</span>
        </div>
      </div>

      <div className="bi-model-workspace">
        <section className="bi-model-panel">
          <div className="bi-model-panel-header">
            <div>
              <span className="workspace-overview-label">
                TABLES
              </span>
              <strong>
                Semantic model structure
              </strong>
            </div>
          </div>

          <div className="bi-model-table-list">
            {studio.tables.map(
              (table) => (
                <div
                  key={table.name}
                  className="bi-model-table-item"
                >
                  <div>
                    <strong>
                      {table.name}
                    </strong>

                    <span>
                      {table.table_type}
                    </span>
                  </div>

                  <small>
                    {table.columns.length} fields
                  </small>
                </div>
              )
            )}
          </div>
        </section>

        <section className="bi-model-panel">
          <div className="bi-model-panel-header">
            <div>
              <span className="workspace-overview-label">
                MEASURES
              </span>
              <strong>
                Business metrics
              </strong>
            </div>
          </div>

          <div className="bi-model-measure-list">
            {definitions.map(
              (definition) => (
                <div
                  key={definition.code}
                  className="bi-model-measure-item"
                >
                  <div>
                    <strong>
                      {definition.title}
                    </strong>

                    <code>
                      {definition.formula ??
                        "No formula"}
                    </code>
                  </div>

                  <span>
                    {definition.formula_mode ===
                    "custom"
                      ? "CUSTOM"
                      : "GUIDED"}
                  </span>
                </div>
              )
            )}
          </div>
        </section>

        <section className="bi-model-panel bi-model-relationships">
          <div className="bi-model-panel-header">
            <div>
              <span className="workspace-overview-label">
                RELATIONSHIPS
              </span>
              <strong>
                Filter paths
              </strong>
            </div>
          </div>

          <div className="bi-model-relationship-list">
            {studio.relationships.map(
              (relationship, index) => (
                <div
                  key={
                    relationship.from_table +
                    "-" +
                    relationship.from_column +
                    "-" +
                    relationship.to_table +
                    "-" +
                    relationship.to_column +
                    "-" +
                    index
                  }
                  className="bi-model-relationship-item"
                >
                  <span>
                    <strong>
                      {relationship.from_table}
                    </strong>
                    .{relationship.from_column}
                  </span>

                  <span className="bi-model-relationship-arrow">
                    →
                  </span>

                  <span>
                    <strong>
                      {relationship.to_table}
                    </strong>
                    .{relationship.to_column}
                  </span>

                  <small>
                    {relationship.cardinality}
                    {relationship.active
                      ? " · active"
                      : " · inactive"}
                  </small>
                </div>
              )
            )}
          </div>
        </section>

        <section className="bi-model-panel bi-model-checks">
          <div className="bi-model-panel-header">
            <div>
              <span className="workspace-overview-label">
                READINESS
              </span>
              <strong>
                Semantic model checks
              </strong>
            </div>
          </div>

          <div className="bi-model-check-list">
            {checks.map(
              (check) => (
                <div
                  key={check.label}
                  className={
                    check.passed
                      ? "bi-model-check passed"
                      : "bi-model-check warning"
                  }
                >
                  <span>
                    {check.passed
                      ? "✓"
                      : "!"}
                  </span>

                  <div>
                    <strong>
                      {check.label}
                    </strong>

                    <small>
                      {check.detail}
                    </small>
                  </div>
                </div>
              )
            )}
          </div>
        </section>
      </div>

      {error && (
        <p className="personal-analysis-error">
          {error}
        </p>
      )}

      <div className="bi-model-actions">
        <span>
          Confirming completes the semantic-model
          review and opens the Analysis stage.
        </span>

        <button
          type="button"
          className="new-workspace-button"
          disabled={
            loading ||
            !requiredReady
          }
          onClick={onConfirm}
        >
          {loading
            ? "Confirming..."
            : "Confirm semantic model"}
        </button>
      </div>
    </section>
  );
}

export default PersonalBiModel;
