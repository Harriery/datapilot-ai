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


export async function runNotebookCells(
  codes: string[],
  inputRows: Record<string, unknown>[],
  targetIndex: number,
): Promise<{
  rows: Record<string, unknown>[];
  output: string;
}> {
  const pyodide = await getPyodide();

  if (!pandasLoaded) {
    await pyodide.loadPackage("pandas");
    pandasLoaded = true;
  }

  pyodide.globals.set(
    "input_json",
    JSON.stringify(inputRows)
  );

  pyodide.globals.set(
    "notebook_codes_json",
    JSON.stringify(
      codes.slice(
        0,
        targetIndex + 1
      )
    )
  );

  try {
    const result =
      await pyodide.runPythonAsync(`
import contextlib
import io
import json
import pandas as pd

_df = pd.DataFrame(
    json.loads(input_json)
)

_codes = json.loads(
    notebook_codes_json
)

_target_stdout = ""

_env = {
    "pd": pd,
    "df": _df,
    "__builtins__": __builtins__,
}

for _index, _code in enumerate(_codes):
    _stdout = io.StringIO()

    with contextlib.redirect_stdout(
        _stdout
    ):
        exec(
            _code,
            _env,
            _env,
        )

    if _index == len(_codes) - 1:
        _target_stdout = (
            _stdout.getvalue()
        )

_df = _env.get("df")

if not isinstance(_df, pd.DataFrame):
    raise TypeError(
        "Notebook code must leave df as a pandas DataFrame."
    )

json.dumps({
    "rows": json.loads(
        _df.to_json(
            orient="records"
        )
    ),
    "output": _target_stdout,
})
`);

    return JSON.parse(
      String(result)
    );
  } finally {
    pyodide.globals.delete(
      "input_json"
    );

    pyodide.globals.delete(
      "notebook_codes_json"
    );
  }
}
