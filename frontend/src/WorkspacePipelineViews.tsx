import { useState } from "react";
import type { AppLanguage } from "./i18n";

import {
  CheckCircle2,
  CircleDashed,
  GitBranch,
  ShieldAlert,
} from "lucide-react";

type Operation = {
  operation_id: string;
  title: string;

  status:
    | "pending"
    | "active"
    | "completed";

  origin:
    | "data_quality"
    | "project_requirement"
    | "user";

  code: string | null;

  pipeline_action:
    | {
        action: string;
      }
    | null;

  decision?:
    | "accepted_as_is"
    | null;
  decision_reason?: string | null;
};

type ProcessedDataset = {
  dataset_id: string;
  name: string;
};

type Props = {
  language: AppLanguage;
  operations: Operation[];

  sourceName:
    | string
    | null
    | undefined;

  developmentRows:
    | number
    | null
    | undefined;

  processedDatasets:
    ProcessedDataset[];

  hasModel: boolean;
  kpiCount: number;

  onAddTransformation: () => void;

  developmentSampleEnabled?: boolean;
  canApplyFullDataset?: boolean;

  fullPipelineLoading?: boolean;
  fullPipelineError?: string | null;

  onApplyFullDataset?: () => void;

  onDeleteOperation?: (
    operationId: string
  ) => void;

  onAcceptAsIs?: (
    operationId: string,
    reason: string
  ) => Promise<boolean>;
};

export function WorkspacePipelineView({
  language,
  operations,
  onAddTransformation,
  developmentSampleEnabled = false,
  canApplyFullDataset = false,
  fullPipelineLoading = false,
  fullPipelineError = null,
  onApplyFullDataset,
  onDeleteOperation,
  onAcceptAsIs,
}: Props) {
  const ui = {
    en:{ pipeline:"PIPELINE", title:"Cleaning pipeline", description:"Only structured completed steps can be replayed safely on the full dataset.", add:"+ Add transformation", applying:"Applying...", apply:"Apply to full dataset", blocker:"Complete every step and convert experimental/custom notebook steps into structured actions before full-dataset replay.", total:"Total steps", replayable:"Replayable", attention:"Needs attention", remove:"Remove", pending:"pending", active:"active", completed:"completed", custom:"custom / experimental", accept:"Accept as-is", reason:"Reason / decision note", reasonPlaceholder:"Explain why no transformation is needed...", accepted:"accepted as-is" },
    nl:{ pipeline:"PIPELINE", title:"Opschoningspipeline", description:"Alleen voltooide gestructureerde stappen kunnen veilig op de volledige dataset worden herhaald.", add:"+ Transformatie toevoegen", applying:"Toepassen...", apply:"Toepassen op volledige dataset", blocker:"Voltooi elke stap en zet experimentele/aangepaste notebookstappen om in gestructureerde acties vóór herhaling op de volledige dataset.", total:"Totaal stappen", replayable:"Herhaalbaar", attention:"Aandacht nodig", remove:"Verwijderen", pending:"in afwachting", active:"actief", completed:"voltooid", custom:"aangepast / experimenteel", accept:"Accepteren zoals het is", reason:"Reden / beslisnotitie", reasonPlaceholder:"Leg uit waarom geen transformatie nodig is...", accepted:"geaccepteerd zoals het is" },
    tr:{ pipeline:"PIPELINE", title:"Temizleme pipeline'ı", description:"Yalnızca tamamlanmış yapılandırılmış adımlar tam veri setinde güvenle yeniden uygulanabilir.", add:"+ Dönüşüm ekle", applying:"Uygulanıyor...", apply:"Tam veri setine uygula", blocker:"Tam veri setine uygulamadan önce tüm adımları tamamla ve deneysel/özel notebook adımlarını yapılandırılmış aksiyonlara dönüştür.", total:"Toplam adım", replayable:"Yeniden uygulanabilir", attention:"İlgilenilmesi gereken", remove:"Kaldır", pending:"bekliyor", active:"aktif", completed:"tamamlandı", custom:"özel / deneysel", accept:"Olduğu gibi kabul et", reason:"Gerekçe / karar notu", reasonPlaceholder:"Neden dönüşüm gerekmediğini açıklayın...", accepted:"olduğu gibi kabul edildi" },
  }[language];

  const [acceptingOperationId, setAcceptingOperationId] =
    useState<string | null>(null);
  const [acceptReason, setAcceptReason] =
    useState("");

  const replayable =
    operations.filter(
      (operation) =>
        operation.status ===
          "completed" &&
        operation.pipeline_action
    ).length;

  const blockers =
    operations.filter(
      (operation) =>
        operation.status !==
          "completed" ||
        (
          !operation.pipeline_action &&
          operation.decision !==
            "accepted_as_is"
        )
    );

  return (
    <div className="pipeline-workspace">
      <div className="pipeline-workspace-header">
        <div>
          <span>
            {ui.pipeline}
          </span>

          <h3>
            {ui.title}
          </h3>

          <p>
            {ui.description}
          </p>
        </div>

        <div className="pipeline-header-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={
              onAddTransformation
            }
          >
            {ui.add}
          </button>

          {developmentSampleEnabled &&
            onApplyFullDataset && (
            <button
              type="button"
              className="new-workspace-button"
              disabled={
                fullPipelineLoading ||
                !canApplyFullDataset
              }
              onClick={
                onApplyFullDataset
              }
            >
              {fullPipelineLoading
                ? ui.applying
                : ui.apply}
            </button>
          )}
        </div>
      </div>

      {developmentSampleEnabled &&
        !canApplyFullDataset && (
        <div className="pipeline-blocker-note">
          <ShieldAlert
            size={14}
          />

          {ui.blocker}
        </div>
      )}

      {fullPipelineError && (
        <div className="workspace-form-error">
          {fullPipelineError}
        </div>
      )}

      <div className="pipeline-summary">
        <div>
          <strong>
            {operations.length}
          </strong>
          <span>{ui.total}</span>
        </div>

        <div>
          <strong>
            {replayable}
          </strong>
          <span>{ui.replayable}</span>
        </div>

        <div>
          <strong>
            {blockers.length}
          </strong>
          <span>{ui.attention}</span>
        </div>
      </div>

      <div className="pipeline-step-list">
        {operations.map(
          (operation, index) => (
            <div
              className="pipeline-step"
              key={
                operation.operation_id
              }
            >
              <div className="pipeline-step-order">
                {index + 1}
              </div>

              <div className="pipeline-step-main">
                <div>
                  <strong>
                    {operation.title}
                  </strong>

                  <span>
                    {operation.origin.replaceAll(
                      "_",
                      " "
                    )}
                  </span>
                </div>

                <div className="pipeline-step-badges">
                  <span
                    className={
                      `pipeline-status ${operation.status}`
                    }
                  >
                    {ui[operation.status]}
                  </span>

                  {operation.origin === "user" &&
                    operation.status !== "completed" &&
                    onDeleteOperation && (
                    <button
                      type="button"
                      className="pipeline-remove-step"
                      onClick={() => {
                        onDeleteOperation(
                          operation.operation_id
                        );
                      }}
                    >
                      {ui.remove}
                    </button>
                  )}

                  {operation.status === "active" &&
                    operation.origin === "data_quality" &&
                    onAcceptAsIs && (
                    <button
                      type="button"
                      className="pipeline-remove-step"
                      onClick={() => {
                        setAcceptingOperationId(
                          operation.operation_id
                        );
                        setAcceptReason("");
                      }}
                    >
                      {ui.accept}
                    </button>
                  )}

                  {operation.decision === "accepted_as_is" ? (
                    <span
                      className="pipeline-replayable"
                      title={operation.decision_reason ?? undefined}
                    >
                      <CheckCircle2 size={12} />
                      {ui.accepted}
                    </span>
                  ) : operation.pipeline_action ? (
                    <span className="pipeline-replayable">
                      <CheckCircle2
                        size={12}
                      />
                      {
                        operation
                          .pipeline_action
                          .action
                      }
                    </span>
                  ) : (
                    <span className="pipeline-nonreplayable">
                      <ShieldAlert
                        size={12}
                      />
                      custom / experimental
                    </span>
                  )}
                </div>
              </div>

              {acceptingOperationId === operation.operation_id &&
                operation.status === "active" && (
                <div className="workspace-form">
                  <label>
                    {ui.reason}
                    <textarea
                      value={acceptReason}
                      placeholder={ui.reasonPlaceholder}
                      onChange={(event) => {
                        setAcceptReason(event.target.value);
                      }}
                    />
                  </label>

                  <div className="workspace-form-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        setAcceptingOperationId(null);
                        setAcceptReason("");
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="new-workspace-button"
                      disabled={acceptReason.trim().length < 3}
                      onClick={async () => {
                        const accepted = await onAcceptAsIs!(
                          operation.operation_id,
                          acceptReason.trim()
                        );
                        if (accepted) {
                          setAcceptingOperationId(null);
                          setAcceptReason("");
                        }
                      }}
                    >
                      {ui.accept}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        )}

        {operations.length === 0 && (
          <div className="pipeline-empty">
            <GitBranch size={24} />

            <strong>
              No pipeline steps yet.
            </strong>

            <span>
              Add structured transformations from Explorer or experiment in a notebook first.
            </span>
          </div>
        )}
      </div>

      {blockers.length > 0 && (
        <div className="pipeline-blocker-note">
          <CircleDashed
            size={14}
          />

          Full-dataset replay stays blocked until every step is completed and has structured pipeline metadata.
        </div>
      )}
    </div>
  );
}

export function WorkspaceLineageView({
  language,
  sourceName,
  developmentRows,
  processedDatasets,
  hasModel,
  kpiCount,
  operations,
}: Props) {
  const lineageUi = {
    en:{ raw:"Raw source", immutable:"Immutable source", development:"Development dataset", rows:"rows", pipeline:"Cleaning pipeline", steps:"steps", processed:"Processed dataset", model:"Logical model", dataModel:"Data Model", kpis:"KPI definitions", lineage:"LINEAGE", title:"Workspace data flow", description:"Follow how the immutable source becomes development data, pipeline outputs and BI artifacts." },
    nl:{ raw:"Ruwe bron", immutable:"Onveranderlijke bron", development:"Ontwikkeldataset", rows:"rijen", pipeline:"Opschoningspipeline", steps:"stappen", processed:"Verwerkte dataset", model:"Logisch model", dataModel:"Datamodel", kpis:"KPI-definities", lineage:"HERKOMST", title:"Gegevensstroom van de werkruimte", description:"Volg hoe de onveranderlijke bron verandert in ontwikkeldata, pipeline-uitvoer en BI-artefacten." },
    tr:{ raw:"Ham kaynak", immutable:"Değiştirilemez kaynak", development:"Geliştirme veri seti", rows:"satır", pipeline:"Temizleme pipeline'ı", steps:"adım", processed:"İşlenmiş veri seti", model:"Mantıksal model", dataModel:"Veri Modeli", kpis:"KPI tanımları", lineage:"VERİ AKIŞI", title:"Çalışma alanı veri akışı", description:"Değiştirilemez kaynağın geliştirme verisine, pipeline çıktılarına ve BI varlıklarına nasıl dönüştüğünü izle." },
  }[language];

  const nodes = [
    {
      label:
        sourceName ??
        lineageUi.raw,
      meta:
        lineageUi.immutable,
      kind:
        "source",
    },
    {
      label:
        lineageUi.development,
      meta:
        `${developmentRows ?? 0} ${lineageUi.rows}`,
      kind:
        "sample",
    },
    {
      label:
        lineageUi.pipeline,
      meta:
        `${operations.length} ${lineageUi.steps}`,
      kind:
        "pipeline",
    },
    ...processedDatasets.map(
      (dataset) => ({
        label:
          dataset.name,
        meta:
          lineageUi.processed,
        kind:
          "processed",
      })
    ),
    ...(hasModel
      ? [
          {
            label:
              lineageUi.model,
            meta:
              lineageUi.dataModel,
            kind:
              "model",
          },
        ]
      : []),
    ...(kpiCount > 0
      ? [
          {
            label:
              lineageUi.kpis,
            meta:
              `${kpiCount} KPIs`,
            kind:
              "kpi",
          },
        ]
      : []),
  ];

  return (
    <div className="lineage-workspace">
      <div className="pipeline-workspace-header">
        <div>
          <span>
            {lineageUi.lineage}
          </span>

          <h3>
            {lineageUi.title}
          </h3>

          <p>
            {lineageUi.description}
          </p>
        </div>
      </div>

      <div className="lineage-flow">
        {nodes.map(
          (node, index) => (
            <div
              className="lineage-flow-fragment"
              key={
                `${node.kind}-${node.label}`
              }
            >
              <div
                className={
                  `lineage-node ${node.kind}`
                }
              >
                <strong>
                  {node.label}
                </strong>

                <span>
                  {node.meta}
                </span>
              </div>

              {index <
                nodes.length - 1 && (
                <div className="lineage-arrow">
                  ↓
                </div>
              )}
            </div>
          )
        )}
      </div>
    </div>
  );
}
