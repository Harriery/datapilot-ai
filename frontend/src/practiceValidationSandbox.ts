export type PracticeValidationFile = {
  path: string;
  content: string;
};

export type PracticeValidationBundle = {
  learner_id: string;
  source_id: string;
  source_exercise_id: string;
  solution_filename: string;
  test_files: PracticeValidationFile[];
  attribution: string;
  source_revision: string | null;
  content_hash: string;
  cached: boolean;
};

export type PracticeSandboxResult = {
  success: boolean;
  testsRun: number;
  failures: string[];
  errors: string[];
  output: string;
};

export async function runPracticeValidationSandbox(
  bundle: PracticeValidationBundle,
  userCode: string,
  timeoutMs = 20000
): Promise<PracticeSandboxResult> {
  return new Promise((resolve, reject) => {
    const worker = new Worker(
      new URL(
        "./practiceValidationWorker.ts",
        import.meta.url
      ),
      {
        type: "module",
      }
    );

    const timeoutId = window.setTimeout(
      () => {
        worker.terminate();
        reject(
          new Error(
            "Validation timed out and the sandbox was stopped."
          )
        );
      },
      timeoutMs
    );

    worker.onmessage = (
      event: MessageEvent<
        | {
            type: "result";
            result: PracticeSandboxResult;
          }
        | {
            type: "error";
            message: string;
          }
      >
    ) => {
      window.clearTimeout(timeoutId);
      worker.terminate();

      if (event.data.type === "result") {
        resolve(event.data.result);
        return;
      }

      reject(
        new Error(event.data.message)
      );
    };

    worker.onerror = (event) => {
      window.clearTimeout(timeoutId);
      worker.terminate();

      reject(
        new Error(
          event.message ||
          "Practice validation worker failed."
        )
      );
    };

    worker.postMessage({
      userCode,
      solutionFilename:
        bundle.solution_filename,
      testFiles: bundle.test_files,
    });
  });
}
