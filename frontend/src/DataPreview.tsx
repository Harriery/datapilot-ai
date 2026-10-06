import type { AppLanguage } from "./i18n";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

export type DataPreviewDataset =
  | "source"
  | "working";

type PreviewColumnType =
  | "text"
  | "number"
  | "datetime"
  | "boolean";

type PreviewFilterOperator =
  | "is_missing"
  | "is_not_missing"
  | "is_blank"
  | "is_not_blank"
  | "equals"
  | "not_equals"
  | "contains"
  | "not_contains"
  | "starts_with"
  | "ends_with"
  | "greater_than"
  | "greater_than_or_equal"
  | "less_than"
  | "less_than_or_equal"
  | "between"
  | "before"
  | "after"
  | "date_between"
  | "in"
  | "not_in"
  | "is_duplicate"
  | "is_unique";

type PreviewFilter = {
  id: string;
  column: string;
  operator: PreviewFilterOperator;
  value: string;
  value_to: string;
};

type DataPreviewResponse = {
  dataset: DataPreviewDataset;
  columns: string[];
  column_types: Record<string, PreviewColumnType>;
  total_row_count: number;
  filtered_row_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  rows: Record<string, unknown>[];
};

type Props = {
  language: AppLanguage;
  learnerId: string;
  workspaceId: string;
  dataset: DataPreviewDataset;
  title: string;
  description?: string;
  pageSize?: number;
  selectedColumn?: string | null;
  refreshToken?: number;
  onColumnClick?: (
    column: string
  ) => void;
};

const OPERATOR_LABELS: Record<
  PreviewFilterOperator,
  string
> = {
  is_missing: "Is missing",
  is_not_missing: "Is not missing",
  is_blank: "Is blank",
  is_not_blank: "Is not blank",
  equals: "Equals",
  not_equals: "Does not equal",
  contains: "Contains",
  not_contains: "Does not contain",
  starts_with: "Starts with",
  ends_with: "Ends with",
  greater_than: "Greater than",
  greater_than_or_equal: "Greater than or equal",
  less_than: "Less than",
  less_than_or_equal: "Less than or equal",
  between: "Between",
  before: "Before",
  after: "After",
  date_between: "Date between",
  in: "Is one of",
  not_in: "Is not one of",
  is_duplicate: "Is duplicate",
  is_unique: "Is unique",
};

const COMMON_OPERATORS: PreviewFilterOperator[] = [
  "is_missing",
  "is_not_missing",
  "is_duplicate",
  "is_unique",
  "equals",
  "not_equals",
  "in",
  "not_in",
];

function operatorsForType(
  type: PreviewColumnType | undefined,
): PreviewFilterOperator[] {
  if (type === "number") {
    return [
      ...COMMON_OPERATORS,
      "greater_than",
      "greater_than_or_equal",
      "less_than",
      "less_than_or_equal",
      "between",
    ];
  }

  if (type === "datetime") {
    return [
      ...COMMON_OPERATORS,
      "before",
      "after",
      "date_between",
    ];
  }

  if (type === "boolean") {
    return [
      "is_missing",
      "is_not_missing",
      "equals",
      "not_equals",
    ];
  }

  return [
    ...COMMON_OPERATORS,
    "is_blank",
    "is_not_blank",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
  ];
}

function operatorNeedsValue(
  operator: PreviewFilterOperator,
) {
  return ![
    "is_missing",
    "is_not_missing",
    "is_blank",
    "is_not_blank",
    "is_duplicate",
    "is_unique",
  ].includes(operator);
}

function operatorNeedsSecondValue(
  operator: PreviewFilterOperator,
) {
  return [
    "between",
    "date_between",
  ].includes(operator);
}

function newFilter(
  columns: string[],
): PreviewFilter {
  return {
    id: crypto.randomUUID(),
    column: columns[0] ?? "",
    operator: "is_missing",
    value: "",
    value_to: "",
  };
}

function DataPreview({
  language,
  learnerId,
  workspaceId,
  dataset,
  title,
  description,
  pageSize = 25,
  selectedColumn = null,
  refreshToken = 0,
  onColumnClick,
}: Props) {
  const ui = {
    en: {
      label:"DATA PREVIEW",
      search:"Search preview...",
      searchButton:"Search",
      clear:"Clear",
      page:"Page",
      of:"of",
      rows:"rows",
      loading:"Loading preview...",
      previous:"← Previous",
      next:"Next →",
      showing:"Showing up to",
      filters:"Filters",
      addFilter:"+ Add filter",
      clearFilters:"Clear filters",
      filterLogic:"Match",
      all:"All conditions (AND)",
      any:"Any condition (OR)",
      value:"Value",
      secondValue:"To",
      readOnly:"Preview filters are read-only and never modify the dataset.",
      remove:"Remove filter",
      empty:"No rows match the current preview filters.",
    },
    nl: {
      label:"DATA VOORBEELD",
      search:"Zoek in voorbeeld...",
      searchButton:"Zoeken",
      clear:"Wissen",
      page:"Pagina",
      of:"van",
      rows:"rijen",
      loading:"Voorbeeld laden...",
      previous:"← Vorige",
      next:"Volgende →",
      showing:"Maximaal weergegeven",
      filters:"Filters",
      addFilter:"+ Filter toevoegen",
      clearFilters:"Filters wissen",
      filterLogic:"Overeenkomst",
      all:"Alle voorwaarden (AND)",
      any:"Een voorwaarde (OR)",
      value:"Waarde",
      secondValue:"Tot",
      readOnly:"Voorbeeldfilters zijn alleen-lezen en wijzigen de dataset nooit.",
      remove:"Filter verwijderen",
      empty:"Geen rijen voldoen aan de huidige voorbeeldfilters.",
    },
    tr: {
      label:"VERİ ÖNİZLEME",
      search:"Önizlemede ara...",
      searchButton:"Ara",
      clear:"Temizle",
      page:"Sayfa",
      of:"/",
      rows:"satır",
      loading:"Önizleme yükleniyor...",
      previous:"← Önceki",
      next:"Sonraki →",
      showing:"En fazla gösterilen",
      filters:"Filtreler",
      addFilter:"+ Filtre ekle",
      clearFilters:"Filtreleri temizle",
      filterLogic:"Eşleştirme",
      all:"Tüm koşullar (AND)",
      any:"Herhangi bir koşul (OR)",
      value:"Değer",
      secondValue:"Bitiş",
      readOnly:"Önizleme filtreleri salt okunurdur; veri setini değiştirmez.",
      remove:"Filtreyi kaldır",
      empty:"Mevcut önizleme filtrelerine uyan satır yok.",
    },
  }[language];

  const [data, setData] =
    useState<DataPreviewResponse | null>(null);

  const [searchDraft, setSearchDraft] =
    useState("");

  const [search, setSearch] =
    useState("");

  const [filters, setFilters] =
    useState<PreviewFilter[]>([]);

  const [filterLogic, setFilterLogic] =
    useState<"and" | "or">("and");

  const [page, setPage] =
    useState(1);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams({
      dataset,
      page: String(page),
      page_size: String(pageSize),
    });

    if (search) {
      params.set(
        "search",
        search
      );
    }

    if (filters.length > 0) {
      params.set(
        "filters",
        JSON.stringify(
          filters.map((filter) => ({
            column: filter.column,
            operator: filter.operator,
            value:
              operatorNeedsValue(filter.operator)
                ? filter.value
                : null,
            value_to:
              operatorNeedsSecondValue(filter.operator)
                ? filter.value_to
                : null,
          }))
        )
      );

      params.set(
        "filter_logic",
        filterLogic
      );
    }

    return params.toString();
  }, [
    dataset,
    page,
    pageSize,
    search,
    filters,
    filterLogic,
    refreshToken,
  ]);

  useEffect(() => {
    let cancelled = false;

    async function loadPreview() {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/workspaces/${learnerId}/${workspaceId}/data/preview?${query}`
        );

        if (!response.ok) {
          const body = await response.json().catch(
            () => null
          );

          throw new Error(
            body?.detail ??
            "Data preview yüklenemedi."
          );
        }

        const result: DataPreviewResponse =
          await response.json();

        if (!cancelled) {
          setData(result);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Data preview yüklenemedi."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadPreview();

    return () => {
      cancelled = true;
    };
  }, [
    learnerId,
    workspaceId,
    query,
    refreshToken,
  ]);

  function submitSearch() {
    setPage(1);
    setSearch(
      searchDraft.trim()
    );
  }

  function clearSearch() {
    setSearchDraft("");
    setSearch("");
    setPage(1);
  }

  function addFilter() {
    const columns =
      data?.columns ?? [];

    if (columns.length === 0) {
      return;
    }

    setFilters((previous) => [
      ...previous,
      newFilter(columns),
    ]);
    setPage(1);
  }

  function updateFilter(
    id: string,
    changes: Partial<PreviewFilter>,
  ) {
    setFilters((previous) =>
      previous.map((filter) => {
        if (filter.id !== id) {
          return filter;
        }

        const updated = {
          ...filter,
          ...changes,
        };

        if (changes.column) {
          const type =
            data?.column_types[
              changes.column
            ];

          const allowed =
            operatorsForType(type);

          if (
            !allowed.includes(
              updated.operator
            )
          ) {
            updated.operator =
              allowed[0];
          }
        }

        return updated;
      })
    );
    setPage(1);
  }

  function removeFilter(
    id: string,
  ) {
    setFilters((previous) =>
      previous.filter(
        (filter) =>
          filter.id !== id
      )
    );
    setPage(1);
  }

  function clearFilters() {
    setFilters([]);
    setFilterLogic("and");
    setPage(1);
  }

  return (
    <section className="data-preview-card">
      <div className="data-preview-header">
        <div>
          <span className="workspace-overview-label">
            {ui.label}
          </span>

          <h3>
            {title}
          </h3>

          {description && (
            <p>
              {description}
            </p>
          )}
        </div>

        {data && (
          <div className="data-preview-counts">
            <strong>
              {data.filtered_row_count}
            </strong>

            <span>
              {ui.of} {data.total_row_count} {ui.rows}
            </span>
          </div>
        )}
      </div>

      <div className="data-preview-toolbar">
        <div className="data-preview-search">
          <input
            value={searchDraft}
            placeholder={ui.search}
            onChange={(event) => {
              setSearchDraft(
                event.target.value
              );
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                submitSearch();
              }
            }}
          />

          <button
            type="button"
            onClick={submitSearch}
          >
            {ui.searchButton}
          </button>

          {search && (
            <button
              type="button"
              className="secondary"
              onClick={clearSearch}
            >
              {ui.clear}
            </button>
          )}
        </div>

        {data && (
          <span className="data-preview-page-label">
            {ui.page} {data.page} / {data.total_pages}
          </span>
        )}
      </div>

      {data && (
        <div className="data-preview-filter-panel">
          <div className="data-preview-filter-heading">
            <div>
              <strong>{ui.filters}</strong>
              <span>{ui.readOnly}</span>
            </div>

            <div className="data-preview-filter-actions">
              <button
                type="button"
                onClick={addFilter}
              >
                {ui.addFilter}
              </button>

              {filters.length > 0 && (
                <button
                  type="button"
                  className="secondary"
                  onClick={clearFilters}
                >
                  {ui.clearFilters}
                </button>
              )}
            </div>
          </div>

          {filters.length > 1 && (
            <label className="data-preview-filter-logic">
              <span>{ui.filterLogic}</span>
              <select
                value={filterLogic}
                onChange={(event) => {
                  setFilterLogic(
                    event.target.value as
                      "and" | "or"
                  );
                  setPage(1);
                }}
              >
                <option value="and">
                  {ui.all}
                </option>
                <option value="or">
                  {ui.any}
                </option>
              </select>
            </label>
          )}

          {filters.map((filter) => {
            const columnType =
              data.column_types[
                filter.column
              ];
            const operators =
              operatorsForType(
                columnType
              );
            const needsValue =
              operatorNeedsValue(
                filter.operator
              );
            const needsSecondValue =
              operatorNeedsSecondValue(
                filter.operator
              );

            return (
              <div
                className="data-preview-filter-row"
                key={filter.id}
              >
                <select
                  value={filter.column}
                  onChange={(event) => {
                    updateFilter(
                      filter.id,
                      {
                        column:
                          event.target.value,
                      }
                    );
                  }}
                >
                  {data.columns.map(
                    (column) => (
                      <option
                        key={column}
                        value={column}
                      >
                        {column}
                      </option>
                    )
                  )}
                </select>

                <select
                  value={filter.operator}
                  onChange={(event) => {
                    updateFilter(
                      filter.id,
                      {
                        operator:
                          event.target.value as
                            PreviewFilterOperator,
                        value: "",
                        value_to: "",
                      }
                    );
                  }}
                >
                  {operators.map(
                    (operator) => (
                      <option
                        key={operator}
                        value={operator}
                      >
                        {
                          OPERATOR_LABELS[
                            operator
                          ]
                        }
                      </option>
                    )
                  )}
                </select>

                {needsValue && (
                  <input
                    type={
                      columnType === "datetime"
                        ? "date"
                        : columnType === "number"
                          ? "number"
                          : "text"
                    }
                    value={filter.value}
                    placeholder={
                      filter.operator === "in" ||
                      filter.operator === "not_in"
                        ? "A, B, C"
                        : ui.value
                    }
                    onChange={(event) => {
                      updateFilter(
                        filter.id,
                        {
                          value:
                            event.target.value,
                        }
                      );
                    }}
                  />
                )}

                {needsSecondValue && (
                  <input
                    type={
                      columnType === "datetime"
                        ? "date"
                        : "number"
                    }
                    value={filter.value_to}
                    placeholder={ui.secondValue}
                    onChange={(event) => {
                      updateFilter(
                        filter.id,
                        {
                          value_to:
                            event.target.value,
                        }
                      );
                    }}
                  />
                )}

                <button
                  type="button"
                  className="data-preview-filter-remove"
                  title={ui.remove}
                  aria-label={ui.remove}
                  onClick={() => {
                    removeFilter(
                      filter.id
                    );
                  }}
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      )}

      {loading ? (
        <p className="muted">
          {ui.loading}
        </p>
      ) : error ? (
        <div className="workspace-form-error">
          {error}
        </div>
      ) : data ? (
        <>
          <div className="workspace-working-table-wrap data-preview-table-wrap">
            <table className="workspace-working-table">
              <thead>
                <tr>
                  {data.columns.map(
                    (column) => (
                      <th
                        key={column}
                        className={
                          selectedColumn === column
                            ? "data-preview-column-selected"
                            : undefined
                        }
                      >
                        {onColumnClick ? (
                          <button
                            type="button"
                            className="data-preview-column-button"
                            onClick={() => {
                              onColumnClick(
                                column
                              );
                            }}
                          >
                            {column}
                          </button>
                        ) : (
                          column
                        )}
                      </th>
                    )
                  )}
                </tr>
              </thead>

              <tbody>
                {data.rows.map(
                  (row, rowIndex) => (
                    <tr key={rowIndex}>
                      {data.columns.map(
                        (column) => (
                          <td
                            key={
                              `${rowIndex}-${column}`
                            }
                          >
                            {row[column] === null ||
                            row[column] === undefined
                              ? "—"
                              : String(
                                  row[column]
                                )}
                          </td>
                        )
                      )}
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>

          {data.rows.length === 0 && (
            <p className="data-preview-empty">
              {ui.empty}
            </p>
          )}

          <div className="data-preview-pagination">
            <button
              type="button"
              disabled={data.page <= 1}
              onClick={() => {
                setPage(
                  Math.max(
                    1,
                    data.page - 1
                  )
                );
              }}
            >
              {ui.previous}
            </button>

            <span>
              {ui.showing} {data.page_size} {ui.rows}
            </span>

            <button
              type="button"
              disabled={
                data.page >= data.total_pages
              }
              onClick={() => {
                setPage(
                  Math.min(
                    data.total_pages,
                    data.page + 1
                  )
                );
              }}
            >
              {ui.next}
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}

export default DataPreview;
