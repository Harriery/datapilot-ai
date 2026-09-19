import json
import os
import uuid

from dotenv import load_dotenv
from openai import OpenAI

from backend.app.models import (
    DataEngineeringTask,
    DataEngineeringTaskStep,
    DataQualityFinding,
    Workspace,
    WorkspacePlanDraft,
)


SUPPORTED_TRANSFORMATION_ISSUES = {
    "missing_values",
    "duplicate_rows",
}

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def generate_workspace_execution_plan(
    workspace: Workspace,
    profile: dict,
    findings: list[DataQualityFinding],
) -> DataEngineeringTask:
    if not findings:
        raise ValueError(
            "Execution plan oluşturmak için finding bulunamadı."
        )
    supported_findings = [
        (index, finding)
        for index, finding in enumerate(findings)
        if finding.issue_type
        in SUPPORTED_TRANSFORMATION_ISSUES
    ]

    if not supported_findings:
        raise ValueError(
            "Bu dataset için şu anda desteklenen "
            "bir transformation finding bulunamadı."
        )

    # Defense in depth:
    # Ham örnek satırlar plan AI'sına gönderilmez.
    safe_profile = {
        key: value
        for key, value in profile.items()
        if key != "sample_rows"
    }

    context = {
        "workspace": {
            "title": workspace.title,
            "usage_context": workspace.usage_context,
            "task_brief": workspace.task_brief,
            "desired_outcome": workspace.desired_outcome,
            "workflow_type": workspace.workflow_type,
        },
        "profile": safe_profile,
        "findings": [
            {
                "index": original_index,
                "issue_type": finding.issue_type,
                "column": finding.column,
                "severity": finding.severity,
                "observation": finding.observation,
                "suggested_action": finding.suggested_action,
            }
            for original_index, finding
            in supported_findings
        ],
    }

    response = client.responses.parse(
        model="gpt-5-mini",
        instructions=(
            "Sen bir Data Engineering execution planner'sın. "
            "Junior'ın verilen işi kendisinin yapacağı kontrollü "
            "bir çalışma planı üret. "
            "Veriyi değiştirme ve çözümü uygulama. "
            "Yalnızca verilen findings listesindeki problemleri kullan. "
            "Bu listedeki her finding backend tarafından "
            "transformation için desteklenmektedir. "
            "Yeni finding uydurma. "
            "Her step için yalnızca geçerli bir finding_index seç. "
            "Aynı finding'i gereksiz yere tekrar kullanma. "
            "Adımları mantıklı çalışma sırasına koy. "
            "En fazla 5 kısa ve uygulanabilir step üret. "
            "Her step başlığı en fazla 90 karakter olsun. "
            "Başlığı tam bir ifade olarak bitir; kesik, yarım veya '/' ile biten başlık üretme. "
            "Step başlıkları çözümü doğrudan vermek yerine "
            "junior'ın yapacağı işi tarif etsin."
        ),
        input=json.dumps(
            context,
            ensure_ascii=False,
            indent=2,
        ),
        text_format=WorkspacePlanDraft,
    )

    draft = response.output_parsed

    if draft is None or not draft.steps:
        raise ValueError(
            "AI geçerli bir execution plan üretmedi."
        )

    task_steps: list[DataEngineeringTaskStep] = []
    used_indexes: set[int] = set()

    for draft_step in draft.steps:
        finding_index = draft_step.finding_index

        supported_indexes = {
            index
            for index, _ in supported_findings
        }
        
        if finding_index not in supported_indexes:
            raise ValueError(
                "AI desteklenmeyen finding index üretti."
            )

        if finding_index in used_indexes:
            continue

        used_indexes.add(finding_index)

        task_steps.append(
            DataEngineeringTaskStep(
                step_number=len(task_steps) + 1,
                title=draft_step.title,
                finding=findings[finding_index],
                status=(
                    "active"
                    if len(task_steps) == 0
                    else "pending"
                ),
            )
        )

    if not task_steps:
        raise ValueError(
            "Execution plan içinde kullanılabilir step bulunamadı."
        )

    return DataEngineeringTask(
        task_id=str(uuid.uuid4()),
        title=draft.title,
        steps=task_steps,
        current_step_number=1,
        status="active",
    )

def generate_local_workspace_execution_plan(
    workspace: Workspace,
    findings: list[DataQualityFinding],
) -> DataEngineeringTask:

    if not findings:
        raise ValueError(
            "Execution plan oluşturmak için finding bulunamadı."
        )

    supported_findings = [
        finding
        for finding in findings
        if finding.issue_type
        in SUPPORTED_TRANSFORMATION_ISSUES
    ]

    if not supported_findings:
        raise ValueError(
            "Bu dataset için şu anda desteklenen "
            "bir transformation finding bulunamadı."
        )

    issue_priority = {
        "duplicate_rows": 0,
        "missing_values": 1,
    }

    severity_priority = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    supported_findings.sort(
        key=lambda finding: (
            issue_priority.get(
                finding.issue_type,
                99,
            ),
            severity_priority.get(
                finding.severity,
                99,
            ),
        )
    )

    task_steps: list[
        DataEngineeringTaskStep
    ] = []

    for finding in supported_findings:

        if (
            finding.issue_type
            == "duplicate_rows"
        ):
            title = (
                "Duplicate kayıtları incele "
                "ve doğrula"
            )

        elif (
            finding.issue_type
            == "missing_values"
        ):
            if finding.column:
                title = (
                    f"{finding.column} kolonundaki "
                    "eksik değerleri incele"
                )
            else:
                title = (
                    "Eksik değerleri incele"
                )

        else:
            continue

        task_steps.append(
            DataEngineeringTaskStep(
                step_number=(
                    len(task_steps) + 1
                ),
                title=title,
                finding=finding,
                status=(
                    "active"
                    if not task_steps
                    else "pending"
                ),
            )
        )

    if not task_steps:
        raise ValueError(
            "Local execution plan oluşturulamadı."
        )

    return DataEngineeringTask(
        task_id=str(uuid.uuid4()),
        title=(
            f"{workspace.title} Data Quality Plan"
        ),
        steps=task_steps,
        current_step_number=1,
        status="active",
    )