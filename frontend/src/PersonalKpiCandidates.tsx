import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  DataModelStudioData,
} from "./DataModelCanvas";

export type PersonalKpiData = {
  code: string;
  title: string;

  fact_table?: string | null;

  measure: string | null;

  aggregation:
    | "count"
    | "sum"
    | "mean"
    | "min"
    | "max";

  dimension_table?: string | null;
  dimension: string | null;

  filter_value?:
    | string
    | number
    | boolean
    | null;

  formula_mode?:
    | "safe_aggregation"
    | null;

  formula?: string | null;

  description: string;

  source:
    | "local"
    | "user";
};

type Props = {
  studio: DataModelStudioData;
  candidates: PersonalKpiData[];
  selectedDefinitions: PersonalKpiData[];
  loading: boolean;
  error: string | null;

  onSave: (
    definitions: PersonalKpiData[]
  ) => void;
};

function normalizeCode(
  value: string
): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
  );
}

function PersonalKpiCandidates({
  studio,
  candidates,
  selectedDefinitions,
  loading,
  error,
  onSave,
}: Props) {
  const [definitions, setDefinitions] =
    useState<PersonalKpiData[]>([]);

  const factTables =
    useMemo(
      () =>
        studio.tables.filter(
          (table) =>
            table.table_type ===
            "fact"
        ),
      [studio.tables]
    );

  const [
    factTable,
    setFactTable,
  ] = useState(
    factTables[0]?.name ?? ""
  );

  const selectedFact =
    factTables.find(
      (table) =>
        table.name === factTable
    ) ?? null;

  const measureColumns =
    selectedFact?.columns.filter(
      (column) =>
        column.role === "measure"
    ) ?? [];

  const [
    measure,
    setMeasure,
  ] = useState(
    measureColumns[0]?.name ?? ""
  );

  const [
    aggregation,
    setAggregation,
  ] = useState<
    "count" |
    "sum" |
    "mean" |
    "min" |
    "max"
  >("sum");

  const relationshipOptions =
    useMemo(
      () =>
        studio.relationships.filter(
          (relationship) =>
            relationship.active &&
            relationship.from_table ===
              factTable
        ),
      [
        studio.relationships,
        factTable,
      ]
    );

  const [
    dimensionTable,
    setDimensionTable,
  ] = useState("");

  const selectedDimensionRelationship =
    relationshipOptions.find(
      (relationship) =>
        relationship.to_table ===
        dimensionTable
    ) ?? null;

  const dimensionTableData =
    studio.tables.find(
      (table) =>
        table.name ===
        dimensionTable
    ) ?? null;

  const [
    dimensionColumn,
    setDimensionColumn,
  ] = useState("");

  const [
    title,
    setTitle,
  ] = useState("");

  const [
    filterValue,
    setFilterValue,
  ] = useState("");

  const [
    builderError,
    setBuilderError,
  ] = useState<string | null>(
    null
  );

  useEffect(() => {
    setDefinitions(
      selectedDefinitions
    );
  }, [selectedDefinitions]);

  useEffect(() => {
    const nextFact =
      factTables[0]?.name ?? "";

    if (
      !factTables.some(
        (table) =>
          table.name === factTable
      )
    ) {
      setFactTable(
        nextFact
      );
    }
  }, [
    factTables,
    factTable,
  ]);

  useEffect(() => {
    const currentFact =
      factTables.find(
        (table) =>
          table.name === factTable
      );

    const nextMeasures =
      currentFact?.columns.filter(
        (column) =>
          column.role ===
          "measure"
      ) ?? [];

    if (
      !nextMeasures.some(
        (column) =>
          column.name === measure
      )
    ) {
      setMeasure(
        nextMeasures[0]?.name ??
        ""
      );
    }

    setDimensionTable("");
    setDimensionColumn("");
  }, [
    factTable,
    factTables,
    measure,
  ]);

  useEffect(() => {
    if (!dimensionTableData) {
      setDimensionColumn("");
      return;
    }

    if (
      !dimensionTableData.columns.some(
        (column) =>
          column.name ===
          dimensionColumn
      )
    ) {
      setDimensionColumn(
        dimensionTableData
          .columns[0]?.name ??
        ""
      );
    }
  }, [
    dimensionTableData,
    dimensionColumn,
  ]);

  const formulaPreview =
    useMemo(
      () => {
        if (
          !factTable ||
          !measure
        ) {
          return "";
        }

        let formula =
          `${aggregation.toUpperCase()}(${factTable}.${measure})`;

        if (
          dimensionTable &&
          dimensionColumn
        ) {
          formula +=
            ` BY ${dimensionTable}.${dimensionColumn}`;
        }

        if (
          filterValue.trim()
        ) {
          formula +=
            ` FILTER=${filterValue.trim()}`;
        }

        return formula;
      },
      [
        aggregation,
        factTable,
        measure,
        dimensionTable,
        dimensionColumn,
        filterValue,
      ]
    );

  function addDefinition() {
    setBuilderError(null);

    if (
      !factTable ||
      !measure
    ) {
      setBuilderError(
        "Select a fact table and measure column."
      );

      return;
    }

    if (
      dimensionTable &&
      !selectedDimensionRelationship
    ) {
      setBuilderError(
        "Selected dimension is not connected to this fact table."
      );

      return;
    }

    const defaultTitle =
      `${aggregation.toUpperCase()} ${measure}`;

    const cleanTitle =
      title.trim() ||
      defaultTitle;

    const codeBase =
      normalizeCode(
        `${cleanTitle}_${factTable}`
      );

    let code =
      codeBase ||
      `kpi_${definitions.length + 1}`;

    let suffix = 2;

    while (
      definitions.some(
        (item) =>
          item.code === code
      )
    ) {
      code =
        `${codeBase}_${suffix}`;

      suffix += 1;
    }

    const definition:
      PersonalKpiData = {
        code,
        title: cleanTitle,
        fact_table:
          factTable,
        measure,
        aggregation,
        dimension_table:
          dimensionTable || null,
        dimension:
          dimensionTable
            ? dimensionColumn || null
            : null,
        filter_value:
          filterValue.trim()
            ? filterValue.trim()
            : null,
        formula_mode:
          "safe_aggregation",
        formula:
          formulaPreview,
        description:
          `${cleanTitle} built from the current logical model.`,
        source:
          "user",
      };

    setDefinitions(
      (previous) => [
        ...previous,
        definition,
      ]
    );

    setTitle("");
    setFilterValue("");
  }

  function addSuggestion(
    candidate: PersonalKpiData
  ) {
    if (
      definitions.some(
        (item) =>
          item.code === candidate.code
      )
    ) {
      return;
    }

    setDefinitions(
      (previous) => [
        ...previous,
        candidate,
      ]
    );
  }

  function removeDefinition(
    code: string
  ) {
    setDefinitions(
      (previous) =>
        previous.filter(
          (item) =>
            item.code !== code
        )
    );
  }

  return (
    <section className="personal-kpi-card kpi-builder-card">
      <div className="personal-kpi-header">
        <div>
          <span className="workspace-overview-label">
            KPI / MEASURE BUILDER
          </span>

          <h2>
            Define model-aware KPIs
          </h2>

          <p>
            Build safe KPI definitions from the
            current fact table, measure columns and
            connected dimensions.
          </p>
        </div>

        <span className="personal-analysis-plan-source">
          Safe aggregation mode
        </span>
      </div>

      <div className="kpi-builder-layout">
        <div className="kpi-builder-form">
          <div className="kpi-builder-grid">
            <label>
              <span>Fact table</span>

              <select
                value={factTable}
                onChange={(event) =>
                  setFactTable(
                    event.target.value
                  )
                }
              >
                {factTables.map(
                  (table) => (
                    <option
                      key={table.name}
                      value={table.name}
                    >
                      {table.name}
                    </option>
                  )
                )}
              </select>
            </label>

            <label>
              <span>
                Measure column
              </span>

              <select
                value={measure}
                onChange={(event) =>
                  setMeasure(
                    event.target.value
                  )
                }
              >
                {measureColumns.map(
                  (column) => (
                    <option
                      key={column.name}
                      value={column.name}
                    >
                      {column.name}
                    </option>
                  )
                )}
              </select>
            </label>

            <label>
              <span>
                Aggregation
              </span>

              <select
                value={aggregation}
                onChange={(event) =>
                  setAggregation(
                    event.target.value as
                      typeof aggregation
                  )
                }
              >
                <option value="sum">
                  Sum
                </option>
                <option value="mean">
                  Average
                </option>
                <option value="count">
                  Count
                </option>
                <option value="min">
                  Minimum
                </option>
                <option value="max">
                  Maximum
                </option>
              </select>
            </label>

            <label>
              <span>
                Dimension table
              </span>

              <select
                value={dimensionTable}
                onChange={(event) =>
                  setDimensionTable(
                    event.target.value
                  )
                }
              >
                <option value="">
                  None
                </option>

                {relationshipOptions.map(
                  (relationship) => (
                    <option
                      key={
                        relationship.to_table
                      }
                      value={
                        relationship.to_table
                      }
                    >
                      {
                        relationship.to_table
                      }
                    </option>
                  )
                )}
              </select>
            </label>

            {dimensionTable && (
              <label>
                <span>
                  Dimension column
                </span>

                <select
                  value={dimensionColumn}
                  onChange={(event) =>
                    setDimensionColumn(
                      event.target.value
                    )
                  }
                >
                  {dimensionTableData
                    ?.columns
                    .map(
                      (column) => (
                        <option
                          key={column.name}
                          value={column.name}
                        >
                          {column.name}
                        </option>
                      )
                    )}
                </select>
              </label>
            )}

            <label>
              <span>
                Optional filter value
              </span>

              <input
                value={filterValue}
                onChange={(event) =>
                  setFilterValue(
                    event.target.value
                  )
                }
                placeholder="e.g. West"
              />
            </label>

            <label className="kpi-builder-title-field">
              <span>
                KPI title
              </span>

              <input
                value={title}
                onChange={(event) =>
                  setTitle(
                    event.target.value
                  )
                }
                placeholder={
                  measure
                    ? `${aggregation.toUpperCase()} ${measure}`
                    : "KPI title"
                }
              />
            </label>
          </div>

          <div className="kpi-formula-preview">
            <span>
              SAFE FORMULA PREVIEW
            </span>

            <code>
              {formulaPreview ||
                "Select a fact table and measure."}
            </code>
          </div>

          {builderError && (
            <div className="personal-analysis-error">
              {builderError}
            </div>
          )}

          {measureColumns.length === 0 && (
            <div className="personal-analysis-error">
              The selected fact table has no columns
              with the measure role. Edit the Data
              Model first.
            </div>
          )}

          <button
            type="button"
            className="new-workspace-button"
            disabled={
              !measure ||
              measureColumns.length === 0
            }
            onClick={addDefinition}
          >
            + Add KPI definition
          </button>
        </div>

        <div className="kpi-builder-definitions">
          <div className="kpi-builder-section-header">
            <div>
              <span className="workspace-overview-label">
                DEFINITIONS
              </span>

              <strong>
                {definitions.length} KPI
                {definitions.length === 1
                  ? ""
                  : "s"}
              </strong>
            </div>
          </div>

          <div className="kpi-definition-list">
            {definitions.map(
              (definition) => (
                <div
                  key={definition.code}
                  className="kpi-definition-item"
                >
                  <div>
                    <strong>
                      {definition.title}
                    </strong>

                    <span>
                      {definition.formula ??
                        `${definition.aggregation.toUpperCase()}(${definition.measure ?? "—"})`}
                    </span>
                  </div>

                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      removeDefinition(
                        definition.code
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              )
            )}

            {definitions.length === 0 && (
              <p className="kpi-builder-empty">
                Add a KPI from the builder or use a
                suggested definition.
              </p>
            )}
          </div>
        </div>
      </div>

      {candidates.length > 0 && (
        <div className="kpi-suggestions">
          <div className="kpi-builder-section-header">
            <div>
              <span className="workspace-overview-label">
                SUGGESTIONS
              </span>

              <strong>
                Model-based starting points
              </strong>
            </div>
          </div>

          <div className="kpi-suggestion-grid">
            {candidates.map(
              (candidate) => {
                const alreadyAdded =
                  definitions.some(
                    (item) =>
                      item.code ===
                      candidate.code
                  );

                return (
                  <div
                    key={candidate.code}
                    className="kpi-suggestion-item"
                  >
                    <div>
                      <strong>
                        {candidate.title}
                      </strong>

                      <span>
                        {candidate.formula ??
                          candidate.description}
                      </span>
                    </div>

                    <button
                      type="button"
                      className="secondary-button"
                      disabled={alreadyAdded}
                      onClick={() =>
                        addSuggestion(
                          candidate
                        )
                      }
                    >
                      {alreadyAdded
                        ? "Added"
                        : "Add"}
                    </button>
                  </div>
                );
              }
            )}
          </div>
        </div>
      )}

      {error && (
        <p className="personal-analysis-error">
          {error}
        </p>
      )}

      <div className="personal-kpi-actions">
        <span>
          {definitions.length} KPI
          {definitions.length === 1
            ? ""
            : "s"}{" "}
          ready
        </span>

        <button
          type="button"
          className="new-workspace-button"
          disabled={
            loading ||
            definitions.length === 0
          }
          onClick={() =>
            onSave(
              definitions
            )
          }
        >
          {loading
            ? "Saving KPIs..."
            : "Save KPI definitions"}
        </button>
      </div>
    </section>
  );
}

export default PersonalKpiCandidates;
