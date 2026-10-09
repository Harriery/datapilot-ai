# Practice Cache Policy

Status: Architecture decision for Practice V2.

## Goal

Keep Practice fast and lightweight while preserving the learner's progress, learning history, and personal notes across long breaks.

The core rule is:

> Exercise content is disposable. Learning evidence and learner notes are persistent.

## 1. Persistent data

The following data is part of the learner's long-term record and must survive cache cleanup, application restarts, topic changes, and returns after long breaks.

### Learning evidence

Store small structured records such as:

- learner_id
- topic_id
- subtopic_id
- practice_mode
- difficulty
- source_id
- source_exercise_id
- challenge_id
- success
- assistance_level
- mastery signals
- timestamps

Do not depend on cached exercise files to calculate learner progress.

### Practice resume state

Store only the minimum information required to continue:

- last selected topic
- last selected subtopic
- last practice mode
- last difficulty
- last active source exercise id, when relevant
- mastery status
- last activity timestamp

If the exercise body has expired from cache, reload it from its source when the learner resumes.

### Learner notes

Learner notes are persistent and separate from exercise cache.

A note may belong to:

- a topic
- a subtopic
- an exercise
- a workspace
- a project stage

Typical examples:

- a concept the learner wants to remember
- a useful one-line pattern
- why a particular approach worked
- a short summary in the learner's own words
- a reminder such as "we validated row count before and after this transform"

Notes must remain available even when the external exercise content has been evicted.

The UI may later expose these notes through a compact right-side notebook panel that can be opened and closed from Practice and project/workspace screens.

## 2. Temporary data

External exercise content is cacheable but not permanent application state.

Examples:

- exercise instructions
- starter/template files
- test metadata
- source-specific supporting files

These files should be fetched only when needed.

They must not be copied into the learner's permanent project storage merely because an exercise was opened.

## 3. Cache isolation

Practice cache must be isolated from real workspace/project data.

Practice source cache and real Data Engineering work must not share the same lifecycle or storage quota.

Logical separation:

```text
External Practice Sources
        |
        v
Small source metadata
        |
        v
Temporary Practice Cache
        |
        v
Practice Runner

Learner Progress
Learning Evidence
Learner Notes
Resume State
        |
        v
Persistent Learner Storage

Workspace / Project Data
        |
        v
Separate Workspace Storage
```

A large project dataset, notebook output, transformation preview, or pipeline artifact must never compete with temporary Practice files for the same storage policy.

## 4. Cache cleanup

Practice cache uses bounded storage.

Policy:

- use TTL (time-to-live) for stale cached content
- use LRU (least recently used) eviction when the cache reaches its size limit
- remove temporary files that are no longer referenced by an active Practice session
- never delete learning evidence, learner notes, mastery history, or resume state as part of cache cleanup
- if content is missing after cleanup, fetch it again from the verified source

Exact TTL and cache-size values are deployment configuration, not hard-coded learning rules.

## 5. Source identity

Persistent records store source identity, not a permanent full copy of the source exercise.

At minimum:

- source_id
- source_exercise_id
- source revision or content hash when available

This lets DataPilot identify what the learner worked on while keeping the actual external content disposable.

If a source exercise changes later, the revision/hash helps distinguish the older learning event from the current source version.

## 6. Offline and source failure behavior

If a cached exercise is still available, an active Practice session may continue from cache.

If the cache has expired and the external source is unavailable:

- preserve the learner's progress and notes
- do not fabricate replacement source content
- show that the exercise cannot currently be reloaded
- allow the learner to select another available exercise or retry later

## 7. Security boundary

External source files are untrusted input.

Fetched Practice content must not receive automatic access to:

- workspace datasets
- environment variables
- API keys
- local filesystem outside the Practice sandbox/cache
- learner documents
- unrelated project state

Executable tests or code from external repositories must not be run directly in the main backend process without an explicit sandboxing policy.

## 8. Product rule

Practice history should answer two different questions:

1. **System view:** What has the learner demonstrated?
2. **Learner view:** What did I learn here, and how did I solve it?

Learning evidence answers the first.

Learner notes and resume state answer the second.

These records remain small and persistent even when the original exercise files are gone.
