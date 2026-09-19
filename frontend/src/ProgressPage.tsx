import {
  useEffect,
  useState,
} from "react";

import {
  translations,
  type AppLanguage,
} from "./i18n";


type AssistanceLevel =
  | "NONE"
  | "NUDGE"
  | "GUIDE"
  | "TEACH"
  | "DEMONSTRATE";


type SkillProgressData = {
  skill_name: string;

  status:
    | "new"
    | "learning"
    | "practicing"
    | "comfortable";

  attempts: number;
  successful_attempts: number;

  success_rate: number;

  last_assistance_level:
    | AssistanceLevel
    | null;

  independence_trend:
    | "improving"
    | "stable"
    | "declining"
    | "insufficient_data";

  practice_priority:
    | "high"
    | "medium"
    | "low"
    | "none";
};


type ProgressResponse = {
  learner_id: string;
  skills: SkillProgressData[];
};


type ProgressPageProps = {
  language: AppLanguage;
};


const ASSISTANCE_INDEPENDENCE_SCORE: Record<
  AssistanceLevel,
  number
> = {
  DEMONSTRATE: 0,
  TEACH: 25,
  GUIDE: 50,
  NUDGE: 75,
  NONE: 100,
};


function formatSkillName(
  skillName: string
) {
  return skillName
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1)
    )
    .join(" ");
}


function ProgressPage({
  language,
}: ProgressPageProps) {
  const t = translations[language];

  const [skills, setSkills] =
    useState<SkillProgressData[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [
    performanceOpen,
    setPerformanceOpen,
  ] = useState(true);

  const [
    independenceOpen,
    setIndependenceOpen,
  ] = useState(true);

  const [
    detailsOpen,
    setDetailsOpen,
  ] = useState(false);


  async function loadProgress() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/mentor/progress/demo-learner"
      );

      if (!response.ok) {
        const errorData =
          await response.json();

        throw new Error(
          errorData.detail ||
            t.progress.loadError
        );
      }

      const data: ProgressResponse =
        await response.json();

      setSkills(data.skills);

    } catch (error) {
      console.error(error);

      setError(
        error instanceof Error
          ? error.message
          : t.progress.loadError
      );

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    void loadProgress();
  }, []);


  const totalAttempts =
    skills.reduce(
      (total, skill) =>
        total + skill.attempts,
      0
    );


  const averageSuccess =
    skills.length === 0
      ? 0
      : Math.round(
          (
            skills.reduce(
              (total, skill) =>
                total +
                skill.success_rate,
              0
            ) /
            skills.length
          ) * 100
        );


  const independenceScores =
    skills
      .filter(
        (skill) =>
          skill.last_assistance_level !==
          null
      )
      .map(
        (skill) =>
          ASSISTANCE_INDEPENDENCE_SCORE[
            skill.last_assistance_level as
              AssistanceLevel
          ]
      );


  const averageIndependence =
    independenceScores.length === 0
      ? 0
      : Math.round(
          independenceScores.reduce(
            (total, score) =>
              total + score,
            0
          ) /
            independenceScores.length
        );


  function getMentorModeLabel(
    level: AssistanceLevel | null
  ) {
    if (level === null) {
      return t.progress.mentorModes.noData;
    }

    return t.progress.mentorModes[level];
  }


  return (
    <section className="progress-page">
      <header className="progress-page-header">
        <div>
          <p className="workspace-eyebrow">
            {t.progress.eyebrow}
          </p>

          <h2>{t.progress.title}</h2>

          <p>
            {t.progress.description}
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={() => {
            void loadProgress();
          }}
          disabled={loading}
        >
          {loading
            ? t.progress.refreshing
            : t.progress.refresh}
        </button>
      </header>


      <div className="progress-kpi-grid">
        <div className="progress-kpi-card">
          <strong>
            {skills.length}
          </strong>

          <span>
            {t.progress.skillsTracked}
          </span>
        </div>

        <div className="progress-kpi-card">
          <strong>
            {averageSuccess}%
          </strong>

          <span>
            {t.progress.averageSuccess}
          </span>
        </div>

        <div className="progress-kpi-card">
          <strong>
            {totalAttempts}
          </strong>

          <span>
            {t.progress.totalAttempts}
          </span>
        </div>

        <div className="progress-kpi-card">
          <strong>
            {averageIndependence}%
          </strong>

          <span>
            {t.progress.averageIndependence}
          </span>
        </div>
      </div>


      {error ? (
        <div className="python-error">
          <strong>
            {t.progress.loadError}
          </strong>

          <p>{error}</p>
        </div>

      ) : loading && skills.length === 0 ? (
        <p className="muted">
          {t.progress.loading}
        </p>

      ) : skills.length === 0 ? (
        <p className="muted">
          {t.progress.empty}
        </p>

      ) : (
        <div className="progress-sections">

          <section className="progress-panel">
            <button
              type="button"
              className="progress-panel-toggle"
              onClick={() =>
                setPerformanceOpen(
                  !performanceOpen
                )
              }
            >
              <div>
                <span className="workspace-overview-label">
                  {t.progress.skillPerformance}
                </span>

                <p>
                  {
                    t.progress
                      .skillPerformanceDescription
                  }
                </p>
              </div>

              <span className="workspace-plan-chevron">
                {performanceOpen
                  ? "−"
                  : "+"}
              </span>
            </button>

            {performanceOpen && (
              <div className="progress-panel-content">
                {skills.map((skill) => {
                  const successPercent =
                    Math.round(
                      skill.success_rate *
                        100
                    );

                  return (
                    <div
                      className="progress-skill-row"
                      key={skill.skill_name}
                    >
                      <div className="progress-skill-heading">
                        <strong>
                          {formatSkillName(
                            skill.skill_name
                          )}
                        </strong>

                        <span>
                          {successPercent}%
                        </span>
                      </div>

                      <div className="progress-bar-track">
                        <div
                          className="progress-bar-fill"
                          style={{
                            width:
                              `${successPercent}%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>


          <section className="progress-panel">
            <button
              type="button"
              className="progress-panel-toggle"
              onClick={() =>
                setIndependenceOpen(
                  !independenceOpen
                )
              }
            >
              <div>
                <span className="workspace-overview-label">
                  {
                    t.progress
                      .mentorIndependence
                  }
                </span>

                <p>
                  {
                    t.progress
                      .mentorIndependenceDescription
                  }
                </p>
              </div>

              <span className="workspace-plan-chevron">
                {independenceOpen
                  ? "−"
                  : "+"}
              </span>
            </button>

            {independenceOpen && (
              <div className="progress-panel-content">
                {skills.map((skill) => {
                  const independence =
                    skill.last_assistance_level
                      ? ASSISTANCE_INDEPENDENCE_SCORE[
                          skill.last_assistance_level
                        ]
                      : 0;

                  return (
                    <div
                      className="mentor-progress-row"
                      key={skill.skill_name}
                    >
                      <div className="mentor-progress-header">
                        <div>
                          <strong>
                            {formatSkillName(
                              skill.skill_name
                            )}
                          </strong>

                          <span>
                            {
                              t.progress
                                .mentorMode
                            }
                            :{" "}
                            {getMentorModeLabel(
                              skill.last_assistance_level
                            )}
                          </span>
                        </div>

                        <strong>
                          {skill.last_assistance_level
                            ? `${independence}%`
                            : "—"}
                        </strong>
                      </div>

                      <div className="progress-bar-track">
                        <div
                          className="progress-bar-fill independence"
                          style={{
                            width:
                              `${independence}%`,
                          }}
                        />
                      </div>

                      <div className="mentor-progress-meta">
                        <span>
                          {
                            t.progress
                              .independenceTrend
                          }
                          :{" "}
                          {
                            t.progress.trends[
                              skill
                                .independence_trend
                            ]
                          }
                        </span>

                        <span>
                          {
                            t.progress
                              .practicePriority
                          }
                          :{" "}
                          {
                            t.progress.priorities[
                              skill
                                .practice_priority
                            ]
                          }
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>


          <section className="progress-panel">
            <button
              type="button"
              className="progress-panel-toggle"
              onClick={() =>
                setDetailsOpen(
                  !detailsOpen
                )
              }
            >
              <div>
                <span className="workspace-overview-label">
                  {t.progress.skillDetails}
                </span>

                <p>
                  {
                    t.progress
                      .skillDetailsDescription
                  }
                </p>
              </div>

              <span className="workspace-plan-chevron">
                {detailsOpen
                  ? "−"
                  : "+"}
              </span>
            </button>

            {detailsOpen && (
              <div className="progress-skill-detail-grid">
                {skills.map((skill) => (
                  <article
                    className="progress-skill-card"
                    key={skill.skill_name}
                  >
                    <div className="progress-skill-card-header">
                      <h3>
                        {formatSkillName(
                          skill.skill_name
                        )}
                      </h3>

                      <span>
                        {
                          t.progress.statuses[
                            skill.status
                          ]
                        }
                      </span>
                    </div>

                    <div className="progress-skill-stats">
                      <div>
                        <strong>
                          {
                            skill.attempts
                          }
                        </strong>

                        <span>
                          {
                            t.progress
                              .attempts
                          }
                        </span>
                      </div>

                      <div>
                        <strong>
                          {
                            skill
                              .successful_attempts
                          }
                        </strong>

                        <span>
                          {
                            t.progress
                              .successfulAttempts
                          }
                        </span>
                      </div>

                      <div>
                        <strong>
                          {Math.round(
                            skill.success_rate *
                              100
                          )}
                          %
                        </strong>

                        <span>
                          {
                            t.progress
                              .success
                          }
                        </span>
                      </div>

                      <div>
                        <strong>
                          {
                            getMentorModeLabel(
                              skill
                                .last_assistance_level
                            )
                          }
                        </strong>

                        <span>
                          {
                            t.progress
                              .mentorMode
                          }
                        </span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

        </div>
      )}
    </section>
  );
}


export default ProgressPage;