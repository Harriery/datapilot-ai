import {
  PERSONAL_WORKSPACE_STAGES,
  PREPARE_STAGES,
  type PersonalWorkspaceStage,
  type PrepareStage,
  type WorkspaceStageStatus,
} from "./workspaceStages";

type WorkspaceStageNavigationProps = {
  activeStage: PersonalWorkspaceStage;
  activePrepareStage: PrepareStage;

  getStageStatus: (
    stage: PersonalWorkspaceStage
  ) => WorkspaceStageStatus;

  getPrepareStageStatus: (
    stage: PrepareStage
  ) => WorkspaceStageStatus;

  onStageChange: (
    stage: PersonalWorkspaceStage
  ) => void;

  onPrepareStageChange: (
    stage: PrepareStage
  ) => void;
};

function WorkspaceStageNavigation({
  activeStage,
  activePrepareStage,
  getStageStatus,
  getPrepareStageStatus,
  onStageChange,
  onPrepareStageChange,
}: WorkspaceStageNavigationProps) {
  const activeStageIndex =
    PERSONAL_WORKSPACE_STAGES.findIndex(
      (stage) => stage.code === activeStage
    );

  const activeStagePosition =
    ((activeStageIndex + 0.5) /
      PERSONAL_WORKSPACE_STAGES.length) *
    100;

  return (
    <nav
      className="workspace-stage-navigation"
      aria-label="Workspace stages"
    >
      <div className="workspace-stage-scroll">
        <div className="workspace-stage-canvas">
          <div className="workspace-stage-main">
            {PERSONAL_WORKSPACE_STAGES.map(
              (stage) => {
                const status =
                  getStageStatus(stage.code);

                const isActive =
                  activeStage === stage.code;

                return (
                  <button
                    key={stage.code}
                    type="button"
                    className={[
                      "workspace-stage-button",
                      `status-${status}`,
                      isActive ? "active" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    disabled={
                      status === "locked"
                    }
                    onClick={() =>
                      onStageChange(stage.code)
                    }
                    aria-current={
                      isActive
                        ? "step"
                        : undefined
                    }
                  >
                    <span className="workspace-stage-label">
                      {stage.label}
                    </span>

                    <span
                      className="workspace-stage-dot"
                      aria-hidden="true"
                    />
                  </button>
                );
              }
            )}
          </div>

          {activeStage === "prepare" && (
            <div className="workspace-stage-tree">
              <span
                className="workspace-stage-tree-stem"
                style={{
                  left: `${activeStagePosition}%`,
                }}
                aria-hidden="true"
              />

              <div
                className="workspace-stage-tree-branches"
                style={{
                  left: `${activeStagePosition}%`,
                }}
              >
                {PREPARE_STAGES.map(
                  (stage, index) => {
                    const isActive =
                      activePrepareStage ===
                      stage.code;

                    const status =
                      getPrepareStageStatus(
                        stage.code
                      );

                    return (
                      <button
                        key={stage.code}
                        type="button"
                        className={[
                          "workspace-stage-subnav-button",
                          `status-${status}`,
                          isActive
                            ? "active"
                            : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                        style={{
                          animationDelay: `${
                            140 +
                            index * 55
                          }ms`,
                        }}
                        disabled={
                          status === "locked"
                        }
                        onClick={() =>
                          onPrepareStageChange(
                            stage.code
                          )
                        }
                        aria-current={
                          isActive
                            ? "page"
                            : undefined
                        }
                      >
                        <span
                          className="workspace-stage-subnav-dot"
                          aria-hidden="true"
                        />

                        <span>
                          {stage.label}
                        </span>
                      </button>
                    );
                  }
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

export default WorkspaceStageNavigation;