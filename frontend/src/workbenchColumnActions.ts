import type {
  WorkbenchOperationCreateData,
  WorkbenchOperationType,
  WorkbenchPipelineActionData,
} from "./AddTransformationModal";

export type ColumnActionKind =
  | "rename"
  | "remove"
  | "change_type"
  | "fill_missing"
  | "replace_values"
  | "derived";

export type ColumnActionDraft = {
  action: ColumnActionKind;
  column: string;
  newName?: string;
  dataType?: "string" | "integer" | "float" | "datetime";
  fillStrategy?: "value" | "mean" | "median" | "mode" | "zero";
  fillValue?: string;
  oldValue?: string;
  newValue?: string;
  derivedName?: string;
  derivedOperation?: "copy" | "uppercase" | "lowercase" | "add" | "multiply";
  derivedValue?: string;
};

export type PreparedColumnAction = {
  operation: WorkbenchOperationCreateData;
  code: string;
  pipelineAction:
    WorkbenchPipelineActionData;
};

function pyString(value: string): string {
  return JSON.stringify(value);
}

function parseLiteral(
  value: string
): string | number | boolean | null {
  const trimmed = value.trim();

  if (!trimmed) return "";

  if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    return Number(trimmed);
  }

  if (trimmed.toLowerCase() === "true") {
    return true;
  }

  if (trimmed.toLowerCase() === "false") {
    return false;
  }

  if (["none", "null"].includes(trimmed.toLowerCase())) {
    return null;
  }

  return trimmed;
}

function pyLiteral(value: string): string {
  const parsed = parseLiteral(value);

  if (parsed === null) return "None";
  if (typeof parsed === "number") return String(parsed);
  if (typeof parsed === "boolean") return parsed ? "True" : "False";

  return pyString(parsed);
}

function operationTypeFor(
  action: ColumnActionKind
): WorkbenchOperationType {
  if (["rename", "remove", "change_type"].includes(action)) {
    return "schema";
  }

  if (["fill_missing", "replace_values"].includes(action)) {
    return "clean";
  }

  return "enrichment";
}

export function prepareColumnAction(
  draft: ColumnActionDraft
): PreparedColumnAction {
  const column = draft.column.trim();

  if (!column) {
    throw new Error("Select a column first.");
  }

  let title = "";
  let goal = "";
  let code = "";
  let expectedColumns = [column];

  const pipelineAction:
    WorkbenchPipelineActionData = {
      action: draft.action,
      column,
    };

  if (draft.action === "rename") {
    const newName = draft.newName?.trim();

    if (!newName) {
      throw new Error("Enter the new column name.");
    }

    title = `Rename ${column} to ${newName}`;
    goal = "Rename the column without changing its values.";
    code = `df = df.rename(columns={${pyString(column)}: ${pyString(newName)}})`;
    expectedColumns = [newName];
    pipelineAction.new_name = newName;
  }

  if (draft.action === "remove") {
    title = `Remove ${column}`;
    goal = `Remove ${column} from the working dataset.`;
    code = `df = df.drop(columns=[${pyString(column)}])`;
    expectedColumns = [];
  }

  if (draft.action === "change_type") {
    if (!draft.dataType) {
      throw new Error("Choose a target data type.");
    }

    title = `Change ${column} type to ${draft.dataType}`;
    goal = `Convert ${column} to ${draft.dataType} with a reproducible transformation.`;

    const targetCode = {
      string: `df[${pyString(column)}] = df[${pyString(column)}].astype("string")`,
      integer: `df[${pyString(column)}] = pd.to_numeric(df[${pyString(column)}], errors="coerce").astype("Int64")`,
      float: `df[${pyString(column)}] = pd.to_numeric(df[${pyString(column)}], errors="coerce")`,
      datetime: `df[${pyString(column)}] = pd.to_datetime(df[${pyString(column)}], errors="coerce")`,
    };

    code = targetCode[draft.dataType];
    pipelineAction.data_type =
      draft.dataType;
  }

  if (draft.action === "fill_missing") {
    if (!draft.fillStrategy) {
      throw new Error("Choose a fill strategy.");
    }

    title = `Fill missing values in ${column}`;
    goal = `Resolve missing values in ${column} using the selected strategy.`;

    const strategyCode = {
      value: `df[${pyString(column)}] = df[${pyString(column)}].fillna(${pyLiteral(draft.fillValue ?? "")})`,
      mean: `df[${pyString(column)}] = df[${pyString(column)}].fillna(df[${pyString(column)}].mean())`,
      median: `df[${pyString(column)}] = df[${pyString(column)}].fillna(df[${pyString(column)}].median())`,
      mode: `df[${pyString(column)}] = df[${pyString(column)}].fillna(df[${pyString(column)}].mode().iloc[0])`,
      zero: `df[${pyString(column)}] = df[${pyString(column)}].fillna(0)`,
    };

    code = strategyCode[draft.fillStrategy];

    pipelineAction.fill_strategy =
      draft.fillStrategy;

    if (draft.fillStrategy === "value") {
      pipelineAction.fill_value =
        parseLiteral(
          draft.fillValue ?? ""
        );
    }
  }

  if (draft.action === "replace_values") {
    if (draft.oldValue === undefined || draft.newValue === undefined) {
      throw new Error("Enter both old and new values.");
    }

    title = `Replace values in ${column}`;
    goal = `Replace a specific value in ${column} while preserving other values.`;
    code = `df[${pyString(column)}] = df[${pyString(column)}].replace(${pyLiteral(draft.oldValue)}, ${pyLiteral(draft.newValue)})`;

    pipelineAction.old_value =
      parseLiteral(draft.oldValue);

    pipelineAction.new_value =
      parseLiteral(draft.newValue);
  }

  if (draft.action === "derived") {
    const derivedName = draft.derivedName?.trim();
    const operation = draft.derivedOperation;

    if (!derivedName || !operation) {
      throw new Error("Enter the derived column name and operation.");
    }

    title = `Create derived column ${derivedName}`;
    goal = `Create ${derivedName} from ${column} using a reusable transformation.`;
    expectedColumns = [column, derivedName];

    pipelineAction.derived_name =
      derivedName;

    pipelineAction.derived_operation =
      operation;

    if (operation === "copy") {
      code = `df[${pyString(derivedName)}] = df[${pyString(column)}]`;
    } else if (operation === "uppercase") {
      code = `df[${pyString(derivedName)}] = df[${pyString(column)}].astype("string").str.upper()`;
    } else if (operation === "lowercase") {
      code = `df[${pyString(derivedName)}] = df[${pyString(column)}].astype("string").str.lower()`;
    } else {
      const operator = operation === "add" ? "+" : "*";
      code = `df[${pyString(derivedName)}] = df[${pyString(column)}] ${operator} ${pyLiteral(draft.derivedValue ?? "")}`;

      pipelineAction.derived_value =
        parseLiteral(
          draft.derivedValue ?? ""
        );
    }
  }

  if (!code) {
    throw new Error("Column action could not be prepared.");
  }

  return {
    operation: {
      title,
      goal,
      operation_type: operationTypeFor(draft.action),
      source_columns: [column],
      expected_columns: expectedColumns,
      pipeline_action:
        pipelineAction,
    },
    code,
    pipelineAction,
  };
}
