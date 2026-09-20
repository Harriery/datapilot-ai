import {
  CheckCircle2,
  Circle,
} from "lucide-react";

import type {
  AppLanguage,
} from "./i18n";



export type ProjectDeliverableData = {
  code: string;
  title: string;

  status:
    | "pending"
    | "in_progress"
    | "completed";

  required: boolean;
};


type PersonalProjectDeliverablesProps = {
  language: AppLanguage;

  projectType:
    | "data_engineering"
    | "data_analysis"
    | "bi_dashboard"
    | "data_quality"
    | "portfolio"
    | null
    | undefined;

  

  deliverables: ProjectDeliverableData[];
};


function PersonalProjectDeliverables({
  language,
  projectType,
  deliverables,
}: PersonalProjectDeliverablesProps) {

  const text =
    language === "tr"
      ? {
          eyebrow: "PROJE ÇIKTISI",
          title: "Proje teslimleri",
          outcome: "Hedef sonuç",
          completed: "tamamlandı",

          projectTypes: {
            data_engineering:
              "Data Engineering Projesi",
            data_analysis:
              "Data Analiz Projesi",
            bi_dashboard:
              "BI / Dashboard Projesi",
            data_quality:
              "Data Quality Projesi",
            portfolio:
              "Portföy Projesi",
          },
        }
      : {
          eyebrow: "PROJECT OUTCOME",
          title: "Project deliverables",
          outcome: "Desired outcome",
          completed: "completed",

          projectTypes: {
            data_engineering:
              "Data Engineering Project",
            data_analysis:
              "Data Analysis Project",
            bi_dashboard:
              "BI / Dashboard Project",
            data_quality:
              "Data Quality Project",
            portfolio:
              "Portfolio Project",
          },
        };


  const completedCount =
    deliverables.filter(
      (item) =>
        item.status === "completed"
    ).length;


  const projectTypeLabel =
    projectType
      ? text.projectTypes[projectType]
      : null;


  return (
    <section className="personal-deliverables-card">
      <div className="personal-deliverables-header">
        <div>
          <span className="workspace-overview-label">
            {text.eyebrow}
          </span>

          <h3>{text.title}</h3>

          {projectTypeLabel && (
            <span className="personal-project-type-badge">
              {projectTypeLabel}
            </span>
          )}
        </div>

        <div className="personal-deliverables-progress">
          <strong>
            {completedCount}/{deliverables.length}
          </strong>

          <span>{text.completed}</span>
        </div>
      </div>


      <div className="personal-deliverables-list">
        {deliverables.map(
          (deliverable) => (
            <div
              className={
                `personal-deliverable-item ${
                  deliverable.status
                }`
              }
              key={deliverable.code}
            >
              {deliverable.status ===
              "completed" ? (
                <CheckCircle2
                  size={17}
                  aria-hidden="true"
                />
              ) : (
                <Circle
                  size={17}
                  aria-hidden="true"
                />
              )}

              <span>
                {deliverable.title}
              </span>
            </div>
          )
        )}
      </div>
    </section>
  );
}


export default PersonalProjectDeliverables;