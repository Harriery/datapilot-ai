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
};

export async function runNotebookCells(
  codes: string[],
  inputRows: Record<string, unknown>[],
  targetIndex: number,
): Promise<NotebookCellRunResult> {
  const results = await runNotebookAllCells(
    codes.slice(0, targetIndex + 1),
    inputRows,
  );

  return results[targetIndex] ?? {
    rows: [],
    output: "",
    expressionKind: "none",
  };
}

export async function runNotebookAllCells(
  codes: string[],
  inputRows: Record<string, unknown>[],
): Promise<NotebookCellRunResult[]> {
  const pyodide = await getPyodide();

  if (!pandasLoaded) {
    await pyodide.loadPackage("pandas");
    pandasLoaded = true;
  }

  pyodide.globals.set("input_json", JSON.stringify(inputRows));
  pyodide.globals.set("notebook_codes_json", JSON.stringify(codes));

  try {
    const result = await pyodide.runPythonAsync(`
import ast
import contextlib
import io
import json
import pandas as pd

_df = pd.DataFrame(json.loads(input_json))
_codes = json.loads(notebook_codes_json)
_env = {"pd": pd, "df": _df, "__builtins__": __builtins__}
_results = []

for _code in _codes:
    _stdout = io.StringIO()
    _expression_kind = "none"

    with contextlib.redirect_stdout(_stdout):
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
    })

json.dumps(_results)
`);

    return JSON.parse(String(result));
  } finally {
    pyodide.globals.delete("input_json");
    pyodide.globals.delete("notebook_codes_json");
  }
}
