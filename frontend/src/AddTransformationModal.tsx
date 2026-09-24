import {
  useEffect,
  useState,
} from "react";

import type {
  AppLanguage,
} from "./i18n";


export type WorkbenchOperationType =
  | "clean"
  | "transform"
  | "schema"
  | "business_rule"
  | "enrichment"
  | "custom";


export type WorkbenchPipelineActionData = {
  action:
    | "rename"
    | "remove"
    | "change_type"
    | "fill_missing"
    | "replace_values"
    | "derived";

  column: string;

  new_name?: string | null;

  data_type?:
    | "string"
    | "integer"
    | "float"
    | "datetime"
    | null;

  fill_strategy?:
    | "value"
    | "mean"
    | "median"
    | "mode"
    | "zero"
    | null;

  fill_value?:
    | string
    | number
    | boolean
    | null;

  old_value?:
    | string
    | number
    | boolean
    | null;

  new_value?:
    | string
    | number
    | boolean
    | null;

  derived_name?: string | null;

  derived_operation?:
    | "copy"
    | "uppercase"
    | "lowercase"
    | "add"
    | "multiply"
    | null;

  derived_value?:
    | string
    | number
    | boolean
    | null;
};


export type WorkbenchOperationCreateData = {
  title: string;
  goal: string;

  operation_type:
    WorkbenchOperationType;

  source_columns: string[];
  expected_columns: string[];

  pipeline_action?:
    WorkbenchPipelineActionData | null;

  draft_code?: string | null;
};


type AddTransformationModalProps = {
  open: boolean;
  language: AppLanguage;

  loading: boolean;
  error: string | null;

  onClose: () => void;

  onSubmit: (
    data: WorkbenchOperationCreateData
  ) => Promise<boolean>;
};


function splitColumns(
  value: string
): string[] {
  return value
    .split(",")
    .map((column) => column.trim())
    .filter(Boolean);
}


function AddTransformationModal({
  open,
  language,
  loading,
  error,
  onClose,
  onSubmit,
}: AddTransformationModalProps) {

  const [title, setTitle] =
    useState("");

  const [goal, setGoal] =
    useState("");

  const [
    operationType,
    setOperationType,
  ] = useState<WorkbenchOperationType>(
    "transform"
  );

  const [
    sourceColumns,
    setSourceColumns,
  ] = useState("");

  const [
    expectedColumns,
    setExpectedColumns,
  ] = useState("");


  const copy =
    language === "tr"
      ? {
          eyebrow:
            "YENİ DÖNÜŞÜM",

          title:
            "Workbench işlemi ekle",

          description:
            "Dataset üzerinde yapmak istediğin dönüşümü tanımla.",

          titleLabel:
            "Başlık",

          titlePlaceholder:
            "Örn. age_group oluştur",

          goalLabel:
            "Amaç",

          goalPlaceholder:
            "Bu dönüşümün ne yapması gerektiğini açıkla.",

          typeLabel:
            "İşlem türü",

          sourceColumns:
            "Kaynak kolonlar",

          sourceColumnsPlaceholder:
            "age, country",

          expectedColumns:
            "Beklenen kolonlar",

          expectedColumnsPlaceholder:
            "age_group",

          columnsHint:
            "Birden fazla kolon varsa virgülle ayır.",

          cancel:
            "İptal",

          submit:
            "Dönüşüm ekle",

          submitting:
            "Ekleniyor...",
        }
      : {
          eyebrow:
            "NEW TRANSFORMATION",

          title:
            "Add workbench operation",

          description:
            "Define the transformation you want to apply to the dataset.",

          titleLabel:
            "Title",

          titlePlaceholder:
            "Example: Create age_group",

          goalLabel:
            "Goal",

          goalPlaceholder:
            "Describe what this transformation should achieve.",

          typeLabel:
            "Operation type",

          sourceColumns:
            "Source columns",

          sourceColumnsPlaceholder:
            "age, country",

          expectedColumns:
            "Expected columns",

          expectedColumnsPlaceholder:
            "age_group",

          columnsHint:
            "Separate multiple columns with commas.",

          cancel:
            "Cancel",

          submit:
            "Add transformation",

          submitting:
            "Adding...",
        };


  useEffect(() => {
    if (!open) {
      return;
    }

    document.body.style.overflow =
      "hidden";

    return () => {
      document.body.style.overflow =
        "";
    };
  }, [open]);


  if (!open) {
    return null;
  }


  async function handleSubmit() {
    if (
      !title.trim() ||
      !goal.trim()
    ) {
      return;
    }

    const success =
      await onSubmit({
        title: title.trim(),

        goal: goal.trim(),

        operation_type:
          operationType,

        source_columns:
          splitColumns(
            sourceColumns
          ),

        expected_columns:
          splitColumns(
            expectedColumns
          ),
      });

    if (!success) {
      return;
    }

    setTitle("");
    setGoal("");

    setOperationType(
      "transform"
    );

    setSourceColumns("");
    setExpectedColumns("");

    onClose();
  }


  return (
    <div
      className="workspace-modal-backdrop"
      onMouseDown={onClose}
    >
      <div
        className="workspace-modal"
        onMouseDown={(event) =>
          event.stopPropagation()
        }
      >
        <div className="workspace-modal-header">
          <div>
            <span className="workspace-overview-label">
              {copy.eyebrow}
            </span>

            <h3>
              {copy.title}
            </h3>

            <p>
              {copy.description}
            </p>
          </div>

          <button
            type="button"
            className="workspace-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>


        <div className="workspace-modal-body">

          <label className="workspace-modal-field">
            <span>
              {copy.titleLabel}
            </span>

            <input
              value={title}
              onChange={(event) =>
                setTitle(
                  event.target.value
                )
              }
              placeholder={
                copy.titlePlaceholder
              }
            />
          </label>


          <label className="workspace-modal-field">
            <span>
              {copy.goalLabel}
            </span>

            <textarea
              value={goal}
              onChange={(event) =>
                setGoal(
                  event.target.value
                )
              }
              placeholder={
                copy.goalPlaceholder
              }
              rows={4}
            />
          </label>


          <label className="workspace-modal-field">
            <span>
              {copy.typeLabel}
            </span>

            <select
              value={operationType}
              onChange={(event) => {
                  const value =
                    event.target.value as WorkbenchOperationType;
                            
                  setOperationType(value);
                }}
            >
              <option value="clean">
                Clean
              </option>

              <option value="transform">
                Transform
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
          </label>


          <div className="workspace-modal-columns">
            <label className="workspace-modal-field">
              <span>
                {copy.sourceColumns}
              </span>

              <input
                value={sourceColumns}
                onChange={(event) =>
                  setSourceColumns(
                    event.target.value
                  )
                }
                placeholder={
                  copy.sourceColumnsPlaceholder
                }
              />
            </label>


            <label className="workspace-modal-field">
              <span>
                {copy.expectedColumns}
              </span>

              <input
                value={
                  expectedColumns
                }
                onChange={(event) =>
                  setExpectedColumns(
                    event.target.value
                  )
                }
                placeholder={
                  copy.expectedColumnsPlaceholder
                }
              />
            </label>
          </div>

          <span className="workspace-modal-hint">
            {copy.columnsHint}
          </span>


          {error && (
            <div className="workspace-form-error">
              {error}
            </div>
          )}

        </div>


        <div className="workspace-modal-footer">
          <button
            type="button"
            className="secondary-button"
            onClick={onClose}
            disabled={loading}
          >
            {copy.cancel}
          </button>

          <button
            type="button"
            className="submit-button"
            onClick={() => {
              void handleSubmit();
            }}
            disabled={
              loading ||
              !title.trim() ||
              !goal.trim()
            }
          >
            {loading
              ? copy.submitting
              : copy.submit}
          </button>
        </div>
      </div>
    </div>
  );
}


export default AddTransformationModal;