import { useEffect, useState } from "react";
import "./App.css";
import { runDataFrameTransformation } from "./pythonRunner";

type SkillProgressData = {
  skill_name: string;
  status: "new" | "learning" | "practicing" | "comfortable";
  attempts: number;
  successful_attempts: number;
  success_rate: number;
  last_assistance_level:
    | "NONE"
    | "NUDGE"
    | "GUIDE"
    | "TEACH"
    | "DEMONSTRATE"
    | null;
  independence_trend:
    | "improving"
    | "stable"
    | "declining"
    | "insufficient_data";
  practice_priority: "high" | "medium" | "low" | "none";
};

type PracticeRecommendationData = {
  skill_name: string;
  priority: "high" | "medium" | "low";
  difficulty: "foundation" | "easy" | "medium" | "hard";
  reason: string;
};

type DashboardWorkspace = {
  workspace_id: string;
  title: string;
  status: "active" | "paused" | "completed";
  mentor_session_id: string | null;

  checkpoint: {
    completed_items: string[];
    current_focus: string | null;
    blocked_reason: string | null;
    last_error: string | null;
    next_actions: string[];
  };
};

function App() {
  const [showSkills, setShowSkills] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState<
  "dashboard" | "workspace"
  >("dashboard");
  const [mentorOpen, setMentorOpen] = useState(false);
  const [mentorInput, setMentorInput] = useState("");
  const [mentorSessionId, setMentorSessionId] = useState<string | null>(
    null
  );
  const [workspaceId, setWorkspaceId] = useState<string | null>(
  null
  );
  const [resumeData, setResumeData] = useState<{
    title: string;
    status: string;
    checkpoint: {
      completed_items: string[];
      current_focus: string | null;
      blocked_reason: string | null;
      last_error: string | null;
      next_actions: string[];
    };
    next_action: string | null;
  } | null>(null);
  const [mentorLoading, setMentorLoading] = useState(false);

  const [mentorMessages, setMentorMessages] = useState<
    { role: "user" | "mentor"; content: string }[]
  >([
    {
      role: "mentor",
      content:
        "I can help you with your current task. Ask me about the code, task, or error.",
    },
  ]);

  
  const [pythonRunning, setPythonRunning] = useState(false);
  const [transformationCode, setTransformationCode] =
  useState(`# Inspect age distribution
age_stats = df["age"].describe()

median_age = df["age"].median()

df["age"] = df["age"].fillna(median_age)`);

  const [resultRows, setResultRows] = useState<
    Record<string, unknown>[] | null
  >(null);
  
  const [validationMessage, setValidationMessage] =
  useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [pythonError, setPythonError] = useState<string | null>(
  null
  );

  const [skillProgress, setSkillProgress] = useState<
  SkillProgressData[]
  >([]);

  const [practiceRecommendation, setPracticeRecommendation] =
  useState<PracticeRecommendationData | null>(null);

  const [dashboardLoading, setDashboardLoading] =
  useState(true);

  const [dashboardWorkspace, setDashboardWorkspace] =
  useState<DashboardWorkspace | null>(null);

   const inputRows = [
      {
        customer_id: 1001,
        name: "Alice",
        age: 31,
        city: "Den Haag",
      },
      {
        customer_id: 1002,
        name: "Bob",
        age: null,
        city: "Rotterdam",
      },
      {
        customer_id: 1003,
        name: "Carol",
        age: 28,
        city: "Utrecht",
      },
      {
        customer_id: 1004,
        name: "David",
        age: null,
        city: "Delft",
      },
    ];

  
  useEffect(() => {
    async function loadDashboardData() {
      try {
        const learnerId = "demo-learner";

        const [
          progressResponse,
          recommendationResponse,
          workspaceResponse,
        ] = await Promise.all([
          fetch(
            `http://127.0.0.1:8000/mentor/progress/${learnerId}`
          ),
          fetch(
            `http://127.0.0.1:8000/mentor/practice/recommendation/${learnerId}`
          ),
          fetch(
            `http://127.0.0.1:8000/workspaces/${learnerId}`
          ),
        ]);

        if (!progressResponse.ok) {
          throw new Error(
            "Progress bilgisi alınamadı."
          );
        }

        if (!recommendationResponse.ok) {
          throw new Error(
            "Practice recommendation alınamadı."
          );
        }
        
        if (!workspaceResponse.ok) {
          throw new Error(
            "Workspace bilgisi alınamadı."
          );
        }

        const progressData =
          await progressResponse.json();

        const recommendationData =
          await recommendationResponse.json();

        const workspaceData: DashboardWorkspace[] =
          await workspaceResponse.json();

        setSkillProgress(progressData.skills);

        setPracticeRecommendation(
          recommendationData.recommendation
        );

        const customerWorkspace =
          workspaceData.find(
            (workspace) =>
              workspace.title === "Customer Data Quality"
          ) ?? null;
        
        setDashboardWorkspace(customerWorkspace);


        setDashboardWorkspace(
          customerWorkspace ?? null
        );
      } catch (error) {
        console.error(
          "Dashboard yüklenemedi:",
          error
        );
      } finally {
        setDashboardLoading(false);
      }
    }

    loadDashboardData();
  }, []);  


  async function openWorkspace() {
    try {
      const learnerId = "demo-learner";

      const listResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/${learnerId}`
      );

      if (!listResponse.ok) {
        throw new Error("Workspace listesi alınamadı.");
      }

      const workspaces = await listResponse.json();

      let workspace = workspaces.find(
        (item: { title: string }) =>
          item.title === "Customer Data Quality"
      );

      let isNewWorkspace = false;

      if (!workspace) {
        const createResponse = await fetch(
          "http://127.0.0.1:8000/workspaces",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              learner_id: learnerId,
              title: "Customer Data Quality",
              workspace_type: "data_engineering",
              current_task_id: null,
            }),
          }
        );

        if (!createResponse.ok) {
          throw new Error("Workspace oluşturulamadı.");
        }

        workspace = await createResponse.json();
        isNewWorkspace = true;
      }

      setWorkspaceId(workspace.workspace_id);
      setMentorSessionId(workspace.mentor_session_id);

      if (isNewWorkspace) {
        const checkpointResponse = await fetch(
          `http://127.0.0.1:8000/workspaces/${learnerId}/${workspace.workspace_id}/checkpoint`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              checkpoint: {
                completed_items: [
                  "Dataset profile",
                  "Duplicate analysis",
                  "Duplicate cleanup",
                ],
                current_focus: "Resolve missing age values",
                blocked_reason:
                  "Imputation strategy has not been selected yet.",
                last_error: null,
                next_actions: [
                  "Choose an imputation strategy",
                  "Validate the transformation",
                ],
              },
            }),
          }
        );

        if (!checkpointResponse.ok) {
          throw new Error("İlk checkpoint kaydedilemedi.");
        }
        const completedWorkspace =
          await checkpointResponse.json();

        setDashboardWorkspace(completedWorkspace);
      }


      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/${learnerId}/${workspace.workspace_id}/resume`
      );

      if (!resumeResponse.ok) {
        throw new Error("Workspace kaldığı yerden yüklenemedi.");
      }

      const resume = await resumeResponse.json();

        setResumeData(resume);
        setCurrentView("workspace");
      } catch (error) {
        console.error(error);

        alert(
          error instanceof Error
            ? error.message
            : "Workspace açılırken hata oluştu."
        );
      }
    }

  async function submitTransformation() {
    if (!resultRows) {
      setValidationMessage(
        "Önce Run butonuyla transformation sonucunu oluştur."
      );
      return;
    }

    if (!workspaceId) {
      setValidationMessage("Workspace henüz hazır değil.");
      return;
    }

    setSubmitting(true);
    setValidationMessage(null);

    try {
      const validationResponse = await fetch(
        "http://127.0.0.1:8000/mentor/data-quality/transformation",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            learner_id: "demo-learner",

            finding: {
              issue_type: "missing_values",
              column: "age",
              severity: "medium",
              observation:
                "age sütununda eksik değerler var.",
              suggested_action:
                "Eksik age değerlerini uygun bir stratejiyle ele al.",
            },

            before_rows: inputRows,
            after_rows: resultRows,
          }),
        }
      );

      if (!validationResponse.ok) {
        const errorData = await validationResponse.json();

        throw new Error(
          errorData.detail ||
            "Transformation doğrulanamadı."
        );
      }

      const validationData =
        await validationResponse.json();

      if (!validationData.validation.success) {
        setValidationMessage(
          `❌ Validation failed. Null count: ${validationData.validation.before_null_count} → ${validationData.validation.after_null_count}`
        );

        return;
      }

      setValidationMessage(
        `✅ Validation passed. Null count: ${validationData.validation.before_null_count} → ${validationData.validation.after_null_count}`
      );

      const checkpointResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/checkpoint`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            checkpoint: {
              completed_items: [
                ...(resumeData?.checkpoint.completed_items ?? []),
                "Resolve missing age values",
                "Validate transformation",
              ],
              current_focus: "Complete task",
              blocked_reason: null,
              last_error: null,
              next_actions: [
                "Review your solution",
                "Complete the workspace",
              ],
            },
          }),
        }
      );

      if (!checkpointResponse.ok) {
        throw new Error(
          "Validation başarılı ama checkpoint kaydedilemedi."
        );
      }

      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/resume`
      );

      if (!resumeResponse.ok) {
        throw new Error(
          "Güncel workspace bilgisi alınamadı."
        );
      }

      const updatedResume =
        await resumeResponse.json();

      setResumeData(updatedResume);

      setDashboardWorkspace((previous) => {
        if (!previous) {
          return previous;
        }
      
        return {
          ...previous,
          status: updatedResume.status,
          checkpoint: updatedResume.checkpoint,
        };
      });
    } catch (error) {
      console.error(error);

      setValidationMessage(
        error instanceof Error
          ? `❌ ${error.message}`
          : "❌ Beklenmeyen bir hata oluştu."
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function completeWorkspace() {
    if (!workspaceId || !resumeData) {
      return;
    }

    try {
      const learnerId = "demo-learner";

      const statusResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/${learnerId}/${workspaceId}/status`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status: "completed",
          }),
        }
      );

      if (!statusResponse.ok) {
        throw new Error(
          "Workspace tamamlanamadı."
        );
      }

      const checkpointResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/${learnerId}/${workspaceId}/checkpoint`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            checkpoint: {
              completed_items: [
                ...resumeData.checkpoint.completed_items,
                "Complete task",
              ],
              current_focus: null,
              blocked_reason: null,
              last_error: null,
              next_actions: [],
            },
          }),
        }
      );

      if (!checkpointResponse.ok) {
        throw new Error(
          "Final checkpoint kaydedilemedi."
        );
      }

      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/${learnerId}/${workspaceId}/resume`
      );

      const updatedResume =
        await resumeResponse.json();

      setResumeData(updatedResume);
    } catch (error) {
      console.error(error);

      alert(
        error instanceof Error
          ? error.message
          : "Workspace tamamlanırken hata oluştu."
      );
    }
  }


  async function sendMentorMessage() {
  const message = mentorInput.trim();

  if (!message || mentorLoading) {
    return;
  }

  setMentorMessages((previous) => [
    ...previous,
    {
      role: "user",
      content: message,
    },
  ]);

  setMentorInput("");
  setMentorLoading(true);

  try {
    if (!mentorSessionId || !workspaceId) {
      throw new Error("Workspace henüz hazır değil.");
    }

    const chatResponse = await fetch(
      "http://127.0.0.1:8000/chat",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: mentorSessionId,
          learner_id: "demo-learner",
          workspace_id: workspaceId,
          message: message,
        }),
      }
    );

    if (!chatResponse.ok) {
      const errorData = await chatResponse.json();

      throw new Error(
        errorData.detail || "Mentor cevabı alınamadı."
      );
    }

    const chatData = await chatResponse.json();

    setMentorMessages((previous) => [
      ...previous,
      {
        role: "mentor",
        content: chatData.reply,
      },
    ]);
  } catch (error) {
    const errorMessage =
      error instanceof Error
        ? error.message
        : "Beklenmeyen bir hata oluştu.";

    setMentorMessages((previous) => [
      ...previous,
      {
        role: "mentor",
        content: `Error: ${errorMessage}`,
      },
    ]);
  } finally {
    setMentorLoading(false);
  }
}

  async function runTransformation() {
    setPythonRunning(true);
    setResultRows(null);
    setPythonError(null);
    setValidationMessage(null);

    try {
      const result = await runDataFrameTransformation(
        transformationCode,
        inputRows
      );

      setResultRows(result);
    } catch (error) {
      console.error(error);

      const fullMessage =
        error instanceof Error
          ? error.message
          : "Python kodu çalıştırılamadı.";

      const lines = fullMessage
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

      const shortMessage =
        lines.at(-1) ?? "Python kodu çalıştırılamadı.";

      setPythonError(shortMessage);
    } finally {
      setPythonRunning(false);
    }
  }


  return (
    <div className="app-shell">
      <aside
        className={`sidebar ${
          sidebarCollapsed ? "collapsed" : ""
        }`}
      >
        <button
          className="sidebar-toggle"
          onClick={() =>
            setSidebarCollapsed(!sidebarCollapsed)
          }
        >
          {sidebarCollapsed ? "→" : "←"}
        </button>  

        <div className="brand">
          <div className="brand-icon">◆</div>

          <div className="brand-text">
            <h1>DataPilot AI</h1>
            <p>Adaptive Mentor</p>
          </div>
        </div>

        <nav className="nav-menu">
          <button className="nav-item active">
            <span className="nav-icon">⌂</span>
            <span className="nav-label">Dashboard</span>
          </button>

          <button className="nav-item">
            <span className="nav-icon">◉</span>
            <span className="nav-label">Practice</span>
          </button>

          <button className="nav-item">
            <span className="nav-icon">✓</span>
            <span className="nav-label">Tasks</span>
          </button>

          <button className="nav-item">
            <span className="nav-icon">▥</span>
            <span className="nav-label">Progress</span>
          </button>

          <button className="nav-item">
            <span className="nav-icon">▤</span>
            <span className="nav-label">Documents</span>
          </button>

          <button className="nav-item">
            <span className="nav-icon">⚙</span>
            <span className="nav-label">Settings</span>
          </button>
        </nav>
      </aside>

      <main className="main-content">
        {currentView === "dashboard" ? (
          <>
            <header className="page-header">
              <div>
                <h2>Good morning 👋</h2>
                <p>
                  Here’s what needs your attention today.
                </p>
              </div>
        
              <div className="profile-badge">
                Junior Data Engineer
              </div>
            </header>
        
            <section className="dashboard-grid">
              <article className="card continue-card">
                <div className="card-heading">
                  <h3>Continue where you left off</h3>
                      
                  <span className="status-badge">
                    {dashboardWorkspace?.status ?? "Loading"}
                  </span>
                </div>
                      
                <h4>
                  {dashboardWorkspace?.title ??
                    "Customer Data Quality"}
                </h4>
                  
                {dashboardLoading ? (
                  <p className="muted">
                    Loading workspace...
                  </p>
                ) : dashboardWorkspace ? (
                  <>
                    <div className="workspace-status">
                      {dashboardWorkspace.status === "completed" ? (
                        <p>
                          ✓ Workspace completed
                        </p>
                      ) : (
                        <>
                          <p>
                            <strong>Current:</strong>{" "}
                            {dashboardWorkspace.checkpoint.current_focus ??
                              "No current focus"}
                          </p>
                            
                          {dashboardWorkspace.checkpoint.blocked_reason && (
                            <p className="warning">
                              ⚠{" "}
                              {
                                dashboardWorkspace.checkpoint
                                  .blocked_reason
                              }
                            </p>
                          )}
                        </>
                      )}
                    </div>
                    
                    {dashboardWorkspace.status !== "completed" && (
                      <button
                        className="primary-button"
                        onClick={openWorkspace}
                      >
                        Resume workspace →
                      </button>
                    )}
                  </>
                ) : (
                  <p className="muted">
                    No workspace found.
                  </p>
                )}
              </article>
                
              <article className="card recommendation-card">
                <h3>Current Recommendation</h3>

                {dashboardLoading ? (
                  <p className="muted">
                    Loading recommendation...
                  </p>
                ) : practiceRecommendation ? (
                  <>
                    <p className="skill-name">
                      {practiceRecommendation.skill_name}
                    </p>
                
                    <div className="badge-row">
                      <span className="priority-badge">
                        {practiceRecommendation.priority} priority
                      </span>
                
                      <span className="difficulty-badge">
                        {practiceRecommendation.difficulty}
                      </span>
                    </div>
                
                    <p className="muted">
                      {practiceRecommendation.reason}
                    </p>
                  </>
                ) : (
                  <p className="muted">
                    No practice recommendation right now.
                  </p>
                )}
              </article>
                
              <article className="card learning-path-card">
                <h3>Today’s path</h3>

                {dashboardLoading ? (
                  <p className="muted">
                    Loading path...
                  </p>
                ) : !dashboardWorkspace ? (
                  <p className="muted">
                    No active workspace.
                  </p>
                ) : dashboardWorkspace.status === "completed" ? (
                  <div className="path-item completed">
                    <span>✓</span>
                
                    <div>
                      <strong>Workspace completed</strong>
                      <p>
                        {dashboardWorkspace.title} is finished.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="path-item completed">
                      <span>✓</span>
                
                      <div>
                        <strong>
                          {dashboardWorkspace.checkpoint.completed_items.at(-1) ??
                            "Workspace started"}
                        </strong>
                          
                        <p>Last completed step.</p>
                      </div>
                    </div>
                          
                    <div className="path-item current">
                      <span>●</span>
                          
                      <div>
                        <strong>
                          {dashboardWorkspace.checkpoint.current_focus ??
                            "No current focus"}
                        </strong>
                          
                        <p>This is your current focus.</p>
                      </div>
                    </div>
                          
                    {dashboardWorkspace.checkpoint.next_actions.map(
                      (action, index) => (
                        <div
                          className="path-item"
                          key={`${action}-${index}`}
                        >
                          <span>○</span>
                      
                          <div>
                            <strong>{action}</strong>
                      
                            <p>Next recommended step.</p>
                          </div>
                        </div>
                      )
                    )}
                  </>
                )}
              </article>      
                
              {showSkills ? (
                <article className="card skill-card">
                  <div className="card-heading">
                    <h3>Skill Progress</h3>
              
                    <button
                      className="icon-button"
                      onClick={() =>
                        setShowSkills(false)
                      }
                    >
                      ×
                    </button>
                  </div>

                  {dashboardLoading ? (
                    <p className="muted">
                      Loading skills...
                    </p>
                  ) : skillProgress.length === 0 ? (
                    <p className="muted">
                      No skill progress yet.
                    </p>
                  ) : (
                    skillProgress.map((skill) => (
                      <SkillProgress
                        key={skill.skill_name}
                        name={skill.skill_name}
                        status={
                          skill.status.charAt(0).toUpperCase() +
                          skill.status.slice(1)
                        }
                        progress={Math.round(
                          skill.success_rate * 100
                        )}
                      />
                    ))
                  )}  

                </article>
              ) : (
                <article className="card collapsed-skill-card">
                  <div>
                    <h3>Skill Progress</h3>
                    <p>Progress panel is hidden.</p>
                  </div>
              
                  <button
                    className="secondary-button"
                    onClick={() =>
                      setShowSkills(true)
                    }
                  >
                    Show skills →
                  </button>
                </article>
              )}
            </section>
          </>
        ) : (
          <section className="workspace-page">
            <div className="workspace-header">
              <div>
                <button
                  className="back-button"
                  onClick={() =>
                    setCurrentView("dashboard")
                  }
                >
                  ← Dashboard
                </button>
                
                <h2>Customer Data Quality</h2>
                
                <p>
                  Focus Workspace ·{" "}
                  {resumeData
                    ? resumeData.status === "completed"
                      ? "Completed"
                      : resumeData.checkpoint.current_focus ?? "No current focus"
                    : "Loading..."}
                </p>
              </div>
                
              <button
                className="mentor-button"
                onClick={() => setMentorOpen(true)}
              >
                Ask Mentor
              </button>
            </div>
                
            <div className="workspace-path">
              <span className="done-step">
                ✓{" "}
                {resumeData?.checkpoint.completed_items.slice(-1)[0] ??
                  "No completed step"}
              </span>
                
              <span className="current-step">
                ● Current:{" "}
                {resumeData?.checkpoint.current_focus ??
                  "No current focus"}
              </span>
                
              <span>
                ○ Next:{" "}
                {resumeData?.next_action ?? "No next action"}
              </span>
            </div>
                
            <div className="current-task">
              <strong>Current focus</strong>

              <p>
                {resumeData?.checkpoint.current_focus ??
                  "No current focus."}
              </p>
                
              {resumeData?.next_action && (
                <p>
                  <strong>Next:</strong>{" "}
                  {resumeData.next_action}
                </p>
              )}

              {resumeData?.checkpoint.blocked_reason && (
                <p className="warning">
                  ⚠ {resumeData.checkpoint.blocked_reason}
                </p>
              )}

              {resumeData?.checkpoint.current_focus ===
                "Complete task" && (
                <button
                  className="complete-workspace-button"
                  onClick={completeWorkspace}
                >
                  ✓ Complete workspace
                </button>
              )}

            </div>
                
            <div className="workspace-grid">
              <section className="workspace-panel">
                <div className="panel-title">
                  Input Dataset
                </div>
                
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>customer_id</th>
                      <th>name</th>
                      <th>age</th>
                      <th>city</th>
                    </tr>
                  </thead>
                
                  <tbody>
                    <tr>
                      <td>1001</td>
                      <td>Alice</td>
                      <td>31</td>
                      <td>Den Haag</td>
                    </tr>
                
                    <tr>
                      <td>1002</td>
                      <td>Bob</td>
                      <td className="missing-cell">
                        NULL
                      </td>
                      <td>Rotterdam</td>
                    </tr>
                
                    <tr>
                      <td>1003</td>
                      <td>Carol</td>
                      <td>28</td>
                      <td>Utrecht</td>
                    </tr>
                
                    <tr>
                      <td>1004</td>
                      <td>David</td>
                      <td className="missing-cell">
                        NULL
                      </td>
                      <td>Delft</td>
                    </tr>
                  </tbody>

                </table>
                <div className="result-preview">
                  <strong>Result preview</strong>

                  {pythonError ? (
                    <div className="python-error">
                      <strong>Python error</strong>
                  
                      <pre>{pythonError}</pre>
                    </div>
                  ) : resultRows === null ? (
                    <p>
                      Run your transformation to preview the result.
                    </p>
                  ) : (
                    <table className="data-table result-table">
                      <thead>
                        <tr>
                          <th>customer_id</th>
                          <th>name</th>
                          <th>age</th>
                          <th>city</th>
                        </tr>
                      </thead>
                  
                      <tbody>
                        {resultRows.map((row, index) => (
                          <tr key={index}>
                            <td>{String(row.customer_id)}</td>
                            <td>{String(row.name)}</td>
                        
                            <td>
                              {row.age == null
                                ? "NULL"
                                : String(row.age)}
                            </td>
                              
                            <td>{String(row.city)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
                
              </section>
                
              <section className="workspace-panel">
                <div className="panel-title">
                  Your Code / Transformation
                </div>
                
                <textarea
                  className="code-editor"
                  value={transformationCode}
                  onChange={(event) => {
                    setTransformationCode(event.target.value);
                  
                    // Kod değiştiyse eski çalıştırma sonucu artık geçerli değildir.
                    setResultRows(null);
                    setPythonError(null);
                    setValidationMessage(null);
                  }}
                />
                

                <div className="workspace-actions">
                  <button
                    className="run-button"
                    onClick={runTransformation}
                    disabled={pythonRunning}
                  >
                    {pythonRunning ? "Running..." : "▶ Run"}
                  </button>
                  
                  <button
                    className="submit-button"
                    onClick={submitTransformation}
                    disabled={submitting || resultRows === null}
                  >
                    {submitting ? "Validating..." : "✓ Submit"}
                  </button>

                </div>
                {validationMessage && (
                  <div className="validation-message">
                    {validationMessage}
                  </div>
                )}

              </section>
            </div>

            {mentorOpen && (
              <>
                <div
                  className="mentor-backdrop"
                  onClick={() => setMentorOpen(false)}
                />

                <aside className="mentor-drawer">
                  <div className="mentor-drawer-header">
                    <div>
                      <h3>Ask your Mentor</h3>

                      <p>
                        Customer Data Quality · age nulls
                      </p>
                    </div>

                    <button
                      className="mentor-close"
                      onClick={() => setMentorOpen(false)}
                    >
                      ×
                    </button>
                  </div>

                  <div className="mentor-context">
                    <span>Current task</span>
                    <span>Last error</span>
                    <span>Current code</span>
                  </div>

                  <div className="mentor-chat">
                    {mentorMessages.map((message, index) =>
                      message.role === "mentor" ? (
                        <div
                          className="mentor-message"
                          key={index}
                        >
                          <strong>Mentor</strong>
                          <p>{message.content}</p>
                        </div>
                      ) : (
                        <div
                          className="user-message"
                          key={index}
                        >
                          <p>{message.content}</p>
                        </div>
                      )
                    )}

                    {mentorLoading && (
                      <div className="mentor-message">
                        <strong>Mentor</strong>
                        <p>Thinking...</p>
                      </div>
                    )}
                  </div>

                  <div className="mentor-input-area">
                    <textarea
                      placeholder="Ask about the task, code, or error..."
                      value={mentorInput}
                      onChange={(event) =>
                        setMentorInput(event.target.value)
                      }
                    />

                    <button
                      onClick={sendMentorMessage}
                      disabled={mentorLoading}
                    >
                      {mentorLoading ? "..." : "Send →"}
                    </button>
                  </div>


                </aside>
              </>
            )}
          </section>
        )}
      </main>    
 
 
    </div>
  );
}

type SkillProgressProps = {
  name: string;
  status: string;
  progress: number;
};

function SkillProgress({
  name,
  status,
  progress,
}: SkillProgressProps) {
  return (
    <div className="skill-progress">
      <div className="skill-progress-header">
        <span>{name}</span>
        <span>{status}</span>
      </div>

      <div className="progress-track">
        <div
          className="progress-bar"
          style={{
            width: `${progress}%`,
          }}
        />
      </div>
    </div>
  );
}

export default App;