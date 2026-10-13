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
  useMemo,
} from "react";

import {
  runNotebookCells,
  runNotebookAllCells,
  NotebookCellExecutionError,
  type NotebookCellRunResult,
} from "./pythonRunner";

export type WorkspaceNotebookCellData = {
  cell_id: string;
  code: string;
  cell_type: "python" | "sql" | "markdown";
  section_title?: string | null;
  last_execution?: {
    success: boolean;
    expression_kind: "dataframe" | "scalar" | "none";
    output?: string | null;
    row_count?: number | null;
    columns?: string[];
    preview_rows?: Record<string, unknown>[];
    executed_at: string;
  } | null;
};

export type NotebookQualityCheck = {
  check_id: string;
  cell_id: string | null;
  section_title: string | null;
  title: string;
  note: string;
  code: string;
  cell_type: "python" | "sql";
  result_summary: string;
  status: "recorded" | "sample_passed" | "needs_review";
  sample_row_count: number;
  total_row_count: number | null;
  dataset_kind: "working" | "raw" | "processed";
  processed_dataset_id: string | null;
  observed_at: string;
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
  quality_checks?: NotebookQualityCheck[];
  section_mode?: "legacy" | "explicit";

  created_at: string;
  updated_at: string;
};

type ProcessedDataset = {
  dataset_id: string;
  name: string;
};

type NotebookRunResult =
  NotebookCellRunResult;

type NotebookDisplayResult = NotebookRunResult & {
  restoredFromSave?: boolean;
  savedRowCount?: number | null;
};

// Saved executions are persisted with their cell in the workspace. Restore
// only that bounded snapshot; never silently rerun cells or infer full-data
// validation from a saved sample preview.
function restoreSavedNotebookResults(
  cells: WorkspaceNotebookCellData[],
): Record<string, NotebookDisplayResult> {
  const restored: Record<string, NotebookDisplayResult> = {};
  for (const cell of cells) {
    const execution = cell.last_execution;
    if (
      !execution ||
      typeof execution.success !== "boolean" ||
      !["dataframe", "scalar", "none"].includes(execution.expression_kind)
    ) {
      continue;
    }
    restored[cell.cell_id] = {
      rows: Array.isArray(execution.preview_rows) ? execution.preview_rows : [],
      output: typeof execution.output === "string" ? execution.output : "",
      expressionKind: execution.expression_kind,
      success: execution.success,
      restoredFromSave: true,
      savedRowCount: execution.row_count ?? null,
    };
  }
  return restored;
}

type Props = {
  workspaceId: string;

  language: "en" | "nl" | "tr";

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

  onAskMentorContext?: (
    code: string
  ) => void;
  dataRevision?: number;
};

function createCell(cellType: "python" | "sql" | "markdown" = "python"):
  WorkspaceNotebookCellData {
  return {
    cell_id:
      crypto.randomUUID(),
    code:
      cellType === "python" ? "# Work with df\n" : cellType === "sql" ? "SELECT * FROM df LIMIT 5;" : "# Notes\n",
    cell_type:
      cellType,
  };
}

function WorkspaceNotebook({
  workspaceId,
  language,
  notebook,
  processedDatasets,
  onSave,
  onDelete,
  onPromoteCode,
  onAskMentorContext,
  dataRevision = 0,
}: Props) {
  const ui = {
    en: {
      notebook: "Notebook", dataset: "Dataset", working: "Development / working",
      raw: "Raw source sample", runAll: "Run all", reset: "Reset", saved: "Saved",
      saveNow: "Save now", saving: "Saving...", unsaved: "Unsaved changes",
      export: "Export .ipynb", loading: "Loading dataset...", rowsLoaded: "rows loaded",
      sampledRows: "sampled rows", fromTotal: "from", totalRows: "total rows",
      columns: "columns", askMentor: "Ask mentor", reviewing: "Reviewing...",
      sendPipeline: "Send to pipeline", deleteCell: "Delete cell", output: "OUTPUT",
      savedPreview: "saved preview",
      addCell: "Add cell", sectionChoice: "Section", ungrouped: "No section", newSection: "New section", newSectionName: "New section name", cellKind: "Cell type", cellLanguage: "Language", section: "Section", sectionPlaceholder: "Optional section title",
    },
    nl: {
      notebook: "Notebook", dataset: "Dataset", working: "Ontwikkeldata / werkset",
      raw: "Ruwe bronsteekproef", runAll: "Alles uitvoeren", reset: "Resetten", saved: "Opgeslagen",
      saveNow: "Nu opslaan", saving: "Opslaan...", unsaved: "Niet-opgeslagen wijzigingen",
      export: "Exporteer .ipynb", loading: "Dataset laden...", rowsLoaded: "rijen geladen",
      sampledRows: "steekproefrijen", fromTotal: "van", totalRows: "totale rijen",
      columns: "kolommen", askMentor: "Vraag mentor", reviewing: "Beoordelen...",
      sendPipeline: "Naar pipeline", deleteCell: "Cel verwijderen", output: "UITVOER",
      savedPreview: "opgeslagen voorbeeld",
      addCell: "Cel toevoegen", sectionChoice: "Sectie", ungrouped: "Geen sectie", newSection: "Nieuwe sectie", newSectionName: "Nieuwe sectienaam", cellKind: "Celtype", cellLanguage: "Taal", section: "Sectie", sectionPlaceholder: "Optionele sectietitel",
    },
    tr: {
      notebook: "Not defteri", dataset: "Veri seti", working: "Geliştirme / çalışma verisi",
      raw: "Ham kaynak örneği", runAll: "Tümünü çalıştır", reset: "Sıfırla", saved: "Kaydedildi",
      saveNow: "Şimdi kaydet", saving: "Kaydediliyor...", unsaved: "Kaydedilmemiş değişiklikler",
      export: ".ipynb dışa aktar", loading: "Veri seti yükleniyor...", rowsLoaded: "satır yüklendi",
      sampledRows: "örnek satır", fromTotal: "/", totalRows: "toplam satır",
      columns: "sütun", askMentor: "Mentora sor", reviewing: "İnceleniyor...",
      sendPipeline: "Pipeline'a gönder", deleteCell: "Cell'i sil", output: "ÇIKTI",
      savedPreview: "kayıtlı önizleme",
      addCell: "Hücre ekle", sectionChoice: "Bölüm", ungrouped: "Bağımsız", newSection: "Yeni bölüm", newSectionName: "Yeni bölüm adı", cellKind: "Hücre türü", cellLanguage: "Dil", section: "Bölüm", sectionPlaceholder: "İsteğe bağlı bölüm başlığı",
    },
  }[language];

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
    inputTotalRowCount,
    setInputTotalRowCount,
  ] = useState<number | null>(null);

  const [
    inputIsSampled,
    setInputIsSampled,
  ] = useState(false);

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
  const [openLanguageMenu, setOpenLanguageMenu] = useState<string | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>(
    Object.fromEntries(
      notebook.cells
        .map((cell) => cell.section_title?.trim())
        .filter((title): title is string => Boolean(title))
        .map((title) => [title, true])
    )
  );
  const [qualityOpen, setQualityOpen] = useState(false);
  const [qualityEditorId, setQualityEditorId] = useState<string | null>(null);
  const [qualityTitle, setQualityTitle] = useState("");
  const [qualityNote, setQualityNote] = useState("");
  const [qualityStatus, setQualityStatus] = useState<NotebookQualityCheck["status"]>("recorded");
  const [qualityExpandedId, setQualityExpandedId] = useState<string | null>(null);
  const [addCellOpen, setAddCellOpen] = useState(false);
  const [addSection, setAddSection] = useState("");
  const [addNewSectionName, setAddNewSectionName] = useState("");
  const [addCellType, setAddCellType] = useState<"python" | "sql" | "markdown">("python");
  const newCellId = useRef<string | null>(null);
  const availableSections = useMemo(() => [...new Set(
    draft.cells.map(cell => cell.section_title?.trim()).filter((value): value is string => Boolean(value))
  )], [draft.cells]);
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
      NotebookDisplayResult
    >
  >({});

  useEffect(() => {
    setDraft(notebook);
    setAddCellOpen(false);
    setAddSection("");
    newCellId.current = null;
    setResults(restoreSavedNotebookResults(notebook.cells));
    setMentorGuidance({});
    setCollapsedSections(
      Object.fromEntries(
        notebook.cells
          .map((cell) => cell.section_title?.trim())
          .filter((title): title is string => Boolean(title))
          .map((title) => [title, true])
      )
    );
    setMessage(null);
    setDirty(false);
    setLastSavedAt(notebook.updated_at);
  }, [notebook.notebook_id]);

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
            total_row_count?: number | null;
            sampled?: boolean;
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

        setInputTotalRowCount(
          data.total_row_count ??
          data.row_count
        );

        setInputIsSampled(
          Boolean(data.sampled)
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
    dataRevision,
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

      setMessage(ui.saved);

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

  function explicitCells() {
    if (draft.section_mode === "explicit") return draft.cells;
    let current = "";
    return draft.cells.map(cell => {
      if (cell.section_title?.trim()) current = cell.section_title.trim();
      return { ...cell, section_title: current || null };
    });
  }

  function insertCell(section: string, kind: "python" | "sql" | "markdown") {
    const normalized = section.trim();
    if (normalized.length > 80) return;
    const cells = explicitCells();
    const cell = { ...createCell(kind), section_title: normalized || null };
    let after = cells.length - 1;
    if (normalized) {
      const last = cells.findLastIndex(item => item.section_title === normalized);
      if (last >= 0) after = last;
    }
    const updated = [...cells.slice(0, after + 1), cell, ...cells.slice(after + 1)];
    markDraftChanged({ ...draft, section_mode: "explicit", cells: updated });
    setCollapsedSections(prev => ({ ...prev, [normalized]: false }));
    setAddCellOpen(false);
    newCellId.current = cell.cell_id;
    requestAnimationFrame(() => {
      document.getElementById(`notebook-cell-${cell.cell_id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
      document.getElementById(`notebook-code-${cell.cell_id}`)?.focus({ preventScroll: true });
      newCellId.current = null;
    });
  }

  function proposeCheckTitle(cell: WorkspaceNotebookCellData): string {
    const comment = cell.code.split("\n").map(line => line.trim())
      .find(line => line.startsWith("# ") || line.startsWith("-- "));
    if (comment) return comment.replace(/^(#|--)\s*/, "").slice(0, 120);
    const columns = [...new Set([...cell.code.matchAll(/df\[["']([^"']+)["']\]/g)].map(match => match[1]))];
    return (columns.length ? columns.slice(0, 3).join(" / ") : "Notebook")
      + " — quality check";
  }

  function openQualityEditor(cell: WorkspaceNotebookCellData) {
    setQualityEditorId(cell.cell_id);
    setQualityTitle(proposeCheckTitle(cell));
    setQualityNote("");
    setQualityStatus("recorded");
  }

  async function saveQualityCheck(cell: WorkspaceNotebookCellData) {
    const result = results[cell.cell_id];
    if (!result || result.success === false || !qualityTitle.trim()) return;
    const summary = result.output.trim().slice(0, 1500) ||
      (result.rows.length ? JSON.stringify(result.rows.slice(0, 5)).slice(0, 1500) : "Executed");
    const check: NotebookQualityCheck = {
      check_id: crypto.randomUUID(),
      cell_id: cell.cell_id,
      section_title: cell.section_title?.trim() || null,
      title: qualityTitle.trim().slice(0, 120),
      note: qualityNote.trim().slice(0, 1000),
      code: cell.code,
      cell_type: cell.cell_type as "python" | "sql",
      result_summary: summary,
      status: qualityStatus,
      sample_row_count: inputRows.length,
      total_row_count: inputTotalRowCount,
      dataset_kind: draft.dataset_kind,
      processed_dataset_id: draft.processed_dataset_id,
      observed_at: new Date().toISOString(),
    };
    const saved = await saveDraft({
      ...draft,
      quality_checks: [...(draft.quality_checks ?? []), check],
    });
    if (saved) {
      setQualityEditorId(null);
      setQualityOpen(true);
      setQualityExpandedId(check.check_id);
    }
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
        cell_type: cell.cell_type === "markdown" ? "markdown" : "code",
        ...(cell.cell_type === "markdown" ? {} : { execution_count: null, outputs: [] }),
        metadata: { datapilot_cell_id: cell.cell_id, language: cell.cell_type ?? "python" },
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
        draft.cells.map((item) => ({ code: item.code, cell_type: item.cell_type ?? "python" })),
        inputRows,
      );

      const nextResults: Record<string, NotebookRunResult> = {};
      draft.cells.forEach((cell, index) => {
        if (allResults[index]) {
          nextResults[cell.cell_id] =
            allResults[index];
        }
      });
      setResults(nextResults);

      const nextDraft: WorkspaceNotebookData = {
        ...draft,
        cells: draft.cells.map((cell, index) => {
          const result = allResults[index];
          if (!result) return cell;

          const previewRows =
            result.expressionKind === "dataframe"
              ? result.rows.slice(0, 5)
              : [];
          const success =
            result.success !== false;

          return {
            ...cell,
            last_execution: {
              success,
              expression_kind:
                result.expressionKind,
              output: result.output.slice(0, 1000),
              row_count:
                result.rows.length || null,
              columns:
                previewRows.length
                  ? Object.keys(
                      previewRows[0]
                    ).slice(0, 30)
                  : [],
              preview_rows:
                previewRows,
              executed_at:
                new Date().toISOString(),
            },
          };
        }),
      };

      setDraft(nextDraft);
      await saveDraft(nextDraft);

      const failedIndex = allResults.findIndex(
        (item) => item.success === false
      );

      if (failedIndex >= 0) {
        setMessage(
          "Cell " +
          String(failedIndex + 1) +
          " failed: " +
          allResults[failedIndex].output
        );
      }
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
    cell: WorkspaceNotebookCellData
  ) {
    if (onAskMentorContext) {
      onAskMentorContext(cell.code);
      return;
    }

    setMentorLoadingCellId(cell.cell_id);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/notebooks/${notebook.notebook_id}/mentor`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: cell.code }),
        }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Mentor guidance could not be loaded.");
      setMentorGuidance((previous) => ({ ...previous, [cell.cell_id]: data.guidance }));
    } catch (error) {
      setMentorGuidance((previous) => ({
        ...previous,
        [cell.cell_id]: [error instanceof Error ? error.message : "Mentor guidance could not be loaded."],
      }));
    } finally {
      setMentorLoadingCellId(null);
    }
  }

  async function persistExecution(
    cellId: string,
    result: NotebookRunResult,
    success = true,
  ) {
    const compactOutput = result.output.slice(0, 1000);
    const previewRows =
      result.expressionKind === "dataframe"
        ? result.rows.slice(0, 5)
        : [];
    const columns =
      previewRows.length > 0
        ? Object.keys(previewRows[0]).slice(0, 30)
        : [];

    const nextDraft: WorkspaceNotebookData = {
      ...draft,
      cells: draft.cells.map((item) =>
        item.cell_id === cellId
          ? {
              ...item,
              last_execution: {
                success,
                expression_kind: result.expressionKind,
                output: compactOutput,
                row_count: result.rows.length || null,
                columns,
                preview_rows: previewRows,
                executed_at: new Date().toISOString(),
              },
            }
          : item
      ),
    };
    setDraft(nextDraft);
    await saveDraft(nextDraft);
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
            (item) => ({ code: item.code, cell_type: item.cell_type ?? "python" })
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
      await persistExecution(cell.cell_id, result, true);
    } catch (error) {
      const failedIndex =
        error instanceof NotebookCellExecutionError
          ? error.failedIndex
          : index;
      const failedCell =
        draft.cells[failedIndex]
        ?? cell;
      const failedResult: NotebookRunResult =
        error instanceof NotebookCellExecutionError
          ? error.result
          : {
              rows: [],
              output:
                error instanceof Error
                  ? error.message
                  : "Notebook cell failed.",
              expressionKind: "none",
              success: false,
            };

      setResults(
        (previous) => ({
          ...previous,
          [failedCell.cell_id]:
            failedResult,
        })
      );

      await persistExecution(
        failedCell.cell_id,
        failedResult,
        false,
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
            {ui.notebook}
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
            <span>{ui.dataset}</span>

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
                {ui.working}
              </option>

              <option value="raw">
                {ui.raw}
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
            {ui.runAll}
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
            {ui.reset}
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
            {saving ? ui.saving : dirty ? ui.saveNow : ui.saved}
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={exportNotebook}
            title={ui.export}
          >
            <Download size={14} />
            {ui.export}
          </button>

          <span className={dirty ? "notebook-save-status unsaved" : "notebook-save-status"}>
            {saving ? ui.saving : dirty ? ui.unsaved : lastSavedAt ? `✓ ${ui.saved}` : ui.saved}
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
          ? ui.loading
          : dataError
            ? dataError
            : (
                inputIsSampled
                  ? `${inputRows.length} ${ui.sampledRows} ${ui.fromTotal} ${inputTotalRowCount ?? inputRows.length} ${ui.totalRows} · ${inputColumns.length} ${ui.columns} · browser sandbox`
                  : `${inputRows.length} ${ui.rowsLoaded} · ${inputColumns.length} ${ui.columns} · browser sandbox`
              )}
      </div>

      <div className="notebook-quality-panel">
        <button type="button" className="notebook-quality-toggle"
          onClick={() => setQualityOpen(value => !value)}>
          {qualityOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          Quality Checks <span>({(draft.quality_checks ?? []).length})</span>
        </button>
        {qualityOpen && (
          <div className="notebook-quality-body">
            {(draft.quality_checks ?? []).length === 0 && (
              <p className="notebook-quality-hint">Run a Python/SQL cell, review its result, then choose “Save as Quality Check”.</p>
            )}
            {(() => {
              const groups = new Map<string, NotebookQualityCheck[]>();
              for (const check of draft.quality_checks ?? []) {
                const section = check.section_title || "Ungrouped";
                groups.set(section, [...(groups.get(section) ?? []), check]);
              }
              return [...groups].map(([section, checks]) => (
                <div key={section} className="notebook-quality-group">
                  <strong>{section}</strong>
                  {checks.map(check => (
                    <div key={check.check_id} className="notebook-quality-entry">
                      <button type="button" className="notebook-quality-entry-head"
                        onClick={() => setQualityExpandedId(value => value === check.check_id ? null : check.check_id)}>
                        <span>{check.title}</span>
                        <small>{check.status.replaceAll("_", " ")} · {check.sample_row_count.toLocaleString()} rows</small>
                        {qualityExpandedId === check.check_id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>
                      {qualityExpandedId === check.check_id && (
                        <div className="notebook-quality-detail">
                          <div>Notebook sample: {check.sample_row_count.toLocaleString()} rows; source context: {check.total_row_count?.toLocaleString() ?? "unknown"} rows · Full-data verification: pending</div>
                          {check.note && <p>{check.note}</p>}
                          <pre>{check.code}</pre>
                          <pre>{check.result_summary}</pre>
                          <div className="notebook-quality-buttons">
                            <button type="button" className="secondary-button"
                              onClick={() => {
                                if (check.cell_id) {
                                  setCollapsedSections(previous => ({ ...previous, [check.section_title ?? ""]: false }));
                                  requestAnimationFrame(() => document.getElementById(`notebook-cell-${check.cell_id}`)?.scrollIntoView({ behavior: "smooth", block: "center" }));
                                }
                              }}>Go to cell</button>
                            <button type="button" className="secondary-button"
                              onClick={() => {
                                if (!window.confirm("Remove this saved check?")) return;
                                markDraftChanged({ ...draft, quality_checks: (draft.quality_checks ?? []).filter(item => item.check_id !== check.check_id) });
                              }}>Remove</button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ));
            })()}
          </div>
        )}
      </div>

      <div className="notebook-cells">
        {(() => {
          // Consolidate same-name sections visually; retain original cell indices for Run.
          let currentSection = "";
          const grouped = new Map<string, Array<{ cell: WorkspaceNotebookCellData; index: number; sectionTitle: string }>>();
          draft.cells.forEach((cell, index) => {
            if (draft.section_mode === "explicit") {
              currentSection = cell.section_title?.trim() || "";
            } else if (cell.section_title?.trim()) {
              currentSection = cell.section_title.trim();
            }
            const sectionKey = currentSection || `__ungrouped_${index}`;
            if (!grouped.has(sectionKey)) grouped.set(sectionKey, []);
            grouped.get(sectionKey)!.push({ cell, index, sectionTitle: currentSection });
          });
          const displayCells = Array.from(grouped.values()).flat();
          const renderedHeadings = new Set<string>();
          return displayCells.map(
            ({ cell, index, sectionTitle }) => {
              const showSectionHeader = Boolean(sectionTitle && !renderedHeadings.has(sectionTitle));
              if (showSectionHeader) renderedHeadings.add(sectionTitle);
              const sectionCollapsed =
                Boolean(
                  sectionTitle &&
                  collapsedSections[sectionTitle]
                );

              const result =
                results[
                  cell.cell_id
                ];

              if (sectionCollapsed && !showSectionHeader) return null;

              return (
                <div
                  className="notebook-cell-section-wrap"
                  key={cell.cell_id}
                  id={`notebook-cell-${cell.cell_id}`}
                >
                  {showSectionHeader && (
                    <div className="notebook-section-header">
                      <button
                        type="button"
                        className="notebook-section-toggle"
                        onClick={() =>
                          setCollapsedSections((previous) => ({
                            ...previous,
                            [sectionTitle]:
                              !previous[sectionTitle],
                          }))
                        }
                      >
                        {sectionCollapsed
                          ? <ChevronRight size={14} />
                          : <ChevronDown size={14} />}
                        <strong>{sectionTitle}</strong>
                      </button>
                      <button type="button" className="notebook-section-add" onClick={() => insertCell(sectionTitle, "python")}>
                        <Plus size={13} /> {ui.addCell}
                      </button>
                    </div>
                  )}

                  {!sectionCollapsed && (
              <article
                className="notebook-cell"
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
                  <div className="notebook-cell-language" onBlur={(event) => {
                    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpenLanguageMenu(null);
                  }}>
                    <span className="notebook-language-label">{ui.cellLanguage}</span>
                    <div className="notebook-language-select">
                      <button type="button" className="notebook-language-trigger"
                        aria-haspopup="listbox" aria-expanded={openLanguageMenu === cell.cell_id}
                        aria-label={ui.cellLanguage} disabled={runningCellId !== null}
                        onClick={() => setOpenLanguageMenu((current) => current === cell.cell_id ? null : cell.cell_id)}>
                        <span className="notebook-language-dot" data-language={cell.cell_type ?? "python"} />
                        {cell.cell_type === "sql" ? "SQL" : cell.cell_type === "markdown" ? "Markdown" : "Python"}
                        <ChevronDown size={14} />
                      </button>
                      {openLanguageMenu === cell.cell_id && (
                        <div className="notebook-language-menu" role="listbox" aria-label={ui.cellLanguage}>
                          {(["python", "sql", "markdown"] as const).map((cellType) => (
                            <button key={cellType} type="button" role="option"
                              aria-selected={(cell.cell_type ?? "python") === cellType}
                              className={(cell.cell_type ?? "python") === cellType ? "selected" : ""}
                              onClick={() => {
                                markDraftChanged({
                                  ...draft,
                                  cells: draft.cells.map((item) => item.cell_id === cell.cell_id
                                    ? { ...item, cell_type: cellType, last_execution: null }
                                    : item),
                                });
                                setResults((previous) => {
                                  const next = { ...previous };
                                  delete next[cell.cell_id];
                                  return next;
                                });
                                setOpenLanguageMenu(null);
                              }}>
                              <span className="notebook-language-dot" data-language={cellType} />
                              <span>{cellType === "python" ? "Python" : cellType === "sql" ? "SQL (read-only)" : "Markdown"}</span>
                              {(cell.cell_type ?? "python") === cellType && <span className="notebook-language-check">✓</span>}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="notebook-cell-section-editor">
                    <label>
                      <span>{ui.section}</span>
                      <input
                        value={draft.section_mode === "explicit" ? (cell.section_title ?? "") : (cell.section_title ?? "")}
                        placeholder={ui.sectionPlaceholder}
                        onChange={(event) => {
                          const sectionTitle =
                            event.target.value;

                          markDraftChanged({
                            ...draft,
                            section_mode: "explicit",
                            cells: explicitCells().map(item =>
                              item.cell_id === cell.cell_id
                                ? { ...item, section_title: sectionTitle || null }
                                : item
                            ),
                          });
                        }}
                      />
                    </label>
                  </div>

                  <textarea
                    id={`notebook-code-${cell.cell_id}`}
                    value={cell.code}
                    spellCheck={false}
                    onChange={(event) => {
                      const code =
                        event.target.value;

                      markDraftChanged({
                        ...draft,
                        cells: draft.cells.map((item) =>
                          item.cell_id === cell.cell_id
                            ? {
                                ...item,
                                code,
                                last_execution:
                                  code === item.code ? item.last_execution : null,
                              }
                            : item
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
                        ? ui.reviewing
                        : ui.askMentor}
                    </button>

                    <button
                      type="button"
                      className="secondary-button"
                      disabled={(cell.cell_type ?? "python") !== "python"}
                      title={(cell.cell_type ?? "python") === "python" ? ui.sendPipeline : "Only Python cells can be sent to the pipeline"}
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
                      {ui.sendPipeline}
                    </button>

                    {(cell.cell_type === "python" || cell.cell_type === "sql") && (
                      <button type="button" className="secondary-button"
                        disabled={!results[cell.cell_id] || results[cell.cell_id].success === false || runningCellId !== null}
                        title="Save this executed result as a quality check"
                        onClick={() => openQualityEditor(cell)}>
                        <Save size={13} /> Save as Quality Check
                      </button>
                    )}

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
                      {ui.deleteCell}
                    </button>
                  </div>

                  {qualityEditorId === cell.cell_id && (
                    <div className="notebook-quality-editor">
                      <strong>Save as Quality Check</strong>
                      <label>Check name<input maxLength={120} value={qualityTitle} onChange={event => setQualityTitle(event.target.value)} /></label>
                      <label>Decision note (optional)<textarea maxLength={1000} rows={2} value={qualityNote} onChange={event => setQualityNote(event.target.value)} /></label>
                      <label>Review status
                        <select value={qualityStatus} onChange={event => setQualityStatus(event.target.value as NotebookQualityCheck["status"])}>
                          <option value="recorded">Recorded — not yet reviewed</option>
                          <option value="sample_passed">Sample passed — reviewed</option>
                          <option value="needs_review">Needs investigation</option>
                        </select>
                      </label>
                      <small>Current result: {results[cell.cell_id]?.output.slice(0, 150) || "DataFrame result"} · {inputRows.length.toLocaleString()} Notebook rows · Full data not verified</small>
                      <div className="notebook-quality-buttons">
                        <button type="button" className="secondary-button" onClick={() => setQualityEditorId(null)}>Cancel</button>
                        <button type="button" className="new-workspace-button" disabled={!qualityTitle.trim() || saving || dirty}
                          onClick={() => void saveQualityCheck(cell)}>Save check</button>
                      </div>
                      {dirty && <small>Wait for the Notebook autosave to finish before saving this check.</small>}
                    </div>
                  )}
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
                          {ui.output}
                        </button>

                        <strong>
                          {result.expressionKind === "scalar"
                            ? "value"
                            : `${result.savedRowCount ?? result.rows.length} rows${result.restoredFromSave ? ` · ${ui.savedPreview}` : ""}`}
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
                  )}
                </div>
              );
            }
          );
        })()}

        <button type="button" className="notebook-add-cell" onClick={() => setAddCellOpen(value => !value)}>
          <Plus size={14} /> {ui.addCell}
        </button>
        {addCellOpen && (
          <div className="notebook-add-panel">
            <label>{ui.sectionChoice}
              <select value={addSection} onChange={event => setAddSection(event.target.value)}>
                <option value="">{ui.ungrouped}</option>
                {availableSections.map(section => <option key={section} value={section}>{section}</option>)}
                <option value="__new__">{ui.newSection}</option>
              </select>
            </label>
            {addSection === "__new__" && (
              <input value={addNewSectionName} maxLength={80} placeholder={ui.newSectionName}
                onChange={event => setAddNewSectionName(event.target.value)} />
            )}
            <label>{ui.cellKind}
              <select value={addCellType} onChange={event => setAddCellType(event.target.value as "python" | "sql" | "markdown")}>
                <option value="python">Python</option>
                <option value="sql">SQL</option>
                <option value="markdown">Markdown</option>
              </select>
            </label>
            <button type="button" className="notebook-add-submit"
              disabled={addSection === "__new__" && !addNewSectionName.trim()}
              onClick={() => insertCell(addSection === "__new__" ? addNewSectionName : addSection, addCellType)}>
              <Plus size={14} /> {ui.addCell}
            </button>
          </div>
        )}
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
