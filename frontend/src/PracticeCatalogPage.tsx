import { useMemo, useState } from "react";

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

type Props = {
  catalog: PracticeCatalogData | null;
  loading: boolean;
  error: string | null;
  onBack: () => void;
  onStartRecommended: () => void;
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
}: Props) {
  const [topicId, setTopicId] = useState<string | null>(null);
  const [subtopic, setSubtopic] = useState<string | null>(null);
  const [mode, setMode] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<
    "easy" | "medium" | "hard" | null
  >(null);

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

        <button
          type="button"
          className="secondary-button"
          onClick={onStartRecommended}
        >
          Recommended practice →
        </button>
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
                    disabled
                    title="Exercise source adapter is the next implementation step."
                  >
                    Start practice
                  </button>
                </div>

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
