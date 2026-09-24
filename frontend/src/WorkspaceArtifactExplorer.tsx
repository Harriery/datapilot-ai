import {
  Boxes,
  Database,
  FileSpreadsheet,
  FlaskConical,
  GitBranch,
  NotebookTabs,
  Plus,
  Table2,
} from "lucide-react";

import {
  useState,
} from "react";

import type { AppLanguage } from "./i18n";

export type WorkbenchView =
  | "explorer"
  | "notebook"
  | "pipeline"
  | "lineage";

type NotebookSummary = {
  notebook_id: string;
  name: string;
};

type ProcessedDatasetSummary = {
  dataset_id: string;
  name: string;
  row_count: number;
};

type Props = {
  language: AppLanguage;
  workspaceTitle: string;

  datasetFilename:
    | string
    | null
    | undefined;

  developmentRows:
    | number
    | null
    | undefined;

  processedDatasets:
    ProcessedDatasetSummary[];

  notebooks:
    NotebookSummary[];

  pipelineOperationCount: number;

  hasModel: boolean;
  kpiCount: number;

  activeView: WorkbenchView;

  selectedNotebookId:
    | string
    | null;

  onViewChange: (
    view: WorkbenchView
  ) => void;

  onNotebookSelect: (
    notebookId: string
  ) => void;

  onCreateNotebook: () => void;

  onOpenSource: () => void;
  onOpenValidate: () => void;
};

function WorkspaceArtifactExplorer({
  language,
  workspaceTitle,
  datasetFilename,
  developmentRows,
  processedDatasets,
  notebooks,
  pipelineOperationCount,
  hasModel,
  kpiCount,
  activeView,
  selectedNotebookId,
  onViewChange,
  onNotebookSelect,
  onCreateNotebook,
  onOpenSource,
  onOpenValidate,
}: Props) {
  const ui = {
    en: { workspace:"WORKSPACE", newNotebook:"New notebook", source:"Dataset / source", processed:"Processed dataset", data:"DATA", raw:"Raw source", rawReadOnly:"Raw · read-only", development:"Development dataset", rows:"rows", notebooks:"NOTEBOOKS", pythonNotebook:"Python notebook", build:"BUILD", pipeline:"Cleaning pipeline", steps:"steps", lineage:"Lineage", dataFlow:"Data flow", model:"Logical model", kpis:"KPI definitions" },
    nl: { workspace:"WERKRUIMTE", newNotebook:"Nieuw notebook", source:"Dataset / bron", processed:"Verwerkte dataset", data:"DATA", raw:"Ruwe bron", rawReadOnly:"Ruw · alleen-lezen", development:"Ontwikkeldataset", rows:"rijen", notebooks:"NOTEBOOKS", pythonNotebook:"Python-notebook", build:"BOUWEN", pipeline:"Opschoningspipeline", steps:"stappen", lineage:"Herkomst", dataFlow:"Gegevensstroom", model:"Logisch model", kpis:"KPI-definities" },
    tr: { workspace:"ÇALIŞMA ALANI", newNotebook:"Yeni notebook", source:"Veri seti / kaynak", processed:"İşlenmiş veri seti", data:"VERİ", raw:"Ham kaynak", rawReadOnly:"Ham · salt okunur", development:"Geliştirme veri seti", rows:"satır", notebooks:"NOTEBOOKLAR", pythonNotebook:"Python notebook", build:"OLUŞTUR", pipeline:"Temizleme pipeline'ı", steps:"adım", lineage:"Veri akışı", dataFlow:"Veri akışı", model:"Mantıksal model", kpis:"KPI tanımları" },
  }[language];

  const [
    menuOpen,
    setMenuOpen,
  ] = useState(false);

  return (
    <aside className="artifact-explorer">
      <div className="artifact-explorer-title">
        <div>
          <span>
            {ui.workspace}
          </span>

          <strong>
            {workspaceTitle}
          </strong>
        </div>

        <button
          type="button"
          className="artifact-add-button"
          onClick={() => {
            setMenuOpen(
              (previous) =>
                !previous
            );
          }}
          aria-label="Create workspace artifact"
        >
          <Plus
            size={15}
            aria-hidden="true"
          />
        </button>

        {menuOpen && (
          <div className="artifact-new-menu">
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onCreateNotebook();
              }}
            >
              <NotebookTabs size={14} />
              {ui.newNotebook}
            </button>

            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onOpenSource();
              }}
            >
              <Database size={14} />
              {ui.source}
            </button>

            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onViewChange(
                  "pipeline"
                );
              }}
            >
              <GitBranch size={14} />
              {ui.pipeline}
            </button>

            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onOpenValidate();
              }}
            >
              <FileSpreadsheet
                size={14}
              />
              {ui.processed}
            </button>
          </div>
        )}
      </div>

      <div className="artifact-section">
        <span className="artifact-section-label">
          {ui.data}
        </span>

        <button
          type="button"
          className={
            activeView === "explorer"
              ? "artifact-item active"
              : "artifact-item"
          }
          onClick={() =>
            onViewChange(
              "explorer"
            )
          }
        >
          <Database
            size={14}
            aria-hidden="true"
          />

          <div>
            <strong>
              {datasetFilename ??
                ui.raw}
            </strong>
            <span>
              {ui.rawReadOnly}
            </span>
          </div>
        </button>

        <button
          type="button"
          className={
            activeView === "explorer"
              ? "artifact-item active"
              : "artifact-item"
          }
          onClick={() =>
            onViewChange(
              "explorer"
            )
          }
        >
          <FlaskConical
            size={14}
            aria-hidden="true"
          />

          <div>
            <strong>
              {ui.development}
            </strong>
            <span>
              {developmentRows ?? 0}
              {" "}{ui.rows}
            </span>
          </div>
        </button>

        {processedDatasets.map(
          (dataset) => (
            <div
              className="artifact-item static"
              key={
                dataset.dataset_id
              }
            >
              <FileSpreadsheet
                size={14}
                aria-hidden="true"
              />

              <div>
                <strong>
                  {dataset.name}
                </strong>
                <span>
                  Processed ·{" "}
                  {dataset.row_count}
                  {" "}{ui.rows}
                </span>
              </div>
            </div>
          )
        )}
      </div>

      <div className="artifact-section">
        <span className="artifact-section-label">
          {ui.notebooks}
        </span>

        {notebooks.map(
          (notebook) => (
            <button
              type="button"
              key={
                notebook.notebook_id
              }
              className={
                activeView ===
                  "notebook" &&
                selectedNotebookId ===
                  notebook.notebook_id
                  ? "artifact-item active"
                  : "artifact-item"
              }
              onClick={() => {
                onNotebookSelect(
                  notebook.notebook_id
                );

                onViewChange(
                  "notebook"
                );
              }}
            >
              <NotebookTabs
                size={14}
                aria-hidden="true"
              />

              <div>
                <strong>
                  {notebook.name}
                </strong>
                <span>
                  {ui.pythonNotebook}
                </span>
              </div>
            </button>
          )
        )}

        {notebooks.length === 0 && (
          <button
            type="button"
            className="artifact-empty-action"
            onClick={
              onCreateNotebook
            }
          >
            + Create notebook
          </button>
        )}
      </div>

      <div className="artifact-section">
        <span className="artifact-section-label">
          {ui.build}
        </span>

        <button
          type="button"
          className={
            activeView === "pipeline"
              ? "artifact-item active"
              : "artifact-item"
          }
          onClick={() =>
            onViewChange(
              "pipeline"
            )
          }
        >
          <GitBranch
            size={14}
            aria-hidden="true"
          />

          <div>
            <strong>
              {ui.pipeline}
            </strong>
            <span>
              {pipelineOperationCount}
              {" "}{ui.steps}
            </span>
          </div>
        </button>

        <button
          type="button"
          className={
            activeView === "lineage"
              ? "artifact-item active"
              : "artifact-item"
          }
          onClick={() =>
            onViewChange(
              "lineage"
            )
          }
        >
          <Boxes
            size={14}
            aria-hidden="true"
          />

          <div>
            <strong>
              {ui.lineage}
            </strong>
            <span>
              {ui.dataFlow}
            </span>
          </div>
        </button>

        {hasModel && (
          <div className="artifact-item static">
            <Table2
              size={14}
              aria-hidden="true"
            />

            <div>
              <strong>
                {ui.model}
              </strong>
              <span>
                Model artifact
              </span>
            </div>
          </div>
        )}

        {kpiCount > 0 && (
          <div className="artifact-item static">
            <span className="artifact-kpi-icon">
              K
            </span>

            <div>
              <strong>
                {ui.kpis}
              </strong>
              <span>
                {kpiCount}
                {" "}KPIs
              </span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default WorkspaceArtifactExplorer;
