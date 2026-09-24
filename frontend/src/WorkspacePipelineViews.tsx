import {
  CheckCircle2,
  CircleDashed,
  GitBranch,
  ShieldAlert,
} from "lucide-react";

type Operation = {
  operation_id: string;
  title: string;

  status:
    | "pending"
    | "active"
    | "completed";

  origin:
    | "data_quality"
    | "project_requirement"
    | "user";

  code: string | null;

  pipeline_action:
    | {
        action: string;
      }
    | null;
};

type ProcessedDataset = {
  dataset_id: string;
  name: string;
};

type Props = {
  operations: Operation[];

  sourceName:
    | string
    | null
    | undefined;

  developmentRows:
    | number
    | null
    | undefined;

  processedDatasets:
    ProcessedDataset[];

  hasModel: boolean;
  kpiCount: number;

  onAddTransformation: () => void;

  developmentSampleEnabled?: boolean;
  canApplyFullDataset?: boolean;

  fullPipelineLoading?: boolean;
  fullPipelineError?: string | null;

  onApplyFullDataset?: () => void;
};

export function WorkspacePipelineView({
  operations,
  onAddTransformation,
  developmentSampleEnabled = false,
  canApplyFullDataset = false,
  fullPipelineLoading = false,
  fullPipelineError = null,
  onApplyFullDataset,
}: Props) {
  const replayable =
    operations.filter(
      (operation) =>
        operation.status ===
          "completed" &&
        operation.pipeline_action
    ).length;

  const blockers =
    operations.filter(
      (operation) =>
        operation.status !==
          "completed" ||
        !operation.pipeline_action
    );

  return (
    <div className="pipeline-workspace">
      <div className="pipeline-workspace-header">
        <div>
          <span>
            PIPELINE
          </span>

          <h3>
            Cleaning pipeline
          </h3>

          <p>
            Only structured completed steps can be replayed safely on the full dataset.
          </p>
        </div>

        <div className="pipeline-header-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={
              onAddTransformation
            }
          >
            + Add transformation
          </button>

          {developmentSampleEnabled &&
            onApplyFullDataset && (
            <button
              type="button"
              className="new-workspace-button"
              disabled={
                fullPipelineLoading ||
                !canApplyFullDataset
              }
              onClick={
                onApplyFullDataset
              }
            >
              {fullPipelineLoading
                ? "Applying..."
                : "Apply to full dataset"}
            </button>
          )}
        </div>
      </div>

      {developmentSampleEnabled &&
        !canApplyFullDataset && (
        <div className="pipeline-blocker-note">
          <ShieldAlert
            size={14}
          />

          Complete every step and convert experimental/custom notebook steps into structured actions before full-dataset replay.
        </div>
      )}

      {fullPipelineError && (
        <div className="workspace-form-error">
          {fullPipelineError}
        </div>
      )}

      <div className="pipeline-summary">
        <div>
          <strong>
            {operations.length}
          </strong>
          <span>Total steps</span>
        </div>

        <div>
          <strong>
            {replayable}
          </strong>
          <span>Replayable</span>
        </div>

        <div>
          <strong>
            {blockers.length}
          </strong>
          <span>Needs attention</span>
        </div>
      </div>

      <div className="pipeline-step-list">
        {operations.map(
          (operation, index) => (
            <div
              className="pipeline-step"
              key={
                operation.operation_id
              }
            >
              <div className="pipeline-step-order">
                {index + 1}
              </div>

              <div className="pipeline-step-main">
                <div>
                  <strong>
                    {operation.title}
                  </strong>

                  <span>
                    {operation.origin.replaceAll(
                      "_",
                      " "
                    )}
                  </span>
                </div>

                <div className="pipeline-step-badges">
                  <span
                    className={
                      `pipeline-status ${operation.status}`
                    }
                  >
                    {operation.status}
                  </span>

                  {operation.pipeline_action ? (
                    <span className="pipeline-replayable">
                      <CheckCircle2
                        size={12}
                      />
                      {
                        operation
                          .pipeline_action
                          .action
                      }
                    </span>
                  ) : (
                    <span className="pipeline-nonreplayable">
                      <ShieldAlert
                        size={12}
                      />
                      custom / experimental
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        )}

        {operations.length === 0 && (
          <div className="pipeline-empty">
            <GitBranch size={24} />

            <strong>
              No pipeline steps yet.
            </strong>

            <span>
              Add structured transformations from Explorer or experiment in a notebook first.
            </span>
          </div>
        )}
      </div>

      {blockers.length > 0 && (
        <div className="pipeline-blocker-note">
          <CircleDashed
            size={14}
          />

          Full-dataset replay stays blocked until every step is completed and has structured pipeline metadata.
        </div>
      )}
    </div>
  );
}

export function WorkspaceLineageView({
  sourceName,
  developmentRows,
  processedDatasets,
  hasModel,
  kpiCount,
  operations,
}: Props) {
  const nodes = [
    {
      label:
        sourceName ??
        "Raw source",
      meta:
        "Immutable source",
      kind:
        "source",
    },
    {
      label:
        "Development dataset",
      meta:
        `${developmentRows ?? 0} rows`,
      kind:
        "sample",
    },
    {
      label:
        "Cleaning pipeline",
      meta:
        `${operations.length} steps`,
      kind:
        "pipeline",
    },
    ...processedDatasets.map(
      (dataset) => ({
        label:
          dataset.name,
        meta:
          "Processed dataset",
        kind:
          "processed",
      })
    ),
    ...(hasModel
      ? [
          {
            label:
              "Logical model",
            meta:
              "Data Model",
            kind:
              "model",
          },
        ]
      : []),
    ...(kpiCount > 0
      ? [
          {
            label:
              "KPI definitions",
            meta:
              `${kpiCount} KPIs`,
            kind:
              "kpi",
          },
        ]
      : []),
  ];

  return (
    <div className="lineage-workspace">
      <div className="pipeline-workspace-header">
        <div>
          <span>
            LINEAGE
          </span>

          <h3>
            Workspace data flow
          </h3>

          <p>
            Follow how the immutable source becomes development data, pipeline outputs and BI artifacts.
          </p>
        </div>
      </div>

      <div className="lineage-flow">
        {nodes.map(
          (node, index) => (
            <div
              className="lineage-flow-fragment"
              key={
                `${node.kind}-${node.label}`
              }
            >
              <div
                className={
                  `lineage-node ${node.kind}`
                }
              >
                <strong>
                  {node.label}
                </strong>

                <span>
                  {node.meta}
                </span>
              </div>

              {index <
                nodes.length - 1 && (
                <div className="lineage-arrow">
                  ↓
                </div>
              )}
            </div>
          )
        )}
      </div>
    </div>
  );
}
