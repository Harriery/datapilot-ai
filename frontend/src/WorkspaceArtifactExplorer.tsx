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
  const [
    menuOpen,
    setMenuOpen,
  ] = useState(false);

  return (
    <aside className="artifact-explorer">
      <div className="artifact-explorer-title">
        <div>
          <span>
            WORKSPACE
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
              New notebook
            </button>

            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onOpenSource();
              }}
            >
              <Database size={14} />
              Dataset / source
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
              Pipeline
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
              Processed dataset
            </button>
          </div>
        )}
      </div>

      <div className="artifact-section">
        <span className="artifact-section-label">
          DATA
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
                "Raw source"}
            </strong>
            <span>
              Raw · read-only
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
              Development dataset
            </strong>
            <span>
              {developmentRows ?? 0}
              {" "}rows
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
                  {" "}rows
                </span>
              </div>
            </div>
          )
        )}
      </div>

      <div className="artifact-section">
        <span className="artifact-section-label">
          NOTEBOOKS
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
                  Python notebook
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
          BUILD
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
              Cleaning pipeline
            </strong>
            <span>
              {pipelineOperationCount}
              {" "}steps
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
              Lineage
            </strong>
            <span>
              Data flow
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
                Logical model
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
                KPI definitions
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
