import {
  useEffect,
  useState,
} from "react";

import {
  translations,
  type AppLanguage,
} from "./i18n";


type TaskSummaryStatus =
  | "todo"
  | "active"
  | "blocked"
  | "completed";


type TaskSummaryItem = {
  workspace_id: string;
  workspace_title: string;

  task_id: string | null;
  task_title: string;

  status: TaskSummaryStatus;

  current_step: string | null;
  next_action: string | null;

  validation_passed: boolean;
  review_completed: boolean;
  handoff_completed: boolean;

  usage_context: "work" | "personal";
};


type TaskSummaryResponse = {
  learner_id: string;
  tasks: TaskSummaryItem[];
};


type TasksPageProps = {
  language: AppLanguage;

  onOpenWorkspace: (
    workspaceId: string
  ) => void;
};


function getSystemTaskText(
  text: string | null,
  language: AppLanguage
): string | null {
  if (text === null) {
    return null;
  }

  const t = translations[language];

  const systemTextMap: Record<
    string,
    string
  > = {
    "Workspace completed":
      t.tasks.systemText.workspaceCompleted,

    "Review transformed dataset":
      t.tasks.systemText.reviewTransformedDataset,

    "Review transformation results":
      t.tasks.systemText.reviewTransformationResults,

    "Review final dataset and changes":
      t.tasks.systemText.reviewFinalDataset,

    "Resolve validation failures":
      t.tasks.systemText.resolveValidationFailures,

    "Prepare handoff":
      t.tasks.systemText.prepareHandoff,

    "Prepare final dataset handoff":
      t.tasks.systemText.prepareFinalDatasetHandoff,
  };

  return systemTextMap[text] ?? text;
}


function TasksPage({
  language,
  onOpenWorkspace,
}: TasksPageProps) {
  const t = translations[language];

  const [tasks, setTasks] =
    useState<TaskSummaryItem[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);


  async function loadTasks() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/tasks/demo-learner"
      );

      if (!response.ok) {
        const errorData =
          await response.json();

        throw new Error(
          errorData.detail ||
            t.tasks.loadError
        );
      }

      const data: TaskSummaryResponse =
        await response.json();

      setTasks(data.tasks);

    } catch (error) {
      console.error(error);

      setError(
        error instanceof Error
          ? error.message
          : t.tasks.loadError
      );

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    void loadTasks();
  }, []);


  return (
    <section className="tasks-page">
      <header className="tasks-page-header">
        <div>
          <p className="workspace-eyebrow">
            {t.tasks.eyebrow}
          </p>

          <h2>{t.tasks.title}</h2>

          <p>
            {t.tasks.description}
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={() => {
            void loadTasks();
          }}
          disabled={loading}
        >
          {loading
            ? t.tasks.refreshing
            : t.tasks.refresh}
        </button>
      </header>


      <div className="task-status-grid">
        {(
          [
            "todo",
            "active",
            "blocked",
            "completed",
          ] as const
        ).map((status) => (
          <div
            className={
              `task-status-summary ${status}`
            }
            key={status}
          >
            <strong>
              {
                tasks.filter(
                  (task) =>
                    task.status === status
                ).length
              }
            </strong>

            <span>
              {t.tasks.status[status]}
            </span>
          </div>
        ))}
      </div>


      {error ? (
        <div className="python-error">
          <strong>
            {t.tasks.loadError}
          </strong>

          <p>{error}</p>
        </div>

      ) : loading && tasks.length === 0 ? (
        <p className="muted">
          {t.tasks.loading}
        </p>

      ) : tasks.length === 0 ? (
        <p className="muted">
          {t.tasks.empty}
        </p>

      ) : (
        <div className="task-list">
          {tasks.map((task) => (
            <article
              className={
                `task-item-card ${task.status}`
              }
              key={task.workspace_id}
            >
              <div className="task-card-content">
                <div className="task-card-badges">
                  <span
                    className={
                      `task-status-badge ${task.status}`
                    }
                  >
                    {
                      t.tasks.status[
                        task.status
                      ]
                    }
                  </span>

                  <span className="task-context-badge">
                    {task.usage_context === "work"
                      ? t.workspace.work
                      : t.workspace.personal}
                  </span>
                </div>


                <h3>
                  {task.task_title}
                </h3>

                <p className="task-workspace-name">
                  {t.tasks.workspace}:{" "}
                  {task.workspace_title}
                </p>


                <div className="task-detail-grid">
                  <div>
                    <span>
                      {t.tasks.currentStep}
                    </span>

                    <strong>
                      {getSystemTaskText(
                          task.current_step,
                          language
                        ) ?? "—"}
                    </strong>
                  </div>

                  <div>
                    <span>
                      {t.tasks.nextAction}
                    </span>

                    <strong>
                      {getSystemTaskText(
                          task.next_action,
                          language
                        ) ?? "—"}
                    </strong>
                  </div>
                </div>


                <div className="task-gates">
                  <span
                    className={
                      task.validation_passed
                        ? "task-gate done"
                        : "task-gate"
                    }
                  >
                    {task.validation_passed
                      ? "✓"
                      : "○"}{" "}
                    {t.tasks.validation}
                  </span>

                  <span
                    className={
                      task.review_completed
                        ? "task-gate done"
                        : "task-gate"
                    }
                  >
                    {task.review_completed
                      ? "✓"
                      : "○"}{" "}
                    {t.tasks.review}
                  </span>

                  <span
                    className={
                      task.handoff_completed
                        ? "task-gate done"
                        : "task-gate"
                    }
                  >
                    {task.handoff_completed
                      ? "✓"
                      : "○"}{" "}
                    {t.tasks.handoff}
                  </span>
                </div>
              </div>


              <button
                className={
                  "secondary-button " +
                  "task-open-button"
                }
                onClick={() =>
                  onOpenWorkspace(
                    task.workspace_id
                  )
                }
              >
                {t.tasks.openWorkspace}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}


export default TasksPage;