import {
  useMemo,
  useState,
} from "react";

import type {
  DataModelStudioData,
} from "./DataModelCanvas";


type Relationship =
  DataModelStudioData[
    "relationships"
  ][number];


type Cardinality =
  Relationship["cardinality"];


type Props = {
  studio: DataModelStudioData;

  editingRelationshipIndex?:
    number | null;

  saving: boolean;

  onCancel: () => void;

  onSave: (
    studio: DataModelStudioData
  ) => Promise<void>;
};


function DataModelRelationshipEditor({
  studio,
  editingRelationshipIndex = null,
  saving,
  onCancel,
  onSave,
}: Props) {

  const editingRelationship =
    editingRelationshipIndex !== null
      ? (
          studio.relationships[
            editingRelationshipIndex
          ] ?? null
        )
      : null;

  const isEditing =
    editingRelationship !== null;

  const defaultFromTable =
    editingRelationship?.from_table ??
    studio.tables.find(
      (table) =>
        table.table_type === "fact"
    )?.name ??
    studio.tables[0]?.name ??
    "";


  const defaultToTable =
    editingRelationship?.to_table ??
    studio.tables.find(
      (table) =>
        table.table_type === "dimension"
    )?.name ??
    studio.tables[1]?.name ??
    "";


  const [
    fromTable,
    setFromTable,
  ] = useState(
    defaultFromTable
  );


  const [
    fromColumn,
    setFromColumn,
  ] = useState(
    editingRelationship?.from_column ??
    ""
  );


  const [
    toTable,
    setToTable,
  ] = useState(
    defaultToTable
  );


  const [
    toColumn,
    setToColumn,
  ] = useState(
    editingRelationship?.to_column ??
    ""
  );


  const [
    cardinality,
    setCardinality,
  ] = useState<Cardinality>(
    editingRelationship?.cardinality ??
    "many_to_one"
  );


  const [
    active,
    setActive,
  ] = useState(
    editingRelationship?.active ??
    true
  );


  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  const fromTableData =
    useMemo(
      () =>
        studio.tables.find(
          (table) =>
            table.name ===
            fromTable
        ),
      [
        studio.tables,
        fromTable,
      ]
    );


  const toTableData =
    useMemo(
      () =>
        studio.tables.find(
          (table) =>
            table.name ===
            toTable
        ),
      [
        studio.tables,
        toTable,
      ]
    );


  function changeFromTable(
    tableName: string,
  ) {
    setFromTable(
      tableName
    );

    setFromColumn("");
  }


  function changeToTable(
    tableName: string,
  ) {
    setToTable(
      tableName
    );

    setToColumn("");
  }


  async function createRelationship() {
    setError(null);


    if (
      !fromTable ||
      !fromColumn ||
      !toTable ||
      !toColumn
    ) {
      setError(
        "Select both tables and columns."
      );

      return;
    }


    if (
      fromTable === toTable &&
      fromColumn === toColumn
    ) {
      setError(
        "A column cannot be related to itself."
      );

      return;
    }


    const duplicate =
      studio.relationships.some(
        (
          relationship,
          index,
        ) => {
        
          if (
            editingRelationshipIndex ===
            index
          ) {
            return false;
          }
        
        
          const sameDirection =
            relationship.from_table ===
              fromTable &&
            relationship.from_column ===
              fromColumn &&
            relationship.to_table ===
              toTable &&
            relationship.to_column ===
              toColumn;
        
        
          const reverseDirection =
            relationship.from_table ===
              toTable &&
            relationship.from_column ===
              toColumn &&
            relationship.to_table ===
              fromTable &&
            relationship.to_column ===
              fromColumn;
        
        
          return (
            sameDirection ||
            reverseDirection
          );
        }
      );


    if (duplicate) {
      setError(
        (
          "A relationship between these " +
          "columns already exists."
        )
      );

      return;
    }


    const selectedFromColumn =
      fromTableData?.columns.find(
        (column) =>
          column.name ===
          fromColumn
      );


    const selectedToColumn =
      toTableData?.columns.find(
        (column) =>
          column.name ===
          toColumn
      );


    /*
     * many_to_one:
     *
     * fact.customer_id  * → 1
     * dim_customer.id
     *
     * Bu yüzden "1" tarafında
     * Key bekliyoruz.
     */
    if (
      cardinality ===
        "many_to_one" &&
      selectedToColumn?.role !==
        "key"
    ) {
      setError(
        (
          "For a many-to-one relationship, " +
          "the target column should be a Key."
        )
      );

      return;
    }


    /*
     * one_to_many:
     *
     * dimension.id  1 → *
     * fact.customer_id
     */
    if (
      cardinality ===
        "one_to_many" &&
      selectedFromColumn?.role !==
        "key"
    ) {
      setError(
        (
          "For a one-to-many relationship, " +
          "the source column should be a Key."
        )
      );

      return;
    }


    if (
      cardinality ===
        "one_to_one" &&
      (
        selectedFromColumn?.role !==
          "key" ||
        selectedToColumn?.role !==
          "key"
      )
    ) {
      setError(
        (
          "For a one-to-one relationship, " +
          "both columns should be Keys."
        )
      );

      return;
    }


    const relationship:
      Relationship = {

      from_table:
        fromTable,

      from_column:
        fromColumn,

      to_table:
        toTable,

      to_column:
        toColumn,

      cardinality,

      active,
    };


    const updatedRelationships =
      isEditing &&
      editingRelationshipIndex !== null
        ? studio.relationships.map(
            (
              currentRelationship,
              index,
            ) =>
              index ===
              editingRelationshipIndex
                ? relationship
                : currentRelationship
          )
        : [
            ...studio.relationships,
            relationship,
          ];
        
        
    const updatedStudio:
      DataModelStudioData = {
      
      ...studio,
      
      source: "user",
      
      relationships:
        updatedRelationships,
    };


    await onSave(
      updatedStudio
    );
  }


  return (
    <div
      className="model-editor-backdrop"
      role="presentation"
    >

      <section
        className="model-editor-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Create relationship"
      >

        <header className="model-editor-header">

          <div>
            <span className="workspace-overview-label">
              MODEL STUDIO
            </span>

            <h3>
              {isEditing
                ? "Edit relationship"
                : "Create relationship"}
            </h3>

            <p>
              {isEditing
                ? (
                    "Update columns, cardinality " +
                    "or relationship status."
                  )
                : (
                    "Connect columns between " +
                    "model tables."
                  )}
            </p>
          </div>


          <button
            type="button"
            className="model-editor-close"
            onClick={onCancel}
            disabled={saving}
          >
            ×
          </button>

        </header>


        <div className="model-editor-body">

          <div className="model-relationship-side">

            <strong>
              From
            </strong>


            <label className="model-editor-field">
              <span>Table</span>

              <select
                value={fromTable}
                onChange={(event) =>
                  changeFromTable(
                    event.target.value
                  )
                }
              >
                {studio.tables.map(
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


            <label className="model-editor-field">
              <span>Column</span>

              <select
                value={fromColumn}
                onChange={(event) =>
                  setFromColumn(
                    event.target.value
                  )
                }
              >
                <option value="">
                  Select column...
                </option>

                {fromTableData?.columns.map(
                  (column) => (
                    <option
                      key={column.name}
                      value={column.name}
                    >
                      {column.name}
                      {" — "}
                      {column.role}
                    </option>
                  )
                )}
              </select>
            </label>

          </div>


          <div className="model-relationship-arrow">
            →
          </div>


          <div className="model-relationship-side">

            <strong>
              To
            </strong>


            <label className="model-editor-field">
              <span>Table</span>

              <select
                value={toTable}
                onChange={(event) =>
                  changeToTable(
                    event.target.value
                  )
                }
              >
                {studio.tables.map(
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


            <label className="model-editor-field">
              <span>Column</span>

              <select
                value={toColumn}
                onChange={(event) =>
                  setToColumn(
                    event.target.value
                  )
                }
              >
                <option value="">
                  Select column...
                </option>

                {toTableData?.columns.map(
                  (column) => (
                    <option
                      key={column.name}
                      value={column.name}
                    >
                      {column.name}
                      {" — "}
                      {column.role}
                    </option>
                  )
                )}
              </select>
            </label>

          </div>


          <label className="model-editor-field">
            <span>Cardinality</span>

            <select
              value={cardinality}
              onChange={(event) =>
                setCardinality(
                  event.target.value as Cardinality
                )
              }
            >
              <option value="many_to_one">
                Many to one (* → 1)
              </option>

              <option value="one_to_many">
                One to many (1 → *)
              </option>

              <option value="one_to_one">
                One to one (1 → 1)
              </option>
            </select>
          </label>


          <label className="model-relationship-active">

            <input
              type="checkbox"
              checked={active}
              onChange={(event) =>
                setActive(
                  event.target.checked
                )
              }
            />

            <span>
              Active relationship
            </span>

          </label>


          {error && (
            <div className="personal-analysis-error">
              {error}
            </div>
          )}

        </div>


        <footer className="model-editor-footer">

          <button
            type="button"
            className="model-editor-cancel"
            onClick={onCancel}
            disabled={saving}
          >
            Cancel
          </button>


          <button
            type="button"
            className="new-workspace-button"
            onClick={
              createRelationship
            }
            disabled={saving}
          >
            {saving
              ? "Saving..."
              : isEditing
                ? "Save changes"
                : "Create relationship"}
          </button>

        </footer>

      </section>

    </div>
  );
}


export default DataModelRelationshipEditor;