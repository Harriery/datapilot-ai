import {
  useState,
} from "react";

import type {
  DataModelDerivation,
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


type DerivationType =
  | "date_part"
  | "text"
  | "numeric"
  | "multi_column"
  | "mapping"
  | "bucketing";


const DERIVATION_HELP:
  Record<
    string,
    {
      title: string;
      description: string;
      example: string;
    }
  > = {
    date_part: {
      title: "Date part",
      description: "Creates a new model column from part of a date.",
      example: "OrderDate → Year = 2026",
    },
    text: {
      title: "Text operation",
      description: "Cleans or reshapes text without changing the source dataset.",
      example: "'  amsterdam ' → Trim → 'amsterdam'",
    },
    numeric: {
      title: "Numeric operation",
      description: "Builds a calculated numeric model column.",
      example: "Revenue / Quantity → UnitPrice",
    },
    multi_column: {
      title: "Combine columns",
      description: "Combines values from two columns into one model column.",
      example: "Address + Suburb → LocationKey",
    },
    mapping: {
      title: "Mapping / Case",
      description: "Translates coded values into readable labels.",
      example: "h → House, u → Unit",
    },
    bucketing: {
      title: "Bucketing",
      description: "Groups numeric values into labeled ranges.",
      example: "18–29 → Young adult",
    },
    trim: {
      title: "Trim",
      description: "Removes spaces at the beginning and end of text.",
      example: "'  Yasin  ' → 'Yasin'",
    },
    uppercase: {
      title: "Uppercase",
      description: "Converts text to capital letters.",
      example: "'abc' → 'ABC'",
    },
    lowercase: {
      title: "Lowercase",
      description: "Converts text to lowercase letters.",
      example: "'ABC' → 'abc'",
    },
    replace: {
      title: "Replace",
      description: "Replaces one text fragment with another.",
      example: "'North Rd' → replace 'Rd' with 'Road'",
    },
    substring: {
      title: "Substring",
      description: "Takes only a selected part of a text value.",
      example: "'2026-NL-001' → start 5, length 2 → 'NL'",
    },
    round: {
      title: "Round",
      description: "Rounds a numeric value to a chosen number of decimals.",
      example: "12.347 → 2 decimals → 12.35",
    },
    add: {
      title: "Add",
      description: "Adds two numeric columns.",
      example: "Net + Tax → Gross",
    },
    subtract: {
      title: "Subtract",
      description: "Subtracts the second numeric column from the first.",
      example: "Revenue - Cost → Profit",
    },
    multiply: {
      title: "Multiply",
      description: "Multiplies two numeric columns.",
      example: "Quantity × UnitPrice → Revenue",
    },
    divide: {
      title: "Divide",
      description: "Divides the first numeric column by the second.",
      example: "Revenue / Quantity → UnitPrice",
    },
    concatenate: {
      title: "Concatenate",
      description: "Joins two values with a separator.",
      example: "Main St + Carlton → Main St | Carlton",
    },
    map_values: {
      title: "Map values",
      description: "Maps known source values to new labels.",
      example: "A => Active; I => Inactive",
    },
  };


function DerivationHelp({
  helpKey,
}: {
  helpKey: string;
}) {
  const help = DERIVATION_HELP[helpKey];

  if (!help) {
    return null;
  }

  return (
    <span
      className="model-derivation-help"
      tabIndex={0}
      aria-label={
        `${help.title}: ${help.description}. Example: ${help.example}`
      }
    >
      ?

      <span
        className="model-derivation-tooltip"
        role="tooltip"
      >
        <strong>{help.title}</strong>
        <span>{help.description}</span>
        <small>Example: {help.example}</small>
      </span>
    </span>
  );
}


type DerivationTypePickerProps = {
  value: DerivationType;

  onChange: (
    value: DerivationType
  ) => void;
};


const DERIVATION_TYPE_OPTIONS:
  Array<{
    value: DerivationType;
    label: string;
  }> = [
    {
      value: "date_part",
      label: "Date part",
    },
    {
      value: "text",
      label: "Text operation",
    },
    {
      value: "numeric",
      label: "Numeric operation",
    },
    {
      value: "multi_column",
      label: "Combine columns",
    },
    {
      value: "mapping",
      label: "Mapping / Case",
    },
    {
      value: "bucketing",
      label: "Bucketing",
    },
  ];


function DerivationTypePicker({
  value,
  onChange,
}: DerivationTypePickerProps) {
  const [
    open,
    setOpen,
  ] = useState(false);

  const selected =
    DERIVATION_TYPE_OPTIONS.find(
      (option) =>
        option.value === value
    ) ??
    DERIVATION_TYPE_OPTIONS[0];


  return (
    <div className="model-derived-type-picker">

      <button
        type="button"
        className={
          `model-derived-type-trigger ${
            open
              ? "open"
              : ""
          }`
        }
        onClick={() =>
          setOpen(
            (previous) =>
              !previous
          )
        }
      >
        <span>
          {selected.label}
        </span>

        <span aria-hidden="true">
          ▾
        </span>
      </button>


      {open && (
        <div className="model-derived-type-menu">

          {DERIVATION_TYPE_OPTIONS.map(
            (option) => {
              const help =
                DERIVATION_HELP[
                  option.value
                ];

              return (
                <button
                  key={option.value}
                  type="button"
                  className={
                    option.value === value
                      ? "selected"
                      : ""
                  }
                  onClick={() => {
                    onChange(
                      option.value
                    );

                    setOpen(false);
                  }}
                >
                  <span className="model-derived-type-label">
                    {option.label}
                  </span>

                  {help && (
                    <span
                      className="model-derived-type-hover-help"
                      role="tooltip"
                    >
                      <strong>
                        {help.title}
                      </strong>

                      <span>
                        {help.description}
                      </span>

                      <small>
                        Example: {
                          help.example
                        }
                      </small>
                    </span>
                  )}
                </button>
              );
            }
          )}

        </div>
      )}

    </div>
  );
}


type SourceColumnPickerProps = {
  value: string;

  placeholder: string;

  options: string[];

  onChange: (
    value: string
  ) => void;
};


function SourceColumnPicker({
  value,
  placeholder,
  options,
  onChange,
}: SourceColumnPickerProps) {

  const [
    open,
    setOpen,
  ] = useState(false);

  const [
    search,
    setSearch,
  ] = useState("");


  const filteredOptions =
    options.filter(
      (option) =>
        option
          .toLowerCase()
          .includes(
            search
              .trim()
              .toLowerCase()
          )
    );


  return (
    <div className="model-source-picker">

      <button
        type="button"
        className={
          `model-source-picker-trigger ${
            open
              ? "open"
              : ""
          }`
        }
        onClick={() =>
          setOpen(
            (previous) =>
              !previous
          )
        }
      >
        <span>
          {value || placeholder}
        </span>

        <span aria-hidden="true">
          ▾
        </span>
      </button>


      {open && (
        <div className="model-source-picker-panel">

          <input
            type="search"
            value={search}
            autoFocus
            placeholder="Search columns..."
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
          />


          <div className="model-source-picker-options">

            {filteredOptions.map(
              (option) => (
                <button
                  key={option}
                  type="button"
                  className={
                    option === value
                      ? "selected"
                      : ""
                  }
                  onClick={() => {
                    onChange(
                      option
                    );

                    setOpen(false);
                    setSearch("");
                  }}
                >
                  {option}
                </button>
              )
            )}


            {filteredOptions.length === 0 && (
              <span className="model-source-picker-empty">
                No columns found.
              </span>
            )}

          </div>

        </div>
      )}

    </div>
  );
}


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

  mode:
    | "source"
    | "derived";

  derivation:
    DataModelDerivation | null;
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

  sourceColumns?: string[];

  timeCandidates?: string[];
};


function DataModelTableEditor({
  studio,
  editingTableName = null,
  onCancel,
  onSave,
  saving,
  sourceColumns = [],
  timeCandidates = [],
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

            mode:
              column.derivation
                ? "derived"
                : "source",

            derivation:
              column.derivation ?? null,
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

            mode:
              "source",

            derivation:
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

          mode:
            "source",

          derivation:
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


  function updateColumnMode(
    id: string,
    mode: "source" | "derived",
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id
              ? {
                  ...column,
                  mode,
                  name: "",
                  sourceColumn: null,
                  derivation:
                    mode === "derived"
                      ? {
                          type: "date_part",
                          operation: "",
                          source_columns: [],
                          parameters: {},
                        }
                      : null,
                }
              : column
        )
    );
  }


  function updateColumnSource(
    id: string,
    sourceColumn: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id
              ? {
                  ...column,
                  name:
                    column.mode === "source"
                      ? sourceColumn
                      : column.name,
                  sourceColumn,
                  derivation:
                    column.mode === "derived" &&
                    column.derivation
                      ? {
                          ...column.derivation,
                          source_columns:
                            sourceColumn
                              ? [sourceColumn]
                              : [],
                        }
                      : null,
                }
              : column
        )
    );
  }


  function updateDerivedType(
    id: string,
    type: DerivationType,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id
              ? {
                  ...column,
                  sourceColumn: null,
                  derivation:
                    type === "multi_column"
                      ? {
                          type,
                          operation: "concatenate",
                          source_columns: ["", ""],
                          parameters: {
                            separator: " | ",
                          },
                        }
                      : type === "mapping"
                        ? {
                            type,
                            operation: "map_values",
                            source_columns: [],
                            parameters: {},
                            mapping_rules: [
                              {
                                source_value: "",
                                display_value: "",
                              },
                            ],
                          }
                        : type === "bucketing"
                          ? {
                              type,
                              operation: "bucket_ranges",
                              source_columns: [],
                              parameters: {},
                              bucket_rules: [
                                {
                                  min_value: "",
                                  max_value: "",
                                  label: "",
                                },
                              ],
                            }
                          : {
                              type,
                              operation: "",
                              source_columns: [],
                              parameters: {},
                            },
                }
              : column
        )
    );
  }


  function updateMultiColumnSource(
    id: string,
    sourceIndex: number,
    sourceColumn: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) => {
            if (
              column.id !== id ||
              (
                column.derivation?.type !==
                  "multi_column" &&
                column.derivation?.type !==
                  "numeric"
              )
            ) {
              return column;
            }

            const nextSources = [
              ...column.derivation
                .source_columns,
            ];

            while (
              nextSources.length < 2
            ) {
              nextSources.push("");
            }

            nextSources[sourceIndex] =
              sourceColumn;

            return {
              ...column,
              sourceColumn: null,
              derivation: {
                ...column.derivation,
                source_columns:
                  nextSources,
              },
            };
          }
        )
    );
  }


  function updateDerivedParameter(
    id: string,
    parameter: string,
    value: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id &&
            column.derivation
              ? {
                  ...column,
                  derivation: {
                    ...column.derivation,
                    parameters: {
                      ...column.derivation
                        .parameters,
                      [parameter]: value,
                    },
                  },
                }
              : column
        )
    );
  }


  function updateMappingRule(
    id: string,
    ruleIndex: number,
    field:
      | "source_value"
      | "display_value",
    value: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) => {
            if (
              column.id !== id ||
              column.derivation?.type !==
                "mapping"
            ) {
              return column;
            }

            const rules = [
              ...(column.derivation
                .mapping_rules ?? []),
            ];

            while (
              rules.length <= ruleIndex
            ) {
              rules.push({
                source_value: "",
                display_value: "",
              });
            }

            rules[ruleIndex] = {
              ...rules[ruleIndex],
              [field]: value,
            };

            return {
              ...column,
              derivation: {
                ...column.derivation,
                mapping_rules: rules,
              },
            };
          }
        )
    );
  }


  function addMappingRule(
    id: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id &&
            column.derivation?.type ===
              "mapping"
              ? {
                  ...column,
                  derivation: {
                    ...column.derivation,
                    mapping_rules: [
                      ...(column.derivation
                        .mapping_rules ?? []),
                      {
                        source_value: "",
                        display_value: "",
                      },
                    ],
                  },
                }
              : column
        )
    );
  }


  function removeMappingRule(
    id: string,
    ruleIndex: number,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) => {
            if (
              column.id !== id ||
              column.derivation?.type !==
                "mapping"
            ) {
              return column;
            }

            const rules =
              (
                column.derivation
                  .mapping_rules ?? []
              ).filter(
                (_rule, index) =>
                  index !== ruleIndex
              );

            return {
              ...column,
              derivation: {
                ...column.derivation,
                mapping_rules:
                  rules.length > 0
                    ? rules
                    : [
                        {
                          source_value: "",
                          display_value: "",
                        },
                      ],
              },
            };
          }
        )
    );
  }


  function updateBucketRule(
    id: string,
    ruleIndex: number,
    field:
      | "min_value"
      | "max_value"
      | "label",
    value: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) => {
            if (
              column.id !== id ||
              column.derivation?.type !==
                "bucketing"
            ) {
              return column;
            }

            const rules = [
              ...(column.derivation
                .bucket_rules ?? []),
            ];

            while (
              rules.length <= ruleIndex
            ) {
              rules.push({
                min_value: "",
                max_value: "",
                label: "",
              });
            }

            rules[ruleIndex] = {
              ...rules[ruleIndex],
              [field]: value,
            };

            return {
              ...column,
              derivation: {
                ...column.derivation,
                bucket_rules: rules,
              },
            };
          }
        )
    );
  }


  function addBucketRule(
    id: string,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) =>
            column.id === id &&
            column.derivation?.type ===
              "bucketing"
              ? {
                  ...column,
                  derivation: {
                    ...column.derivation,
                    bucket_rules: [
                      ...(column.derivation
                        .bucket_rules ?? []),
                      {
                        min_value: "",
                        max_value: "",
                        label: "",
                      },
                    ],
                  },
                }
              : column
        )
    );
  }


  function removeBucketRule(
    id: string,
    ruleIndex: number,
  ) {
    setColumns(
      (previous) =>
        previous.map(
          (column) => {
            if (
              column.id !== id ||
              column.derivation?.type !==
                "bucketing"
            ) {
              return column;
            }

            const rules =
              (
                column.derivation
                  .bucket_rules ?? []
              ).filter(
                (_rule, index) =>
                  index !== ruleIndex
              );

            return {
              ...column,
              derivation: {
                ...column.derivation,
                bucket_rules:
                  rules.length > 0
                    ? rules
                    : [
                        {
                          min_value: "",
                          max_value: "",
                          label: "",
                        },
                      ],
              },
            };
          }
        )
    );
  }


  function updateDerivedOperation(
    id: string,
    operation: string,
  ) {
    const defaultNames:
      Record<string, string> = {
        year: "Year",
        quarter: "Quarter",
        month: "Month",
        month_name: "MonthName",
        day_of_week: "DayOfWeek",
      };

    setColumns(
      (previous) =>
        previous.map(
          (column) => {
            if (
              column.id !== id ||
              !column.derivation
            ) {
              return column;
            }

            const type =
              column.derivation.type;

            let sourceColumns = [
              ...column.derivation
                .source_columns,
            ];

            let parameters = {
              ...column.derivation
                .parameters,
            };

            if (
              type === "numeric" &&
              operation === "round"
            ) {
              sourceColumns =
                sourceColumns.slice(0, 1);

              parameters = {
                decimals:
                  parameters.decimals ??
                  "0",
              };
            }

            if (
              type === "numeric" &&
              [
                "add",
                "subtract",
                "multiply",
                "divide",
              ].includes(operation)
            ) {
              sourceColumns = [
                sourceColumns[0] ?? "",
                sourceColumns[1] ?? "",
              ];

              parameters = {};
            }

            if (type === "text") {
              parameters =
                operation === "replace"
                  ? {
                      find:
                        parameters.find ??
                        "",
                      replacement:
                        parameters.replacement ??
                        "",
                    }
                  : operation === "substring"
                    ? {
                        start:
                          parameters.start ??
                          "0",
                        length:
                          parameters.length ??
                          "",
                      }
                    : {};
            }

            return {
              ...column,
              name:
                defaultNames[operation] ??
                column.name,
              derivation: {
                ...column.derivation,
                operation,
                source_columns:
                  sourceColumns,
                parameters,
              },
            };
          }
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


    const invalidDerivedColumn =
      cleanColumns.find(
        (column) => {
          if (
            column.mode !== "derived"
          ) {
            return false;
          }

          const derivation =
            column.derivation;

          if (!derivation) {
            return true;
          }

          const sources =
            derivation.source_columns
              .map(
                (source) =>
                  source.trim()
              )
              .filter(Boolean);

          if (
            derivation.type ===
              "date_part"
          ) {
            return (
              sources.length !== 1 ||
              !derivation.operation
            );
          }

          if (
            derivation.type ===
              "multi_column"
          ) {
            return (
              derivation.operation !==
                "concatenate" ||
              sources.length < 2
            );
          }

          if (
            derivation.type === "text"
          ) {
            return (
              sources.length !== 1 ||
              ![
                "trim",
                "uppercase",
                "lowercase",
                "replace",
                "substring",
              ].includes(
                derivation.operation
              )
            );
          }

          if (
            derivation.type ===
              "numeric"
          ) {
            const arithmetic =
              [
                "add",
                "subtract",
                "multiply",
                "divide",
              ].includes(
                derivation.operation
              );

            return (
              ![
                "round",
                "add",
                "subtract",
                "multiply",
                "divide",
              ].includes(
                derivation.operation
              ) ||
              (
                derivation.operation ===
                  "round" &&
                sources.length !== 1
              ) ||
              (
                arithmetic &&
                sources.length < 2
              )
            );
          }

          if (
            derivation.type ===
              "mapping"
          ) {
            const rules =
              derivation.mapping_rules ??
              [];

            return (
              derivation.operation !==
                "map_values" ||
              sources.length !== 1 ||
              rules.length === 0 ||
              rules.some(
                (rule) =>
                  !rule.source_value.trim() ||
                  !rule.display_value.trim()
              )
            );
          }

          if (
            derivation.type ===
              "bucketing"
          ) {
            const rules =
              derivation.bucket_rules ??
              [];

            return (
              derivation.operation !==
                "bucket_ranges" ||
              sources.length !== 1 ||
              rules.length === 0 ||
              rules.some(
                (rule) =>
                  !rule.min_value.trim() ||
                  !rule.max_value.trim() ||
                  !rule.label.trim()
              )
            );
          }

          return true;
        }
      );


    if (invalidDerivedColumn) {
      setError(
        (
          `Complete the derived column "${invalidDerivedColumn.name}". ` +
          "Choose the required source columns and derivation."
        )
      );

      return;
    }


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

            derivation:
              column.derivation,
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


    const nextNodePositions = {
      ...(studio.node_positions ?? {}),
    };

    if (
      editingTable.name !==
      cleanTableName
    ) {
      const previousPosition =
        nextNodePositions[
          editingTable.name
        ];

      delete nextNodePositions[
        editingTable.name
      ];

      if (previousPosition) {
        nextNodePositions[
          cleanTableName
        ] = previousPosition;
      }
    }

    const updatedStudio:
      DataModelStudioData = {

      ...studio,

      source:
        "user",

      node_positions:
        nextNodePositions,

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


    const nextNodePositions = {
      ...(studio.node_positions ?? {}),
    };

    delete nextNodePositions[
      editingTable.name
    ];

    const updatedStudio:
      DataModelStudioData = {

      ...studio,

      source:
        "user",

      node_positions:
        nextNodePositions,

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

                  <div className="model-editor-column-main">
                    {column.originalName === null && (
                      <select
                        className="model-editor-column-mode"
                        value={column.mode}
                        onChange={(event) =>
                          updateColumnMode(
                            column.id,
                            event.target.value as
                              | "source"
                              | "derived"
                          )
                        }
                      >
                        <option value="source">
                          Source column
                        </option>
                        <option value="derived">
                          Derived column
                        </option>
                      </select>
                    )}

                    {column.mode === "source" ? (
                      column.originalName === null &&
                      sourceColumns.length > 0 ? (
                        <select
                          value={column.sourceColumn ?? ""}
                          onChange={(event) =>
                            updateColumnSource(
                              column.id,
                              event.target.value
                            )
                          }
                        >
                          <option value="">
                            Select source column...
                          </option>

                          {sourceColumns
                            .filter(
                              (sourceColumn) =>
                                !columns.some(
                                  (candidate) =>
                                    candidate.id !== column.id &&
                                    candidate.mode === "source" &&
                                    candidate.sourceColumn === sourceColumn
                                )
                            )
                            .map(
                              (sourceColumn) => (
                                <option
                                  key={sourceColumn}
                                  value={sourceColumn}
                                >
                                  {sourceColumn}
                                </option>
                              )
                            )}
                        </select>
                      ) : (
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
                      )
                    ) : (
                      <div className="model-editor-derived-fields">
                        <div className="model-editor-derived-selector-row">
                          <DerivationTypePicker
                            value={
                              column.derivation?.type ??
                              "date_part"
                            }
                            onChange={(
                              derivationType,
                            ) =>
                              updateDerivedType(
                                column.id,
                                derivationType
                              )
                            }
                          />

                          <DerivationHelp
                            helpKey={
                              column.derivation
                                ?.type ??
                              "date_part"
                            }
                          />
                        </div>

                        {column.derivation?.type ===
                        "multi_column" ? (
                          <>
                            {[0, 1].map(
                              (sourceIndex) => {
                                const selectedValue =
                                  column.derivation
                                    ?.source_columns[
                                      sourceIndex
                                    ] ?? "";

                                const availableOptions =
                                  sourceColumns.filter(
                                    (sourceColumn) =>
                                      !column.derivation
                                        ?.source_columns
                                        .some(
                                          (
                                            selected,
                                            selectedIndex,
                                          ) =>
                                            selectedIndex !==
                                              sourceIndex &&
                                            selected ===
                                              sourceColumn
                                        )
                                  );

                                return (
                                  <SourceColumnPicker
                                    key={sourceIndex}
                                    value={selectedValue}
                                    placeholder={
                                      sourceIndex === 0
                                        ? "First source column..."
                                        : "Second source column..."
                                    }
                                    options={availableOptions}
                                    onChange={(sourceColumn) =>
                                      updateMultiColumnSource(
                                        column.id,
                                        sourceIndex,
                                        sourceColumn
                                      )
                                    }
                                  />
                                );
                              }
                            )}

                            <div className="model-editor-operation-row">
                              <select
                                value="concatenate"
                                disabled
                              >
                                <option value="concatenate">
                                  Concatenate
                                </option>
                              </select>

                              <DerivationHelp
                                helpKey="concatenate"
                              />
                            </div>

                            <input
                              type="text"
                              value={
                                String(
                                  column.derivation
                                    ?.parameters
                                    .separator ??
                                  " | "
                                )
                              }
                              placeholder="Separator"
                              onChange={(event) =>
                                updateDerivedParameter(
                                  column.id,
                                  "separator",
                                  event.target.value
                                )
                              }
                            />
                          </>
                        ) : column.derivation?.type ===
                          "text" ? (
                          <>
                            <SourceColumnPicker
                              value={
                                column.derivation
                                  .source_columns[0] ??
                                ""
                              }
                              placeholder="Source column..."
                              options={sourceColumns}
                              onChange={(sourceColumn) =>
                                updateColumnSource(
                                  column.id,
                                  sourceColumn
                                )
                              }
                            />

                            <div className="model-editor-operation-row">
                              <select
                                value={
                                  column.derivation
                                    .operation
                                }
                                onChange={(event) =>
                                  updateDerivedOperation(
                                    column.id,
                                    event.target.value
                                  )
                                }
                              >
                                <option value="">
                                  Select text operation...
                                </option>
                                <option value="trim">Trim</option>
                                <option value="uppercase">Uppercase</option>
                                <option value="lowercase">Lowercase</option>
                                <option value="replace">Replace</option>
                                <option value="substring">Substring</option>
                              </select>

                              {column.derivation
                                .operation && (
                                <DerivationHelp
                                  helpKey={
                                    column.derivation
                                      .operation
                                  }
                                />
                              )}
                            </div>

                            {column.derivation
                              .operation ===
                              "replace" && (
                              <>
                                <input
                                  type="text"
                                  value={
                                    String(
                                      column.derivation
                                        .parameters
                                        .find ?? ""
                                    )
                                  }
                                  placeholder="Find text..."
                                  onChange={(event) =>
                                    updateDerivedParameter(
                                      column.id,
                                      "find",
                                      event.target.value
                                    )
                                  }
                                />

                                <input
                                  type="text"
                                  value={
                                    String(
                                      column.derivation
                                        .parameters
                                        .replacement ??
                                      ""
                                    )
                                  }
                                  placeholder="Replace with..."
                                  onChange={(event) =>
                                    updateDerivedParameter(
                                      column.id,
                                      "replacement",
                                      event.target.value
                                    )
                                  }
                                />
                              </>
                            )}

                            {column.derivation
                              .operation ===
                              "substring" && (
                              <>
                                <input
                                  type="number"
                                  value={
                                    String(
                                      column.derivation
                                        .parameters
                                        .start ?? "0"
                                    )
                                  }
                                  placeholder="Start position"
                                  onChange={(event) =>
                                    updateDerivedParameter(
                                      column.id,
                                      "start",
                                      event.target.value
                                    )
                                  }
                                />

                                <input
                                  type="number"
                                  value={
                                    String(
                                      column.derivation
                                        .parameters
                                        .length ?? ""
                                    )
                                  }
                                  placeholder="Length"
                                  onChange={(event) =>
                                    updateDerivedParameter(
                                      column.id,
                                      "length",
                                      event.target.value
                                    )
                                  }
                                />
                              </>
                            )}
                          </>
                        ) : column.derivation?.type ===
                          "numeric" ? (
                          <>
                            <div className="model-editor-operation-row">
                              <select
                                value={
                                  column.derivation
                                    .operation
                                }
                                onChange={(event) =>
                                  updateDerivedOperation(
                                    column.id,
                                    event.target.value
                                  )
                                }
                              >
                                <option value="">
                                  Select numeric operation...
                                </option>
                                <option value="round">Round</option>
                                <option value="add">Add</option>
                                <option value="subtract">Subtract</option>
                                <option value="multiply">Multiply</option>
                                <option value="divide">Divide</option>
                              </select>

                              {column.derivation
                                .operation && (
                                <DerivationHelp
                                  helpKey={
                                    column.derivation
                                      .operation
                                  }
                                />
                              )}
                            </div>

                            {column.derivation
                              .operation ===
                              "round" ? (
                              <>
                                <SourceColumnPicker
                                  value={
                                    column.derivation
                                      .source_columns[0] ??
                                    ""
                                  }
                                  placeholder="Numeric source column..."
                                  options={sourceColumns}
                                  onChange={(sourceColumn) =>
                                    updateColumnSource(
                                      column.id,
                                      sourceColumn
                                    )
                                  }
                                />

                                <input
                                  type="number"
                                  min="0"
                                  value={
                                    String(
                                      column.derivation
                                        .parameters
                                        .decimals ?? "0"
                                    )
                                  }
                                  placeholder="Decimal places"
                                  onChange={(event) =>
                                    updateDerivedParameter(
                                      column.id,
                                      "decimals",
                                      event.target.value
                                    )
                                  }
                                />
                              </>
                            ) : (
                              [
                                "add",
                                "subtract",
                                "multiply",
                                "divide",
                              ].includes(
                                column.derivation
                                  .operation
                              ) && (
                                <>
                                  {[0, 1].map(
                                    (sourceIndex) => (
                                      <SourceColumnPicker
                                        key={sourceIndex}
                                        value={
                                          column.derivation
                                            ?.source_columns[
                                              sourceIndex
                                            ] ?? ""
                                        }
                                        placeholder={
                                          sourceIndex === 0
                                            ? "First numeric column..."
                                            : "Second numeric column..."
                                        }
                                        options={sourceColumns}
                                        onChange={(sourceColumn) =>
                                          updateMultiColumnSource(
                                            column.id,
                                            sourceIndex,
                                            sourceColumn
                                          )
                                        }
                                      />
                                    )
                                  )}
                                </>
                              )
                            )}
                          </>
                        ) : column.derivation?.type ===
                          "mapping" ? (
                          <>
                            <SourceColumnPicker
                              value={
                                column.derivation
                                  .source_columns[0] ??
                                ""
                              }
                              placeholder="Source column..."
                              options={sourceColumns}
                              onChange={(sourceColumn) =>
                                updateColumnSource(
                                  column.id,
                                  sourceColumn
                                )
                              }
                            />

                            <div className="model-editor-operation-row">
                              <select
                                value="map_values"
                                disabled
                              >
                                <option value="map_values">
                                  Map values
                                </option>
                              </select>

                              <DerivationHelp
                                helpKey="map_values"
                              />
                            </div>

                            <div className="model-rule-builder">

                              <div className="model-rule-header mapping">
                                <span>Value in data</span>
                                <span>Display as</span>
                                <span />
                              </div>

                              {(
                                column.derivation
                                  .mapping_rules ?? []
                              ).map(
                                (
                                  rule,
                                  ruleIndex,
                                ) => (
                                  <div
                                    key={ruleIndex}
                                    className="model-rule-row mapping"
                                  >
                                    <input
                                      type="text"
                                      value={
                                        rule.source_value
                                      }
                                      placeholder="e.g. h"
                                      onChange={(event) =>
                                        updateMappingRule(
                                          column.id,
                                          ruleIndex,
                                          "source_value",
                                          event.target.value
                                        )
                                      }
                                    />

                                    <input
                                      type="text"
                                      value={
                                        rule.display_value
                                      }
                                      placeholder="e.g. House"
                                      onChange={(event) =>
                                        updateMappingRule(
                                          column.id,
                                          ruleIndex,
                                          "display_value",
                                          event.target.value
                                        )
                                      }
                                    />

                                    <button
                                      type="button"
                                      className="model-rule-remove"
                                      onClick={() =>
                                        removeMappingRule(
                                          column.id,
                                          ruleIndex
                                        )
                                      }
                                    >
                                      ×
                                    </button>
                                  </div>
                                )
                              )}

                              <button
                                type="button"
                                className="model-rule-add"
                                onClick={() =>
                                  addMappingRule(
                                    column.id
                                  )
                                }
                              >
                                + Add mapping
                              </button>

                            </div>
                          </>
                        ) : column.derivation?.type ===
                          "bucketing" ? (
                          <>
                            <SourceColumnPicker
                              value={
                                column.derivation
                                  .source_columns[0] ??
                                ""
                              }
                              placeholder="Numeric source column..."
                              options={sourceColumns}
                              onChange={(sourceColumn) =>
                                updateColumnSource(
                                  column.id,
                                  sourceColumn
                                )
                              }
                            />

                            <div className="model-rule-builder">
                              <div className="model-rule-header bucket">
                                <span>From</span>
                                <span>To</span>
                                <span>Label</span>
                                <span />
                              </div>

                              {(
                                column.derivation
                                  .bucket_rules ?? []
                              ).map(
                                (
                                  rule,
                                  ruleIndex,
                                ) => (
                                  <div
                                    key={ruleIndex}
                                    className="model-rule-row bucket"
                                  >
                                    <input
                                      type="number"
                                      value={rule.min_value}
                                      placeholder="0"
                                      onChange={(event) =>
                                        updateBucketRule(
                                          column.id,
                                          ruleIndex,
                                          "min_value",
                                          event.target.value
                                        )
                                      }
                                    />

                                    <input
                                      type="number"
                                      value={rule.max_value}
                                      placeholder="18"
                                      onChange={(event) =>
                                        updateBucketRule(
                                          column.id,
                                          ruleIndex,
                                          "max_value",
                                          event.target.value
                                        )
                                      }
                                    />

                                    <input
                                      type="text"
                                      value={rule.label}
                                      placeholder="Young"
                                      onChange={(event) =>
                                        updateBucketRule(
                                          column.id,
                                          ruleIndex,
                                          "label",
                                          event.target.value
                                        )
                                      }
                                    />

                                    <button
                                      type="button"
                                      className="model-rule-remove"
                                      onClick={() =>
                                        removeBucketRule(
                                          column.id,
                                          ruleIndex
                                        )
                                      }
                                    >
                                      ×
                                    </button>
                                  </div>
                                )
                              )}

                              <button
                                type="button"
                                className="model-rule-add"
                                onClick={() =>
                                  addBucketRule(
                                    column.id
                                  )
                                }
                              >
                                + Add range
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <SourceColumnPicker
                              value={
                                column.sourceColumn ?? ""
                              }
                              placeholder="Date source column..."
                              options={sourceColumns}
                              onChange={(sourceColumn) =>
                                updateColumnSource(
                                  column.id,
                                  sourceColumn
                                )
                              }
                            />

                            <div className="model-editor-operation-row">
                              <select
                                value={
                                  column.derivation
                                    ?.operation ?? ""
                                }
                                disabled={
                                  !column.sourceColumn ||
                                  !timeCandidates.includes(
                                    column.sourceColumn
                                  )
                                }
                                onChange={(event) =>
                                  updateDerivedOperation(
                                    column.id,
                                    event.target.value
                                  )
                                }
                              >
                                <option value="">
                                  {
                                    column.sourceColumn &&
                                    !timeCandidates.includes(
                                      column.sourceColumn
                                    )
                                      ? "No supported date derivation"
                                      : "Select date operation..."
                                  }
                                </option>

                                {column.sourceColumn &&
                                timeCandidates.includes(
                                  column.sourceColumn
                                ) && (
                                  <>
                                    <option value="year">Year</option>
                                    <option value="quarter">Quarter</option>
                                    <option value="month">Month</option>
                                    <option value="month_name">Month name</option>
                                    <option value="day_of_week">Day of week</option>
                                  </>
                                )}
                              </select>

                              {column.derivation
                                ?.operation && (
                                <DerivationHelp
                                  helpKey={
                                    column.derivation
                                      .operation
                                  }
                                />
                              )}
                            </div>
                          </>
                        )}

                        <input
                          type="text"
                          value={column.name}
                          placeholder="Derived column name..."
                          onChange={(event) =>
                            updateColumnName(
                              column.id,
                              event.target.value
                            )
                          }
                        />
                      </div>
                    )}
                  </div>


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