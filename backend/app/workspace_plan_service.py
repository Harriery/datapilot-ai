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
                "index": index,
                "issue_type": finding.issue_type,
                "column": finding.column,
                "severity": finding.severity,
                "observation": finding.observation,
                "suggested_action": finding.suggested_action,
            }
            for index, finding in enumerate(findings)
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

        if (
            finding_index < 0
            or finding_index >= len(findings)
        ):
            raise ValueError(
                "AI geçersiz finding index üretti."
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