import {
  loadPyodide,
  version as pyodideVersion,
} from "pyodide";

type ValidationFile = {
  path: string;
  content: string;
};

type ValidationRequest = {
  userCode: string;
  solutionFilename: string;
  testFiles: ValidationFile[];
};

type ValidationResult = {
  success: boolean;
  testsRun: number;
  failures: string[];
  errors: string[];
  output: string;
};

function ensureParentDirectories(
  fs: {
    mkdir: (path: string) => unknown;
  },
  path: string
) {
  const parts = path.split("/").slice(0, -1);
  let current = "";

  for (const part of parts) {
    if (!part) {
      continue;
    }

    current += `/${part}`;

    try {
      fs.mkdir(current);
    } catch {
      // Directory already exists.
    }
  }
}

self.onmessage = async (
  event: MessageEvent<ValidationRequest>
) => {
  try {
    const request = event.data;

    if (request.userCode.length > 50000) {
      throw new Error(
        "Solution is too large for Practice validation."
      );
    }

    const pyodide = await loadPyodide({
      indexURL:
        `https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/`,
    });

    // Pyodide itself needs network while loading. After that,
    // external code in this disposable worker gets no fetch API.
    Object.defineProperty(
      globalThis,
      "fetch",
      {
        configurable: false,
        writable: false,
        value: () =>
          Promise.reject(
            new Error(
              "Network access is disabled in Practice validation."
            )
          ),
      }
    );

    try {
      Object.defineProperty(
        globalThis,
        "WebSocket",
        {
          configurable: false,
          writable: false,
          value: undefined,
        }
      );
    } catch {
      // Some runtimes may not expose WebSocket.
    }

    ensureParentDirectories(
      pyodide.FS,
      request.solutionFilename
    );

    pyodide.FS.writeFile(
      request.solutionFilename,
      request.userCode
    );

    for (const file of request.testFiles) {
      ensureParentDirectories(
        pyodide.FS,
        file.path
      );

      pyodide.FS.writeFile(
        file.path,
        file.content
      );
    }

    pyodide.globals.set(
      "validation_test_paths_json",
      JSON.stringify(
        request.testFiles.map(
          (file) => file.path
        )
      )
    );

    const rawResult = await pyodide.runPythonAsync(`
import importlib.util
import io
import json
import os
import sys
import unittest

_test_paths = json.loads(
    validation_test_paths_json
)

_stream = io.StringIO()
_suite = unittest.TestSuite()

for _index, _path in enumerate(_test_paths):
    _absolute_path = (
        _path
        if _path.startswith("/")
        else "/" + _path
    )

    _module_name = (
        "_datapilot_external_test_"
        + str(_index)
    )

    _spec = importlib.util.spec_from_file_location(
        _module_name,
        _absolute_path,
    )

    if _spec is None or _spec.loader is None:
        raise RuntimeError(
            "Validation test module could not be loaded."
        )

    _module = importlib.util.module_from_spec(
        _spec
    )
    sys.modules[_module_name] = _module
    _spec.loader.exec_module(_module)

    _suite.addTests(
        unittest.defaultTestLoader
        .loadTestsFromModule(_module)
    )

_runner = unittest.TextTestRunner(
    stream=_stream,
    verbosity=1,
)

_result = _runner.run(_suite)

json.dumps({
    "success": _result.wasSuccessful(),
    "testsRun": _result.testsRun,
    "failures": [
        text[-1200:]
        for _, text in _result.failures
    ],
    "errors": [
        text[-1200:]
        for _, text in _result.errors
    ],
    "output": _stream.getvalue()[-3000:],
})
`);

    const result =
      JSON.parse(String(rawResult)) as ValidationResult;

    postMessage({
      type: "result",
      result,
    });
  } catch (error) {
    postMessage({
      type: "error",
      message:
        error instanceof Error
          ? error.message
          : "Practice validation failed.",
    });
  }
};
