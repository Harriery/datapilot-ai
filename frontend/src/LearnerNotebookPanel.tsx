import {
  BookOpen,
  Check,
  Pencil,
  Plus,
  Save,
  Trash2,
  X,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

export type LearnerResumePayload = {
  topic_id?: string | null;
  subtopic_id?: string | null;
  practice_mode?: string | null;
  difficulty?: string | null;
  source_id?: string | null;
  source_exercise_id?: string | null;
  workspace_id?: string | null;
  stage?: string | null;
  current_view?: string | null;
  metadata?: Record<string, unknown>;
};

type LearnerNote = {
  note_id: string;
  learner_id: string;
  context_type: "practice" | "workspace";
  context_key: string;
  title: string | null;
  body: string;
  source_exercise_id: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type JournalResponse = {
  learner_id: string;
  context_type: "practice" | "workspace";
  context_key: string;
  resume_state: {
    learner_id: string;
    context_type: "practice" | "workspace";
    context_key: string;
    state: LearnerResumePayload;
    updated_at: string | null;
  } | null;
  notes: LearnerNote[];
};

type Props = {
  learnerId: string;
  contextType: "practice" | "workspace";
  contextKey: string | null;
  contextLabel: string;
  resumeState?: LearnerResumePayload | null;
};

function readable(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase()
    );
}

export default function LearnerNotebookPanel({
  learnerId,
  contextType,
  contextKey,
  contextLabel,
  resumeState = null,
}: Props) {
  const [open, setOpen] = useState(false);
  const [journal, setJournal] =
    useState<JournalResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingResume, setSavingResume] =
    useState(false);
  const [error, setError] =
    useState<string | null>(null);

  const [newTitle, setNewTitle] = useState("");
  const [newBody, setNewBody] = useState("");
  const [adding, setAdding] = useState(false);

  const [editingId, setEditingId] =
    useState<string | null>(null);
  const [editingTitle, setEditingTitle] =
    useState("");
  const [editingBody, setEditingBody] =
    useState("");

  const resumeSummary = useMemo(() => {
    const state =
      journal?.resume_state?.state ?? resumeState;

    if (!state) {
      return [];
    }

    if (contextType === "practice") {
      return [
        readable(state.topic_id),
        readable(state.subtopic_id),
        readable(state.practice_mode),
        readable(state.difficulty),
        readable(state.source_exercise_id),
      ].filter(Boolean) as string[];
    }

    return [
      readable(state.stage),
      readable(state.current_view),
    ].filter(Boolean) as string[];
  }, [
    contextType,
    journal,
    resumeState,
  ]);

  async function loadJournal() {
    if (!contextKey) {
      setJournal(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        context_type: contextType,
        context_key: contextKey,
      });

      const response = await fetch(
        `http://127.0.0.1:8000/mentor/journal/${learnerId}?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(
          "Notebook could not be loaded."
        );
      }

      setJournal(
        (await response.json()) as JournalResponse
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Notebook could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) {
      void loadJournal();
    }
  }, [
    open,
    learnerId,
    contextType,
    contextKey,
  ]);

  useEffect(() => {
    if (!contextKey || !resumeState) {
      return;
    }

    let cancelled = false;

    async function persistResume() {
      setSavingResume(true);

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/mentor/journal/${learnerId}/resume`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              context_type: contextType,
              context_key: contextKey,
              state: resumeState,
            }),
          }
        );

        if (
          !response.ok &&
          !cancelled
        ) {
          console.error(
            "Resume state could not be saved."
          );
        }
      } catch (caught) {
        if (!cancelled) {
          console.error(caught);
        }
      } finally {
        if (!cancelled) {
          setSavingResume(false);
        }
      }
    }

    void persistResume();

    return () => {
      cancelled = true;
    };
  }, [
    learnerId,
    contextType,
    contextKey,
    resumeState,
  ]);

  async function addNote() {
    if (!contextKey || !newBody.trim()) {
      return;
    }

    setAdding(true);
    setError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/mentor/journal/${learnerId}/notes`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            context_type: contextType,
            context_key: contextKey,
            title:
              newTitle.trim() || null,
            body: newBody.trim(),
            source_exercise_id:
              resumeState?.source_exercise_id
              ?? null,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          "Note could not be saved."
        );
      }

      setNewTitle("");
      setNewBody("");
      await loadJournal();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Note could not be saved."
      );
    } finally {
      setAdding(false);
    }
  }

  function beginEdit(note: LearnerNote) {
    setEditingId(note.note_id);
    setEditingTitle(note.title ?? "");
    setEditingBody(note.body);
  }

  async function saveEdit() {
    if (
      !editingId ||
      !editingBody.trim()
    ) {
      return;
    }

    setError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/mentor/journal/${learnerId}/notes/${editingId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title:
              editingTitle.trim() || null,
            body: editingBody.trim(),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          "Note could not be updated."
        );
      }

      setEditingId(null);
      await loadJournal();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Note could not be updated."
      );
    }
  }

  async function deleteNote(noteId: string) {
    setError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/mentor/journal/${learnerId}/notes/${noteId}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error(
          "Note could not be deleted."
        );
      }

      await loadJournal();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Note could not be deleted."
      );
    }
  }

  return (
    <>
      <button
        type="button"
        className="learner-notebook-trigger"
        disabled={!contextKey}
        onClick={() => setOpen(true)}
        title={
          contextKey
            ? "Open your learning notes"
            : "Choose a context first"
        }
      >
        <BookOpen
          size={16}
          aria-hidden="true"
        />
        <span>Notebook</span>
      </button>

      {open && (
        <>
          <button
            type="button"
            className="learner-notebook-backdrop"
            aria-label="Close notebook"
            onClick={() => setOpen(false)}
          />

          <aside
            className="learner-notebook-panel"
            aria-label="Learning notebook"
          >
            <header className="learner-notebook-header">
              <div>
                <span>LEARNING NOTEBOOK</span>
                <h3>{contextLabel}</h3>
              </div>

              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close notebook"
              >
                <X
                  size={18}
                  aria-hidden="true"
                />
              </button>
            </header>

            <div className="learner-notebook-body">
              <section className="learner-notebook-resume">
                <div className="learner-notebook-section-title">
                  <strong>Continue from here</strong>

                  {savingResume ? (
                    <span>Saving…</span>
                  ) : (
                    <span>
                      <Check
                        size={12}
                        aria-hidden="true"
                      />
                      Saved
                    </span>
                  )}
                </div>

                {resumeSummary.length ? (
                  <div className="learner-notebook-resume-tags">
                    {resumeSummary.map(
                      (item, index) => (
                        <span
                          key={`${item}-${index}`}
                        >
                          {item}
                        </span>
                      )
                    )}
                  </div>
                ) : (
                  <p>
                    Your current position will
                    appear here.
                  </p>
                )}
              </section>

              <section className="learner-notebook-add">
                <div className="learner-notebook-section-title">
                  <strong>Add a note</strong>
                  <Plus
                    size={14}
                    aria-hidden="true"
                  />
                </div>

                <input
                  type="text"
                  value={newTitle}
                  maxLength={120}
                  placeholder="Optional title"
                  onChange={(event) =>
                    setNewTitle(event.target.value)
                  }
                />

                <textarea
                  value={newBody}
                  maxLength={4000}
                  placeholder="What do you want to remember?"
                  onChange={(event) =>
                    setNewBody(event.target.value)
                  }
                />

                <button
                  type="button"
                  className="learner-notebook-primary"
                  disabled={
                    adding ||
                    !newBody.trim()
                  }
                  onClick={() => {
                    void addNote();
                  }}
                >
                  <Save
                    size={14}
                    aria-hidden="true"
                  />
                  {adding
                    ? "Saving…"
                    : "Save note"}
                </button>
              </section>

              <section className="learner-notebook-notes">
                <div className="learner-notebook-section-title">
                  <strong>Your notes</strong>
                  <span>
                    {journal?.notes.length ?? 0}
                  </span>
                </div>

                {error && (
                  <div className="learner-notebook-error">
                    {error}
                  </div>
                )}

                {loading ? (
                  <p>Loading notes…</p>
                ) : journal?.notes.length ? (
                  <div className="learner-notebook-note-list">
                    {journal.notes.map((note) => (
                      <article
                        key={note.note_id}
                        className="learner-notebook-note"
                      >
                        {editingId === note.note_id ? (
                          <>
                            <input
                              type="text"
                              value={editingTitle}
                              maxLength={120}
                              placeholder="Optional title"
                              onChange={(event) =>
                                setEditingTitle(
                                  event.target.value
                                )
                              }
                            />

                            <textarea
                              value={editingBody}
                              maxLength={4000}
                              onChange={(event) =>
                                setEditingBody(
                                  event.target.value
                                )
                              }
                            />

                            <div className="learner-notebook-note-actions">
                              <button
                                type="button"
                                onClick={() =>
                                  setEditingId(null)
                                }
                              >
                                Cancel
                              </button>

                              <button
                                type="button"
                                className="primary"
                                disabled={
                                  !editingBody.trim()
                                }
                                onClick={() => {
                                  void saveEdit();
                                }}
                              >
                                Save
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="learner-notebook-note-heading">
                              <div>
                                {note.title && (
                                  <strong>
                                    {note.title}
                                  </strong>
                                )}

                                {note.source_exercise_id && (
                                  <span>
                                    {readable(
                                      note.source_exercise_id
                                    )}
                                  </span>
                                )}
                              </div>

                              <div className="learner-notebook-note-icons">
                                <button
                                  type="button"
                                  aria-label="Edit note"
                                  onClick={() =>
                                    beginEdit(note)
                                  }
                                >
                                  <Pencil
                                    size={13}
                                    aria-hidden="true"
                                  />
                                </button>

                                <button
                                  type="button"
                                  aria-label="Delete note"
                                  onClick={() => {
                                    void deleteNote(
                                      note.note_id
                                    );
                                  }}
                                >
                                  <Trash2
                                    size={13}
                                    aria-hidden="true"
                                  />
                                </button>
                              </div>
                            </div>

                            <p>{note.body}</p>
                          </>
                        )}
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="learner-notebook-empty">
                    <BookOpen
                      size={20}
                      aria-hidden="true"
                    />
                    <p>
                      No notes yet. Save a short
                      reminder for your future self.
                    </p>
                  </div>
                )}
              </section>
            </div>
          </aside>
        </>
      )}
    </>
  );
}
