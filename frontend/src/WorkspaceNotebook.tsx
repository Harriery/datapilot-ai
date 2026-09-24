import {
  Play,
  Plus,
  RotateCcw,
  Save,
  Send,
  Trash2,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";

import {
  runNotebookCells,
} from "./pythonRunner";

export type WorkspaceNotebookCellData = {
  cell_id: string;
  code: string;
  cell_type: "python";
};

export type WorkspaceNotebookData = {
  notebook_id: string;
  name: string;

  dataset_kind:
    | "working"
    | "raw"
    | "processed";

  processed_dataset_id:
    | string
    | null;

  cells:
    WorkspaceNotebookCellData[];

  created_at: string;
  updated_at: string;
};

type ProcessedDataset = {
  dataset_id: string;
  name: string;
};

type NotebookRunResult = {
  rows:
    Record<string, unknown>[];

  output: string;
};

type Props = {
  workspaceId: string;

  notebook:
    WorkspaceNotebookData;

  processedDatasets:
    ProcessedDataset[];

  onSave: (
    notebook:
      WorkspaceNotebookData
  ) => Promise<
    WorkspaceNotebookData
  >;

  onDelete: (
    notebookId: string
  ) => Promise<void>;

  onPromoteCode: (
    code: string
  ) => Promise<boolean>;
};

function createCell():
  WorkspaceNotebookCellData {
  return {
    cell_id:
      crypto.randomUUID(),
    code:
      "# Work with df\n",
    cell_type:
      "python",
  };
}

function WorkspaceNotebook({
  workspaceId,
  notebook,
  processedDatasets,
  onSave,
  onDelete,
  onPromoteCode,
}: Props) {
  const [
    draft,
    setDraft,
  ] = useState<
    WorkspaceNotebookData
  >(notebook);

  const [
    inputRows,
    setInputRows,
  ] = useState<
    Record<string, unknown>[]
  >([]);

  const [
    inputColumns,
    setInputColumns,
  ] = useState<string[]>([]);

  const [
    loadingData,
    setLoadingData,
  ] = useState(false);

  const [
    dataError,
    setDataError,
  ] = useState<string | null>(
    null
  );

  const [
    runningCellId,
    setRunningCellId,
  ] = useState<string | null>(
    null
  );

  const [
    saving,
    setSaving,
  ] = useState(false);

  const [
    message,
    setMessage,
  ] = useState<string | null>(
    null
  );

  const [
    results,
    setResults,
  ] = useState<
    Record<
      string,
      NotebookRunResult
    >
  >({});

  useEffect(() => {
    setDraft(notebook);
    setResults({});
    setMessage(null);
  }, [notebook]);

  useEffect(() => {
    async function loadData() {
      setLoadingData(true);
      setDataError(null);

      try {
        const response =
          await fetch(
            `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/notebooks/${notebook.notebook_id}/data`
          );

        if (!response.ok) {
          const errorData =
            await response.json();

          throw new Error(
            errorData.detail ||
              "Notebook dataset yüklenemedi."
          );
        }

        const data:
          {
            columns: string[];
            row_count: number;
            rows:
              Record<
                string,
                unknown
              >[];
          } =
            await response.json();

        setInputColumns(
          data.columns
        );

        setInputRows(
          data.rows
        );
      } catch (error) {
        setDataError(
          error instanceof Error
            ? error.message
            : "Notebook dataset yüklenemedi."
        );
      } finally {
        setLoadingData(false);
      }
    }

    void loadData();
  }, [
    workspaceId,
    notebook.notebook_id,
    notebook.dataset_kind,
    notebook.processed_dataset_id,
  ]);

  async function saveDraft(
    nextDraft = draft
  ) {
    setSaving(true);
    setMessage(null);

    try {
      const saved =
        await onSave(
          nextDraft
        );

      setDraft(saved);

      setMessage(
        "Notebook saved."
      );

      return saved;
    } finally {
      setSaving(false);
    }
  }

  async function changeDataset(
    datasetKind:
      WorkspaceNotebookData[
        "dataset_kind"
      ],
    processedDatasetId:
      string | null = null,
  ) {
    const next = {
      ...draft,
      dataset_kind:
        datasetKind,
      processed_dataset_id:
        processedDatasetId,
    };

    setDraft(next);
    setResults({});

    await saveDraft(next);
  }

  async function runCell(
    index: number
  ) {
    const cell =
      draft.cells[index];

    if (!cell) {
      return;
    }

    setRunningCellId(
      cell.cell_id
    );

    setMessage(null);

    try {
      const result =
        await runNotebookCells(
          draft.cells.map(
            (item) =>
              item.code
          ),
          inputRows,
          index,
        );

      setResults(
        (previous) => ({
          ...previous,
          [cell.cell_id]:
            result,
        })
      );
    } catch (error) {
      setResults(
        (previous) => ({
          ...previous,
          [cell.cell_id]: {
            rows: [],
            output:
              error instanceof Error
                ? error.message
                : "Notebook cell failed.",
          },
        })
      );
    } finally {
      setRunningCellId(
        null
      );
    }
  }

  return (
    <div className="notebook-workspace">
      <div className="notebook-toolbar">
        <div className="notebook-name-group">
          <span>
            NOTEBOOK
          </span>

          <input
            value={draft.name}
            onChange={(event) => {
              setDraft(
                (previous) => ({
                  ...previous,
                  name:
                    event.target.value,
                })
              );
            }}
          />
        </div>

        <div className="notebook-toolbar-actions">
          <label>
            <span>
              Dataset
            </span>

            <select
              value={
                draft.dataset_kind ===
                  "processed"
                  ? `processed:${draft.processed_dataset_id ?? ""}`
                  : draft.dataset_kind
              }
              onChange={(event) => {
                const value =
                  event.target.value;

                if (
                  value.startsWith(
                    "processed:"
                  )
                ) {
                  void changeDataset(
                    "processed",
                    value.replace(
                      "processed:",
                      ""
                    ),
                  );
                } else {
                  void changeDataset(
                    value as
                      | "working"
                      | "raw",
                    null,
                  );
                }
              }}
            >
              <option value="working">
                Development / working
              </option>

              <option value="raw">
                Raw source sample
              </option>

              {processedDatasets.map(
                (dataset) => (
                  <option
                    key={
                      dataset.dataset_id
                    }
                    value={
                      `processed:${dataset.dataset_id}`
                    }
                  >
                    {dataset.name}
                  </option>
                )
              )}
            </select>
          </label>

          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setResults({});
              setMessage(
                "Session reset. The next run starts again from the selected dataset."
              );
            }}
          >
            <RotateCcw size={14} />
            Reset
          </button>

          <button
            type="button"
            className="new-workspace-button"
            disabled={saving}
            onClick={() => {
              void saveDraft();
            }}
          >
            <Save size={14} />
            {saving
              ? "Saving..."
              : "Save"}
          </button>

          <button
            type="button"
            className="notebook-delete-button"
            onClick={() => {
              if (
                window.confirm(
                  `Delete notebook "${draft.name}"?`
                )
              ) {
                void onDelete(
                  draft.notebook_id
                );
              }
            }}
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="notebook-dataset-context">
        {loadingData
          ? "Loading dataset..."
          : dataError
            ? dataError
            : (
                `${inputRows.length} rows loaded · ${inputColumns.length} columns · browser sandbox`
              )}
      </div>

      <div className="notebook-cells">
        {draft.cells.map(
          (cell, index) => {
            const result =
              results[
                cell.cell_id
              ];

            return (
              <article
                className="notebook-cell"
                key={
                  cell.cell_id
                }
              >
                <div className="notebook-cell-gutter">
                  <span>
                    [{index + 1}]
                  </span>

                  <button
                    type="button"
                    title="Run cell"
                    disabled={
                      runningCellId !==
                        null ||
                      loadingData
                    }
                    onClick={() => {
                      void runCell(
                        index
                      );
                    }}
                  >
                    <Play
                      size={14}
                      fill="currentColor"
                    />
                  </button>
                </div>

                <div className="notebook-cell-body">
                  <textarea
                    value={cell.code}
                    spellCheck={false}
                    onChange={(event) => {
                      const code =
                        event.target.value;

                      setDraft(
                        (previous) => ({
                          ...previous,
                          cells:
                            previous.cells.map(
                              (item) =>
                                item.cell_id ===
                                cell.cell_id
                                  ? {
                                      ...item,
                                      code,
                                    }
                                  : item
                            ),
                        })
                      );

                      setResults(
                        (previous) => {
                          const next = {
                            ...previous,
                          };

                          delete next[
                            cell.cell_id
                          ];

                          return next;
                        }
                      );
                    }}
                  />

                  <div className="notebook-cell-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        void onPromoteCode(
                          cell.code
                        ).then(
                          (success) => {
                            setMessage(
                              success
                                ? "Cell sent to the Workbench pipeline as a custom step. Convert it to a structured action before full-dataset replay."
                                : "Cell could not be sent to the pipeline."
                            );
                          }
                        );
                      }}
                    >
                      <Send size={13} />
                      Send to pipeline
                    </button>

                    <button
                      type="button"
                      className="notebook-cell-delete"
                      onClick={() => {
                        setDraft(
                          (previous) => ({
                            ...previous,
                            cells:
                              previous.cells.filter(
                                (item) =>
                                  item.cell_id !==
                                  cell.cell_id
                              ),
                          })
                        );
                      }}
                    >
                      Delete cell
                    </button>
                  </div>

                  {result && (
                    <div className="notebook-output">
                      <div className="notebook-output-header">
                        <span>
                          OUTPUT
                        </span>

                        <strong>
                          {result.rows.length}
                          {" "}rows
                        </strong>
                      </div>

                      {result.output && (
                        <pre>
                          {result.output}
                        </pre>
                      )}

                      {result.rows.length > 0 && (
                        <div className="notebook-preview-table-wrap">
                          <table>
                            <thead>
                              <tr>
                                {Object.keys(
                                  result.rows[0]
                                )
                                  .slice(
                                    0,
                                    10
                                  )
                                  .map(
                                    (column) => (
                                      <th
                                        key={
                                          column
                                        }
                                      >
                                        {column}
                                      </th>
                                    )
                                  )}
                              </tr>
                            </thead>

                            <tbody>
                              {result.rows
                                .slice(
                                  0,
                                  8
                                )
                                .map(
                                  (
                                    row,
                                    rowIndex
                                  ) => (
                                    <tr
                                      key={
                                        rowIndex
                                      }
                                    >
                                      {Object.keys(
                                        result.rows[0]
                                      )
                                        .slice(
                                          0,
                                          10
                                        )
                                        .map(
                                          (column) => (
                                            <td
                                              key={
                                                column
                                              }
                                            >
                                              {row[
                                                column
                                              ] == null
                                                ? "—"
                                                : String(
                                                    row[
                                                      column
                                                    ]
                                                  )}
                                            </td>
                                          )
                                        )}
                                    </tr>
                                  )
                                )}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </article>
            );
          }
        )}

        <button
          type="button"
          className="notebook-add-cell"
          onClick={() => {
            setDraft(
              (previous) => ({
                ...previous,
                cells: [
                  ...previous.cells,
                  createCell(),
                ],
              })
            );
          }}
        >
          <Plus size={14} />
          Add Python cell
        </button>
      </div>

      {message && (
        <div className="notebook-message">
          {message}
        </div>
      )}
    </div>
  );
}

export default WorkspaceNotebook;
