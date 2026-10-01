import pytest

from backend.app.models import (
    PersonalProjectDataModelColumn,
    PersonalProjectDataModelRelationship,
    PersonalProjectDataModelStudio,
    PersonalProjectDataModelTable,
    PersonalProjectKPIDefinition,
)
from backend.app.personal_bi_model_service import (
    validate_personal_bi_model_ready,
)


def _studio():
    return PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="fact_events",
                table_type="fact",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="category_id",
                        source_column="category",
                        role="foreign_key",
                    ),
                    PersonalProjectDataModelColumn(
                        name="amount",
                        source_column="amount",
                        role="measure",
                    ),
                ],
            ),
            PersonalProjectDataModelTable(
                name="dim_category",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="category",
                        source_column="category",
                        role="key",
                    ),
                ],
            ),
        ],
        relationships=[
            PersonalProjectDataModelRelationship(
                from_table="fact_events",
                from_column="category_id",
                to_table="dim_category",
                to_column="category",
                cardinality="many_to_one",
                active=True,
            ),
        ],
        source="user",
    )


def _definitions():
    return [
        PersonalProjectKPIDefinition(
            code="total_amount",
            title="Total amount",
            fact_table="fact_events",
            measure="amount",
            aggregation="sum",
            formula_mode="safe_aggregation",
            formula="SUM(fact_events.amount)",
            description="Total amount.",
            source="user",
        )
    ]


def test_bi_model_ready_accepts_generic_star_model():
    validate_personal_bi_model_ready(
        studio=_studio(),
        definitions=_definitions(),
    )


def test_bi_model_ready_requires_kpi_definition():
    with pytest.raises(
        ValueError,
        match="at least one KPI definition",
    ):
        validate_personal_bi_model_ready(
            studio=_studio(),
            definitions=[],
        )
