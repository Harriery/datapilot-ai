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