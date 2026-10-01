from backend.app.models import (
    PersonalProjectDataModelStudio,
    PersonalProjectKPIDefinition,
)


def validate_personal_bi_model_ready(
    studio: PersonalProjectDataModelStudio,
    definitions: list[
        PersonalProjectKPIDefinition
    ],
) -> None:
    """
    Validate the minimum semantic-model contract before
    advancing a personal BI project to Analysis.

    This intentionally uses model roles and relationships,
    not dataset-specific table or column names.
    """

    fact_tables = [
        table
        for table in studio.tables
        if table.table_type == "fact"
    ]

    if not fact_tables:
        raise ValueError(
            "BI semantic model requires at least one fact table."
        )

    dimension_tables = [
        table
        for table in studio.tables
        if table.table_type == "dimension"
    ]

    if not dimension_tables:
        raise ValueError(
            "BI semantic model requires at least one dimension table."
        )

    active_relationships = [
        relationship
        for relationship in studio.relationships
        if relationship.active
    ]

    if not active_relationships:
        raise ValueError(
            "BI semantic model requires at least one active relationship."
        )

    if not definitions:
        raise ValueError(
            "BI semantic model requires at least one KPI definition."
        )

    table_names = {
        table.name
        for table in studio.tables
    }

    for relationship in active_relationships:
        if (
            relationship.from_table
            not in table_names
            or relationship.to_table
            not in table_names
        ):
            raise ValueError(
                "BI semantic model contains a relationship "
                "to a missing table."
            )
