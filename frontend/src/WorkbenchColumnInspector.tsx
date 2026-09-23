import { useEffect, useState } from "react";

import {
  prepareColumnAction,
  type ColumnActionDraft,
  type ColumnActionKind,
} from "./workbenchColumnActions";

type Props = {
  column: string | null;
  disabledReason?: string | null;
  onClose: () => void;
  onPrepare: (draft: ColumnActionDraft) => Promise<boolean>;
};

function WorkbenchColumnInspector({
  column,
  disabledReason,
  onClose,
  onPrepare,
}: Props) {
  const [action, setAction] = useState<ColumnActionKind>("rename");
  const [newName, setNewName] = useState("");
  const [dataType, setDataType] =
    useState<"string" | "integer" | "float" | "datetime">("string");
  const [fillStrategy, setFillStrategy] =
    useState<"value" | "mean" | "median" | "mode" | "zero">("value");
  const [fillValue, setFillValue] = useState("");
  const [oldValue, setOldValue] = useState("");
  const [newValue, setNewValue] = useState("");
  const [derivedName, setDerivedName] = useState("");
  const [derivedOperation, setDerivedOperation] =
    useState<"copy" | "uppercase" | "lowercase" | "add" | "multiply">("copy");
  const [derivedValue, setDerivedValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);

  useEffect(() => {
    setError(null);
    setNewName("");
    setFillValue("");
    setOldValue("");
    setNewValue("");
    setDerivedName("");
    setDerivedValue("");
  }, [column]);

  if (!column) return null;

  const selectedColumn = column;

  async function handlePrepare() {
    setError(null);

    try {
      const draft: ColumnActionDraft = {
        action,
        column: selectedColumn,
        newName,
        dataType,
        fillStrategy,
        fillValue,
        oldValue,
        newValue,
        derivedName,
        derivedOperation,
        derivedValue,
      };

      prepareColumnAction(draft);

      setPreparing(true);
      const success = await onPrepare(draft);

      if (success) onClose();
    } catch (prepareError) {
      setError(
        prepareError instanceof Error
          ? prepareError.message
          : "Column action could not be prepared."
      );
    } finally {
      setPreparing(false);
    }
  }

  return (
    <aside className="column-inspector">
      <div className="column-inspector-header">
        <div>
          <span className="workspace-overview-label">COLUMN ACTION</span>
          <h4>{column}</h4>
        </div>

        <button type="button" onClick={onClose} aria-label="Close column inspector">
          ×
        </button>
      </div>

      {disabledReason && (
        <div className="column-inspector-warning">{disabledReason}</div>
      )}

      <label className="column-inspector-field">
        <span>Action</span>
        <select
          value={action}
          onChange={(event) => {
            setAction(event.target.value as ColumnActionKind);
            setError(null);
          }}
        >
          <option value="rename">Rename column</option>
          <option value="remove">Remove column</option>
          <option value="change_type">Change data type</option>
          <option value="fill_missing">Fill missing values</option>
          <option value="replace_values">Replace values</option>
          <option value="derived">Add derived column</option>
        </select>
      </label>

      {action === "rename" && (
        <label className="column-inspector-field">
          <span>New name</span>
          <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="new_column_name" />
        </label>
      )}

      {action === "change_type" && (
        <label className="column-inspector-field">
          <span>Target type</span>
          <select value={dataType} onChange={(e) => setDataType(e.target.value as typeof dataType)}>
            <option value="string">String</option>
            <option value="integer">Integer</option>
            <option value="float">Float</option>
            <option value="datetime">Datetime</option>
          </select>
        </label>
      )}

      {action === "fill_missing" && (
        <>
          <label className="column-inspector-field">
            <span>Strategy</span>
            <select value={fillStrategy} onChange={(e) => setFillStrategy(e.target.value as typeof fillStrategy)}>
              <option value="value">Specific value</option>
              <option value="mean">Mean</option>
              <option value="median">Median</option>
              <option value="mode">Mode</option>
              <option value="zero">Zero</option>
            </select>
          </label>

          {fillStrategy === "value" && (
            <label className="column-inspector-field">
              <span>Fill value</span>
              <input value={fillValue} onChange={(e) => setFillValue(e.target.value)} placeholder="Unknown" />
            </label>
          )}
        </>
      )}

      {action === "replace_values" && (
        <div className="column-inspector-two">
          <label className="column-inspector-field">
            <span>Old value</span>
            <input value={oldValue} onChange={(e) => setOldValue(e.target.value)} />
          </label>
          <label className="column-inspector-field">
            <span>New value</span>
            <input value={newValue} onChange={(e) => setNewValue(e.target.value)} />
          </label>
        </div>
      )}

      {action === "derived" && (
        <>
          <label className="column-inspector-field">
            <span>New column</span>
            <input value={derivedName} onChange={(e) => setDerivedName(e.target.value)} placeholder="derived_column" />
          </label>

          <label className="column-inspector-field">
            <span>Operation</span>
            <select value={derivedOperation} onChange={(e) => setDerivedOperation(e.target.value as typeof derivedOperation)}>
              <option value="copy">Copy source</option>
              <option value="uppercase">Uppercase text</option>
              <option value="lowercase">Lowercase text</option>
              <option value="add">Add value</option>
              <option value="multiply">Multiply by value</option>
            </select>
          </label>

          {(derivedOperation === "add" || derivedOperation === "multiply") && (
            <label className="column-inspector-field">
              <span>Value</span>
              <input value={derivedValue} onChange={(e) => setDerivedValue(e.target.value)} placeholder="10" />
            </label>
          )}
        </>
      )}

      {error && <div className="workspace-form-error">{error}</div>}

      <div className="column-inspector-actions">
        <button type="button" className="secondary-button" onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className="new-workspace-button"
          disabled={preparing || Boolean(disabledReason)}
          onClick={() => void handlePrepare()}
        >
          {preparing ? "Preparing..." : "Prepare transformation"}
        </button>
      </div>
    </aside>
  );
}

export default WorkbenchColumnInspector;
