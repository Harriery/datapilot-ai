type DataUnderstandingPlan = {
  measure_candidates: string[];

  dimension_candidates: string[];

  time_candidates: string[];

  suggested_questions: string[];

  source: "local";
};


type Props = {
  plan: DataUnderstandingPlan;
};


function PersonalDataUnderstanding({
  plan,
}: Props) {

  return (
    <section className="personal-analysis-plan">

      <div className="personal-analysis-plan-header">

        <div>

          <span className="workspace-overview-label">
            DATA UNDERSTANDING
          </span>


          <h2>
            Understand the validated dataset
          </h2>


          <p>
            Review candidate measures,
            dimensions, time fields and
            business questions before
            designing the analytical model.
          </p>

        </div>


        <span className="personal-analysis-plan-source">
          Local profiling
        </span>

      </div>


      <div className="personal-analysis-plan-grid">

        <div className="personal-analysis-plan-group">

          <span className="personal-analysis-plan-label">
            Numeric / measure candidates
          </span>


          <div className="personal-analysis-plan-tags">

            {plan.measure_candidates.length > 0 ? (
              plan.measure_candidates.map(
                (item) => (

                  <span
                    key={item}
                    className="personal-analysis-plan-tag"
                  >
                    {item}
                  </span>

                )
              )
            ) : (

              <span className="personal-analysis-plan-empty">
                No measure candidates detected.
              </span>

            )}

          </div>

        </div>


        <div className="personal-analysis-plan-group">

          <span className="personal-analysis-plan-label">
            Dimension candidates
          </span>


          <div className="personal-analysis-plan-tags">

            {plan.dimension_candidates.length > 0 ? (
              plan.dimension_candidates.map(
                (item) => (

                  <span
                    key={item}
                    className="personal-analysis-plan-tag"
                  >
                    {item}
                  </span>

                )
              )
            ) : (

              <span className="personal-analysis-plan-empty">
                No dimension candidates detected.
              </span>

            )}

          </div>

        </div>


        <div className="personal-analysis-plan-group">

          <span className="personal-analysis-plan-label">
            Time candidates
          </span>


          <div className="personal-analysis-plan-tags">

            {plan.time_candidates.length > 0 ? (
              plan.time_candidates.map(
                (item) => (

                  <span
                    key={item}
                    className="personal-analysis-plan-tag"
                  >
                    {item}
                  </span>

                )
              )
            ) : (

              <span className="personal-analysis-plan-empty">
                No time column detected.
              </span>

            )}

          </div>

        </div>

      </div>


      {plan.suggested_questions.length > 0 && (

        <div className="personal-analysis-questions">

          <span className="personal-analysis-plan-label">
            Questions the future model
            should support
          </span>


          <ul>

            {plan.suggested_questions.map(
              (question) => (

                <li key={question}>
                  {question}
                </li>

              )
            )}

          </ul>

        </div>

      )}


      <div className="data-understanding-note">

        <strong>
          Next: Data Model
        </strong>

        <span>
          These are candidates, not final
          KPIs or analysis results. Use them
          to decide the fact tables,
          dimensions and relationships.
        </span>

      </div>

    </section>
  );
}


export default PersonalDataUnderstanding;