import {
  BarChart3,
  BriefcaseBusiness,
  CheckCircle2,
  Database,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import type {
  AppLanguage,
} from "./i18n";


type WorkspaceModeCardsProps = {
  language: AppLanguage;

  onStartPersonal: () => void;
  onExploreWork: () => void;
};


function WorkspaceModeCards({
  language,
  onStartPersonal,
  onExploreWork,
}: WorkspaceModeCardsProps) {
  const text =
    language === "nl"
      ? {
          eyebrow: "WERKMODUS",
          title: "Hoe wil je werken?",
          description:
            "Bouw je eigen dataprojecten of werk aan bedrijfsopdrachten in een beveiligde omgeving.",

          personal: {
            title: "Persoonlijke projecten",
            status: "Functionele MVP",
            description:
              "Bouw complete dataprojecten met openbare of persoonlijke datasets.",
            features: [
              "Dataprofilering en kwaliteitsanalyse",
              "Opschoning en transformatie",
              "Analyse- en BI-uitvoer",
              "Portfolio-projectontwikkeling",
            ],
            button: "Persoonlijk project starten",
          },

          work: {
            title: "Veilige werkomgeving",
            status: "Preview · In ontwikkeling",
            description:
              "Werk met bedrijfs- of klantgegevens onder local-first beveiligingscontroles.",
            features: [
              "Local Data Engine actief",
              "Externe AI geblokkeerd voor gevoelige gegevens",
              "Centraal beveiligingsbeleid",
              "Local LLM en enterprise-beveiliging in ontwikkeling",
            ],
            button: "Veilige werkomgeving bekijken",
          },
        }
      :     language === "tr"
      ? {
          eyebrow: "ÇALIŞMA MODU",
          title: "Nasıl çalışmak istiyorsun?",
          description:
            "Kendi veri projelerini geliştir veya güvenli iş ortamında şirket görevleri üzerinde çalış.",

          personal: {
            title: "Kişisel Projeler",
            status: "Çalışan MVP",
            description:
              "Açık veya kişisel verilerle uçtan uca veri projeleri oluştur.",
            features: [
              "Veri profilleme ve kalite analizi",
              "Temizleme ve dönüşüm",
              "Analiz ve BI çıktıları",
              "Portföy projesi oluşturma",
            ],
            button: "Kişisel proje başlat",
          },

          work: {
            title: "Güvenli İş Alanı",
            status: "Önizleme · Geliştiriliyor",
            description:
              "Şirket veya müşteri verileriyle local-first güvenlik kontrolleri altında çalış.",
            features: [
              "Local Data Engine aktif",
              "Gizli veriler için external AI engeli",
              "Merkezi güvenlik politikası",
              "Local LLM ve kurumsal güvenlik geliştirme aşamasında",
            ],
            button: "Güvenli iş alanını incele",
          },
        }
      : {
          eyebrow: "WORK MODE",
          title: "How do you want to work?",
          description:
            "Build your own data projects or work on company assignments in a security-focused environment.",

          personal: {
            title: "Personal Projects",
            status: "Functional MVP",
            description:
              "Build complete data projects using public or personal datasets.",
            features: [
              "Data profiling and quality analysis",
              "Cleaning and transformation",
              "Analysis and BI outputs",
              "Portfolio project development",
            ],
            button: "Start personal project",
          },

          work: {
            title: "Secure Work",
            status: "Preview · In Development",
            description:
              "Work with company or client data using local-first security controls.",
            features: [
              "Local Data Engine active",
              "External AI blocking for sensitive data",
              "Central security policy",
              "Local LLM and enterprise security in development",
            ],
            button: "Explore secure work",
          },
        };


  return (
    <section className="workspace-mode-section">
      <div className="workspace-mode-heading">
        <p className="workspace-eyebrow">
          {text.eyebrow}
        </p>

        <h3>{text.title}</h3>

        <p>{text.description}</p>
      </div>


      <div className="workspace-mode-grid">
        <article className="workspace-mode-card personal">
          <div className="workspace-mode-card-header">
            <div className="workspace-mode-icon personal">
              <UserRound
                size={22}
                aria-hidden="true"
              />
            </div>

            <span className="workspace-mode-status ready">
              <CheckCircle2
                size={13}
                aria-hidden="true"
              />

              {text.personal.status}
            </span>
          </div>


          <div className="workspace-mode-content">
            <h3>{text.personal.title}</h3>

            <p>
              {text.personal.description}
            </p>


            <ul className="workspace-mode-features">
              <li>
                <Database size={15} />
                {text.personal.features[0]}
              </li>

              <li>
                <CheckCircle2 size={15} />
                {text.personal.features[1]}
              </li>

              <li>
                <BarChart3 size={15} />
                {text.personal.features[2]}
              </li>

              <li>
                <UserRound size={15} />
                {text.personal.features[3]}
              </li>
            </ul>
          </div>


          <button
            type="button"
            className="workspace-mode-action personal"
            onClick={onStartPersonal}
          >
            {text.personal.button}
            <span aria-hidden="true">→</span>
          </button>
        </article>


        <article className="workspace-mode-card work">
          <div className="workspace-mode-card-header">
            <div className="workspace-mode-icon work">
              <BriefcaseBusiness
                size={22}
                aria-hidden="true"
              />
            </div>

            <span className="workspace-mode-status preview">
              <ShieldCheck
                size={13}
                aria-hidden="true"
              />

              {text.work.status}
            </span>
          </div>


          <div className="workspace-mode-content">
            <h3>{text.work.title}</h3>

            <p>
              {text.work.description}
            </p>


            <ul className="workspace-mode-features">
              <li>
                <Database size={15} />
                {text.work.features[0]}
              </li>

              <li>
                <LockKeyhole size={15} />
                {text.work.features[1]}
              </li>

              <li>
                <ShieldCheck size={15} />
                {text.work.features[2]}
              </li>

              <li>
                <BriefcaseBusiness size={15} />
                {text.work.features[3]}
              </li>
            </ul>
          </div>


          <button
            type="button"
            className="workspace-mode-action work"
            onClick={onExploreWork}
          >
            {text.work.button}
            <span aria-hidden="true">→</span>
          </button>
        </article>
      </div>
    </section>
  );
}


export default WorkspaceModeCards;