import { useState } from "react";
import "./App.css";

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

  async function completeCurrentStep() {
    if (!workspaceId || !resumeData) {
      alert("Workspace henüz hazır değil.");
      return;
    }

    try {
      const learnerId = "demo-learner";

      const currentFocus =
        resumeData.checkpoint.current_focus;

      const updatedCompletedItems = [
        ...resumeData.checkpoint.completed_items,
      ];

      if (
        currentFocus &&
        !updatedCompletedItems.includes(currentFocus)
      ) {
        updatedCompletedItems.push(currentFocus);
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
              completed_items: updatedCompletedItems,
              current_focus: "Validate transformation",
              blocked_reason: null,
              last_error: null,
              next_actions: [
                "Review the transformation result",
                "Complete the task",
              ],
            },
          }),
        }
      );

      if (!checkpointResponse.ok) {
        throw new Error(
          "Checkpoint güncellenemedi."
        );
      }

      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/${learnerId}/${workspaceId}/resume`
      );

      if (!resumeResponse.ok) {
        throw new Error(
          "Güncel workspace bilgisi alınamadı."
        );
      }

      const updatedResume =
        await resumeResponse.json();

      setResumeData(updatedResume);
    } catch (error) {
      console.error(error);

      alert(
        error instanceof Error
          ? error.message
          : "İlerleme kaydedilirken hata oluştu."
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
                    In progress
                  </span>
                </div>
        
                <h4>Customer Data Quality</h4>
        
                <p className="muted">
                  Last worked: Yesterday
                </p>
        
                <div className="workspace-status">
                  <p>
                    <strong>Current:</strong>{" "}
                    Missing values / age
                  </p>
        
                  <p className="warning">
                    ⚠ Blocked: choose an imputation strategy
                  </p>
                </div>
        
                <button
                  className="primary-button"
                  onClick={openWorkspace}
                >
                  Resume workspace →
                </button>
              </article>
                
              <article className="card recommendation-card">
                <h3>Current Recommendation</h3>
                
                <p className="skill-name">
                  duplicate_analysis
                </p>
                
                <div className="badge-row">
                  <span className="priority-badge">
                    Medium priority
                  </span>
                
                  <span className="difficulty-badge">
                    Easy
                  </span>
                </div>
                
                <p className="muted">
                  More practice will help you become more
                  independent with this skill.
                </p>
              </article>
                
              <article className="card learning-path-card">
                <h3>Today’s path</h3>
                
                <div className="path-item completed">
                  <span>✓</span>
                
                  <div>
                    <strong>Resume workspace</strong>
                    <p>Open your current work context.</p>
                  </div>
                </div>
                
                <div className="path-item current">
                  <span>●</span>
                
                  <div>
                    <strong>Resolve age nulls</strong>
                    <p>This is your current focus.</p>
                  </div>
                </div>
                
                <div className="path-item">
                  <span>○</span>
                
                  <div>
                    <strong>
                      Validate transformation
                    </strong>
                
                    <p>
                      Check whether the result is correct.
                    </p>
                  </div>
                </div>
                
                <div className="path-item">
                  <span>○</span>
                
                  <div>
                    <strong>Review progress</strong>
                
                    <p>
                      Update your learning evidence.
                    </p>
                  </div>
                </div>
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
                    
                  <SkillProgress
                    name="python_data_structures"
                    status="Practicing"
                    progress={72}
                  />

                  <SkillProgress
                    name="null_analysis"
                    status="Practicing"
                    progress={58}
                  />

                  <SkillProgress
                    name="duplicate_analysis"
                    status="Learning"
                    progress={42}
                  />
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
                  {resumeData?.checkpoint.current_focus ?? "Loading..."}
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
                ✓ Duplicate cleanup
              </span>
                
              <span className="current-step">
                ● Current: age nulls
              </span>
                
              <span>
                ○ Next: validate
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
                
                  <p>
                    Run your transformation to preview
                    the result.
                  </p>
                </div>
              </section>
                
              <section className="workspace-panel">
                <div className="panel-title">
                  Your Code / Transformation
                </div>
                
                <textarea
                  className="code-editor"
                  defaultValue={`# Inspect age distribution
      age_stats = df["age"].describe()
                  
      median_age = df["age"].median()
                  
      df["age"] = df["age"].fillna(median_age)`}
                />

                <div className="workspace-actions">
                  <button className="run-button">
                    ▶ Run
                  </button>
                  
                  <button
                    className="submit-button"
                    onClick={completeCurrentStep}
                  >
                    ✓ Submit
                  </button>
                </div>
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