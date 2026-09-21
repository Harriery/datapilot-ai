export type PersonalWorkspaceStage =
  | "source"
  | "prepare"
  | "analysis"
  | "kpis"
  | "data_model"
  | "bi_dataset"
  | "dashboard"
  | "insights"
  | "docs";

export type PrepareStage =
  | "profile"
  | "workbench"
  | "validate";

export type WorkspaceStageStatus =
  | "completed"
  | "current"
  | "available"
  | "locked";

export type WorkspaceStageDefinition = {
  code: PersonalWorkspaceStage;
  label: string;
};

export type PrepareStageDefinition = {
  code: PrepareStage;
  label: string;
};

export const PERSONAL_WORKSPACE_STAGES: WorkspaceStageDefinition[] = [
  {
    code: "source",
    label: "Source",
  },
  {
    code: "prepare",
    label: "Prepare",
  },
  {
    code: "analysis",
    label: "Analysis",
  },
  {
    code: "kpis",
    label: "KPIs",
  },
  {
    code: "data_model",
    label: "Data Model",
  },
  {
    code: "bi_dataset",
    label: "BI Dataset",
  },
  {
    code: "dashboard",
    label: "Dashboard",
  },
  {
    code: "insights",
    label: "Insights",
  },
  {
    code: "docs",
    label: "Docs",
  },
];

export const PREPARE_STAGES: PrepareStageDefinition[] = [
  {
    code: "profile",
    label: "Profile",
  },
    {
    code: "workbench",
    label: "Workbench",
  },
  {
    code: "validate",
    label: "Validate",
  },
];