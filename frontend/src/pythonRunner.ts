import {
  loadPyodide,
  version as pyodideVersion,
  type PyodideInterface,
} from "pyodide";

let pyodideInstance: PyodideInterface | null = null;
let pandasLoaded = false;

async function getPyodide() {
  if (!pyodideInstance) {
    pyodideInstance = await loadPyodide({
      indexURL: `https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/`,
    });
  }

  return pyodideInstance;
}

export async function runDataFrameTransformation(
  code: string,
  inputRows: Record<string, unknown>[]
) {
  const pyodide = await getPyodide();

  if (!pandasLoaded) {
    await pyodide.loadPackage("pandas");
    pandasLoaded = true;
  }

  pyodide.globals.set(
    "input_json",
    JSON.stringify(inputRows)
  );

  try {
    const result = await pyodide.runPythonAsync(`
import json
import pandas as pd

df = pd.DataFrame(json.loads(input_json))

${code}

df.to_json(orient="records")
`);

    return JSON.parse(String(result));
  } finally {
    pyodide.globals.delete("input_json");
  }
}

export async function runPythonCode(
  code: string
): Promise<string> {
  const pyodide = await getPyodide();

  pyodide.globals.set("user_code", code);

  try {
    const result = await pyodide.runPythonAsync(`
import io
import contextlib

_stdout = io.StringIO()

with contextlib.redirect_stdout(_stdout):
    exec(user_code, globals())

_stdout.getvalue()
`);

    return String(result).trim();
  } finally {
    pyodide.globals.delete("user_code");
  }
}


export type NotebookCellRunResult = {
  rows: Record<string, unknown>[];
  output: string;
  expressionKind: "dataframe" | "scalar" | "none";
  success: boolean;
};

export class NotebookCellExecutionError extends Error {
  failedIndex: number;
  result: NotebookCellRunResult;

  constructor(
    failedIndex: number,
    result: NotebookCellRunResult,
  ) {
    super(result.output || "Notebook cell failed.");
    this.name = "NotebookCellExecutionError";
    this.failedIndex = failedIndex;
    this.result = result;
  }
}

export type NotebookExecutableCell = string | { code: string; cell_type?: "python" | "sql" | "markdown" };

export async function runNotebookCells(
  codes: NotebookExecutableCell[],
  inputRows: Record<string, unknown>[],
  targetIndex: number,
): Promise<NotebookCellRunResult> {
  const results = await runNotebookAllCells(
    codes.slice(0, targetIndex + 1),
    inputRows,
  );

  const failedIndex = results.findIndex(
    (item) => item.success === false
  );

  if (failedIndex >= 0) {
    throw new NotebookCellExecutionError(
      failedIndex,
      results[failedIndex],
    );
  }

  return results[targetIndex] ?? {
    rows: [],
    output: "",
    expressionKind: "none",
    success: true,
  };
}

export async function runNotebookAllCells(
  codes: NotebookExecutableCell[],
  inputRows: Record<string, unknown>[],
): Promise<NotebookCellRunResult[]> {
  const pyodide = await getPyodide();

  if (!pandasLoaded) {
    await pyodide.loadPackage("pandas");
    pandasLoaded = true;
  }

  pyodide.globals.set("input_json", JSON.stringify(inputRows));
  pyodide.globals.set("notebook_codes_json", JSON.stringify(codes.map((cell) => typeof cell === "string" ? { code: cell, cell_type: "python" } : cell)));

  try {
    const result = await pyodide.runPythonAsync(`
import ast
import contextlib
import io
import json
import pandas as pd
import sqlite3

_df = pd.DataFrame(json.loads(input_json))
_codes = json.loads(notebook_codes_json)
_env = {"pd": pd, "df": _df, "__builtins__": __builtins__}
_results = []

for _cell in _codes:
    _code = _cell.get("code", "")
    _language = _cell.get("cell_type", "python")
    _stdout = io.StringIO()
    _expression_kind = "none"

    try:
        with contextlib.redirect_stdout(_stdout):
            if _language == "markdown":
                _expression_kind = "scalar"
                print(_code)
                _results.append({
                    "rows": [], "output": _stdout.getvalue(),
                    "expressionKind": "scalar", "success": True,
                })
                continue
            if _language == "sql":
                _sql = _code.strip().rstrip(";").strip()
                if not _sql.upper().startswith(("SELECT ", "WITH ", "SELECT\\n", "WITH\\n")):
                    raise ValueError("Only read-only SELECT and WITH queries are supported.")
                _connection = sqlite3.connect(":memory:")
                try:
                    _working = _env.get("df")
                    if not isinstance(_working, pd.DataFrame):
                        raise TypeError("df must be a pandas DataFrame.")
                    _working.to_sql("df", _connection, index=False, if_exists="replace")
                    _connection.set_authorizer(
                        lambda action, arg1, arg2, db, source:
                        sqlite3.SQLITE_OK if action in (
                            sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
                            sqlite3.SQLITE_FUNCTION
                        ) else sqlite3.SQLITE_DENY
                    )
                    _query_df = pd.read_sql_query(_sql, _connection)
                    _expression_kind = "dataframe"
                    print(_query_df.head(10).to_string(index=False))
                finally:
                    _connection.close()
                _results.append({
                    "rows": json.loads(_query_df.head(200).to_json(orient="records")),
                    "output": _stdout.getvalue(),
                    "expressionKind": "dataframe", "success": True,
                })
                continue
            if _language != "python":
                raise ValueError("Unsupported notebook cell type.")
            _tree = ast.parse(_code, mode="exec")

            if _tree.body and isinstance(_tree.body[-1], ast.Expr):
                _prefix = ast.Module(body=_tree.body[:-1], type_ignores=[])
                if _prefix.body:
                    exec(compile(_prefix, "<notebook>", "exec"), _env, _env)

                _value = eval(
                    compile(ast.Expression(_tree.body[-1].value), "<notebook>", "eval"),
                    _env,
                    _env,
                )
                if _value is not None:
                    print(repr(_value))
                    _expression_kind = (
                        "dataframe"
                        if isinstance(_value, pd.DataFrame)
                        else "scalar"
                    )
            else:
                exec(compile(_tree, "<notebook>", "exec"), _env, _env)

        _df = _env.get("df")
        if not isinstance(_df, pd.DataFrame):
            raise TypeError("Notebook code must leave df as a pandas DataFrame.")

        _results.append({
            "rows": json.loads(_df.to_json(orient="records")),
            "output": _stdout.getvalue(),
            "expressionKind": _expression_kind,
            "success": True,
        })
    except Exception as _exc:
        _current_df = _env.get("df")
        _rows = (
            json.loads(_current_df.to_json(orient="records"))
            if isinstance(_current_df, pd.DataFrame)
            else []
        )
        _results.append({
            "rows": _rows,
            "output": f"{type(_exc).__name__}: {_exc}",
            "expressionKind": "none",
            "success": False,
        })
        break

json.dumps(_results)
`);

    return JSON.parse(String(result));
  } finally {
    pyodide.globals.delete("input_json");
    pyodide.globals.delete("notebook_codes_json");
  }
}
