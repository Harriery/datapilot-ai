import {
  Play,
  PlayCircle,
  Plus,
  RotateCcw,
  Sparkles,
  Save,
  Download,
  ChevronDown,
  ChevronRight,
  Send,
  Trash2,
} from "lucide-react";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  runNotebookCells,
  runNotebookAllCells,
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
  expressionKind: "dataframe" | "scalar" | "none";
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

  const [dirty, setDirty] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [collapsedOutputs, setCollapsedOutputs] = useState<Record<string, boolean>>({});
  const autosaveTimer = useRef<number | null>(null);

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
    mentorLoadingCellId,
    setMentorLoadingCellId,
  ] = useState<string | null>(
    null
  );

  const [
    mentorGuidance,
    setMentorGuidance,
  ] = useState<
    Record<string, string[]>
  >({});

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
    setMentorGuidance({});
    setMessage(null);
    setDirty(false);
    setLastSavedAt(notebook.updated_at);
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
      setDirty(false);
      setLastSavedAt(saved.updated_at);

      setMessage(
        "Notebook saved."
      );

      return saved;
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Notebook could not be saved."
      );

      return null;
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (!dirty) return;

    if (autosaveTimer.current !== null) {
      window.clearTimeout(autosaveTimer.current);
    }

    autosaveTimer.current = window.setTimeout(() => {
      void saveDraft(draft);
    }, 800);

    return () => {
      if (autosaveTimer.current !== null) {
        window.clearTimeout(autosaveTimer.current);
      }
    };
  }, [draft, dirty]);

  useEffect(() => {
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [dirty]);

  function markDraftChanged(next: WorkspaceNotebookData) {
    setDraft(next);
    setDirty(true);
  }

  function exportNotebook() {
    const payload = {
      nbformat: 4,
      nbformat_minor: 5,
      metadata: {
        kernelspec: { display_name: "Python 3", language: "python", name: "python3" },
        datapilot: {
          notebook_id: draft.notebook_id,
          dataset_kind: draft.dataset_kind,
          processed_dataset_id: draft.processed_dataset_id,
        },
      },
      cells: draft.cells.map((cell) => ({
        cell_type: "code",
        execution_count: null,
        metadata: { datapilot_cell_id: cell.cell_id },
        outputs: [],
        source: cell.code.split(/(?<=\n)/),
      })),
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/x-ipynb+json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${draft.name || "notebook"}.ipynb`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function runAllCells() {
    if (draft.cells.length === 0) return;
    setRunningCellId("all");
    setMessage(null);

    try {
      const saved = await saveDraft(draft);
      if (!saved) return;

      const allResults = await runNotebookAllCells(
        draft.cells.map((item) => item.code),
        inputRows,
      );

      const nextResults: Record<string, NotebookRunResult> = {};
      draft.cells.forEach((cell, index) => {
        if (allResults[index]) nextResults[cell.cell_id] = allResults[index];
      });
      setResults(nextResults);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Notebook run failed.");
    } finally {
      setRunningCellId(null);
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

  async function askMentor(
    cell:
      WorkspaceNotebookCellData
  ) {
    setMentorLoadingCellId(
      cell.cell_id
    );

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/notebooks/${notebook.notebook_id}/mentor`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            code: cell.code,
          }),
        }
      );

      if (!response.ok) {
        const errorData =
          await response.json();

        throw new Error(
          errorData.detail ||
            "Mentor guidance could not be loaded."
        );
      }

      const data:
        {
          guidance: string[];
        } =
          await response.json();

      setMentorGuidance(
        (previous) => ({
          ...previous,
          [cell.cell_id]:
            data.guidance,
        })
      );

    } catch (error) {
      setMentorGuidance(
        (previous) => ({
          ...previous,
          [cell.cell_id]: [
            error instanceof Error
              ? error.message
              : "Mentor guidance could not be loaded.",
          ],
        })
      );
    } finally {
      setMentorLoadingCellId(
        null
      );
    }
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
      const saved =
        await saveDraft(
          draft
        );

      if (!saved) {
        return;
      }

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
              markDraftChanged({ ...draft, name: event.target.value });
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
            disabled={
              draft.cells.length === 0 ||
              runningCellId !== null ||
              loadingData
            }
            onClick={() => { void runAllCells(); }}
          >
            <PlayCircle size={14} />
            Run all
          </button>

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
            {saving ? "Saving..." : dirty ? "Save now" : "Saved"}
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={exportNotebook}
            title="Export as Jupyter notebook"
          >
            <Download size={14} />
            Export .ipynb
          </button>

          <span className={dirty ? "notebook-save-status unsaved" : "notebook-save-status"}>
            {saving ? "Saving…" : dirty ? "Unsaved changes" : lastSavedAt ? "✓ Saved" : "Saved"}
          </span>

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

                      markDraftChanged({
                        ...draft,
                        cells: draft.cells.map((item) =>
                          item.cell_id === cell.cell_id ? { ...item, code } : item
                        ),
                      });

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
                      disabled={
                        mentorLoadingCellId !== null
                      }
                      onClick={() => {
                        void askMentor(
                          cell
                        );
                      }}
                    >
                      <Sparkles size={13} />
                      {mentorLoadingCellId ===
                      cell.cell_id
                        ? "Reviewing..."
                        : "Ask mentor"}
                    </button>

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
                        markDraftChanged({
                          ...draft,
                          cells: draft.cells.filter((item) => item.cell_id !== cell.cell_id),
                        });
                      }}
                    >
                      Delete cell
                    </button>
                  </div>

                  {mentorGuidance[
                    cell.cell_id
                  ] && (
                    <div className="notebook-mentor-guidance">
                      <div>
                        <Sparkles size={13} />
                        <strong>
                          DataPilot Mentor
                        </strong>
                      </div>

                      <ul>
                        {mentorGuidance[
                          cell.cell_id
                        ].map(
                          (
                            guidance,
                            guidanceIndex
                          ) => (
                            <li
                              key={
                                guidanceIndex
                              }
                            >
                              {guidance}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {result && (
                    <div className="notebook-output">
                      <div className="notebook-output-header">
                        <button
                          type="button"
                          className="notebook-output-toggle"
                          onClick={() => setCollapsedOutputs((previous) => ({
                            ...previous,
                            [cell.cell_id]: !previous[cell.cell_id],
                          }))}
                        >
                          {collapsedOutputs[cell.cell_id] ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                          OUTPUT
                        </button>

                        <strong>
                          {result.expressionKind === "scalar"
                            ? "value"
                            : `${result.rows.length} rows`}
                        </strong>
                      </div>

                      {!collapsedOutputs[cell.cell_id] && result.output && (
                        <pre>
                          {result.output}
                        </pre>
                      )}

                      {!collapsedOutputs[cell.cell_id] && result.expressionKind === "dataframe" && result.rows.length > 0 && (
                        <div className="notebook-preview-table-wrap">
                          <table>
                            <thead>
                              <tr>
                                {Object.keys(result.rows[0])
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
                                      {Object.keys(result.rows[0])
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
            markDraftChanged({
              ...draft,
              cells: [...draft.cells, createCell()],
            });
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
