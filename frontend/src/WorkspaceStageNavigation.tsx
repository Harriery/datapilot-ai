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
  onStageChange,
  onPrepareStageChange,
}: WorkspaceStageNavigationProps) {
  return (
    <nav className="workspace-stage-navigation">
      <div className="workspace-stage-main">
        {PERSONAL_WORKSPACE_STAGES.map(
          (stage) => {
            const status = getStageStatus(
              stage.code
            );

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
              >
                <span className="workspace-stage-status">
                  {status === "completed"
                    ? "✓"
                    : status === "current"
                      ? "●"
                      : "○"}
                </span>

                <span>
                  {stage.label}
                </span>
              </button>
            );
          }
        )}
      </div>

      {activeStage === "prepare" && (
        <div className="workspace-stage-subnav">
          {PREPARE_STAGES.map(
            (stage) => {
              const isActive =
                activePrepareStage ===
                stage.code;

              return (
                <button
                  key={stage.code}
                  type="button"
                  className={[
                    "workspace-stage-subnav-button",
                    isActive
                      ? "active"
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={() =>
                    onPrepareStageChange(
                      stage.code
                    )
                  }
                >
                  {stage.label}
                </button>
              );
            }
          )}
        </div>
      )}
    </nav>
  );
}

export default WorkspaceStageNavigation;