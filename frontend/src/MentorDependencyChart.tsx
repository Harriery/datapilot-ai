import {
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


export type MentorDependencyPointData = {
  attempt_number: number;
  skill_name: string;

  assistance_level:
    AssistanceLevel;

  independence_percent: number;

  created_at: string | null;
};


type MentorDependencyChartProps = {
  language: AppLanguage;

  history:
    MentorDependencyPointData[];
};


const CHART_WIDTH = 900;
const CHART_HEIGHT = 300;

const PADDING_LEFT = 92;
const PADDING_RIGHT = 34;
const PADDING_TOP = 24;
const PADDING_BOTTOM = 52;

const PLOT_WIDTH =
  CHART_WIDTH -
  PADDING_LEFT -
  PADDING_RIGHT;

const PLOT_HEIGHT =
  CHART_HEIGHT -
  PADDING_TOP -
  PADDING_BOTTOM;


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


function MentorDependencyChart({
  language,
  history,
}: MentorDependencyChartProps) {
  const t = translations[language];

  const [open, setOpen] =
    useState(true);


  function getX(
    index: number
  ) {
    if (history.length <= 1) {
      return (
        PADDING_LEFT +
        PLOT_WIDTH / 2
      );
    }

    return (
      PADDING_LEFT +
      (
        index /
        (history.length - 1)
      ) *
        PLOT_WIDTH
    );
  }


  function getY(
    independencePercent: number
  ) {
    return (
      PADDING_TOP +
      (
        (100 - independencePercent) /
        100
      ) *
        PLOT_HEIGHT
    );
  }


  const points = history
    .map(
      (item, index) =>
        `${getX(index)},${getY(
          item.independence_percent
        )}`
    )
    .join(" ");


  const levels = [
    {
      percent: 100,
      label:
        t.progress.mentorModes.NONE,
    },
    {
      percent: 75,
      label:
        t.progress.mentorModes.NUDGE,
    },
    {
      percent: 50,
      label:
        t.progress.mentorModes.GUIDE,
    },
    {
      percent: 25,
      label:
        t.progress.mentorModes.TEACH,
    },
    {
      percent: 0,
      label:
        t.progress.mentorModes
          .DEMONSTRATE,
    },
  ];


  return (
    <section className="progress-panel">
      <button
        type="button"
        className="progress-panel-toggle"
        onClick={() =>
          setOpen(!open)
        }
      >
        <div>
          <span className="workspace-overview-label">
            {
              t.progress
                .mentorDependencyHistory
            }
          </span>

          <p>
            {
              t.progress
                .mentorDependencyHistoryDescription
            }
          </p>
        </div>

        <span className="workspace-plan-chevron">
          {open ? "−" : "+"}
        </span>
      </button>


      {open && (
        <div className="progress-panel-content">
          {history.length === 0 ? (
            <p className="muted">
              {
                t.progress
                  .mentorDependencyEmpty
              }
            </p>

          ) : (
            <div className="mentor-history-chart">
              <svg
                viewBox={
                  `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`
                }
                role="img"
                aria-label={
                  t.progress
                    .mentorDependencyHistory
                }
              >
                {levels.map(
                  (level) => {
                    const y =
                      getY(
                        level.percent
                      );

                    return (
                      <g
                        key={
                          level.percent
                        }
                      >
                        <line
                          className="mentor-chart-grid-line"
                          x1={
                            PADDING_LEFT
                          }
                          x2={
                            CHART_WIDTH -
                            PADDING_RIGHT
                          }
                          y1={y}
                          y2={y}
                        />

                        <text
                          className="mentor-chart-level-label"
                          x={
                            PADDING_LEFT -
                            12
                          }
                          y={y + 4}
                          textAnchor="end"
                        >
                          {level.label}
                        </text>
                      </g>
                    );
                  }
                )}


                <polyline
                  className="mentor-chart-line"
                  points={points}
                />


                {history.map(
                  (
                    item,
                    index
                  ) => {
                    const x =
                      getX(index);

                    const y =
                      getY(
                        item.independence_percent
                      );

                    return (
                      <g
                        key={
                          `${item.attempt_number}-${item.skill_name}`
                        }
                      >
                        <circle
                          className="mentor-chart-point"
                          cx={x}
                          cy={y}
                          r="6"
                        >
                          <title>
                            {
                              t.progress
                                .attempt
                            }{" "}
                            {
                              item.attempt_number
                            }
                            {" · "}
                            {
                              formatSkillName(
                                item.skill_name
                              )
                            }
                            {" · "}
                            {
                              t.progress
                                .mentorModes[
                                item.assistance_level
                              ]
                            }
                            {" · "}
                            {
                              item.independence_percent
                            }
                            %
                          </title>
                        </circle>

                        <text
                          className="mentor-chart-attempt-label"
                          x={x}
                          y={
                            CHART_HEIGHT -
                            22
                          }
                          textAnchor="middle"
                        >
                          {
                            item.attempt_number
                          }
                        </text>
                      </g>
                    );
                  }
                )}


                <text
                  className="mentor-chart-axis-title"
                  x={
                    PADDING_LEFT +
                    PLOT_WIDTH / 2
                  }
                  y={
                    CHART_HEIGHT -
                    3
                  }
                  textAnchor="middle"
                >
                  {
                    t.progress
                      .attemptsAxis
                  }
                </text>
              </svg>


              <div className="mentor-history-summary">
                <span>
                  {
                    t.progress
                      .historyStart
                  }
                  :{" "}
                  <strong>
                    {
                      t.progress
                        .mentorModes[
                        history[0]
                          .assistance_level
                      ]
                    }
                  </strong>
                </span>

                <span>
                  {
                    t.progress
                      .historyCurrent
                  }
                  :{" "}
                  <strong>
                    {
                      t.progress
                        .mentorModes[
                        history[
                          history.length -
                          1
                        ]
                          .assistance_level
                      ]
                    }
                  </strong>
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}


export default MentorDependencyChart;