type TransformStep = {
  step_number: number;
  title: string;
  status: string;

  finding: {
    issue_type: string;
    column: string | null;
  };
};

type PersonalTransformSummaryProps = {
  steps: TransformStep[];
  workingRowCount: number | null;
};

function PersonalTransformSummary({
  steps,
  workingRowCount,
}: PersonalTransformSummaryProps) {
  const completedSteps = steps.filter(
    (step) => step.status === "completed"
  );

  return (
    <section className="workspace-overview-card personal-transform-summary">
      <div className="personal-transform-summary-header">
        <div>
          <span className="workspace-overview-label">
            TRANSFORM
          </span>

          <h3>Transformation summary</h3>

          <p>
            Completed transformations applied to
            the current working dataset.
          </p>
        </div>

        <span className="workspace-list-status completed">
          Completed
        </span>
      </div>

      <div className="personal-transform-summary-steps">
        {completedSteps.map((step) => (
          <div
            key={step.step_number}
            className="personal-transform-summary-step"
          >
            <span className="personal-transform-summary-check">
              ✓
            </span>

            <div>
              <strong>{step.title}</strong>

              <p>
                {step.finding.issue_type.replaceAll(
                  "_",
                  " "
                )}

                {step.finding.column
                  ? ` · ${step.finding.column}`
                  : ""}
              </p>
            </div>
          </div>
        ))}
      </div>

      {workingRowCount !== null && (
        <div className="personal-transform-summary-result">
          <span>Current working dataset</span>

          <strong>
            {workingRowCount} rows
          </strong>
        </div>
      )}
    </section>
  );
}

export default PersonalTransformSummary;