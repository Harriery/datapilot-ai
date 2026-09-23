export type PersonalWorkspaceStage =
  | "source"
  | "prepare"
  | "data_model"
  | "kpis"
  | "bi_dataset"
  | "analysis"
  | "dashboard"
  | "insights"
  | "docs";


export type PrepareStage =
  | "profile"
  | "workbench"
  | "validate"
  | "understand";


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


export const PERSONAL_WORKSPACE_STAGES:
  WorkspaceStageDefinition[] = [

  {
    code: "source",
    label: "Source",
  },

  {
    code: "prepare",
    label: "Prepare",
  },

  {
    code: "data_model",
    label: "Data Model",
  },

  {
    code: "kpis",
    label: "KPIs",
  },

  {
    code: "bi_dataset",
    label: "BI Model",
  },

  {
    code: "analysis",
    label: "Analysis",
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


export const PREPARE_STAGES:
  PrepareStageDefinition[] = [

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

  {
    code: "understand",
    label: "Understand",
  },
];