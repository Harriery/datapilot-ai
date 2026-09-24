import type { AppLanguage } from "./i18n";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

export type DataPreviewDataset =
  | "source"
  | "working";

type DataPreviewResponse = {
  dataset: DataPreviewDataset;
  columns: string[];
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
    en: { label:"{ui.label}", search:"Search preview...", searchButton:"Search", clear:"Clear", page:"Page", of:"of", rows:"rows", loading:"{ui.loading}", previous:"{ui.previous}", next:"{ui.next}", showing:"Showing up to" },
    nl: { label:"DATA VOORBEELD", search:"Zoek in voorbeeld...", searchButton:"Zoeken", clear:"Wissen", page:"Pagina", of:"van", rows:"rijen", loading:"Voorbeeld laden...", previous:"← Vorige", next:"Volgende →", showing:"Maximaal weergegeven" },
    tr: { label:"VERİ ÖNİZLEME", search:"Önizlemede ara...", searchButton:"Ara", clear:"Temizle", page:"Sayfa", of:"/", rows:"satır", loading:"Önizleme yükleniyor...", previous:"← Önceki", next:"Sonraki →", showing:"En fazla gösterilen" },
  }[language];
  const [data, setData] =
    useState<DataPreviewResponse | null>(null);

  const [searchDraft, setSearchDraft] =
    useState("");

  const [search, setSearch] =
    useState("");

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

    return params.toString();
  }, [
    dataset,
    page,
    pageSize,
    search,
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
              No rows match this preview search.
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
              Showing up to {data.page_size} rows
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
