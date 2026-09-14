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