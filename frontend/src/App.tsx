import { useEffect, useState } from "react";
import {
  translations,
  type AppLanguage,
} from "./i18n";

import "./App.css";
import PersonalProjectDeliverables, {
  type ProjectDeliverableData,
} from "./PersonalProjectDeliverables";
import TasksPage from "./TasksPage";
import ProgressPage from "./ProgressPage";
import WorkspaceModeCards from "./WorkspaceModeCards";

import {
  runDataFrameTransformation,
  runPythonCode,
} from "./pythonRunner";



import {
  ArrowLeft,
  BriefcaseBusiness,
  Plus,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";

type SkillProgressData = {
  skill_name: string;
  status: "new" | "learning" | "practicing" | "comfortable";
  attempts: number;
  successful_attempts: number;
  success_rate: number;
  last_assistance_level:
    | "NONE"
    | "NUDGE"
    | "GUIDE"
    | "TEACH"
    | "DEMONSTRATE"
    | null;
  independence_trend:
    | "improving"
    | "stable"
    | "declining"
    | "insufficient_data";
  practice_priority: "high" | "medium" | "low" | "none";
};

type PracticeRecommendationData = {
  skill_name: string;
  priority: "high" | "medium" | "low";
  difficulty: "foundation" | "easy" | "medium" | "hard";
  reason: string;
};

type WorkspaceValidationCheckCode =
  | "dataset_integrity"
  | "schema_preserved"
  | "duplicate_rows"
  | "missing_values";

type WorkspaceValidationResult = {
  passed: boolean;
  source_row_count: number;
  working_row_count: number;

  checks: {
    name: string;

    status:
      | "passed"
      | "failed"
      | "warning";

    message: string;

    code?: WorkspaceValidationCheckCode | null;

    params?: Record<string, unknown>;
  }[];
};

type DashboardWorkspace = {
  workspace_id: string;
  title: string;
  status: "active" | "paused" | "completed";
  current_task_id: string | null;
  dataset_filename?: string | null;

  dataset_profile?:
    | WorkspaceDataProfileResponse["profile"]
    | null;

  dataset_analysis?:
    | WorkspaceDataProfileResponse["analysis"]
    | null;
  mentor_session_id: string | null;

  validation_result?:
  | WorkspaceValidationResult
  | null;

  checkpoint: {
    completed_items: string[];
    current_focus: string | null;
    blocked_reason: string | null;
    last_error: string | null;
    next_actions: string[];
  };

  task_brief: string | null;
  desired_outcome: string | null;

  project_type:
    | "data_engineering"
    | "data_analysis"
    | "bi_dashboard"
    | "data_quality"
    | "portfolio"
    | null;
  
  project_deliverables?:
    ProjectDeliverableData[];

  usage_context: "work" | "personal";

  data_sensitivity:
    | "public"
    | "internal"
    | "confidential"
    | "restricted"
    | "unknown"
    | null;

  workflow_type:
    | "auto"
    | "etl"
    | "elt"
    | "data_quality"
    | "analysis"
    | "pipeline";
};

type WorkspaceDataProfileResponse = {
  workspace_id: string;
  filename: string | null;

  profile: {
    row_count: number;
    column_count: number;
    columns: string[];
    null_counts: Record<string, number>;
    duplicate_count: number;
  };

  analysis: {
    findings: {
      issue_type: string;
      column: string | null;
      severity: "low" | "medium" | "high";
      observation: string;
      suggested_action: string;
    }[];
  };
};

type WorkspaceWorkingData = {
  columns: string[];
  row_count: number;
  rows: Record<string, unknown>[];
};

type WorkspaceVersionSummary = {
  version_number: number;
  label: string;
  created_at: string;
  row_count: number;
};

type WorkspaceTask = {
  task_id: string;
  title: string;

  steps: {
    step_number: number;
    title: string;

    finding: {
      issue_type: string;
      column: string | null;
      severity: "low" | "medium" | "high";
      observation: string;
      suggested_action: string;
    };

    status: "pending" | "active" | "completed";
  }[];

  current_step_number: number;

  status: "pending" | "active" | "completed";
};

type PracticeChallengeData = {
  challenge_id: string;
  skill_name: string;
  difficulty: "foundation" | "easy" | "medium" | "hard";
  challenge_type:
    | "code"
    | "debug"
    | "output_prediction"
    | "sql"
    | "data_investigation"
    | "transformation"
    | "validation"
    | "explain";
  title: string;
  instructions: string;
  context_code: string | null;
  options: string[] | null;
  starter_code: string | null;
  input_rows: Record<string, unknown>[] | null;
};

type PracticeAttemptReviewData = {
  learner_id: string;
  challenge_id: string;
  attempt_id: string;
  attempt_number: number;

  validation: {
    success: boolean;
    feedback: string;
  };

  mentor_support: {
    message: string;
    micro_check: string | null;
  } | null;
};

type PracticeHintData = {
  challenge_id: string;
  hint: string | null;
  hint_number: number;
  total_hints: number;
  assistance_level:
    | "NUDGE"
    | "GUIDE"
    | "TEACH"
    | null;
  solution_available: boolean;
};

type PracticeSolutionData = {
  challenge_id: string;
  solution: string;
  assistance_level: "DEMONSTRATE";
};


function App() {
  const [language, setLanguage] =
    useState<AppLanguage>("en");

  const t = translations[language];

  function getValidationCheckText(
    check: WorkspaceValidationResult["checks"][number]
  ) {
    const params = check.params ?? {};
  
    const legacyCode =
      check.name === "Dataset integrity"
        ? "dataset_integrity"
        : check.name === "Schema preserved"
          ? "schema_preserved"
          : check.name === "Duplicate rows"
            ? "duplicate_rows"
            : check.name.startsWith("Missing values")
              ? "missing_values"
              : null;
  
    const code = check.code ?? legacyCode;
  
    if (code === "dataset_integrity") {
      const rowCount =
        typeof params.row_count === "number"
          ? params.row_count
          : workspaceValidation?.working_row_count ?? 0;
    
      return {
        name:
          t.workspace.validationChecks.datasetIntegrity,
      
        message:
          t.workspace.validationChecks
            .datasetIntegrityMessage(rowCount),
      };
    }
  
    if (code === "schema_preserved") {
      const preserved =
        typeof params.preserved === "boolean"
          ? params.preserved
          : check.status === "passed";
    
      return {
        name:
          t.workspace.validationChecks.schemaPreserved,
      
        message: preserved
          ? t.workspace.validationChecks
              .schemaPreservedMessage
          : t.workspace.validationChecks
              .schemaChangedMessage,
      };
    }
  
    if (code === "duplicate_rows") {
      const legacyCount =
        Number.parseInt(
          check.message.match(/^\d+/)?.[0] ?? "0",
          10
        );
      
      const duplicateCount =
        typeof params.duplicate_count === "number"
          ? params.duplicate_count
          : legacyCount;
      
      return {
        name:
          t.workspace.validationChecks.duplicateRows,
      
        message:
          t.workspace.validationChecks
            .duplicateRowsMessage(duplicateCount),
      };
    }
  
    if (code === "missing_values") {
      const legacyCount =
        Number.parseInt(
          check.message.match(/^\d+/)?.[0] ?? "0",
          10
        );
      
      const legacyColumn =
        check.name.includes("·")
          ? check.name.split("·").at(-1)?.trim() ?? ""
          : "";
      
      const column =
        typeof params.column === "string"
          ? params.column
          : legacyColumn;
      
      const missingCount =
        typeof params.missing_count === "number"
          ? params.missing_count
          : legacyCount;
      
      return {
        name:
          t.workspace.validationChecks
            .missingValues(column),
      
        message:
          t.workspace.validationChecks
            .missingValuesMessage(
              missingCount,
              column
            ),
      };
    }
  
    return {
      name: check.name,
      message: check.message,
    };
  }

  const [showSkills, setShowSkills] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState<
  "dashboard"
  | "workspace"
  | "practice"
  | "tasks"
  |"progress"
  | "new-workspace"
  >("dashboard");
 

  const [workspaceId, setWorkspaceId] = useState<string | null>(
  null
  );
  const [resumeData, setResumeData] = useState<{
    title: string;
    status: string;
    checkpoint: {
      completed_items: string[];
      current_focus: string | null;
      blocked_reason: string | null;
      last_error: string | null;
      next_actions: string[];
    };
    next_action: string | null;
  } | null>(null);




  
  const [pythonRunning, setPythonRunning] = useState(false);
  const [transformationCode, setTransformationCode] =
  useState(`# Inspect age distribution
age_stats = df["age"].describe()

median_age = df["age"].median()

df["age"] = df["age"].fillna(median_age)`);

  const [resultRows, setResultRows] = useState<
    Record<string, unknown>[] | null
  >(null);
  
  const [validationMessage, setValidationMessage] =
  useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [pythonError, setPythonError] = useState<string | null>(
  null
  );

  const [skillProgress, setSkillProgress] = useState<
  SkillProgressData[]
  >([]);

  const [practiceRecommendation, setPracticeRecommendation] =
  useState<PracticeRecommendationData | null>(null);

  const [dashboardLoading, setDashboardLoading] =
  useState(true);

  const [
    dashboardWorkspace,
    setDashboardWorkspace,
  ] = useState<DashboardWorkspace | null>(null);

  const [dashboardWorkspaces, setDashboardWorkspaces] =
  useState<DashboardWorkspace[]>([]);

  const [newWorkspaceTitle, setNewWorkspaceTitle] =
    useState("");

  const [newWorkspaceTaskBrief, setNewWorkspaceTaskBrief] =
    useState("");

  const [newWorkspaceOutcome, setNewWorkspaceOutcome] =
    useState("");

  const [newWorkspaceWorkflow, setNewWorkspaceWorkflow] =
    useState<
      | "auto"
      | "etl"
      | "elt"
      | "data_quality"
      | "analysis"
      | "pipeline"
    >("auto");

  type PersonalProjectType =
    | "data_engineering"
    | "data_analysis"
    | "bi_dashboard"
    | "data_quality"
    | "portfolio";

  const [
    newPersonalProjectType,
    setNewPersonalProjectType,
  ] = useState<PersonalProjectType | "">("");

  const [
    newWorkspaceUsageContext,
    setNewWorkspaceUsageContext,
  ] = useState<"work" | "personal">("work");

  const [
    newWorkspaceDataSensitivity,
    setNewWorkspaceDataSensitivity,
  ] = useState<
    | "public"
    | "internal"
    | "confidential"
    | "restricted"
    | "unknown"
  >("unknown");

  const [workspaceCreating, setWorkspaceCreating] =
    useState(false);

  const [workspaceCreateError, setWorkspaceCreateError] =
    useState<string | null>(null);

  const [
    workspaceDataProfile,
    setWorkspaceDataProfile,
  ] = useState<WorkspaceDataProfileResponse | null>(
    null
  );

  const [
    workspaceDataLoading,
    setWorkspaceDataLoading,
  ] = useState(false);

  const [
    workspaceDataError,
    setWorkspaceDataError,
  ] = useState<string | null>(null);
  
  const [
    workspaceTask,
    setWorkspaceTask,
  ] = useState<WorkspaceTask | null>(null);

  const [
    workspacePlanLoading,
    setWorkspacePlanLoading,
  ] = useState(false);

  const [
    workspacePlanError,
    setWorkspacePlanError,
  ] = useState<string | null>(null);

  const [
    workspaceWorkingData,
    setWorkspaceWorkingData,
  ] = useState<WorkspaceWorkingData | null>(
    null
  );

  const [
    workspaceWorkingDataLoading,
    setWorkspaceWorkingDataLoading,
  ] = useState(false);

  const [
    workspaceWorkingDataError,
    setWorkspaceWorkingDataError,
  ] = useState<string | null>(null);

  const [
    workspaceVersions,
    setWorkspaceVersions,
  ] = useState<WorkspaceVersionSummary[]>([]);

  const [
    workspaceVersionError,
    setWorkspaceVersionError,
  ] = useState<string | null>(null);

  const [
    restoringVersion,
    setRestoringVersion,
  ] = useState<number | null>(null);

  const [
    workspaceValidation,
    setWorkspaceValidation,
  ] = useState<WorkspaceValidationResult | null>(
    null
  );

  const [
    workspaceValidationLoading,
    setWorkspaceValidationLoading,
  ] = useState(false);

  const [
    workspaceValidationError,
    setWorkspaceValidationError,
  ] = useState<string | null>(null);

  const [
    workspaceReviewLoading,
    setWorkspaceReviewLoading,
  ] = useState(false);

  const [
    workspaceReviewError,
    setWorkspaceReviewError,
  ] = useState<string | null>(null);

  const [
    workspaceHandoffLoading,
    setWorkspaceHandoffLoading,
  ] = useState(false);

  const [
    workspaceHandoffError,
    setWorkspaceHandoffError,
  ] = useState<string | null>(null);

  const [
    workspaceExportLoading,
    setWorkspaceExportLoading,
  ] = useState(false);

  const [
    workspacePlanOpen,
    setWorkspacePlanOpen,
  ] = useState(true);

  const [
    workspaceDataOpen,
    setWorkspaceDataOpen,
  ] = useState(true);

  const [practiceChallenge, setPracticeChallenge] =
  useState<PracticeChallengeData | null>(null);

  const [practiceLoading, setPracticeLoading] =
    useState(false);

  const [practiceError, setPracticeError] =
    useState<string | null>(null);


  const [practiceCode, setPracticeCode] = useState("");

  const [practiceOutput, setPracticeOutput] =
    useState<string | null>(null);

  const [practiceExecutionError, setPracticeExecutionError] =
    useState<string | null>(null);

  const [practiceRunning, setPracticeRunning] =
    useState(false);

  const [practiceSubmitting, setPracticeSubmitting] =
  useState(false);

  const [practiceReview, setPracticeReview] =
    useState<PracticeAttemptReviewData | null>(null);

  const [practiceHint, setPracticeHint] =
  useState<PracticeHintData | null>(null);

  const [practiceHintLoading, setPracticeHintLoading] =
    useState(false);

  const [practiceHintError, setPracticeHintError] =
    useState<string | null>(null);

  const [practiceSolution, setPracticeSolution] =
  useState<PracticeSolutionData | null>(null);

  const [practiceSolutionLoading, setPracticeSolutionLoading] =
    useState(false);

  const [practiceSolutionError, setPracticeSolutionError] =
    useState<string | null>(null);



  
  useEffect(() => {
    async function loadDashboardData() {
      try {
        const learnerId = "demo-learner";

        const [
          progressResponse,
          recommendationResponse,
          workspaceResponse,
        ] = await Promise.all([
          fetch(
            `http://127.0.0.1:8000/mentor/progress/${learnerId}`
          ),
          fetch(
            `http://127.0.0.1:8000/mentor/practice/recommendation/${learnerId}`
          ),
          fetch(
            `http://127.0.0.1:8000/workspaces/${learnerId}`
          ),
        ]);

        if (!progressResponse.ok) {
          throw new Error(
            "Progress bilgisi alınamadı."
          );
        }

        if (!recommendationResponse.ok) {
          throw new Error(
            "Practice recommendation alınamadı."
          );
        }
        
        if (!workspaceResponse.ok) {
          throw new Error(
            "Workspace bilgisi alınamadı."
          );
        }

        const progressData =
          await progressResponse.json();

        const recommendationData =
          await recommendationResponse.json();

        const workspaceData: DashboardWorkspace[] =
          await workspaceResponse.json();

        setSkillProgress(progressData.skills);

        setPracticeRecommendation(
          recommendationData.recommendation
        );

        setDashboardWorkspaces(workspaceData);

        const defaultWorkspace =
          workspaceData.find(
            (workspace) => workspace.status === "active"
          ) ??
          workspaceData[0] ??
          null;
        
        setDashboardWorkspace(defaultWorkspace);

      } catch (error) {
        console.error(
          "Dashboard yüklenemedi:",
          error
        );
      } finally {
        setDashboardLoading(false);
      }
    }

    loadDashboardData();
  }, []);  

  async function openPractice() {
    // Zaten bir challenge yüklenmişse
    // yeni challenge oluşturma, sadece Practice ekranını aç.
    if (practiceChallenge) {
      setCurrentView("practice");
      return;
    }

    setPracticeLoading(true);
    setPracticeError(null);

    try {
      const learnerId = "demo-learner";

      const response = await fetch(
        `http://127.0.0.1:8000/mentor/practice/challenge/${learnerId}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Practice challenge oluşturulamadı."
        );
      }

      const data = await response.json();

      setPracticeChallenge(data.challenge);

      setPracticeCode(
        data.challenge.starter_code ?? ""
      );

      setPracticeOutput(null);
      setPracticeExecutionError(null);
      setPracticeHint(null);
      setPracticeHintError(null);

      setCurrentView("practice");
    } catch (error) {
      console.error(error);

      setPracticeError(
        error instanceof Error
          ? error.message
          : "Practice challenge yüklenemedi."
      );
    } finally {
      setPracticeLoading(false);
    }
  }

  async function runPracticeCode() {
    if (!practiceCode.trim()) {
      setPracticeExecutionError(
        "Önce Python kodunu yaz."
      );
      return;
    }

    setPracticeRunning(true);
    setPracticeOutput(null);
    setPracticeExecutionError(null);
    setPracticeReview(null);

    try {
      const executableCode = [
        practiceChallenge?.context_code ?? "",
        practiceCode,
      ]
        .filter(Boolean)
        .join("\n\n");

      const output =
        await runPythonCode(executableCode);

      setPracticeOutput(
        output || "Program finished with no output."
      );
    } catch (error) {
      console.error(error);

      const fullMessage =
        error instanceof Error
          ? error.message
          : "Python kodu çalıştırılamadı.";

      const lines = fullMessage
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

      setPracticeExecutionError(
        lines.at(-1) ??
          "Python kodu çalıştırılamadı."
      );
    } finally {
      setPracticeRunning(false);
    }
  }

  async function submitPracticeAnswer() {
    if (!practiceChallenge) {
      return;
    }

    if (
      practiceOutput === null &&
      practiceExecutionError === null
    ) {
      return;
    }

    setPracticeSubmitting(true);
    setPracticeReview(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/mentor/practice/attempt",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            learner_id: "demo-learner",

            challenge_id:
              practiceChallenge.challenge_id,

            answer: practiceCode,

            execution_output:
              practiceExecutionError === null
                ? practiceOutput
                : null,

            execution_error:
              practiceExecutionError,

            result_rows: null,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Practice cevabı değerlendirilemedi."
        );
      }

      const data: PracticeAttemptReviewData =
        await response.json();

      setPracticeReview(data);
    } catch (error) {
      console.error(error);

      setPracticeExecutionError(
        error instanceof Error
          ? error.message
          : "Practice cevabı gönderilemedi."
      );
    } finally {
      setPracticeSubmitting(false);
    }
  }

  async function requestPracticeHint() {
    if (!practiceChallenge) {
      return;
    }

    setPracticeHintLoading(true);
    setPracticeHintError(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/mentor/practice/hint",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            learner_id: "demo-learner",
            challenge_id:
              practiceChallenge.challenge_id,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Hint alınamadı."
        );
      }

      const data: PracticeHintData =
        await response.json();

      setPracticeHint(data);
    } catch (error) {
      console.error(error);

      setPracticeHintError(
        error instanceof Error
          ? error.message
          : "Hint alınamadı."
      );
    } finally {
      setPracticeHintLoading(false);
    }
  }

  async function requestPracticeSolution() {
    if (!practiceChallenge) {
      return;
    }

    setPracticeSolutionLoading(true);
    setPracticeSolutionError(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/mentor/practice/solution",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            learner_id: "demo-learner",
            challenge_id:
              practiceChallenge.challenge_id,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Solution alınamadı."
        );
      }

      const data: PracticeSolutionData =
        await response.json();

      setPracticeSolution(data);
    } catch (error) {
      console.error(error);

      setPracticeSolutionError(
        error instanceof Error
          ? error.message
          : "Solution alınamadı."
      );
    } finally {
      setPracticeSolutionLoading(false);
    }
  }

async function loadWorkspaceVersions(
  targetWorkspaceId: string
) {
  setWorkspaceVersionError(null);

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/workspaces/demo-learner/${targetWorkspaceId}/versions`
    );

    if (!response.ok) {
      throw new Error(
        "Version history yüklenemedi."
      );
    }

    const versions: WorkspaceVersionSummary[] =
      await response.json();

    setWorkspaceVersions(versions);
  } catch (error) {
    setWorkspaceVersionError(
      error instanceof Error
        ? error.message
        : "Version history yüklenemedi."
    );
  }
}


async function openSelectedWorkspace(
  workspace: Pick<
    DashboardWorkspace,
    "workspace_id"
  >
) {
  const learnerId = "demo-learner";

  try {
    setWorkspaceDataProfile(null);
    setWorkspaceDataError(null);
    setWorkspaceTask(null);
    setWorkspacePlanError(null);
    setWorkspaceWorkingData(null);
    setWorkspaceWorkingDataError(null);
    setWorkspaceVersions([]);
    setWorkspaceVersionError(null);
    setWorkspaceValidation(null);
    setWorkspaceValidationError(null);
    setWorkspaceReviewError(null);
    setWorkspaceHandoffError(null);
    setTransformationCode(
    "# df is already loaded.\n# Write your pandas transformation below.\n"
    );
    setResultRows(null);
    setPythonError(null);
    setValidationMessage(null);

    // Dashboard'daki kopyaya güvenmek yerine
    // workspace'in en güncel halini backend'den alıyoruz.
    const workspaceResponse = await fetch(
      `http://127.0.0.1:8000/workspaces/${learnerId}/${workspace.workspace_id}`
    );

    if (!workspaceResponse.ok) {
      throw new Error(
        "Workspace bilgisi yüklenemedi."
      );
    }

    const latestWorkspace: DashboardWorkspace =
      await workspaceResponse.json();

    setWorkspaceId(
      latestWorkspace.workspace_id
    );

 

    setDashboardWorkspace(
      latestWorkspace
    );

    setWorkspaceValidation(
      latestWorkspace.validation_result ?? null
    );

    // Persist edilmiş dataset profile varsa
    // frontend state'ine geri yüklüyoruz.
    if (
      latestWorkspace.dataset_profile &&
      latestWorkspace.dataset_analysis
    ) {
      setWorkspaceDataProfile({
        workspace_id:
          latestWorkspace.workspace_id,

        filename:
          latestWorkspace.dataset_filename ??
          null,

        profile:
          latestWorkspace.dataset_profile,

        analysis:
          latestWorkspace.dataset_analysis,
      });

    }

    if (latestWorkspace.dataset_profile) {
      setWorkspaceWorkingDataLoading(true);

      try {
        const workingDataResponse = await fetch(
          `http://127.0.0.1:8000/workspaces/${learnerId}/${latestWorkspace.workspace_id}/data/working`
        );
      
        if (!workingDataResponse.ok) {
          throw new Error(
            "Working dataset yüklenemedi."
          );
        }
      
        const workingData: WorkspaceWorkingData =
          await workingDataResponse.json();
      
        setWorkspaceWorkingData(workingData);
        
      } catch (error) {
        setWorkspaceWorkingDataError(
          error instanceof Error
            ? error.message
            : "Working dataset yüklenemedi."
        );
      } finally {
        setWorkspaceWorkingDataLoading(false);
      }
    }

    await loadWorkspaceVersions(
      latestWorkspace.workspace_id
    );

    const resumeResponse = await fetch(
      `http://127.0.0.1:8000/workspaces/${learnerId}/${latestWorkspace.workspace_id}/resume`
    );

    if (!resumeResponse.ok) {
      throw new Error(
        "Workspace resume bilgisi yüklenemedi."
      );
    }

    const resume =
      await resumeResponse.json();

    setResumeData(resume);

    if (latestWorkspace.current_task_id) {
      const taskResponse = await fetch(
        `http://127.0.0.1:8000/mentor/task/${latestWorkspace.current_task_id}?learner_id=${learnerId}`
      );

      if (taskResponse.ok) {
        const task: WorkspaceTask =
          await taskResponse.json();

        setWorkspaceTask(task);
      }
    }

    setCurrentView("workspace");
  } catch (error) {
    console.error(error);

    alert(
      error instanceof Error
        ? error.message
        : "Workspace açılırken hata oluştu."
    );
  }
}

async function uploadWorkspaceData(
    file: File | null
  ) {
    if (!file || !workspaceId) {
      return;
    }

    setWorkspaceDataLoading(true);
    setWorkspaceDataError(null);

    try {
      const formData = new FormData();

      formData.append("file", file);

      const response = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/data/profile`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Dataset profile oluşturulamadı."
        );
      }

      const data: WorkspaceDataProfileResponse =
        await response.json();

      setWorkspaceDataProfile(data);

      // Backend yeni dataset yüklenince eski planı
      // geçersiz kılıyor. Frontend de aynı duruma gelsin.
      setWorkspaceTask(null);

      const workspaceResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}`
      );
      
      if (workspaceResponse.ok) {
        const updatedWorkspace: DashboardWorkspace =
          await workspaceResponse.json();
      
        setDashboardWorkspace(
          updatedWorkspace
        );
      
        setDashboardWorkspaces(
          (previous) =>
            previous.map((workspace) =>
              workspace.workspace_id ===
              updatedWorkspace.workspace_id
                ? updatedWorkspace
                : workspace
            )
        );
      }
          
      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/resume`
      );
      
      if (resumeResponse.ok) {
        const resume =
          await resumeResponse.json();
      
        setResumeData(resume);
      }

    } catch (error) {
      console.error(error);

      setWorkspaceDataError(
        error instanceof Error
          ? error.message
          : "Dataset yüklenemedi."
      );
    } finally {
      setWorkspaceDataLoading(false);
    }
  }

async function buildWorkspaceExecutionPlan() {
      if (!workspaceId || !workspaceDataProfile) {
        return;
      }
    
      setWorkspacePlanLoading(true);
      setWorkspacePlanError(null);
    
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/plan`,
          {
            method: "POST",
          
            headers: {
              "Content-Type": "application/json",
            },
          
            body: JSON.stringify({
              profile: workspaceDataProfile.profile,
              findings:
                workspaceDataProfile.analysis.findings,
            }),
          }
        );
      
        if (!response.ok) {
          const errorData = await response.json();
        
          throw new Error(
            errorData.detail ||
              "Execution plan oluşturulamadı."
          );
        }
      
        const data: {
          task: WorkspaceTask;
        } = await response.json();
      
        setWorkspaceTask(data.task);
      } catch (error) {
        console.error(error);
      
        setWorkspacePlanError(
          error instanceof Error
            ? error.message
            : "Execution plan oluşturulamadı."
        );
      } finally {
        setWorkspacePlanLoading(false);
      }
    }

async function createNewWorkspace() {
    const title = newWorkspaceTitle.trim();
    const taskBrief = newWorkspaceTaskBrief.trim();

    if (!title) {
      setWorkspaceCreateError(
        "Workspace name is required."
      );
      return;
    }



    if (!taskBrief) {
      setWorkspaceCreateError(
        "Task brief is required."
      );
      return;
    }

    if (
      newWorkspaceUsageContext === "personal" &&
      !newPersonalProjectType
    ) {
      setWorkspaceCreateError(
        "Please choose a project type."
      );
      return;
    }

    setWorkspaceCreating(true);
    setWorkspaceCreateError(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/workspaces",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            learner_id: "demo-learner",

            title,

            usage_context:
              newWorkspaceUsageContext,

            data_sensitivity:
              newWorkspaceUsageContext === "work"
                ? newWorkspaceDataSensitivity
                : null,

            task_brief: taskBrief,

            desired_outcome:
              newWorkspaceOutcome.trim() || null,
            
            project_type:
              newWorkspaceUsageContext === "personal"
                ? newPersonalProjectType || null
                : null,

            workflow_type:
              newWorkspaceWorkflow,

            workspace_type:
              "data_engineering",

            current_task_id: null,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Workspace oluşturulamadı."
        );
      }

      const workspace = await response.json();

      setWorkspaceId(workspace.workspace_id);
      

      setNewWorkspaceTitle("");
      setNewWorkspaceTaskBrief("");
      setNewWorkspaceOutcome("");
      setNewWorkspaceWorkflow("auto");
      setNewWorkspaceUsageContext("work");
      setNewPersonalProjectType("");
      setNewWorkspaceDataSensitivity("unknown");

      // Şimdilik yeni workspace oluşturulduktan sonra
      // Dashboard'a dönüyoruz.
      // Sonraki adımda workspace listesine ekleyeceğiz.
      setCurrentView("dashboard");
    } catch (error) {
      console.error(error);

      setWorkspaceCreateError(
        error instanceof Error
          ? error.message
          : "Workspace oluşturulamadı."
      );
    } finally {
      setWorkspaceCreating(false);
    }
  }

async function runWorkspaceValidation() {
    if (!workspaceId) {
      setWorkspaceValidationError(
        "Workspace bulunamadı."
      );
      return;
    }

    setWorkspaceValidationLoading(true);
    setWorkspaceValidationError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/validate`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Workspace validation başarısız."
        );
      }

      const data: WorkspaceValidationResult =
        await response.json();

      setWorkspaceValidation(data);

      const workspaceResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}`
      );

      if (workspaceResponse.ok) {
        const updatedWorkspace: DashboardWorkspace =
          await workspaceResponse.json();

        setDashboardWorkspace(
          updatedWorkspace
        );
      }

      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/resume`
      );

      if (resumeResponse.ok) {
        const updatedResume =
          await resumeResponse.json();

        setResumeData(updatedResume);
      }
    } catch (error) {
      setWorkspaceValidationError(
        error instanceof Error
          ? error.message
          : "Workspace validation başarısız."
      );
    } finally {
      setWorkspaceValidationLoading(false);
    }
  }

async function completeWorkspaceReview() {
    if (!workspaceId) {
      setWorkspaceReviewError(
        "Workspace bulunamadı."
      );
      return;
    }

    setWorkspaceReviewLoading(true);
    setWorkspaceReviewError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/review/complete`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Review tamamlanamadı."
        );
      }

      await response.json();

      const workspaceResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}`
      );

      if (!workspaceResponse.ok) {
        throw new Error(
          "Review tamamlandı fakat workspace durumu yenilenemedi."
        );
      }

      const updatedWorkspace: DashboardWorkspace =
        await workspaceResponse.json();

      setDashboardWorkspace(
        updatedWorkspace
      );

      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/resume`
      );

      if (resumeResponse.ok) {
        const updatedResume =
          await resumeResponse.json();

        setResumeData(updatedResume);
      }
    } catch (error) {
      setWorkspaceReviewError(
        error instanceof Error
          ? error.message
          : "Review tamamlanamadı."
      );
    } finally {
      setWorkspaceReviewLoading(false);
    }
  }

async function downloadWorkspaceHandoff() {
  if (!workspaceId) {
    setWorkspaceHandoffError(
      "Workspace bulunamadı."
    );
    return;
  }

  setWorkspaceExportLoading(true);
  setWorkspaceHandoffError(null);

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/handoff/export`
    );

    if (!response.ok) {
      const errorData = await response.json();

      throw new Error(
        errorData.detail ||
          "Final CSV indirilemedi."
      );
    }

    const blob = await response.blob();

    const downloadUrl =
      URL.createObjectURL(blob);

    const link =
      document.createElement("a");

    link.href = downloadUrl;
    link.download = "datapilot_final.csv";

    document.body.appendChild(link);

    link.click();

    link.remove();

    URL.revokeObjectURL(
      downloadUrl
    );
  } catch (error) {
    setWorkspaceHandoffError(
      error instanceof Error
        ? error.message
        : "Final CSV indirilemedi."
    );
  } finally {
    setWorkspaceExportLoading(false);
  }
}


async function completeWorkspaceHandoff() {
  if (!workspaceId) {
    setWorkspaceHandoffError(
      "Workspace bulunamadı."
    );
    return;
  }

  setWorkspaceHandoffLoading(true);
  setWorkspaceHandoffError(null);

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/handoff/complete`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const errorData = await response.json();

      throw new Error(
        errorData.detail ||
          "Handoff tamamlanamadı."
      );
    }

    const updatedWorkspace: DashboardWorkspace =
      await response.json();

    setDashboardWorkspace(
      updatedWorkspace
    );

    setDashboardWorkspaces(
      (previous) =>
        previous.map((workspace) =>
          workspace.workspace_id ===
          updatedWorkspace.workspace_id
            ? updatedWorkspace
            : workspace
        )
    );

    const resumeResponse = await fetch(
      `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/resume`
    );

    if (resumeResponse.ok) {
      const updatedResume =
        await resumeResponse.json();

      setResumeData(
        updatedResume
      );
    }
  } catch (error) {
    setWorkspaceHandoffError(
      error instanceof Error
        ? error.message
        : "Handoff tamamlanamadı."
    );
  } finally {
    setWorkspaceHandoffLoading(false);
  }
}


async function runTransformation() {
    if (!transformationCode.trim()) {
      setPythonError(
        "Önce Python transformation kodunu yaz."
      );
      return;
    }
    if (!workspaceWorkingData) {
      setPythonError(
        "Working dataset henüz yüklenmedi."
      );
      return;
    }
    setPythonRunning(true);
    setResultRows(null);
    setPythonError(null);
    setValidationMessage(null);
    try {
      const result =
        await runDataFrameTransformation(
          transformationCode,
          workspaceWorkingData.rows
        );
      setResultRows(result);
    } catch (error) {
      console.error(error);
      const fullMessage =
        error instanceof Error
          ? error.message
          : "Python kodu çalıştırılamadı.";
      const lines = fullMessage
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      const shortMessage =
        lines.at(-1) ??
        "Python kodu çalıştırılamadı.";
      setPythonError(shortMessage);
    } finally {
      setPythonRunning(false);
    }
  }

async function submitWorkspaceTransformation() {
    if (
      !workspaceId ||
      !workspaceTask ||
      !resultRows
    ) {
      setValidationMessage(
        "Önce transformation kodunu çalıştır."
      );
      return;
    }

    setSubmitting(true);
    setValidationMessage(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/data/transform`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            after_rows: resultRows,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Transformation doğrulanamadı."
        );
      }

      const data: {
        task: WorkspaceTask;

        validation: {
          success: boolean;
        };

        skill_name: string;
        skill_status: string;
      } = await response.json();

      setWorkspaceTask(data.task);

      if (!data.validation.success) {
        setValidationMessage(
          "❌ Validation failed. working.csv değiştirilmedi."
        );

        return;
      }

      // Validation başarılıysa backend working.csv'yi
      // zaten güncelledi. Yeni halini tekrar çekiyoruz.
      const workingDataResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/data/working`
      );

      if (!workingDataResponse.ok) {
        throw new Error(
          "Transformation kaydedildi fakat güncel dataset yüklenemedi."
        );
      }

      const workingData: WorkspaceWorkingData =
        await workingDataResponse.json();

      setWorkspaceWorkingData(workingData);
        await loadWorkspaceVersions(
          workspaceId
        );

      setWorkspaceValidation(null);
      setWorkspaceValidationError(null);

      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/resume`
      );

      if (!resumeResponse.ok) {
        throw new Error(
          "Transformation kaydedildi fakat workspace durumu yenilenemedi."
        );
      }

      const updatedResume =
        await resumeResponse.json();

      setResumeData(updatedResume);

      setDashboardWorkspace((previous) => {
        if (!previous) {
          return previous;
        }

        return {
          ...previous,
          checkpoint:
            updatedResume.checkpoint,
        };
      });

      setResultRows(null);
      setPythonError(null);

      setTransformationCode(
        "# df is already loaded.\n# Write your pandas transformation below.\n"
      );

      if (data.task.status === "completed") {
        setValidationMessage(
          "✅ Transformation validated. Execution plan transformations are complete."
        );
      } else {
        setValidationMessage(
          "✅ Transformation validated and saved. The next step is now active."
        );
      }
    } catch (error) {
      console.error(error);

      setValidationMessage(
        error instanceof Error
          ? `❌ ${error.message}`
          : "❌ Beklenmeyen bir hata oluştu."
      );
    } finally {
      setSubmitting(false);
    }
  }

async function restoreWorkspaceVersion(
    versionNumber: number
  ) {
    if (!workspaceId) {
      return;
    }

    const confirmed = window.confirm(
      `Version ${versionNumber} geri yüklensin mi?\n\nMevcut working dataset ve task durumu bu checkpoint'e dönecek.`
    );

    if (!confirmed) {
      return;
    }

    setRestoringVersion(versionNumber);
    setWorkspaceVersionError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/versions/${versionNumber}/restore`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail ||
            "Version geri yüklenemedi."
        );
      }

      const data: {
        version_number: number;

        task: WorkspaceTask;

        working_data: WorkspaceWorkingData;
      } = await response.json();

      setWorkspaceTask(data.task);

      setWorkspaceWorkingData(
        data.working_data
      );
      setWorkspaceValidation(null);
      setWorkspaceValidationError(null);


      const resumeResponse = await fetch(
        `http://127.0.0.1:8000/workspaces/demo-learner/${workspaceId}/resume`
      );

      if (!resumeResponse.ok) {
        throw new Error(
          "Version restore edildi fakat workspace bilgisi yenilenemedi."
        );
      }

      const updatedResume =
        await resumeResponse.json();

      setResumeData(updatedResume);

      setDashboardWorkspace((previous) => {
        if (!previous) {
          return previous;
        }

        return {
          ...previous,
          current_task_id:
            data.task.task_id,
          checkpoint:
            updatedResume.checkpoint,
        };
      });

      setResultRows(null);
      setPythonError(null);

      setTransformationCode(
        "# df is already loaded.\n# Write your pandas transformation below.\n"
      );

      setValidationMessage(
        `↩ Version ${versionNumber} restored.`
      );

      await loadWorkspaceVersions(
        workspaceId
      );
    } catch (error) {
      console.error(error);

      setWorkspaceVersionError(
        error instanceof Error
          ? error.message
          : "Version geri yüklenemedi."
      );
    } finally {
      setRestoringVersion(null);
    }
  }

  const workspaceReviewCompleted =
    dashboardWorkspace?.checkpoint.completed_items.includes(
      "Final review completed"
    ) ?? false;
    
  const workspaceHandoffCompleted =
    dashboardWorkspace?.checkpoint.completed_items.includes(
      "Handoff completed"
    ) ?? false;  

  return (
    <div className="app-shell">
      <aside
        className={`sidebar ${
          sidebarCollapsed ? "collapsed" : ""
        }`}
      >
        <button
          className="sidebar-toggle"
          onClick={() =>
            setSidebarCollapsed(!sidebarCollapsed)
          }
        >
          {sidebarCollapsed ? "→" : "←"}
        </button>  

        <div className="brand">
          <div className="brand-icon">◆</div>

          <div className="brand-text">
            <h1>DataPilot AI</h1>
            <p>Adaptive Mentor</p>
          </div>
        </div>
        <div className="language-switch">
          <button
            type="button"
            className={
              language === "en"
                ? "language-option active"
                : "language-option"
            }
            onClick={() => setLanguage("en")}
          >
            EN
          </button>
          
          <button
            type="button"
            className={
              language === "tr"
                ? "language-option active"
                : "language-option"
            }
            onClick={() => setLanguage("tr")}
          >
            TR
          </button>
        </div>

      <nav className="nav-menu">
        <button
          className={
            currentView === "dashboard"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={() =>
            setCurrentView("dashboard")
          }
        >
          <span className="nav-icon">⌂</span>
          <span className="nav-label">
            {t.sidebar.dashboard}
          </span>
        </button>
        
        {currentView === "workspace" && (
          <button
            className="nav-item active"
            onClick={() =>
              setCurrentView("workspace")
            }
          >
            <span className="nav-icon">◇</span>
            <span className="nav-label">
              {t.sidebar.workspace}
            </span>
          </button>
        )}
      
        <button
          className={
            currentView === "practice"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={openPractice}
          disabled={practiceLoading}
        >
          <span className="nav-icon">◉</span>
        
          <span className="nav-label">
            {practiceLoading
              ? "Loading..."
              : t.sidebar.practice}
          </span>
        </button>
            
        <button
          className={
            currentView === "tasks"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={() =>
            setCurrentView("tasks")
          }
        >
          <span className="nav-icon">
            ✓
          </span>
        
          <span className="nav-label">
            {t.sidebar.tasks}
          </span>
        </button>
            
        <button
          className={
            currentView === "progress"
              ? "nav-item active"
              : "nav-item"
          }
          onClick={() =>
            setCurrentView("progress")
          }
        >
          <span className="nav-icon">
            ▥
          </span>
        
          <span className="nav-label">
            {t.sidebar.progress}
          </span>
        </button>
            
        <button className="nav-item">
          <span className="nav-icon">▤</span>
          <span className="nav-label">
            {t.sidebar.documents}
          </span>
        </button>
            
        <button className="nav-item">
          <span className="nav-icon">⚙</span>
          <span className="nav-label">
            {t.sidebar.settings}
          </span>
        </button>
      </nav>    
    </aside>

      <main className="main-content">
        {currentView === "dashboard" ? (
          <>
            <header className="page-header">
              <div>
                <h2>Good morning 👋</h2>
                <p>
                  Here’s what needs your attention today.
                </p>
              </div>
        
             <div className="dashboard-header-actions">
              <div className="profile-badge">
                Junior Data Engineer
              </div>
            </div>
            </header>

            <WorkspaceModeCards
              language={language}
              onStartPersonal={() => {
                setNewWorkspaceUsageContext(
                  "personal"
                );
              
                setNewWorkspaceDataSensitivity(
                  "public"
                );
              
                setCurrentView(
                  "new-workspace"
                );
              }}
              onExploreWork={() => {
                setNewWorkspaceUsageContext(
                  "work"
                );
              
                setNewWorkspaceDataSensitivity(
                  "unknown"
                );
              
                setCurrentView(
                  "new-workspace"
                );
              }}
            />

        
            <section className="dashboard-grid">
              
              <article className="card continue-card">
                <div className="card-heading">
                  <div>
                    <p className="workspace-eyebrow">
                      WORKSPACES
                    </p>
                              
                    <h3>Your workspaces</h3>
                  </div>
                              
                  <span className="status-badge">
                    {
                      dashboardWorkspaces.filter(
                        (workspace) =>
                          workspace.status === "active"
                      ).length
                    }{" "}
                    active
                  </span>
                </div>
                  
                {dashboardLoading ? (
                  <p className="muted">
                    Loading workspaces...
                  </p>
                ) : dashboardWorkspaces.length === 0 ? (
                  <p className="muted">
                    No workspaces yet.
                  </p>
                ) : (
                  <div className="dashboard-workspace-list">
                    {dashboardWorkspaces.map(
                      (workspace) => (
                        <div
                          className="dashboard-workspace-item"
                          key={workspace.workspace_id}
                        >
                          <div className="dashboard-workspace-main">
                            <div className="dashboard-workspace-title-row">
                              <strong>
                                {workspace.title}
                              </strong>
                      
                              <span
                                className={
                                  workspace.status ===
                                  "completed"
                                    ? "workspace-list-status completed"
                                    : "workspace-list-status active"
                                }
                              >
                                {workspace.status}
                              </span>
                            </div>
                              
                            <p>
                              {workspace.task_brief ??
                                "No task brief added yet."}
                            </p>
                              
                            <div className="workspace-list-meta">
                              <span>
                                {workspace.usage_context ===
                                "personal"
                                  ? "Personal"
                                  : "Work"}
                              </span>
                                
                              {workspace.data_sensitivity && (
                                <span>
                                  {
                                    workspace.data_sensitivity
                                  }
                                </span>
                              )}
              
                              <span>
                                {workspace.workflow_type}
                              </span>
                            </div>
                            <button
                              className="workspace-open-button"
                              onClick={() =>
                                openSelectedWorkspace(workspace)
                              }
                            >
                              Open workspace →
                            </button>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </article>
                
              <article className="card recommendation-card">
                <h3>Current Recommendation</h3>

                {dashboardLoading ? (
                  <p className="muted">
                    Loading recommendation...
                  </p>
                ) : practiceRecommendation ? (
                  <>
                    <p className="skill-name">
                      {practiceRecommendation.skill_name}
                    </p>
                
                    <div className="badge-row">
                      <span className="priority-badge">
                        {practiceRecommendation.priority} priority
                      </span>
                
                      <span className="difficulty-badge">
                        {practiceRecommendation.difficulty}
                      </span>
                    </div>
                
                    <p className="muted">
                      {practiceRecommendation.reason}
                    </p>
                  </>
                ) : (
                  <p className="muted">
                    No practice recommendation right now.
                  </p>
                )}
              </article>
                
              <article className="card learning-path-card">
                <h3>Today’s path</h3>

                {dashboardLoading ? (
                  <p className="muted">
                    Loading path...
                  </p>
                ) : !dashboardWorkspace ? (
                  <p className="muted">
                    No active workspace.
                  </p>
                ) : dashboardWorkspace.status === "completed" ? (
                  <div className="path-item completed">
                    <span>✓</span>
                
                    <div>
                      <strong>{t.workspace.workspaceCompleted}</strong>
                      <p>
                        {dashboardWorkspace.title} is finished.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="path-item completed">
                      <span>✓</span>
                
                      <div>
                        <strong>
                          {dashboardWorkspace.checkpoint.completed_items.at(-1) ??
                            "Workspace started"}
                        </strong>
                          
                        <p>Last completed step.</p>
                      </div>
                    </div>
                          
                    <div className="path-item current">
                      <span>●</span>
                          
                      <div>
                        <strong>
                          {dashboardWorkspace.checkpoint.current_focus ??
                            "No current focus"}
                        </strong>
                          
                        <p>This is your current focus.</p>
                      </div>
                    </div>
                          
                    {dashboardWorkspace.checkpoint.next_actions.map(
                      (action, index) => (
                        <div
                          className="path-item"
                          key={`${action}-${index}`}
                        >
                          <span>○</span>
                      
                          <div>
                            <strong>{action}</strong>
                      
                            <p>Next recommended step.</p>
                          </div>
                        </div>
                      )
                    )}
                  </>
                )}
              </article>      
                
              {showSkills ? (
                <article className="card skill-card">
                  <div className="card-heading">
                    <h3>Skill Progress</h3>
              
                    <button
                      className="icon-button"
                      onClick={() =>
                        setShowSkills(false)
                      }
                    >
                      ×
                    </button>
                  </div>

                  {dashboardLoading ? (
                    <p className="muted">
                      Loading skills...
                    </p>
                  ) : skillProgress.length === 0 ? (
                    <p className="muted">
                      No skill progress yet.
                    </p>
                  ) : (
                    skillProgress.map((skill) => (
                      <SkillProgress
                        key={skill.skill_name}
                        name={skill.skill_name}
                        status={
                          skill.status.charAt(0).toUpperCase() +
                          skill.status.slice(1)
                        }
                        progress={Math.round(
                          skill.success_rate * 100
                        )}
                      />
                    ))
                  )}  

                </article>
              ) : (
                <article className="card collapsed-skill-card">
                  <div>
                    <h3>Skill Progress</h3>
                    <p>Progress panel is hidden.</p>
                  </div>
              
                  <button
                    className="secondary-button"
                    onClick={() =>
                      setShowSkills(true)
                    }
                  >
                    Show skills →
                  </button>
                </article>
              )}
            </section>
          </>
                          ) : currentView === "tasks" ? (
                            <TasksPage
                              language={language}
                              onOpenWorkspace={(workspaceId) => {
                                void openSelectedWorkspace({
                                  workspace_id: workspaceId,
                                });
                              }}
                            />
                            
                          ) : currentView === "progress" ? (
                            <ProgressPage
                              language={language}
                            />
                          
                          ) : currentView === "new-workspace" ? (
            <section className="new-workspace-page">
              <div className="new-workspace-topbar">
                <button
                  className="back-button new-workspace-back"
                  onClick={() =>
                    setCurrentView("dashboard")
                  }
                >
                  <ArrowLeft
                    size={16}
                    aria-hidden="true"
                  />

                  {t.workspace.backToDashboard}
                </button>
              </div>
                
              <header className="new-workspace-header">
                <div>
                  <p className="workspace-eyebrow">
                    {newWorkspaceUsageContext === "personal"
                      ? "PERSONAL PROJECT SETUP"
                      : "SECURE WORK SETUP"}
                  </p>
                    
                  <h2>
                    {newWorkspaceUsageContext === "personal"
                      ? "Create a personal project"
                      : "Create a secure work workspace"}
                  </h2>
                    
                  <p>
                    {newWorkspaceUsageContext === "personal"
                      ? (
                          "Start with a project goal. DataPilot will guide you " +
                          "from raw data toward a validated, documented and " +
                          "usable data product."
                        )
                      : (
                          "Define the assignment you received from your team. " +
                          "DataPilot will guide the work while applying " +
                          "security controls to company or client data."
                        )}
                  </p>
                </div>
              </header>
                
              <div className="new-workspace-layout">
                <div className="workspace-create-card">
                  <div className="workspace-context-row">
                    <div className="workspace-context-field">
                      <span className="workspace-form-label">
                        Workspace type
                      </span>

                      <div
                        className="workspace-type-switch"
                        role="group"
                        aria-label="Workspace type"
                      >
                        <button
                          type="button"
                          className={
                            newWorkspaceUsageContext === "work"
                              ? "workspace-type-option active"
                              : "workspace-type-option"
                          }
                          onClick={() =>
                            setNewWorkspaceUsageContext("work")
                          }
                        >
                          <BriefcaseBusiness
                            size={16}
                            aria-hidden="true"
                          />

                          Work
                        </button>
                        
                        <button
                          type="button"
                          className={
                            newWorkspaceUsageContext === "personal"
                              ? "workspace-type-option active"
                              : "workspace-type-option"
                          }
                          onClick={() =>
                            setNewWorkspaceUsageContext("personal")
                          }
                        >
                          <UserRound
                            size={16}
                            aria-hidden="true"
                          />

                          Personal
                        </button>
                      </div>
                    </div>
                        
                    {newWorkspaceUsageContext === "work" && (
                      <div className="workspace-context-field">
                        <label
                          className="workspace-form-label sensitivity-label"
                          htmlFor="data-sensitivity"
                        >
                          <ShieldCheck
                            size={15}
                            aria-hidden="true"
                          />

                          Data sensitivity
                        </label>
                    
                        <select
                          id="data-sensitivity"
                          className="workspace-form-select"
                          value={newWorkspaceDataSensitivity}
                          onChange={(event) =>
                            setNewWorkspaceDataSensitivity(
                              event.target.value as
                                | "public"
                                | "internal"
                                | "confidential"
                                | "restricted"
                                | "unknown"
                            )
                          }
                        >
                          <option value="unknown">
                            Not sure yet
                          </option>
                        
                          <option value="public">
                            Public / non-sensitive
                          </option>
                        
                          <option value="internal">
                            Internal
                          </option>
                        
                          <option value="confidential">
                            Confidential
                          </option>
                        
                          <option value="restricted">
                            Restricted / sensitive
                          </option>
                        </select>
                      </div>
                    )}
                  </div>

                  {newWorkspaceUsageContext === "personal" && (
                    <div className="workspace-form-section">
                      <label
                        className="workspace-form-label"
                        htmlFor="personal-project-type"
                      >
                        What do you want to build?
                      </label>

                      <select
                        id="personal-project-type"
                        className="workspace-form-select"
                        value={newPersonalProjectType}
                        onChange={(event) =>
                          setNewPersonalProjectType(
                            event.target.value as
                              | PersonalProjectType
                              | ""
                          )
                        }
                      >
                        <option value="" disabled>
                          Choose a project type
                        </option>
                      
                        <option value="data_engineering">
                          Data Engineering Project
                        </option>
                      
                        <option value="data_analysis">
                          Data Analysis Project
                        </option>
                      
                        <option value="bi_dashboard">
                          BI / Dashboard Project
                        </option>
                      
                        <option value="data_quality">
                          Data Quality Project
                        </option>
                      
                        <option value="portfolio">
                          Portfolio Project
                        </option>
                      </select>
                      
                      <p className="workspace-field-help">
                        DataPilot will use this choice to shape the
                        project stages and final deliverables.
                      </p>
                    </div>
                  )}

                  <div className="workspace-form-row">
                    <div className="workspace-form-section">
                      <label
                        className="workspace-form-label"
                        htmlFor="workspace-name"
                      >
                        {newWorkspaceUsageContext === "personal"
                           ? "Project name"
                           : "Workspace name"}
                      </label>
                                  
                      <input
                        id="workspace-name"
                        className="workspace-form-input"
                        type="text"
                        placeholder={
                          newWorkspaceUsageContext === "personal"
                            ? "e.g. Netherlands Housing Analysis"
                            : "e.g. Customer Orders Cleanup"
                        }
                        value={newWorkspaceTitle}
                        onChange={(event) =>
                          setNewWorkspaceTitle(event.target.value)
                        }
                      />
                  
                      <p className="workspace-field-help">
                        {newWorkspaceUsageContext === "personal"
                          ? "A short name for your data project."
                          : "A short name for this assignment."}
                      </p>
                    </div>
                      
                    <div className="workspace-form-section">
                      <label
                        className="workspace-form-label"
                        htmlFor="workflow-type"
                      >
                        Workflow
                      </label>
                      
                      <select
                        id="workflow-type"
                        className="workspace-form-select"
                        value={newWorkspaceWorkflow}
                        onChange={(event) =>
                          setNewWorkspaceWorkflow(
                            event.target.value as
                              | "auto"
                              | "etl"
                              | "elt"
                              | "data_quality"
                              | "analysis"
                              | "pipeline"
                          )
                        }
                      >
                        <option value="auto">
                          Auto - let DataPilot decide
                        </option>
                        <option value="etl">ETL</option>
                        <option value="elt">ELT</option>
                        <option value="data_quality">
                          Data Quality
                        </option>
                        <option value="analysis">
                          Data Analysis
                        </option>
                        <option value="pipeline">
                          Pipeline
                        </option>
                      </select>
                      
                      <p className="workspace-field-help">
                        Auto is recommended if you are unsure.
                      </p>
                    </div>
                  </div>
                    
                  <div className="workspace-form-section">
                    <label
                      className="workspace-form-label"
                      htmlFor="task-brief"
                    >
                      {newWorkspaceUsageContext === "work"
                        ? "Task brief"
                        : "Project goal"}
                    </label>
                    
                    <textarea
                      id="task-brief"
                      className="workspace-form-textarea"
                      placeholder={
                        newWorkspaceUsageContext === "work"
                          ? "What did your team ask you to do?"
                          : "What do you want to build or discover with this data?"
                      }
                      value={
                        newWorkspaceTaskBrief
                      }
                      onChange={(event) =>
                        setNewWorkspaceTaskBrief(
                          event.target.value
                        )
                      }
                    />

                    <p className="workspace-field-help">
                      {newWorkspaceUsageContext === "personal"
                        ? (
                            "Describe the problem, question or data product you want " +
                            "to create. DataPilot will use this as the project goal."
                          )
                        : (
                            "Write the task as you received it. The mentor will use " +
                            "this as the working context."
                          )}
                    </p>
                  </div>
                    
                  <div className="workspace-form-section">
                    <label
                      className="workspace-form-label"
                      htmlFor="desired-outcome"
                    >
                      {newWorkspaceUsageContext === "personal"
                        ? "Desired project outcome"
                        : "Expected outcome"}
                    </label>
                    
                    <textarea
                      id="desired-outcome"
                      className="workspace-form-textarea small"
                      placeholder={
                        newWorkspaceUsageContext === "personal"
                          ? (
                              "e.g. A Power BI-ready dataset and dashboard showing " +
                              "housing price trends by region"
                            )
                          : (
                              "e.g. A cleaned orders table with validated daily aggregates"
                            )
                      }
                      value={
                        newWorkspaceOutcome
                      }
                      onChange={(event) =>
                        setNewWorkspaceOutcome(
                          event.target.value
                        )
                      }
                    />
                  </div>
                    
                    
                  {workspaceCreateError && (
                    <div className="workspace-form-error">
                      {workspaceCreateError}
                    </div>
                  )}

                  <div className="workspace-form-actions">
                    <button
                      className="secondary-button"
                      onClick={() =>
                        setCurrentView(
                          "dashboard"
                        )
                      }
                      disabled={
                        workspaceCreating
                      }
                    >
                      Cancel
                    </button>
                    
                    <button
                      className="new-workspace-button"
                      onClick={
                        createNewWorkspace
                      }
                      disabled={
                        workspaceCreating
                      }
                    >
                      <Plus
                        size={17}
                        aria-hidden="true"
                      />

                      {workspaceCreating
                        ? "Creating..."
                        : "Create Workspace"}
                    </button>
                  </div>
                </div>
                      
                <aside className="workspace-mentor-guide">
                  <div className="mentor-guide-icon">
                    <Sparkles
                      size={20}
                      aria-hidden="true"
                    />
                  </div>
                      
                  <div>
                    <span className="mentor-guide-label">
                      DATAPILOT MENTOR
                    </span>
                      
                    <h3>
                      {newWorkspaceUsageContext === "personal"
                        ? "Start with the outcome, not the tools."
                        : "Start with the assignment, not the solution."}
                    </h3>
                      
                    <p>
                      {newWorkspaceUsageContext === "personal"
                        ? (
                            "Describe what you want to learn, analyze or produce. " +
                            "You do not need to know the final technical steps yet."
                          )
                        : (
                            "Describe what your team expects. You do not need to " +
                            "know every technical step yet."
                          )}
                    </p>
                  </div>
                      
                  <div className="mentor-guide-example">
                    <span>Example task brief</span>
                      
                    <p>
                      Remove duplicate orders, investigate
                      missing customer IDs and create a
                      validated daily sales output.
                    </p>
                  </div>
                      
                  <div className="mentor-guide-next">
                    <span>Next</span>
                      
                    <p>
                      After creating the workspace,
                      you will attach the data source
                      and DataPilot will help build
                      the execution plan.
                    </p>
                  </div>
                </aside>
              </div>

            </section>


          ) : currentView === "practice" ? (
          <section className="workspace-page practice-page">
            <div className="workspace-header">
              <div>
                <button
                  className="back-button"
                  onClick={() =>
                    setCurrentView("dashboard")
                  }
                >
                  ← Dashboard
                </button>

                <h2>Practice</h2>

                <p>
                  Adaptive challenge based on your
                  learning progress.
                </p>
              </div>
            </div>

            {practiceError ? (
              <div className="python-error">
                <strong>Practice error</strong>
                <p>{practiceError}</p>
              </div>
            ) : practiceChallenge ? (
              <div className="card practice-card">
                <div className="card-heading">
                  <h3>
                    {practiceChallenge.title}
                  </h3>

                  <span className="status-badge">
                    {practiceChallenge.difficulty}
                  </span>
                </div>

                <p className="skill-name">
                  {practiceChallenge.skill_name}
                </p>

                <p>
                  {practiceChallenge.instructions}
                </p>

                <div className="badge-row">
                  <span className="priority-badge">
                    {practiceChallenge.challenge_type}
                  </span>
                </div>
                
                <div className="practice-workbench">
                  {practiceChallenge.context_code && (
                    <div className="practice-context-section">
                      <div className="panel-title">
                        Given data
                      </div>
                  
                      <pre className="practice-context-code">
                        {practiceChallenge.context_code}
                      </pre>
                    </div>
                  )}

                  <div className="practice-editor-section">
                    <div className="panel-title">
                      Your solution
                    </div>
                
                    <textarea
                      className="code-editor practice-code-editor"
                      value={practiceCode}
                      onChange={(event) => {
                        setPracticeCode(event.target.value);
                        setPracticeOutput(null);
                        setPracticeExecutionError(null);
                      }}
                    />

                    <div className="workspace-actions">
                      <button
                        className="run-button"
                        onClick={runPracticeCode}
                        disabled={practiceRunning}
                      >
                        {practiceRunning
                          ? "Running..."
                          : "▶ Run"}
                      </button>
                        
                      <button
                        className="hint-button"
                        onClick={requestPracticeHint}
                        disabled={
                          practiceHintLoading ||
                          practiceHint?.solution_available === true
                        }
                      >
                        {practiceHintLoading
                          ? "Loading hint..."
                          : practiceHint?.solution_available
                            ? "Hints completed"
                            : "💡 Hint"}
                      </button>
                        
                      <button
                        className="submit-button"
                        onClick={submitPracticeAnswer}
                        disabled={
                          practiceSubmitting ||
                          (
                            practiceOutput === null &&
                            practiceExecutionError === null
                          )
                        }
                      >
                        {practiceSubmitting
                          ? "Checking..."
                          : "✓ Submit answer"}
                      </button>
                    </div>
                  </div>
                </div>
                        
                <div className="practice-feedback-panel">
                  <div className="practice-output-panel">
                    <strong>Output</strong>
                        
                    {practiceExecutionError ? (
                      <div className="python-error">
                        <strong>Python error</strong>
                    
                        <pre>
                          {practiceExecutionError}
                        </pre>
                      </div>
                    ) : practiceOutput !== null ? (
                      <pre className="practice-output-value">
                        {practiceOutput}
                      </pre>
                    ) : (
                      <p className="muted">
                        Run your code to see the output.
                      </p>
                    )}
                  </div>
                  
                  <div className="practice-support-panel">
                    <strong>Help & feedback</strong>
                  
                    <div className="practice-support-scroll">
                      {practiceHint && practiceHint.hint ? (
                        <div className="practice-hint">
                          <strong>
                            Hint {practiceHint.hint_number}
                            {" / "}
                            {practiceHint.total_hints}
                          </strong>
                      
                          <p>{practiceHint.hint}</p>
                      
                          {practiceHint.assistance_level && (
                            <span className="practice-hint-level">
                              Support: {practiceHint.assistance_level}
                            </span>
                          )}

                          {practiceHint.solution_available && (
                            <div className="solution-available">
                              <button
                                className="solution-button"
                                onClick={requestPracticeSolution}
                                disabled={
                                  practiceSolutionLoading ||
                                  practiceSolution !== null
                                }
                              >
                                {practiceSolutionLoading
                                  ? "Loading solution..."
                                  : practiceSolution
                                    ? "Solution shown"
                                    : "👁 Show solution"}
                              </button>
                            </div>
                          )}
                        </div>
                      ) : (
                        !practiceReview && (
                          <p className="muted">
                            Use Hint if you need support.
                          </p>
                        )
                      )}

                      {practiceSolution && (
                        <div className="practice-solution">
                          <strong>Example solution</strong>
                      
                          <pre>
                            {practiceSolution.solution}
                          </pre>
                      
                          <span className="practice-solution-level">
                            Support: {practiceSolution.assistance_level}
                          </span>
                        </div>
                      )}

                      {practiceSolutionError && (
                        <div className="practice-hint-error">
                          {practiceSolutionError}
                        </div>
                      )}

                      {practiceHintError && (
                        <div className="practice-hint-error">
                          {practiceHintError}
                        </div>
                      )}

                      {practiceReview && (
                        <div
                          className={
                            practiceReview.validation.success
                              ? "practice-feedback success"
                              : "practice-feedback failure"
                          }
                        >
                          <strong>
                            {practiceReview.validation.success
                              ? "✓ Correct"
                              : "Not quite yet"}
                          </strong>
                            
                          <p>
                            {practiceReview.validation.feedback}
                          </p>
                            
                          {practiceReview.mentor_support && (
                            <div className="mentor-practice-feedback">
                              <strong>Mentor</strong>
                          
                              <p>
                                {practiceReview.mentor_support.message}
                              </p>
                          
                              {practiceReview.mentor_support.micro_check && (
                                <div className="micro-check">
                                  <strong>Quick check</strong>
                              
                                  <p>
                                    {
                                      practiceReview.mentor_support
                                        .micro_check
                                    }
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                  

                </div>
              
            ) : (
              <p className="muted">
                No challenge loaded.
              </p>
            )}
          </section>
                ) : dashboardWorkspace ? (
                  <section className="workspace-page workspace-overview-page">
                    <div className="workspace-sticky-shell">
                      <div className="workspace-overview-topbar">
                        <button
                          className="back-button"
                          onClick={() =>
                            setCurrentView("dashboard")
                          }
                        >
                          <ArrowLeft
                            size={16}
                            aria-hidden="true"
                          />
                          {t.workspace.backToDashboard}
                        </button>
                      </div>
                      
                    <header className="workspace-overview-header">
                      <div>
                        <p className="workspace-eyebrow">
                          {t.workspace.workspaceLabel}
                        </p>
                      
                        <h2>
                          {dashboardWorkspace.title}
                        </h2>
                      
                        <div className="workspace-overview-meta">
                          <span>
                            {dashboardWorkspace.usage_context === "personal"
                              ? t.workspace.personal
                              : t.workspace.work}
                          </span>
                            
                          {dashboardWorkspace.data_sensitivity && (
                            <span>
                              {dashboardWorkspace.data_sensitivity === "public"
                                ? t.workspace.public
                                : dashboardWorkspace.data_sensitivity === "internal"
                                  ? t.workspace.internal
                                  : dashboardWorkspace.data_sensitivity === "confidential"
                                    ? t.workspace.confidential
                                    : dashboardWorkspace.data_sensitivity === "restricted"
                                      ? t.workspace.restricted
                                      : t.workspace.unknown}
                            </span>
                          )}

                          <span>
                            {dashboardWorkspace.workflow_type === "auto"
                              ? t.workspace.auto
                              : dashboardWorkspace.workflow_type === "etl"
                                ? t.workspace.etl
                                : dashboardWorkspace.workflow_type === "elt"
                                  ? t.workspace.elt
                                  : dashboardWorkspace.workflow_type === "data_quality"
                                    ? t.workspace.dataQuality
                                    : dashboardWorkspace.workflow_type === "analysis"
                                      ? t.workspace.analysis
                                      : t.workspace.pipeline}
                          </span>
                        </div>
                      </div>
                          
                      <span
                        className={
                          dashboardWorkspace.status ===
                          "completed"
                            ? "workspace-list-status completed"
                            : "workspace-list-status active"
                        }
                      >
                        {dashboardWorkspace.status === "completed"
                          ? t.workspace.completed
                          : dashboardWorkspace.status === "paused"
                            ? t.workspace.paused
                            : t.workspace.active}
                      </span>
                    </header>
                      

                    <div className="workspace-flow">
                      <div className="workspace-flow-step completed">
                        <span>✓</span>
                        <strong>{t.workspace.source}</strong>
                      </div>

                      <div className="workspace-flow-line completed" />

                      <div
                        className={
                          workspaceDataProfile
                            ? "workspace-flow-step completed"
                            : "workspace-flow-step current"
                        }
                      >
                        <span>
                          {workspaceDataProfile ? "✓" : "2"}
                        </span>
                        <strong>{t.workspace.profile}</strong>
                      </div>
                      
                      <div
                        className={
                          workspaceDataProfile
                            ? "workspace-flow-line completed"
                            : "workspace-flow-line"
                        }
                      />

                      <div
                        className={
                          workspaceTask
                            ? "workspace-flow-step completed"
                            : workspaceDataProfile
                              ? "workspace-flow-step current"
                              : "workspace-flow-step"
                        }
                      >
                        <span>
                          {workspaceTask ? "✓" : "3"}
                        </span>
                      
                        <strong>{t.workspace.plan}</strong>
                      </div>
                      
                      <div
                        className={
                          workspaceTask
                            ? "workspace-flow-line completed"
                            : "workspace-flow-line"
                        }
                      />
                      
                      <div
                        className={
                          workspaceTask?.status === "completed"
                            ? "workspace-flow-step completed"
                            : workspaceTask
                              ? "workspace-flow-step current"
                              : "workspace-flow-step"
                        }
                      >
                        <span>
                          {workspaceTask?.status === "completed"
                            ? "✓"
                            : "4"}
                        </span>
                          
                        <strong>{t.workspace.transform}</strong>
                      </div>
                          
                      <div
                        className={
                          workspaceTask?.status === "completed"
                            ? "workspace-flow-line completed"
                            : "workspace-flow-line"
                        }
                      />

                      <div
                        className={
                          workspaceValidation?.passed
                            ? "workspace-flow-step completed"
                            : workspaceTask?.status === "completed"
                              ? "workspace-flow-step current"
                              : "workspace-flow-step"
                        }
                      >
                        <span>
                          {workspaceValidation?.passed
                            ? "✓"
                            : "5"}
                        </span>
                          
                        <strong>{t.workspace.validate}</strong>
                      </div>
                          
                      <div
                        className={
                          workspaceValidation?.passed
                            ? "workspace-flow-line completed"
                            : "workspace-flow-line"
                        }
                      />

                      <div
                        className={
                          workspaceReviewCompleted
                            ? "workspace-flow-step completed"
                            : workspaceValidation?.passed
                              ? "workspace-flow-step current"
                              : "workspace-flow-step"
                        }
                      >
                        <span>
                          {workspaceReviewCompleted
                            ? "✓"
                            : "6"}
                        </span>
                          
                        <strong>{t.workspace.review}</strong>
                      </div>
                      
                      <div
                        className={
                          workspaceReviewCompleted
                            ? "workspace-flow-line completed"
                            : "workspace-flow-line"
                        }
                      />

                      <div
                        className={
                          workspaceHandoffCompleted
                            ? "workspace-flow-step completed"
                            : workspaceReviewCompleted
                              ? "workspace-flow-step current"
                              : "workspace-flow-step"
                        }
                      >
                        <span>
                          {workspaceHandoffCompleted
                            ? "✓"
                            : "7"}
                        </span>
                          
                        <strong>{t.workspace.handoff}</strong>
                      </div>

                    </div>
                    </div>
                      
                    <div className="workspace-overview-grid">
                      <section className="workspace-overview-card">
                        <span className="workspace-overview-label">
                          {dashboardWorkspace.usage_context === "personal"
                            ? "PROJECT GOAL"
                            : t.workspace.taskBrief}
                        </span>
                      
                        <p>
                          {dashboardWorkspace.task_brief ??
                            t.workspace.noTaskBriefProvided}
                        </p>
                      </section>
                          
                      <section className="workspace-overview-card">
                        <span className="workspace-overview-label">
                          {t.workspace.expectedOutcome}
                        </span>
                          
                        <p>
                          {dashboardWorkspace.desired_outcome ??
                            t.workspace.noExpectedOutcomeProvided}
                        </p>
                      </section>

                      {dashboardWorkspace.usage_context ===
                        "personal" &&
                        dashboardWorkspace.project_deliverables &&
                        dashboardWorkspace.project_deliverables.length > 0 && (
                          <PersonalProjectDeliverables
                            language={language}
                            projectType={
                              dashboardWorkspace.project_type
                            }
                            deliverables={
                              dashboardWorkspace.project_deliverables
                            }
                          />
                        )}
                          
                      <section className="workspace-overview-card">
                        <span className="workspace-overview-label">
                          {t.workspace.progress}
                        </span>
                          
                        <h3>
                          {resumeData?.checkpoint.current_focus ===
                          "Workspace completed"
                            ? t.workspace.workspaceCompleted
                            : resumeData?.checkpoint.current_focus ??
                              "Ready to start"}
                        </h3>
                          
                        <p>
                          {resumeData?.checkpoint.completed_items
                            .length
                            ? `${resumeData.checkpoint.completed_items.length} ${t.workspace.stepsCompleted}`
                            : "No work has been completed yet."}
                        </p>
                      </section>
                          
                      <section className="workspace-overview-card workspace-data-card">
                        <button
                          type="button"
                          className="workspace-section-toggle"
                          onClick={() =>
                            setWorkspaceDataOpen(
                              (previous) => !previous
                            )
                          }
                          aria-expanded={workspaceDataOpen}
                        >
                          <span className="workspace-overview-label">
                            {t.workspace.dataSource}
                          </span>
                        
                          <span className="workspace-plan-chevron">
                            {workspaceDataOpen ? "−" : "+"}
                          </span>
                        </button>
                        
                        {workspaceDataOpen && (
                          <div className="workspace-collapsible-content">

                        {!workspaceDataProfile ? (
                          <>
                            <h3>No data attached yet</h3>
                        
                            <p>
                              Attach the CSV dataset you will work
                              with. DataPilot will profile the data
                              before creating the execution plan.
                            </p>
                        
                            <label className="new-workspace-button workspace-upload-label">
                              <Plus
                                size={17}
                                aria-hidden="true"
                              />

                              {workspaceDataLoading
                                ? "Profiling..."
                                : "Attach CSV"}

                              <input
                                type="file"
                                accept=".csv,text/csv"
                                disabled={workspaceDataLoading}
                                onChange={(event) => {
                                  const file =
                                    event.target.files?.[0] ?? null;
                                
                                  void uploadWorkspaceData(file);
                                
                                  event.currentTarget.value = "";
                                }}
                              />
                            </label>
                          </>
                        ) : (
                          <>
                            <div className="workspace-dataset-heading">
                              <div>
                                <h3>
                                  {workspaceDataProfile.filename}
                                </h3>
                        
                                <p>
                                  {t.workspace.datasetProfiled}
                                </p>
                              </div>
                        
                              <label className="workspace-replace-data">
                                {t.workspace.replaceCsv}
                        
                                <input
                                  type="file"
                                  accept=".csv,text/csv"
                                  disabled={workspaceDataLoading}
                                  onChange={(event) => {
                                    const file =
                                      event.target.files?.[0] ?? null;
                                  
                                    void uploadWorkspaceData(file);
                                  
                                    event.currentTarget.value = "";
                                  }}
                                />
                              </label>
                            </div>
                                
                            <div className="workspace-profile-layout">
                              <div className="workspace-profile-summary">
                                <span className="workspace-overview-label">
                                  {t.workspace.dataProfile}
                                </span>

                                <div className="workspace-profile-stats">
                                  <div>
                                    <strong>
                                      {workspaceDataProfile.profile.row_count}
                                    </strong>
                                    <span>{t.workspace.rows}</span>
                                  </div>

                                  <div>
                                    <strong>
                                      {workspaceDataProfile.profile.column_count}
                                    </strong>
                                    <span>{t.workspace.columns}</span>
                                  </div>

                                  <div>
                                    <strong>
                                      {Object.values(
                                        workspaceDataProfile.profile.null_counts
                                      ).reduce(
                                        (total, count) => total + count,
                                        0
                                      )}
                                    </strong>
                                    <span>{t.workspace.missing}</span>
                                  </div>
                                    
                                  <div>
                                    <strong>
                                      {
                                        workspaceDataProfile.profile
                                          .duplicate_count
                                      }
                                    </strong>
                                    <span>{t.workspace.duplicates}</span>
                                  </div>
                                </div>
                                    
                                <div className="workspace-column-list">
                                  <span className="workspace-overview-label">
                                    {t.workspace.columns}
                                  </span>
                                    
                                  {workspaceDataProfile.profile.columns.map(
                                    (column) => (
                                      <div
                                        className="workspace-column-item"
                                        key={column}
                                      >
                                        <span>{column}</span>
                                    
                                        <span>
                                          {
                                            workspaceDataProfile.profile
                                              .null_counts[column]
                                          }{" "}
                                          {t.workspace.missing.toLowerCase()}
                                        </span>
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                                
                              <div className="workspace-findings-panel">
                                <div className="workspace-findings-header">
                                  <span className="workspace-overview-label">
                                    {t.workspace.findings}
                                  </span>
                                
                                  <span className="workspace-findings-count">
                                    {
                                      workspaceDataProfile.analysis.findings
                                        .length
                                    }{" "}
                                    {t.workspace.detected}
                                  </span>
                                </div>
                                  
                                <div className="workspace-findings">
                                  {workspaceDataProfile.analysis.findings.map(
                                    (finding, index) => (
                                      <details
                                        className="workspace-finding"
                                        key={`${finding.issue_type}-${finding.column}-${index}`}
                                      >
                                        <summary>
                                          <div className="workspace-finding-summary">
                                            <div>
                                              <strong>
                                                {t.workspace.findingTypes[
                                                  finding.issue_type as keyof typeof t.workspace.findingTypes
                                                ] ?? finding.issue_type.replaceAll("_", " ")}
                                              </strong>
                                                
                                              {finding.column && (
                                                <span>
                                                  {finding.column}
                                                </span>
                                              )}
                                            </div>
                                            
                                            <span
                                              className={`finding-severity ${finding.severity}`}
                                            >
                                              {t.workspace.severity[
                                                finding.severity as keyof typeof t.workspace.severity
                                              ]}
                                            </span>
                                          </div>
                                        </summary>
                                            
                                        <div className="workspace-finding-details">
                                          <p>{finding.observation}</p>
                                            
                                          <div>
                                            <strong>
                                              Suggested action
                                            </strong>
                                            
                                            <p>
                                              {finding.suggested_action}
                                            </p>
                                          </div>
                                        </div>
                                      </details>
                                    )
                                  )}
                                </div>
                              </div>
                            </div>
                                
                       {!workspaceTask && (
                        <div className="workspace-profile-next">
                          <button
                            type="button"
                            className="new-workspace-button"
                            disabled={
                              workspacePlanLoading ||
                              !workspaceDataProfile
                            }
                            onClick={() => {
                              void buildWorkspaceExecutionPlan();
                            }}
                          >
                            {workspacePlanLoading
                              ? "Building plan..."
                              : "Build execution plan →"}
                          </button>
                            
                          <span>
                            DataPilot will create a guided workflow
                            from the dataset profile.
                          </span>
                        </div>
                      )}

                      {workspacePlanError && (
                        <div className="workspace-form-error">
                          {workspacePlanError}
                        </div>
                      )}

                        </>
                        )}

                        {workspaceDataError && (
                          <div className="workspace-form-error">
                            {workspaceDataError}
                          </div>
                        )}

                            </div>
                          )}

                        </section>

                        {workspaceTask && (
                          <section className="workspace-overview-card workspace-plan-card">
                            <button
                              type="button"
                              className="workspace-plan-header workspace-plan-toggle"
                              onClick={() =>
                                setWorkspacePlanOpen(
                                  (previous) => !previous
                                )
                              }
                              aria-expanded={workspacePlanOpen}
                            >
                              <div>
                                <span className="workspace-overview-label">
                                  {t.workspace.executionPlan}
                                </span>
                            
                                <h3>{workspaceTask.title}</h3>
                              </div>
                            
                              <div className="workspace-plan-header-actions">
                                <span
                                  className={
                                    workspaceTask.status === "completed"
                                      ? "workspace-list-status completed"
                                      : "workspace-list-status active"
                                  }
                                >
                                  {workspaceTask.status === "completed"
                                    ? t.workspace.completed
                                    : t.workspace.active}
                                </span>
                                  
                                <span className="workspace-plan-chevron">
                                  {workspacePlanOpen ? "−" : "+"}
                                </span>
                              </div>
                            </button>
                                  
                            {workspacePlanOpen && (
                              <div className="workspace-plan-steps">
                                {workspaceTask.steps.map((step) => (
                                  <div
                                    className={`workspace-plan-step ${step.status}`}
                                    key={step.step_number}
                                  >
                                    <div className="workspace-plan-step-number">
                                      {step.status === "completed"
                                        ? "✓"
                                        : step.step_number}
                                    </div>
                                      
                                    <div className="workspace-plan-step-content">
                                      <div className="workspace-plan-step-heading">
                                        <strong>
                                          {step.title}
                                        </strong>
                                      
                                        <span>
                                          {step.status}
                                        </span>
                                      </div>
                                      
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
                            )}
                          </section>
                        )}

                      {workspaceTask && 
                        workspaceTask.status !== "completed" && (
                        <section className="workspace-overview-card workspace-transform-card">
                          <div className="workspace-transform-header">
                            <div>
                              <span className="workspace-overview-label">
                                Transform workbench
                              </span>
                                            
                              <h3>
                                {workspaceTask.steps.find(
                                  (step) => step.status === "active"
                                )?.title ?? "No active step"}
                              </h3>
                            </div>
                              
                            {workspaceWorkingData && (
                              <span className="workspace-transform-count">
                                {workspaceWorkingData.row_count} rows
                              </span>
                            )}
                          </div>
                          
                          
                          {workspaceVersions.length > 0 && (
                            <div className="workspace-version-history">
                              <div className="workspace-version-history-header">
                                <span className="workspace-overview-label">
                                  Version history
                                </span>

                                <span>
                                  {workspaceVersions.length} checkpoint
                                </span>
                              </div>

                              <div className="workspace-version-list">
                                {workspaceVersions.map(
                                  (version) => (
                                    <div
                                      className="workspace-version-item"
                                      key={version.version_number}
                                    >
                                      <div>
                                        <strong>
                                          v{version.version_number}
                                        </strong>
                                  
                                        <p>
                                          {version.label}
                                        </p>
                                  
                                        <span>
                                          {version.row_count} rows ·{" "}
                                          {new Date(
                                            version.created_at
                                          ).toLocaleString()}
                                        </span>
                                      </div>
                                        
                                      <button
                                        type="button"
                                        className="workspace-version-restore"
                                        disabled={
                                          restoringVersion !== null
                                        }
                                        onClick={() => {
                                          void restoreWorkspaceVersion(
                                            version.version_number
                                          );
                                        }}
                                      >
                                        {restoringVersion ===
                                        version.version_number
                                          ? "Restoring..."
                                          : "↩ Restore"}
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              
                            </div>
                          )}

                        
                          {workspaceVersionError && (
                            <div className="workspace-form-error">
                              {workspaceVersionError}
                            </div>
                          )}


                          {workspaceWorkingDataLoading ? (
                            <p className="muted">
                              Loading working dataset...
                            </p>
                          ) : workspaceWorkingDataError ? (
                            <div className="workspace-form-error">
                              {workspaceWorkingDataError}
                            </div>
                          ) : workspaceWorkingData ? (
                            <div className="workspace-working-table-wrap">
                              <table className="workspace-working-table">
                                <thead>
                                  <tr>
                                    {workspaceWorkingData.columns.map(
                                      (column) => (
                                        <th key={column}>
                                          {column}
                                        </th>
                                      )
                                    )}
                                  </tr>
                                </thead>
                                  
                                <tbody>
                                  {workspaceWorkingData.rows.map(
                                    (row, rowIndex) => (
                                      <tr key={rowIndex}>
                                        {workspaceWorkingData.columns.map(
                                          (column) => (
                                            <td
                                              key={`${rowIndex}-${column}`}
                                            >
                                              {row[column] === null ||
                                              row[column] === undefined
                                                ? "—"
                                                : String(row[column])}
                                            </td>
                                          )
                                        )}
                                      </tr>
                                    )
                                  )}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p className="muted">
                              Working dataset is not available.
                            </p>
                          )}

                          {workspaceWorkingData && (
                            <div className="workspace-transform-editor-grid">
                              <div className="workspace-transform-editor-panel">
                                <div className="workspace-transform-panel-header">
                                  <div>
                                    <span className="workspace-overview-label">
                                      Python transformation
                                    </span>

                                    <p>
                                      Work on <code>df</code>. Your code runs
                                      locally in the browser.
                                    </p>
                                  </div>
                                </div>

                                <textarea
                                  className="workspace-transform-editor"
                                  value={transformationCode}
                                  spellCheck={false}
                                  onChange={(event) => {
                                    setTransformationCode(
                                      event.target.value
                                    );
                                  
                                    setResultRows(null);
                                    setPythonError(null);
                                    setValidationMessage(null);
                                  }}
                                />

                                <div className="workspace-transform-actions">
                                  <button
                                    type="button"
                                    className="run-button"
                                    onClick={() => {
                                      void runTransformation();
                                    }}
                                    disabled={pythonRunning}
                                  >
                                    {pythonRunning
                                      ? "Running..."
                                      : "▶ Run"}
                                  </button>
                                    
                                  <button
                                    type="button"
                                    className="submit-button"
                                    onClick={() => {
                                      void submitWorkspaceTransformation();
                                    }}
                                    disabled={
                                      submitting ||
                                      pythonRunning ||
                                      resultRows === null
                                    }
                                  >
                                    {submitting
                                      ? "Validating..."
                                      : "✓ Submit transformation"}
                                  </button>
                                    
                                  <span>
                                    Run only previews. Submit validates and,
                                    if successful, updates working.csv.
                                  </span>
                                </div>
                                    
                                {validationMessage && (
                                  <div className="validation-message">
                                    {validationMessage}
                                  </div>
                                )}
                                    
                                {pythonError && (
                                  <div className="python-error">
                                    <strong>Python error</strong>
                                    <pre>{pythonError}</pre>
                                  </div>
                                )}
                              </div>
                              
                              <div className="workspace-transform-result-panel">
                                <span className="workspace-overview-label">
                                  Result preview
                                </span>
                              
                                {!resultRows ? (
                                  <p className="muted">
                                    Run your code to preview the
                                    transformed dataset.
                                  </p>
                                ) : (
                                  <>
                                    <div className="workspace-result-summary">
                                      <strong>
                                        {resultRows.length}
                                      </strong>
                                      <span>rows after transformation</span>
                                    </div>
                                
                                    <div className="workspace-working-table-wrap">
                                      <table className="workspace-working-table">
                                        <thead>
                                          <tr>
                                            {workspaceWorkingData.columns.map(
                                              (column) => (
                                                <th key={column}>
                                                  {column}
                                                </th>
                                              )
                                            )}
                                          </tr>
                                        </thead>
                                          
                                        <tbody>
                                          {resultRows.map(
                                            (row, rowIndex) => (
                                              <tr key={rowIndex}>
                                                {workspaceWorkingData.columns.map(
                                                  (column) => (
                                                    <td
                                                      key={`${rowIndex}-${column}`}
                                                    >
                                                      {row[column] === null ||
                                                      row[column] === undefined
                                                        ? "—"
                                                        : String(row[column])}
                                                    </td>
                                                  )
                                                )}
                                              </tr>
                                            )
                                          )}
                                        </tbody>
                                      </table>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          )}
                        </section>
                      )}

                      {workspaceTask &&
                        workspaceTask.status === "completed" && (
                          <section className="workspace-overview-card">
                            <div className="workspace-plan-header">
                              <div>
                                <span className="workspace-overview-label">
                                  {t.workspace.finalValidation}
                                </span>
                        
                                <h3>
                                  {t.workspace.validateDataset}
                                </h3>
                        
                                <p>
                                  {t.workspace.validationDescription}
                                </p>
                              </div>
                        
                              {workspaceValidation && (
                                <span
                                  className={
                                    workspaceValidation.passed
                                      ? "workspace-list-status completed"
                                      : "workspace-list-status active"
                                  }
                                >
                                  {workspaceValidation.passed
                                    ? t.workspace.passed
                                    : t.workspace.failed}
                                </span>
                              )}
                            </div>
                            
                            {!workspaceValidation ? (
                              <div className="workspace-profile-next">
                                <button
                                  type="button"
                                  className="new-workspace-button"
                                  disabled={workspaceValidationLoading}
                                  onClick={() => {
                                    void runWorkspaceValidation();
                                  }}
                                >
                                  {workspaceValidationLoading
                                    ? t.workspace.validating
                                    : t.workspace.runFinalValidation}
                                </button>
                                  
                                <span>
                                  {t.workspace.validationIntro}
                                </span>
                              </div>
                            ) : (
                              <>
                                <div className="workspace-profile-stats">
                                  <div>
                                    <strong>
                                      {workspaceValidation.source_row_count}
                                    </strong>
                                    <span>{t.workspace.sourceRows}</span>
                                  </div>
                            
                                  <div>
                                    <strong>
                                      {workspaceValidation.working_row_count}
                                    </strong>
                                    <span>{t.workspace.workingRows}</span>
                                  </div>
                            
                                  <div>
                                    <strong>
                                      {
                                        workspaceValidation.checks.filter(
                                          (check) =>
                                            check.status === "passed"
                                        ).length
                                      }
                                    </strong>
                                    <span>{t.workspace.checksPassed}</span>
                                  </div>
                                    
                                  <div>
                                    <strong>
                                      {workspaceValidation.checks.length}
                                    </strong>
                                    <span>{t.workspace.totalChecks}</span>
                                  </div>
                                </div>
                                    
                                <div className="workspace-plan-steps">
                                  {workspaceValidation.checks.map(
                                    (check, index) => {
                                      const localizedCheck =
                                        getValidationCheckText(check);
                                    
                                      return (
                                        <div
                                          className={
                                            check.status === "passed"
                                              ? "workspace-plan-step completed"
                                              : "workspace-plan-step active"
                                          }
                                          key={`${check.name}-${index}`}
                                        >
                                          <div className="workspace-plan-step-number">
                                            {check.status === "passed"
                                              ? "✓"
                                              : "!"}
                                          </div>
                                            
                                          <div>
                                            <strong>
                                              {localizedCheck.name}
                                            </strong>
                                            
                                            <p>
                                              {localizedCheck.message}
                                            </p>
                                          </div>
                                        </div>
                                      );
                                    }
                                  )}
                                </div>
                                
                                {!workspaceReviewCompleted && (
                                  <div className="workspace-profile-next">
                                    <button
                                      type="button"
                                      className="new-workspace-button"
                                      disabled={workspaceValidationLoading}
                                      onClick={() => {
                                        void runWorkspaceValidation();
                                      }}
                                    >
                                      {workspaceValidationLoading
                                        ? t.workspace.validating
                                        : t.workspace.runValidationAgain}
                                    </button>
                                      
                                    <span>
                                      {workspaceValidation.passed
                                        ? t.workspace.validationReady
                                        : t.workspace.validationNeedsFix}
                                    </span>
                                  </div>
                                )}
                              </>
                            )}

                            {workspaceValidationError && (
                              <div className="workspace-form-error">
                                {workspaceValidationError}
                              </div>
                            )}
                          </section>
                        )}

                        {workspaceValidation?.passed && (
                          <section className="workspace-overview-card">
                            <div className="workspace-plan-header">
                              <div>
                                <span className="workspace-overview-label">
                                  {t.workspace.finalReview}
                                </span>

                                <h3>
                                  {t.workspace.reviewDataset}
                                </h3>

                                <p>
                                  {t.workspace.reviewDescription}
                                </p>
                              </div>

                              {workspaceReviewCompleted && (
                                <span className="workspace-list-status completed">
                                  {t.workspace.completed}
                                </span>
                              )}
                            </div>
                           
                            <div className="workspace-overview-grid">
                              <div className="workspace-overview-card">
                                <span className="workspace-overview-label">
                                  {t.workspace.taskBrief}
                                </span>
                            
                                <p>
                                  {dashboardWorkspace.task_brief ??
                                    "No task brief provided."}
                                </p>
                              </div>
                                  
                              <div className="workspace-overview-card">
                                <span className="workspace-overview-label">
                                  {t.workspace.expectedOutcome}
                                </span>
                                  
                                <p>
                                  {dashboardWorkspace.desired_outcome ??
                                    "No expected outcome provided."}
                                </p>
                              </div>
                            </div>
                                  
                            {workspaceWorkingData && (
                              <>
                                <div className="workspace-profile-next">
                                  <span>
                                    {t.workspace.finalWorkingDataset} ·{" "}
                                    {workspaceWorkingData.row_count}{" "} 
                                    {t.workspace.rows.toLowerCase()}
                                  </span>
                                </div>
                            
                                <div className="workspace-working-table-wrap">
                                  <table className="workspace-working-table">
                                    <thead>
                                      <tr>
                                        {workspaceWorkingData.columns.map(
                                          (column) => (
                                            <th key={column}>
                                              {column}
                                            </th>
                                          )
                                        )}
                                      </tr>
                                    </thead>
                                      
                                    <tbody>
                                      {workspaceWorkingData.rows.map(
                                        (row, rowIndex) => (
                                          <tr key={rowIndex}>
                                            {workspaceWorkingData.columns.map(
                                              (column) => (
                                                <td
                                                  key={`${rowIndex}-${column}`}
                                                >
                                                  {row[column] === null ||
                                                  row[column] === undefined
                                                    ? "—"
                                                    : String(row[column])}
                                                </td>
                                              )
                                            )}
                                          </tr>
                                        )
                                      )}
                                    </tbody>
                                  </table>
                                </div>
                              </>
                            )}

                            <div className="workspace-profile-next">
                              {!workspaceReviewCompleted ? (
                                <>
                                  <button
                                    type="button"
                                    className="new-workspace-button"
                                    disabled={workspaceReviewLoading}
                                    onClick={() => {
                                      void completeWorkspaceReview();
                                    }}
                                  >
                                    {workspaceReviewLoading
                                      ? t.workspace.completingReview
                                      :t.workspace.completeReview}
                                  </button>
                                    
                                  <span>
                                    {t.workspace.reviewConfirm}
                                  </span>
                                </>
                              ) : (
                                <span>
                                  {t.workspace.reviewCompletedReady}
                                </span>
                              )}
                            </div>
                            
                            {workspaceReviewError && (
                              <div className="workspace-form-error">
                                {workspaceReviewError}
                              </div>
                            )}
                          </section>
                        )}
                        {workspaceReviewCompleted && (
                          <section className="workspace-overview-card">
                            <div className="workspace-plan-header">
                              <div>
                                <span className="workspace-overview-label">
                                  {t.workspace.prepareHandoff}
                                </span>
                        
                                <h3>
                                  {t.workspace.prepareFinalDelivery}
                                </h3>
                        
                                <p>
                                  {t.workspace.handoffDescription}
                                </p>
                              </div>
                        
                              {workspaceHandoffCompleted && (
                                <span className="workspace-list-status completed">
                                  {t.workspace.completed}
                                </span>
                              )}
                            </div>
                            
                            <div className="workspace-profile-stats">
                              <div>
                                <strong>
                                  {workspaceWorkingData?.row_count ?? 0}
                                </strong>
                                <span>{t.workspace.finalRows}</span>
                              </div>
                            
                              <div>
                                <strong>
                                  {workspaceValidation?.checks.filter(
                                    (check) =>
                                      check.status === "passed"
                                  ).length ?? 0}
                                </strong>
                                <span>{t.workspace.checksPassed}</span>
                              </div>
                                
                              <div>
                                <strong>
                                  {workspaceValidation?.passed
                                    ? t.workspace.yes
                                    : t.workspace.no}
                                </strong>
                                <span>{t.workspace.validated}</span>
                              </div>
                                  
                              <div>
                                <strong>
                                  {workspaceReviewCompleted
                                    ? t.workspace.yes
                                    : t.workspace.no}
                                </strong>
                                <span>{t.workspace.reviewed}</span>
                              </div>
                            </div>
                                  
                            {!workspaceHandoffCompleted ? (
                              <div className="workspace-profile-next">
                                <button
                                  type="button"
                                  className="new-workspace-button"
                                  disabled={workspaceExportLoading}
                                  onClick={() => {
                                    void downloadWorkspaceHandoff();
                                  }}
                                >
                                  {workspaceExportLoading
                                    ? t.workspace.preparingCsv
                                    : t.workspace.downloadFinalCsv}
                                </button>
                                  
                                <button
                                  type="button"
                                  className="new-workspace-button"
                                  disabled={workspaceHandoffLoading}
                                  onClick={() => {
                                    void completeWorkspaceHandoff();
                                  }}
                                >
                                  {workspaceHandoffLoading
                                    ? t.workspace.completingHandoff
                                    : t.workspace.completeHandoff}
                                </button>
                                  
                                <span>
                                  {t.workspace.handoffNotice}
                                </span>
                              </div>
                            ) : (
                              <div className="workspace-profile-next">
                                <span>
                                  {t.workspace.handoffCompleted}
                                </span>
                              </div>
                            )}
                        
                            {workspaceHandoffError && (
                              <div className="workspace-form-error">
                                {workspaceHandoffError}
                              </div>
                            )}
                          </section>
                        )}

                    </div>
                  </section>
                ) : (
                 <section className="workspace-page">
                   <p className="muted">
                     No workspace selected.
                   </p>
                 </section>
               )}
      </main>
         
 
 
    </div>
  );
}

type SkillProgressProps = {
  name: string;
  status: string;
  progress: number;
};

function SkillProgress({
  name,
  status,
  progress,
}: SkillProgressProps) {
  return (
    <div className="skill-progress">
      <div className="skill-progress-header">
        <span>{name}</span>
        <span>{status}</span>
      </div>

      <div className="progress-track">
        <div
          className="progress-bar"
          style={{
            width: `${progress}%`,
          }}
        />
      </div>
    </div>
  );
}

export default App;