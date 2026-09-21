import { useState } from "react";

type OperationType =
  | "clean"
  | "transform"
  | "schema"
  | "business_rule"
  | "enrichment"
  | "custom";

type CreatedWorkbenchOperation = {
  operation_id: string;

  title: string;
  goal: string;

  operation_type: OperationType;

  origin:
    | "data_quality"
    | "project_requirement"
    | "user";

  status:
    | "pending"
    | "active"
    | "completed";

  source_columns: string[];
  expected_columns: string[];

  code: string | null;

  finding_index: number | null;

  rollback_version_number: number | null;

  result_version_id: string | null;
};

type Props = {
  workspaceId: string;

  onCreated: (
    operation: CreatedWorkbenchOperation
  ) => void;
};

function AddWorkbenchOperationForm({
  workspaceId,
  onCreated,
}: Props) {
  const [open, setOpen] =
    useState(false);

  const [title, setTitle] =
    useState("");

  const [goal, setGoal] =
    useState("");

  const [operationType, setOperationType] =
    useState<OperationType>(
      "transform"
    );

  const [sourceColumns, setSourceColumns] =
    useState("");

  const [
    expectedColumns,
    setExpectedColumns,
  ] = useState("");

  const [saving, setSaving] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  async function createOperation() {
    if (
      !title.trim() ||
      !goal.trim()
    ) {
      setError(
        "Title ve goal gerekli."
      );

      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await fetch(
        (
          `http://127.0.0.1:8000/workspaces/` +
          `demo-learner/${workspaceId}` +
          `/workbench/operations`
        ),
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            title:
              title.trim(),

            goal:
              goal.trim(),

            operation_type:
              operationType,

            source_columns:
              sourceColumns
                .split(",")
                .map(
                  (column) =>
                    column.trim()
                )
                .filter(Boolean),

            expected_columns:
              expectedColumns
                .split(",")
                .map(
                  (column) =>
                    column.trim()
                )
                .filter(Boolean),
          }),
        }
      );

      if (!response.ok) {
        const data =
          await response.json();

        throw new Error(
          data.detail ||
            "Transformation eklenemedi."
        );
      }

      const operation:
        CreatedWorkbenchOperation =
          await response.json();

      onCreated(
        operation
      );

      setTitle("");
      setGoal("");
      setSourceColumns("");
      setExpectedColumns("");
      setOperationType(
        "transform"
      );

      setOpen(false);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Transformation eklenemedi."
      );
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <div
        style={{
          marginBottom: "16px",
        }}
      >
        <button
          type="button"
          className="new-workspace-button"
          onClick={() => {
            setOpen(true);
          }}
        >
          + Add transformation
        </button>
      </div>
    );
  }

  return (
    <div
      className="workspace-version-history"
    >
      <div className="workspace-form-section">
        <label className="workspace-form-label">
          Title
        </label>

        <input
          className="workspace-form-input"
          value={title}
          placeholder="Create age_group"
          onChange={(event) => {
            setTitle(
              event.target.value
            );
          }}
        />
      </div>

      <div className="workspace-form-section">
        <label className="workspace-form-label">
          Goal
        </label>

        <textarea
          className="workspace-form-textarea small"
          value={goal}
          placeholder="Create an age category from age."
          onChange={(event) => {
            setGoal(
              event.target.value
            );
          }}
        />
      </div>

      <div className="workspace-form-section">
        <label className="workspace-form-label">
          Type
        </label>

        <select
          className="workspace-form-select"
          value={operationType}
          onChange={(event) => {
            setOperationType(
              event.target
                .value as OperationType
            );
          }}
        >
          <option value="transform">
            Transform
          </option>

          <option value="clean">
            Clean
          </option>

          <option value="schema">
            Schema
          </option>

          <option value="business_rule">
            Business rule
          </option>

          <option value="enrichment">
            Enrichment
          </option>

          <option value="custom">
            Custom
          </option>
        </select>
      </div>

      <div className="workspace-form-section">
        <label className="workspace-form-label">
          Source columns
        </label>

        <input
          className="workspace-form-input"
          value={sourceColumns}
          placeholder="age"
          onChange={(event) => {
            setSourceColumns(
              event.target.value
            );
          }}
        />

        <p className="workspace-field-help">
          Birden fazla kolon varsa
          virgülle ayır.
        </p>
      </div>

      <div className="workspace-form-section">
        <label className="workspace-form-label">
          Expected columns
        </label>

        <input
          className="workspace-form-input"
          value={expectedColumns}
          placeholder="age_group"
          onChange={(event) => {
            setExpectedColumns(
              event.target.value
            );
          }}
        />
      </div>

      {error && (
        <div className="workspace-form-error">
          {error}
        </div>
      )}

      <div className="workspace-form-actions">
        <button
          type="button"
          className="workspace-version-restore"
          disabled={saving}
          onClick={() => {
            setOpen(false);
            setError(null);
          }}
        >
          Cancel
        </button>

        <button
          type="button"
          className="new-workspace-button"
          disabled={
            saving ||
            !title.trim() ||
            !goal.trim()
          }
          onClick={() => {
            void createOperation();
          }}
        >
          {saving
            ? "Adding..."
            : "Add transformation"}
        </button>
      </div>
    </div>
  );
}

export default AddWorkbenchOperationForm;