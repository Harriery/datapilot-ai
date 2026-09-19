import {
  translations,
  type AppLanguage,
} from "./i18n";


export type OverallReadinessData = {
  level:
    | "GUIDE"
    | "NUDGE"
    | "INDEPENDENT";

  score: number;

  knowledge_score: number;
  independence_score: number;
  skill_coverage: number;

  covered_skills: number;
  total_skills: number;
  total_attempts: number;
};


type OverallReadinessPanelProps = {
  language: AppLanguage;

  readiness:
    OverallReadinessData | null;
};


function OverallReadinessPanel({
  language,
  readiness,
}: OverallReadinessPanelProps) {
  const t = translations[language];

  if (!readiness) {
    return null;
  }


  const levelLabel =
    t.progress.readinessLevels[
      readiness.level
    ];


  return (
    <section className="overall-readiness-panel">

      <div className="overall-readiness-main">
        <div>
          <span className="workspace-overview-label">
            {t.progress.overallReadiness}
          </span>

          <p className="overall-readiness-description">
            {
              t.progress
                .overallReadinessDescription
            }
          </p>
        </div>


        <div className="overall-readiness-score">
          <strong>
            {readiness.score}%
          </strong>

          <span
            className={
              `readiness-level ${readiness.level.toLowerCase()}`
            }
          >
            {levelLabel}
          </span>
        </div>
      </div>


      <div className="readiness-metrics">

        <div className="readiness-metric">
          <div className="readiness-metric-heading">
            <span>
              {
                t.progress
                  .knowledgeScore
              }
            </span>

            <strong>
              {
                readiness
                  .knowledge_score
              }
              %
            </strong>
          </div>

          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{
                width:
                  `${readiness.knowledge_score}%`,
              }}
            />
          </div>
        </div>


        <div className="readiness-metric">
          <div className="readiness-metric-heading">
            <span>
              {
                t.progress
                  .independenceScore
              }
            </span>

            <strong>
              {
                readiness
                  .independence_score
              }
              %
            </strong>
          </div>

          <div className="progress-bar-track">
            <div
              className="progress-bar-fill independence"
              style={{
                width:
                  `${readiness.independence_score}%`,
              }}
            />
          </div>
        </div>


        <div className="readiness-metric">
          <div className="readiness-metric-heading">
            <span>
              {
                t.progress
                  .skillCoverage
              }
            </span>

            <strong>
              {
                readiness
                  .skill_coverage
              }
              %
            </strong>
          </div>

          <div className="progress-bar-track">
            <div
              className="progress-bar-fill coverage"
              style={{
                width:
                  `${readiness.skill_coverage}%`,
              }}
            />
          </div>
        </div>

      </div>


      <div className="overall-readiness-footer">
        <span>
          {
            readiness.covered_skills
          }
          /
          {
            readiness.total_skills
          }{" "}
          {t.progress.skillsCovered}
        </span>

        <span>
          {
            readiness.total_attempts
          }{" "}
          {t.progress.attempts.toLowerCase()}
        </span>
      </div>

    </section>
  );
}


export default OverallReadinessPanel;