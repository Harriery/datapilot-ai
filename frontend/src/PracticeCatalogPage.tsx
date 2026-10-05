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
  level_target: number;
  theory_target: number;
  applied_target: number;
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

export default function PracticeCatalogPage({
  catalog,
  loading,
  error,
  onBack,
  onStartRecommended,
}: Props) {
  const [topicId, setTopicId] = useState<string | null>(null);
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
    setTopicId(nextTopicId);
    setMode(null);
    setDifficulty(null);
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
            Choose what you want to refresh, how you want
            to practice it, and the difficulty level.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={onStartRecommended}
        >
          Current adaptive challenge →
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
        <>
          <section className="practice-v2-section">
            <div className="practice-v2-section-heading">
              <div>
                <span>1</span>
                <div>
                  <strong>Choose a topic</strong>
                  <p>
                    Start with the skill you want to rebuild.
                  </p>
                </div>
              </div>
            </div>

            <div className="practice-topic-grid">
              {catalog.topics.map((topic) => (
                <button
                  type="button"
                  key={topic.topic_id}
                  className={
                    topicId === topic.topic_id
                      ? "practice-topic-card active"
                      : "practice-topic-card"
                  }
                  onClick={() =>
                    selectTopic(topic.topic_id)
                  }
                >
                  <strong>{topic.title}</strong>
                  <p>{topic.description}</p>
                  <span>
                    {topic.subtopics.length} subtopics
                  </span>
                </button>
              ))}
            </div>
          </section>

          {selectedTopic && (
            <section className="practice-v2-section">
              <div className="practice-v2-section-heading">
                <div>
                  <span>2</span>
                  <div>
                    <strong>
                      Choose how to practice
                    </strong>
                    <p>
                      Theory checks understanding; applied
                      modes make you write or design.
                    </p>
                  </div>
                </div>
              </div>

              <div className="practice-choice-row">
                {selectedTopic.modes.map(
                  (topicMode) => (
                    <button
                      type="button"
                      key={topicMode}
                      className={
                        mode === topicMode
                          ? "practice-choice active"
                          : "practice-choice"
                      }
                      onClick={() =>
                        setMode(topicMode)
                      }
                    >
                      {topicMode.replaceAll("_", " ")}
                    </button>
                  )
                )}
              </div>
            </section>
          )}

          {selectedTopic && mode && (
            <section className="practice-v2-section">
              <div className="practice-v2-section-heading">
                <div>
                  <span>3</span>
                  <div>
                    <strong>
                      Choose difficulty
                    </strong>
                    <p>
                      Each level has its own completion goal.
                    </p>
                  </div>
                </div>
              </div>

              <div className="practice-level-grid">
                {selectedTopic.difficulties.map(
                  (level) => (
                    <button
                      type="button"
                      key={level}
                      className={
                        difficulty === level
                          ? "practice-level-card active"
                          : "practice-level-card"
                      }
                      onClick={() =>
                        setDifficulty(level)
                      }
                    >
                      <div>
                        <strong>
                          {level.charAt(0).toUpperCase() +
                            level.slice(1)}
                        </strong>
                        <span>0 / {selectedTopic.level_target}</span>
                      </div>

                      <div className="practice-level-track">
                        <div style={{ width: "0%" }} />
                      </div>

                      <small>
                        Theory 0 / {selectedTopic.theory_target}
                        {" · "}
                        Applied 0 / {selectedTopic.applied_target}
                      </small>
                    </button>
                  )
                )}
              </div>
            </section>
          )}

          {selectedTopic && mode && difficulty && (
            <section className="card practice-v2-path-summary">
              <div>
                <p className="workspace-eyebrow">
                  SELECTED PATH
                </p>
                <h3>
                  {selectedTopic.title}
                  {" · "}
                  {mode.replaceAll("_", " ")}
                  {" · "}
                  {difficulty}
                </h3>

                <p>
                  {selectedTopic.subtopics
                    .map((item) =>
                      item.replaceAll("_", " ")
                    )
                    .join(" · ")}
                </p>
              </div>

              <div className="practice-v2-source-info">
                <strong>Exercise sources</strong>

                {sourceNames.map((source) => (
                  <span key={source.source_id}>
                    {source.name}
                    {" · "}
                    {source.license}
                    {" · "}
                    {source.delivery === "on_demand"
                      ? "on demand"
                      : "reference only"}
                  </span>
                ))}
              </div>

              <div className="practice-v2-unlock">
                <strong>
                  Level target: {selectedTopic.level_target}
                  {" successful exercises"}
                </strong>
                <span>
                  {selectedTopic.theory_target} theory +
                  {" "}
                  {selectedTopic.applied_target} applied
                </span>
                <span>
                  Complete easy, medium and hard to unlock
                  {" "}
                  {selectedTopic.mini_project_target}
                  {" mini projects."}
                </span>
              </div>

              <button
                type="button"
                className="run-button"
                disabled
                title="Exercise source adapter is the next implementation step."
              >
                Exercise pack integration next
              </button>
            </section>
          )}
        </>
      )}
    </section>
  );
}
