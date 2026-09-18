export type AppLanguage = "en" | "tr";

export const translations = {
  en: {
    sidebar: {
      dashboard: "Dashboard",
      workspace: "Workspace",
      practice: "Practice",
      tasks: "Tasks",
      progress: "Progress",
      documents: "Documents",
      settings: "Settings",
    },

    workspace: {
      source: "Source",
      profile: "Profile",
      plan: "Plan",
      transform: "Transform",
      validate: "Validate",
      review: "Review",
      handoff: "Handoff",

      dataSource: "Data source",
      executionPlan: "Execution plan",
      finalValidation: "Final validation",
      finalReview: "Final review",
      prepareHandoff: "Handoff",

      completed: "Completed",
      active: "Active",

      taskBrief: "Task brief",
      expectedOutcome: "Expected outcome",
      progress: "Progress",
      workspaceCompleted: "Workspace completed",
      stepsCompleted: "step(s) completed.",

      dataProfile: "Data profile",
      findings: "Findings",
      rows: "Rows",
      columns: "Columns",
      missing: "Missing",
      duplicates: "Duplicates",
      replaceCsv: "Replace CSV",
      datasetProfiled: "Dataset profiled successfully.",
      detected: "detected",

      work: "Work",
    personal: "Personal",
    public: "Public",
    internal: "Internal",
    confidential: "Confidential",
    restricted: "Restricted",
    unknown: "Unknown",
        
    auto: "Auto",
    etl: "ETL",
    elt: "ELT",
    dataQuality: "Data Quality",
    analysis: "Analysis",
    pipeline: "Pipeline",
        
    paused: "Paused",
        
    findingTypes: {
      missing_values: "Missing Values",
      duplicate_rows: "Duplicate Rows",
      suspicious_values: "Suspicious Values",
      data_type_issue: "Data Type Issue",
      schema_issue: "Schema Issue",
    },
    
    severity: {
      low: "Low",
      medium: "Medium",
      high: "High",
    },
    },
  },

  tr: {
    sidebar: {
      dashboard: "Ana Sayfa",
      workspace: "Çalışma Alanı",
      practice: "Pratik",
      tasks: "Görevler",
      progress: "Gelişim",
      documents: "Dokümanlar",
      settings: "Ayarlar",
    },

    workspace: {
      source: "Kaynak",
      profile: "Profil",
      plan: "Plan",
      transform: "Dönüştür",
      validate: "Doğrula",
      review: "İnceleme",
      handoff: "Teslim",

      dataSource: "Veri kaynağı",
      executionPlan: "Uygulama planı",
      finalValidation: "Son doğrulama",
      finalReview: "Son inceleme",
      prepareHandoff: "Teslim",

      completed: "Tamamlandı",
      active: "Aktif",

      taskBrief: "Görev özeti",
      expectedOutcome: "Beklenen sonuç",
      progress: "İlerleme",
      workspaceCompleted: "Çalışma alanı tamamlandı",
      stepsCompleted: "adım tamamlandı.",

      dataProfile: "Veri profili",
      findings: "Bulgular",
      rows: "Satır",
      columns: "Sütun",
      missing: "Eksik",
      duplicates: "Tekrar",
      replaceCsv: "CSV'yi değiştir",
      datasetProfiled: "Veri seti başarıyla profillendi.",
      detected: "bulgu tespit edildi",

      work: "İş",
    personal: "Kişisel",
    public: "Herkese Açık",
    internal: "Dahili",
    confidential: "Gizli",
    restricted: "Kısıtlı",
    unknown: "Bilinmiyor",
        
    auto: "Otomatik",
    etl: "ETL",
    elt: "ELT",
    dataQuality: "Veri Kalitesi",
    analysis: "Analiz",
    pipeline: "Veri Hattı",
        
    paused: "Duraklatıldı",
        
    findingTypes: {
      missing_values: "Eksik Değerler",
      duplicate_rows: "Tekrarlanan Satırlar",
      suspicious_values: "Şüpheli Değerler",
      data_type_issue: "Veri Tipi Sorunu",
      schema_issue: "Şema Sorunu",
    },
    
    severity: {
      low: "Düşük",
      medium: "Orta",
      high: "Yüksek",
    },
    },
  },
} as const;