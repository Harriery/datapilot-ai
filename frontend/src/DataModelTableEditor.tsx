import {
  useState,
} from "react";

import type {
  DataModelStudioData,
} from "./DataModelCanvas";


type ColumnRole =
  DataModelStudioData["tables"][number]["columns"][number]["role"];


type DraftColumn = {
  id: string;
  name: string;
  role: ColumnRole;
};


type Props = {
  studio: DataModelStudioData;

  onCancel: () => void;

  onSave: (
    studio: DataModelStudioData
  ) => Promise<void>;

  saving: boolean;
};


function DataModelTableEditor({
  studio,
  onCancel,
  onSave,
  saving,
}: Props) {

  const [
    tableName,
    setTableName,
  ] = useState("");


  const [
    tableType,
    setTableType,
  ] = useState<
    "fact" |
    "dimension" |
    "bridge"
  >("dimension");


  const [
    columns,
    setColumns,
  ] = useState<DraftColumn[]>([
    {
      id: crypto.randomUUID(),
      name: "",
      role: "key",
    },
  ]);


  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  function addColumn() {
    setColumns(
      (previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          name: "",
          role: "attribute",
        },
      ]
    );
  }


  function removeColumn(
    id: string,
  ) {
    setColumns(
      (previous) =>
        previous.filter(
          (column) =>
            column.id !== id
        )
    );
  }


  function updateColumnName(
    id: string,
    name: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id
              ? {
                  ...column,
                  name,
                }
              : column
        )
    );
  }


  function updateColumnRole(
    id: string,
    role: ColumnRole,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id
              ? {
                  ...column,
                  role,
                }
              : column
        )
    );
  }


  async function createTable() {
    setError(null);

    const cleanTableName =
      tableName.trim();

    if (!cleanTableName) {
      setError(
        "Table name is required."
      );
      return;
    }


    const tableAlreadyExists =
      studio.tables.some(
        (table) =>
          table.name.toLowerCase() ===
          cleanTableName.toLowerCase()
      );

    if (tableAlreadyExists) {
      setError(
        "A table with this name already exists."
      );
      return;
    }


    const cleanColumns =
      columns
        .map(
          (column) => ({
            ...column,
            name: column.name.trim(),
          })
        )
        .filter(
          (column) =>
            column.name.length > 0
        );


    if (
      cleanColumns.length === 0
    ) {
      setError(
        "Add at least one column."
      );
      return;
    }


    const columnNames =
      cleanColumns.map(
        (column) =>
          column.name.toLowerCase()
      );


    if (
      new Set(columnNames).size !==
      columnNames.length
    ) {
      setError(
        "Column names must be unique."
      );
      return;
    }


    const updatedStudio:
      DataModelStudioData = {

      ...studio,

      source: "user",

      tables: [
        ...studio.tables,

        {
          name: cleanTableName,

          table_type:
            tableType,

          columns:
            cleanColumns.map(
              (column) => ({
                name:
                  column.name,

                source_column:
                  null,

                role:
                  column.role,

                aggregation:
                  null,
              })
            ),
        },
      ],
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
        aria-label="Create table"
      >

        <header className="model-editor-header">

          <div>
            <span className="workspace-overview-label">
              MODEL STUDIO
            </span>

            <h3>
              Create table
            </h3>

            <p>
              Add a fact, dimension or
              bridge table to the model.
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

          <label className="model-editor-field">
            <span>Table name</span>

            <input
              type="text"
              value={tableName}
              placeholder="Enter table name..."
              onChange={(event) =>
                setTableName(
                  event.target.value
                )
              }
            />
          </label>


          <label className="model-editor-field">
            <span>Table type</span>

            <select
              value={tableType}
              onChange={(event) =>
                setTableType(
                  event.target.value as
                    | "fact"
                    | "dimension"
                    | "bridge"
                )
              }
            >
              <option value="fact">
                Fact
              </option>

              <option value="dimension">
                Dimension
              </option>

              <option value="bridge">
                Bridge
              </option>
            </select>
          </label>


          <div className="model-editor-columns">

            <div className="model-editor-columns-header">
              <strong>
                Columns
              </strong>

              <button
                type="button"
                onClick={addColumn}
              >
                + Column
              </button>
            </div>


            {columns.map(
              (column) => (

                <div
                  key={column.id}
                  className="model-editor-column-row"
                >

                  <input
                    type="text"
                    value={column.name}
                    placeholder="Enter column name..."
                    onChange={(event) =>
                      updateColumnName(
                        column.id,
                        event.target.value
                      )
                    }
                  />


                  <select
                      value={column.role}
                      onChange={(event) =>
                        updateColumnRole(
                          column.id,
                          event.target.value as ColumnRole
                        )
                      }
                    >
                    <option value="key">
                      Key
                    </option>

                    <option value="foreign_key">
                      Foreign Key
                    </option>

                    <option value="measure">
                      Measure
                    </option>

                    <option value="attribute">
                      Attribute
                    </option>

                    <option value="dimension">
                      Dimension
                    </option>

                    <option value="time">
                      Time
                    </option>
                  </select>


                  <button
                    type="button"
                    className="model-editor-remove-column"
                    onClick={() =>
                      removeColumn(
                        column.id
                      )
                    }
                    disabled={
                      columns.length === 1
                    }
                    title="Remove column"
                  >
                    ×
                  </button>

                </div>

              )
            )}

          </div>


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
            onClick={createTable}
            disabled={saving}
          >
            {saving
              ? "Creating..."
              : "Create table"}
          </button>

        </footer>

      </section>

    </div>
  );
}


export default DataModelTableEditor;