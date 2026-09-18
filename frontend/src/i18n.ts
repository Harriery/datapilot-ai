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
    passed: "Passed",
failed: "Failed",

validateDataset: "Validate transformed dataset",
validationDescription:
  "Check the final working dataset against the source and execution plan.",

validating: "Validating...",
runFinalValidation: "Run final validation →",
validationIntro:
  "DataPilot will run deterministic checks on the final working dataset.",

sourceRows: "Source rows",
workingRows: "Working rows",
checksPassed: "Checks passed",
totalChecks: "Total checks",

runValidationAgain: "Run validation again",
validationReady:
  "All required checks passed. Ready for review.",
validationNeedsFix:
  "Resolve failed checks before review.",

  reviewDataset: "Review final dataset",
reviewDescription:
  "Confirm that the transformed dataset, validation results and expected outcome are ready for handoff.",

noTaskBriefProvided: "No task brief provided.",
noExpectedOutcomeProvided: "No expected outcome provided.",

finalWorkingDataset: "Final working dataset",

completingReview: "Completing review...",
completeReview: "✓ Complete review",
reviewConfirm:
  "Confirm the final result before preparing the handoff.",
reviewCompletedReady:
  "✓ Final review completed. Ready to prepare the handoff.",
  prepareFinalDelivery: "Prepare final delivery",
handoffDescription:
  "Export the validated working dataset and complete the workspace when the result is ready to hand off.",

finalRows: "Final rows",
validated: "Validated",
reviewed: "Reviewed",
yes: "Yes",
no: "No",

preparingCsv: "Preparing CSV...",
downloadFinalCsv: "↓ Download final CSV",

completingHandoff: "Completing...",
completeHandoff: "✓ Complete handoff",

handoffNotice:
  "Downloading does not complete the workspace. Complete the handoff only when the result is ready for delivery.",

handoffCompleted:
  "✓ Handoff completed. Workspace is complete.",
  backToDashboard: "Dashboard",
workspaceLabel: "Workspace",
validationChecks: {
  datasetIntegrity: "Dataset integrity",
  datasetIntegrityMessage: (rowCount: number) =>
    `Working dataset contains ${rowCount} rows.`,

  schemaPreserved: "Schema preserved",
  schemaPreservedMessage:
    "Working dataset columns match the original source.",
  schemaChangedMessage:
    "Working dataset columns differ from the original source.",

  duplicateRows: "Duplicate rows",
  duplicateRowsMessage: (count: number) =>
    `${count} duplicate rows remain.`,

  missingValues: (column: string) =>
    `Missing values · ${column}`,
  missingValuesMessage: (
    count: number,
    column: string
  ) =>
    `${count} missing values remain in ${column}.`,
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
    passed: "Başarılı",
failed: "Başarısız",

validateDataset: "Dönüştürülen veri setini doğrula",
validationDescription:
  "Son çalışma veri setini kaynak veri ve uygulama planına göre kontrol et.",

validating: "Doğrulanıyor...",
runFinalValidation: "Son doğrulamayı çalıştır →",
validationIntro:
  "DataPilot son çalışma veri seti üzerinde deterministik kontroller çalıştıracak.",

sourceRows: "Kaynak satırlar",
workingRows: "Çalışma satırları",
checksPassed: "Başarılı kontroller",
totalChecks: "Toplam kontrol",

runValidationAgain: "Doğrulamayı tekrar çalıştır",
validationReady:
  "Gerekli tüm kontroller başarılı. İncelemeye hazır.",
validationNeedsFix:
  "İncelemeden önce başarısız kontrolleri düzelt.",
  reviewDataset: "Son veri setini incele",
reviewDescription:
  "Dönüştürülen veri setinin, doğrulama sonuçlarının ve beklenen sonucun teslim için hazır olduğunu onayla.",

noTaskBriefProvided: "Görev özeti eklenmemiş.",
noExpectedOutcomeProvided: "Beklenen sonuç eklenmemiş.",

finalWorkingDataset: "Son çalışma veri seti",

completingReview: "İnceleme tamamlanıyor...",
completeReview: "✓ İncelemeyi tamamla",
reviewConfirm:
  "Teslime hazırlamadan önce son sonucu onayla.",
reviewCompletedReady:
  "✓ Son inceleme tamamlandı. Teslime hazırlanmaya hazır.",

  prepareFinalDelivery: "Son teslimi hazırla",
handoffDescription:
  "Doğrulanmış çalışma veri setini dışa aktar ve sonuç teslime hazır olduğunda çalışma alanını tamamla.",

finalRows: "Son satırlar",
validated: "Doğrulandı",
reviewed: "İncelendi",
yes: "Evet",
no: "Hayır",

preparingCsv: "CSV hazırlanıyor...",
downloadFinalCsv: "↓ Son CSV'yi indir",

completingHandoff: "Tamamlanıyor...",
completeHandoff: "✓ Teslimi tamamla",

handoffNotice:
  "CSV'yi indirmek çalışma alanını tamamlamaz. Teslim yalnızca sonuç gerçekten hazır olduğunda tamamlanmalıdır.",

handoffCompleted:
  "✓ Teslim tamamlandı. Çalışma alanı tamamlandı.",
  backToDashboard: "Ana Sayfa",
workspaceLabel: "Çalışma Alanı",
validationChecks: {
  datasetIntegrity: "Veri seti bütünlüğü",
  datasetIntegrityMessage: (rowCount: number) =>
    `Çalışma veri seti ${rowCount} satır içeriyor.`,

  schemaPreserved: "Şema korundu",
  schemaPreservedMessage:
    "Çalışma veri setinin sütunları kaynak veriyle eşleşiyor.",
  schemaChangedMessage:
    "Çalışma veri setinin sütunları kaynak veriden farklı.",

  duplicateRows: "Tekrarlanan satırlar",
  duplicateRowsMessage: (count: number) =>
    `${count} tekrarlanan satır kaldı.`,

  missingValues: (column: string) =>
    `Eksik değerler · ${column}`,
  missingValuesMessage: (
    count: number,
    column: string
  ) =>
    `${column} sütununda ${count} eksik değer kaldı.`,
},
    },
  },
} as const;