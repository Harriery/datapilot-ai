import {
  useState,
} from "react";

import type {
  DataModelStudioData,
} from "./DataModelCanvas";


type TableData =
  DataModelStudioData[
    "tables"
  ][number];


type ColumnData =
  TableData[
    "columns"
  ][number];


type ColumnRole =
  ColumnData["role"];


type DraftColumn = {
  id: string;

  /*
   * Mevcut kolon edit ediliyorsa
   * eski adını burada tutuyoruz.
   *
   * Böylece rename sırasında
   * relationship'i de güncelleyebiliriz.
   */
  originalName: string | null;

  name: string;

  role: ColumnRole;

  sourceColumn: string | null;

  aggregation:
    ColumnData["aggregation"];
};


type Props = {
  studio: DataModelStudioData;

  editingTableName?:
    string | null;

  onCancel: () => void;

  onSave: (
    studio: DataModelStudioData
  ) => Promise<void>;

  saving: boolean;
};


function DataModelTableEditor({
  studio,
  editingTableName = null,
  onCancel,
  onSave,
  saving,
}: Props) {

  const editingTable =
    studio.tables.find(
      (table) =>
        table.name ===
        editingTableName
    ) ?? null;


  const isEditing =
    editingTable !== null;


  const [
    tableName,
    setTableName,
  ] = useState(
    editingTable?.name ?? ""
  );


  const [
    tableType,
    setTableType,
  ] = useState<
    "fact" |
    "dimension" |
    "bridge"
  >(
    editingTable?.table_type ??
      "dimension"
  );


  const [
    columns,
    setColumns,
  ] = useState<DraftColumn[]>(
    editingTable
      ? editingTable.columns.map(
          (column) => ({
            id:
              crypto.randomUUID(),

            originalName:
              column.name,

            name:
              column.name,

            role:
              column.role,

            sourceColumn:
              column.source_column,

            aggregation:
              column.aggregation,
          })
        )
      : [
          {
            id:
              crypto.randomUUID(),

            originalName:
              null,

            name:
              "",

            role:
              "key",

            sourceColumn:
              null,

            aggregation:
              null,
          },
        ]
  );


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
          id:
            crypto.randomUUID(),

          originalName:
            null,

          name:
            "",

          role:
            "attribute",

          sourceColumn:
            null,

          aggregation:
            null,
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


  async function saveTable() {
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
          table.name
            .toLowerCase() ===
            cleanTableName
              .toLowerCase() &&
          table.name !==
            editingTableName
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

            name:
              column.name.trim(),
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
      new Set(
        columnNames
      ).size !==
      columnNames.length
    ) {
      setError(
        "Column names must be unique."
      );

      return;
    }


    /*
     * Edit modundaysak:
     * silinen kolonlardan herhangi biri
     * relationship tarafından kullanılıyor mu?
     */
    if (editingTable) {

      const retainedOriginalNames =
        new Set(
          cleanColumns
            .map(
              (column) =>
                column.originalName
            )
            .filter(
              (
                value,
              ): value is string =>
                value !== null
            )
        );


      const removedColumns =
        editingTable.columns
          .map(
            (column) =>
              column.name
          )
          .filter(
            (name) =>
              !retainedOriginalNames.has(
                name
              )
          );


      const usedRemovedColumn =
        removedColumns.find(
          (columnName) =>
            studio.relationships.some(
              (relationship) =>
                (
                  relationship.from_table ===
                    editingTable.name &&
                  relationship.from_column ===
                    columnName
                ) ||
                (
                  relationship.to_table ===
                    editingTable.name &&
                  relationship.to_column ===
                    columnName
                )
            )
        );


      if (usedRemovedColumn) {
        setError(
          (
            `"${usedRemovedColumn}" is used ` +
            "by a relationship. Delete the " +
            "relationship before removing " +
            "this column."
          )
        );

        return;
      }
    }


    const updatedTable:
      TableData = {

      name:
        cleanTableName,

      table_type:
        tableType,

      columns:
        cleanColumns.map(
          (column) => ({

            name:
              column.name,

            source_column:
              column.sourceColumn,

            role:
              column.role,

            aggregation:
              column.aggregation,
          })
        ),
    };


    /*
     * CREATE
     */
    if (!editingTable) {

      const updatedStudio:
        DataModelStudioData = {

        ...studio,

        source:
          "user",

        tables: [
          ...studio.tables,
          updatedTable,
        ],
      };


      await onSave(
        updatedStudio
      );

      return;
    }


    /*
     * EDIT
     *
     * Kolon rename map:
     *
     * customer → customer_id
     */
    const columnRenameMap =
      new Map<
        string,
        string
      >();


    cleanColumns.forEach(
      (column) => {

        if (
          column.originalName &&
          column.originalName !==
            column.name
        ) {
          columnRenameMap.set(
            column.originalName,
            column.name
          );
        }
      }
    );


    const updatedRelationships =
      studio.relationships.map(
        (relationship) => {

          let nextRelationship = {
            ...relationship,
          };


          if (
            relationship.from_table ===
            editingTable.name
          ) {
            nextRelationship = {
              ...nextRelationship,

              from_table:
                cleanTableName,

              from_column:
                columnRenameMap.get(
                  relationship.from_column
                ) ??
                relationship.from_column,
            };
          }


          if (
            relationship.to_table ===
            editingTable.name
          ) {
            nextRelationship = {
              ...nextRelationship,

              to_table:
                cleanTableName,

              to_column:
                columnRenameMap.get(
                  relationship.to_column
                ) ??
                relationship.to_column,
            };
          }


          return nextRelationship;
        }
      );


    const updatedStudio:
      DataModelStudioData = {

      ...studio,

      source:
        "user",

      tables:
        studio.tables.map(
          (table) =>
            table.name ===
            editingTable.name
              ? updatedTable
              : table
        ),

      relationships:
        updatedRelationships,
    };


    await onSave(
      updatedStudio
    );
  }


  async function deleteTable() {

    if (!editingTable) {
      return;
    }


    const relationshipCount =
      studio.relationships.filter(
        (relationship) =>
          relationship.from_table ===
            editingTable.name ||
          relationship.to_table ===
            editingTable.name
      ).length;


    const message =
      relationshipCount > 0
        ? (
            `Delete "${editingTable.name}"? ` +
            `${relationshipCount} connected ` +
            "relationship(s) will also be deleted."
          )
        : (
            `Delete "${editingTable.name}"?`
          );


    if (
      !window.confirm(
        message
      )
    ) {
      return;
    }


    const updatedStudio:
      DataModelStudioData = {

      ...studio,

      source:
        "user",

      tables:
        studio.tables.filter(
          (table) =>
            table.name !==
            editingTable.name
        ),

      relationships:
        studio.relationships.filter(
          (relationship) =>
            relationship.from_table !==
              editingTable.name &&
            relationship.to_table !==
              editingTable.name
        ),
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
        aria-label={
          isEditing
            ? "Edit table"
            : "Create table"
        }
      >

        <header className="model-editor-header">

          <div>
            <span className="workspace-overview-label">
              MODEL STUDIO
            </span>

            <h3>
              {isEditing
                ? "Edit table"
                : "Create table"}
            </h3>

            <p>
              {isEditing
                ? (
                    "Edit table structure, " +
                    "columns and model roles."
                  )
                : (
                    "Add a fact, dimension or " +
                    "bridge table to the model."
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

          <label className="model-editor-field">

            <span>
              Table name
            </span>

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

            <span>
              Table type
            </span>

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
                        event.target.value as
                          ColumnRole
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

          {isEditing && (
            <button
              type="button"
              className="model-table-delete-button"
              onClick={deleteTable}
              disabled={saving}
            >
              Delete table
            </button>
          )}


          <div className="model-editor-footer-spacer" />


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
            onClick={saveTable}
            disabled={saving}
          >
            {saving
              ? "Saving..."
              : isEditing
                ? "Save changes"
                : "Create table"}
          </button>

        </footer>

      </section>

    </div>
  );
}


export default DataModelTableEditor;