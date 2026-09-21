from backend.app.models import (
    PersonalProjectDataModelColumn,
    PersonalProjectDataModelPlan,
    PersonalProjectDataModelRelationship,
    PersonalProjectDataModelStudio,
    PersonalProjectDataModelTable,
)


def _normalize_name(value: str) -> str:
    return (
        value
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def build_personal_data_model_studio(
    data_model_plan: PersonalProjectDataModelPlan,
) -> PersonalProjectDataModelStudio:

    fact_columns: list[
        PersonalProjectDataModelColumn
    ] = []

    dimension_tables: list[
        PersonalProjectDataModelTable
    ] = []

    relationships: list[
        PersonalProjectDataModelRelationship
    ] = []

    used_fact_columns: set[str] = set()

    # Dimensions used by the fact table.
    for dimension in data_model_plan.dimensions:
        if dimension not in used_fact_columns:
            fact_columns.append(
                PersonalProjectDataModelColumn(
                    name=dimension,
                    source_column=dimension,
                    role="foreign_key",
                    aggregation=None,
                )
            )

            used_fact_columns.add(
                dimension
            )

        dimension_table_name = (
            f"dim_{_normalize_name(dimension)}"
        )

        dimension_tables.append(
            PersonalProjectDataModelTable(
                name=dimension_table_name,
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name=dimension,
                        source_column=dimension,
                        role="key",
                        aggregation=None,
                    )
                ],
            )
        )

        relationships.append(
            PersonalProjectDataModelRelationship(
                from_table=(
                    data_model_plan.base_table
                ),
                from_column=dimension,
                to_table=dimension_table_name,
                to_column=dimension,
                cardinality="many_to_one",
                active=True,
            )
        )

    # Optional time dimension.
    if data_model_plan.time_dimension:
        time_column = (
            data_model_plan.time_dimension
        )

        if time_column not in used_fact_columns:
            fact_columns.append(
                PersonalProjectDataModelColumn(
                    name=time_column,
                    source_column=time_column,
                    role="foreign_key",
                    aggregation=None,
                )
            )

            used_fact_columns.add(
                time_column
            )

        time_table_name = (
            f"dim_{_normalize_name(time_column)}"
        )

        dimension_tables.append(
            PersonalProjectDataModelTable(
                name=time_table_name,
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name=time_column,
                        source_column=time_column,
                        role="key",
                        aggregation=None,
                    )
                ],
            )
        )

        relationships.append(
            PersonalProjectDataModelRelationship(
                from_table=(
                    data_model_plan.base_table
                ),
                from_column=time_column,
                to_table=time_table_name,
                to_column=time_column,
                cardinality="many_to_one",
                active=True,
            )
        )

    # Physical source columns used by confirmed measures.
    for measure in data_model_plan.measures:
        if measure.column is None:
            continue

        if measure.column in used_fact_columns:
            continue

        fact_columns.append(
            PersonalProjectDataModelColumn(
                name=measure.column,
                source_column=measure.column,
                role="measure",
                aggregation=None,
            )
        )

        used_fact_columns.add(
            measure.column
        )

    fact_table = (
        PersonalProjectDataModelTable(
            name=data_model_plan.base_table,
            table_type="fact",
            columns=fact_columns,
        )
    )

    return PersonalProjectDataModelStudio(
        tables=[
            fact_table,
            *dimension_tables,
        ],
        relationships=relationships,
        source="local",
    )