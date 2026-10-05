import { useMemo, useState } from "react";
import LearnerNotebookPanel from "./LearnerNotebookPanel";

export type PracticeCatalogSource = {
  source_id: string;
  name: string;
  repository: string;
  license: string;
  import_policy: string;
  delivery: "on_demand" | "metadata_only";
  topics: string[];
};

export type PracticeCatalogTopic = {
  topic_id: string;
  title: string;
  description: string;
  modes: string[];
  difficulties: Array<"easy" | "medium" | "hard">;
  subtopics: string[];
  mastery_policy: "evidence_based";
  mastery_signals: string[];
  mini_project_target: number;
  source_ids: string[];
};

export type PracticeCatalogData = {
  learner_id: string;
  level_completion_rule: string;
  project_unlock_rule: string;
  topics: PracticeCatalogTopic[];
  sources: PracticeCatalogSource[];
};

export type ExternalPracticeExercise = {
  source_id: string;
  source_exercise_id: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  practices: string[];
  prerequisites: string[];
  mastery_signals: string[];
  attribution: string;
};

export type PracticeTheoryChallenge = {
  challenge_id: string;
  skill_name: string;
  topic_id: string | null;
  subtopic_id: string | null;
  practice_mode: string | null;
  source_id: string | null;
  source_exercise_id: string | null;
  mastery_signals: string[];
  difficulty: "easy" | "medium" | "hard";
  challenge_type: "multiple_choice";
  title: string;
  instructions: string;
  options: string[];
  starter_code: string | null;
};

export type PracticeTheoryCheckData = {
  learner_id: string;
  topic_id: string;
  subtopic_id: string;
  difficulty: "easy" | "medium" | "hard";
  concept_id: string;
  challenge: PracticeTheoryChallenge;
  attribution: string;
};

export type ExternalPracticeContent = {
  learner_id: string;
  source_id: string;
  source_exercise_id: string;
  title: string;
  instructions: string;
  solution_filename: string | null;
  starter_code: string | null;
  attribution: string;
  source_revision: string | null;
  content_hash: string;
  cached: boolean;
};

type Props = {
  catalog: PracticeCatalogData | null;
  loading: boolean;
  error: string | null;
  onBack: () => void;
  onStartRecommended: () => void;
  onStartExternal: (data: {
    topicId: string;
    subtopicId: string;
    mode: string;
    difficulty: "easy" | "medium" | "hard";
    exercise: ExternalPracticeExercise;
    content: ExternalPracticeContent;
  }) => void;
  onStartTheory: (data: PracticeTheoryCheckData) => void;
};

function label(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/w/g, (char) =>
      char.toUpperCase()
    );
}

export default function PracticeCatalogPage({
  catalog,
  loading,
  error,
  onBack,
  onStartRecommended,
  onStartExternal,
  onStartTheory,
}: Props) {
  const [topicId, setTopicId] = useState<string | null>(null);
  const [subtopic, setSubtopic] = useState<string | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<
    "easy" | "medium" | "hard" | null
  >(null);
  const [startLoading, setStartLoading] = useState(false);
  const [startError, setStartError] =
    useState<string | null>(null);

  const selectedTopic = useMemo(
    () =>
      catalog?.topics.find(
        (topic) => topic.topic_id === topicId
      ) ?? null,
    [catalog, topicId]
  );

  const sourceNames = useMemo(() => {
    if (!catalog || !selectedTopic) {
      return [];
    }

    const selectedIds = new Set(
      selectedTopic.source_ids
    );

    return catalog.sources.filter((source) =>
      selectedIds.has(source.source_id)
    );
  }, [catalog, selectedTopic]);

  async function startSelectedPractice() {
    if (
      !catalog ||
      !selectedTopic ||
      !subtopic ||
      !mode ||
      !difficulty
    ) {
      return;
    }

    if (selectedTopic.topic_id !== "python") {
      setStartError(
        "External Practice currently supports Python first. Other topics are next."
      );
      return;
    }

    if (!["code", "theory"].includes(mode)) {
      setStartError(
        "This Practice mode is not connected yet."
      );
      return;
    }

    setStartLoading(true);
    setStartError(null);

    try {
      if (mode === "theory") {
        const conceptParams = new URLSearchParams({
          subtopic_id: subtopic,
        });

        const conceptResponse = await fetch(
          `http://127.0.0.1:8000/mentor/practice/source/exercism/python/${catalog.learner_id}/theory?${conceptParams.toString()}`
        );

        if (!conceptResponse.ok) {
          const detail = await conceptResponse
            .json()
            .catch(() => null);

          throw new Error(
            detail?.detail ||
            "Theory concepts could not be loaded."
          );
        }

        const conceptData = await conceptResponse.json() as {
          concepts: Array<{
            concept_id: string;
            title: string;
          }>;
        };

        const concept = conceptData.concepts[0];

        if (!concept) {
          throw new Error(
            "No theory concept is available for this focus area."
          );
        }

        const checkResponse = await fetch(
          "http://127.0.0.1:8000/mentor/practice/theory/check",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              learner_id: catalog.learner_id,
              subtopic_id: subtopic,
              concept_id: concept.concept_id,
              difficulty,
              language: "en",
            }),
          }
        );

        if (!checkResponse.ok) {
          const detail = await checkResponse
            .json()
            .catch(() => null);

          throw new Error(
            detail?.detail ||
            "Theory check could not be generated."
          );
        }

        const theoryData =
          await checkResponse.json() as PracticeTheoryCheckData;

        onStartTheory(theoryData);
        return;
      }

      const params = new URLSearchParams({
        subtopic_id: subtopic,
        difficulty,
        practice_mode: mode,
      });

      const sourceResponse = await fetch(
        `http://127.0.0.1:8000/mentor/practice/source/exercism/python/${catalog.learner_id}/next?${params.toString()}`
      );

      if (!sourceResponse.ok) {
        const detail = await sourceResponse
          .json()
          .catch(() => null);

        throw new Error(
          detail?.detail ||
          "Next exercise could not be loaded."
        );
      }

      const sourceData = await sourceResponse.json() as {
        status:
          | "new"
          | "resume"
          | "next"
          | "cycle_complete";
        exercise: ExternalPracticeExercise | null;
        completed_exercise_count: number;
        available_exercise_count: number;
      };

      if (
        sourceData.status === "cycle_complete" ||
        !sourceData.exercise
      ) {
        setStartError(
          `You have completed the available ${difficulty} exercises for this path. This is exercise coverage, not mastery yet.`
        );
        return;
      }

      const exercise = sourceData.exercise;

      const contentParams = new URLSearchParams({
        title: exercise.title,
      });

      const contentResponse = await fetch(
        `http://127.0.0.1:8000/mentor/practice/source/exercism/python/${catalog.learner_id}/exercise/${encodeURIComponent(exercise.source_exercise_id)}?${contentParams.toString()}`
      );

      if (!contentResponse.ok) {
        const detail = await contentResponse
          .json()
          .catch(() => null);

        throw new Error(
          detail?.detail ||
          "Exercise content could not be loaded."
        );
      }

      const content =
        await contentResponse.json() as ExternalPracticeContent;

      onStartExternal({
        topicId: selectedTopic.topic_id,
        subtopicId: subtopic,
        mode,
        difficulty,
        exercise,
        content,
      });
    } catch (caught) {
      setStartError(
        caught instanceof Error
          ? caught.message
          : "Practice could not be started."
      );
    } finally {
      setStartLoading(false);
    }
  }

  function selectTopic(nextTopicId: string) {
    const nextTopic = catalog?.topics.find(
      (topic) => topic.topic_id === nextTopicId
    );

    setTopicId(nextTopicId);
    setSubtopic(
      nextTopic?.subtopics[0] ?? null
    );
    setMode(nextTopic?.modes[0] ?? null);
    setDifficulty("easy");
  }

  return (
    <section className="workspace-page practice-v2-page">
      <div className="workspace-header practice-v2-header">
        <div>
          <button
            className="back-button"
            onClick={onBack}
          >
            ← Dashboard
          </button>

          <p className="workspace-eyebrow">
            PRACTICE V2
          </p>

          <h2>Build your skills deliberately</h2>

          <p>
            Choose a topic and focus area. DataPilot will
            track mastery, not a fixed question quota.
          </p>
        </div>

        <div className="practice-v2-header-actions">
          <LearnerNotebookPanel
            learnerId={catalog?.learner_id ?? "demo-learner"}
            contextType="practice"
            contextKey={
              topicId && subtopic
                ? `${topicId}:${subtopic}`
                : null
            }
            contextLabel={
              selectedTopic && subtopic
                ? `${selectedTopic.title} · ${label(subtopic)}`
                : "Practice"
            }
            resumeState={
              selectedTopic && subtopic
                ? {
                    topic_id: selectedTopic.topic_id,
                    subtopic_id: subtopic,
                    practice_mode: mode,
                    difficulty,
                  }
                : null
            }
          />

          <button
            type="button"
            className="secondary-button"
            onClick={onStartRecommended}
          >
            Recommended practice →
          </button>
        </div>
      </div>

      {loading ? (
        <div className="card practice-v2-loading">
          Loading practice catalog...
        </div>
      ) : error ? (
        <div className="python-error">
          <strong>Practice catalog error</strong>
          <p>{error}</p>
        </div>
      ) : !catalog ? (
        <div className="card">
          Practice catalog is not available.
        </div>
      ) : (
        <div className="practice-v2-shell">
          <aside className="practice-v2-topic-list">
            <strong>Topics</strong>

            {catalog.topics.map((topic) => (
              <button
                type="button"
                key={topic.topic_id}
                className={
                  topicId === topic.topic_id
                    ? "active"
                    : ""
                }
                onClick={() =>
                  selectTopic(topic.topic_id)
                }
              >
                <span>{topic.title}</span>
                <small>
                  {topic.subtopics.length} areas
                </small>
              </button>
            ))}
          </aside>

          <div className="practice-v2-workspace">
            {!selectedTopic ? (
              <div className="practice-v2-empty">
                <strong>Choose a topic</strong>
                <p>
                  Select the skill you want to refresh or
                  strengthen.
                </p>
              </div>
            ) : (
              <>
                <div className="practice-v2-topic-heading">
                  <div>
                    <p className="workspace-eyebrow">
                      {selectedTopic.title}
                    </p>
                    <h3>{selectedTopic.description}</h3>
                  </div>

                  <details className="practice-v2-source-details">
                    <summary>Sources</summary>
                    {sourceNames.map((source) => (
                      <span key={source.source_id}>
                        {source.name} · {source.license}
                      </span>
                    ))}
                  </details>
                </div>

                <div className="practice-v2-control-grid">
                  <label>
                    <span>Focus area</span>
                    <select
                      value={subtopic ?? ""}
                      onChange={(event) =>
                        setSubtopic(event.target.value)
                      }
                    >
                      {selectedTopic.subtopics.map(
                        (item) => (
                          <option
                            key={item}
                            value={item}
                          >
                            {label(item)}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <label>
                    <span>Practice mode</span>
                    <select
                      value={mode ?? ""}
                      onChange={(event) =>
                        setMode(event.target.value)
                      }
                    >
                      {selectedTopic.modes.map(
                        (item) => (
                          <option
                            key={item}
                            value={item}
                          >
                            {label(item)}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <label>
                    <span>Difficulty</span>
                    <select
                      value={difficulty ?? ""}
                      onChange={(event) =>
                        setDifficulty(
                          event.target.value as
                            | "easy"
                            | "medium"
                            | "hard"
                        )
                      }
                    >
                      {selectedTopic.difficulties.map(
                        (item) => (
                          <option
                            key={item}
                            value={item}
                          >
                            {label(item)}
                          </option>
                        )
                      )}
                    </select>
                  </label>
                </div>

                <div className="practice-v2-selected">
                  <div>
                    <span>Selected path</span>
                    <strong>
                      {selectedTopic.title}
                      {" · "}
                      {subtopic ? label(subtopic) : "All"}
                      {" · "}
                      {mode ? label(mode) : "Mixed"}
                      {" · "}
                      {difficulty
                        ? label(difficulty)
                        : "Easy"}
                    </strong>
                  </div>

                  <div className="practice-v2-mastery-signals">
                    <span>Mastery evidence</span>
                    <div>
                      {selectedTopic.mastery_signals.map(
                        (signal) => (
                          <small key={signal}>
                            {label(signal)}
                          </small>
                        )
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="run-button"
                    disabled={
                      startLoading ||
                      selectedTopic.topic_id !== "python" ||
                      (
                        mode === null ||
                        !["code", "theory"].includes(mode)
                      )
                    }
                    title={
                      selectedTopic.topic_id === "python" &&
                      (
                        mode !== null &&
                        ["code", "theory"].includes(mode)
                      )
                        ? (
                            mode === "theory"
                              ? "Start a source-grounded theory check"
                              : "Load a matching exercise"
                          )
                        : "This Practice path is not connected yet."
                    }
                    onClick={() => {
                      void startSelectedPractice();
                    }}
                  >
                    {startLoading
                      ? "Loading…"
                      : "Start practice"}
                  </button>
                </div>

                {startError && (
                  <div className="practice-v2-start-error">
                    {startError}
                  </div>
                )}

                <div className="practice-v2-project-note">
                  <strong>Mini projects</strong>
                  <span>
                    Unlock after mastery is demonstrated
                    across easy, medium and hard.
                  </span>
                  <small>
                    {selectedTopic.mini_project_target}
                    {" projects planned for this topic."}
                  </small>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
