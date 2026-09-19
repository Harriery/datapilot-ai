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
    tasks: {
    eyebrow: "TASKS",
    title: "Task overview",
    description:
      "Track work across all workspaces from one place.",

    loading: "Loading tasks...",
    loadError: "Tasks could not be loaded.",
    empty: "No tasks yet.",

    refresh: "Refresh",
    refreshing: "Refreshing...",

    workspace: "Workspace",
    currentStep: "Current step",
    nextAction: "Next action",

    validation: "Validation",
    review: "Review",
    handoff: "Handoff",

    openWorkspace: "Open workspace →",

    status: {
      todo: "To do",
      active: "Active",
      blocked: "Blocked",
      completed: "Completed",
    },

    systemText: {
    workspaceCompleted: "Workspace completed",
    reviewTransformedDataset:
      "Review transformed dataset",
    reviewTransformationResults:
      "Review transformation results",
    reviewFinalDataset:
      "Review final dataset and changes",
    resolveValidationFailures:
      "Resolve validation failures",
    prepareHandoff:
      "Prepare handoff",
    prepareFinalDatasetHandoff:
      "Prepare final dataset handoff",
  },
  },

  progress: {
    eyebrow: "PROGRESS",
    title: "Development overview",
    description:
      "See how your skills, success rate and independence are developing.",

    loading: "Loading progress...",
    loadError: "Progress could not be loaded.",
    empty: "No progress data yet.",

    refresh: "Refresh",
    refreshing: "Refreshing...",

    skillsTracked: "Skills tracked",
    averageSuccess: "Average success",
    totalAttempts: "Total attempts",
    averageIndependence:
      "Average independence",

    skillPerformance:
      "Skill performance",
    skillPerformanceDescription:
      "Success rate for each tracked skill.",

    mentorIndependence:
      "Mentor support & independence",
    mentorIndependenceDescription:
      "See how much mentor support you currently need for each skill.",
    mentorDependencyHistory:
      "Mentor dependency over time",
    mentorDependencyHistoryDescription:
      "See how your need for mentor support changes across attempts.",
    mentorDependencyEmpty:
      "Not enough attempt history yet.",

    attempt: "Attempt",
    attemptsAxis: "Attempts",
    historyStart: "Started at",
    historyCurrent: "Current level",

    skillDetails: "Skill details",
    skillDetailsDescription:
      "Attempts, current learning stage and mentor mode.",

    success: "Success",
    attempts: "Attempts",
    successfulAttempts:
      "Successful attempts",

    mentorMode: "Mentor mode",
    independenceTrend:
      "Independence trend",
    practicePriority:
      "Practice priority",

    mentorModes: {
      DEMONSTRATE: "Demonstrate",
      TEACH: "Teach",
      GUIDE: "Guide",
      NUDGE: "Nudge",
      NONE: "Independent",
      noData: "No data",
    },

    trends: {
      improving: "Improving",
      stable: "Stable",
      declining: "Declining",
      insufficient_data:
        "Not enough data",
    },

    priorities: {
      high: "High",
      medium: "Medium",
      low: "Low",
      none: "None",
    },

    statuses: {
      new: "New",
      learning: "Learning",
      practicing: "Practicing",
      comfortable: "Comfortable",
    },

    overallReadiness:
      "Overall independence & readiness",

    overallReadinessDescription:
      "A combined view of knowledge, independence and skill coverage.",

    knowledgeScore:
      "Knowledge & success",

    independenceScore:
      "Independence",

    skillCoverage:
      "Skill coverage",

    skillsCovered:
      "skills covered",

    readinessLevels: {
      GUIDE: "Guide",
      NUDGE: "Nudge",
      INDEPENDENT: "Independent",
    },
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

    tasks: {
      eyebrow: "GÖREVLER",
      title: "Görevler",
      description:
        "Tüm çalışma alanlarındaki işleri tek yerden takip et.",

      loading: "Görevler yükleniyor...",
      loadError: "Görevler yüklenemedi.",
      empty: "Henüz görev yok.",

      refresh: "Yenile",
      refreshing: "Yenileniyor...",

      workspace: "Çalışma alanı",
      currentStep: "Mevcut adım",
      nextAction: "Sonraki işlem",

      validation: "Doğrulama",
      review: "İnceleme",
      handoff: "Teslim",

      openWorkspace: "Çalışma alanını aç →",

      status: {
        todo: "Yapılacak",
        active: "Aktif",
        blocked: "Engelli",
        completed: "Tamamlandı",
      },

      systemText: {
      workspaceCompleted:
        "Çalışma alanı tamamlandı",
      reviewTransformedDataset:
        "Dönüştürülen veri setini incele",
      reviewTransformationResults:
        "Dönüştürme sonuçlarını incele",
      reviewFinalDataset:
        "Son veri setini ve değişiklikleri incele",
      resolveValidationFailures:
        "Doğrulama hatalarını çöz",
      prepareHandoff:
        "Teslimi hazırla",
      prepareFinalDatasetHandoff:
        "Son veri setini teslime hazırla",
    },
    },

    progress: {
      eyebrow: "GELİŞİM",
      title: "Gelişim özeti",
      description:
        "Becerilerinin, başarı oranının ve bağımsızlığının nasıl geliştiğini gör.",
        
      loading: "Gelişim verileri yükleniyor...",
      loadError:
        "Gelişim verileri yüklenemedi.",
      empty:
        "Henüz gelişim verisi yok.",
        
      refresh: "Yenile",
      refreshing: "Yenileniyor...",
        
      skillsTracked:
        "Takip edilen beceri",
      averageSuccess:
        "Ortalama başarı",
      totalAttempts:
        "Toplam deneme",
      averageIndependence:
        "Ortalama bağımsızlık",
        
      skillPerformance:
        "Beceri performansı",
      skillPerformanceDescription:
        "Takip edilen her becerideki başarı oranını gör.",
        
      mentorIndependence:
          "Mentor desteği ve bağımsızlık",
      mentorIndependenceDescription:
          "Her beceride şu anda ne kadar mentor desteğine ihtiyaç duyduğunu gör.",
              mentorDependencyHistory:
          "Zaman içinde mentor bağımlılığı",
       mentorDependencyHistoryDescription:
        "Denemeler ilerledikçe mentor desteğine olan ihtiyacının nasıl değiştiğini gör.",

      mentorDependencyEmpty:
        "Henüz yeterli deneme geçmişi yok.",

      attempt: "Deneme",
      attemptsAxis: "Denemeler",
      historyStart: "Başlangıç",
      historyCurrent: "Mevcut seviye",
      
        
      skillDetails:
        "Beceri detayları",
      skillDetailsDescription:
        "Denemeler, öğrenme seviyesi ve mevcut mentor yaklaşımı.",
        
      success: "Başarı",
      attempts: "Deneme",
      successfulAttempts:
        "Başarılı deneme",
        
      mentorMode:
        "Mentor yaklaşımı",
      independenceTrend:
        "Bağımsızlık eğilimi",
      practicePriority:
        "Pratik önceliği",
        
      mentorModes: {
        DEMONSTRATE: "Göster",
        TEACH: "Öğret",
        GUIDE: "Rehberlik et",
        NUDGE: "Hafif yönlendir",
        NONE: "Bağımsız",
        noData: "Veri yok",
      },
    
      trends: {
        improving: "Gelişiyor",
        stable: "Sabit",
        declining: "Geriliyor",
        insufficient_data:
          "Yeterli veri yok",
      },
    
      priorities: {
        high: "Yüksek",
        medium: "Orta",
        low: "Düşük",
        none: "Yok",
      },
    
      statuses: {
        new: "Yeni",
        learning: "Öğreniyor",
        practicing: "Pratik yapıyor",
        comfortable: "Rahat",
      },

      overallReadiness:
        "Genel bağımsızlık ve hazırlık",

      overallReadinessDescription:
        "Bilgi ve başarı, bağımsızlık ve beceri kapsamının birleşik değerlendirmesi.",

      knowledgeScore:
        "Bilgi ve başarı",

      independenceScore:
        "Bağımsızlık",

      skillCoverage:
        "Beceri kapsamı",

      skillsCovered:
        "beceri kapsandı",

      readinessLevels: {
        GUIDE: "Rehberlik gerekli",
        NUDGE: "Hafif yönlendirme",
        INDEPENDENT: "Bağımsız",
      },
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