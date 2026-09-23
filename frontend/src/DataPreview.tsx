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
  learnerId: string;
  workspaceId: string;
  dataset: DataPreviewDataset;
  title: string;
  description?: string;
  pageSize?: number;
};

function DataPreview({
  learnerId,
  workspaceId,
  dataset,
  title,
  description,
  pageSize = 25,
}: Props) {
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
            DATA PREVIEW
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
              of {data.total_row_count} rows
            </span>
          </div>
        )}
      </div>

      <div className="data-preview-toolbar">
        <div className="data-preview-search">
          <input
            value={searchDraft}
            placeholder="Search preview..."
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
            Search
          </button>

          {search && (
            <button
              type="button"
              className="secondary"
              onClick={clearSearch}
            >
              Clear
            </button>
          )}
        </div>

        {data && (
          <span className="data-preview-page-label">
            Page {data.page} / {data.total_pages}
          </span>
        )}
      </div>

      {loading ? (
        <p className="muted">
          Loading preview...
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
                      <th key={column}>
                        {column}
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
              ← Previous
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
              Next →
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}

export default DataPreview;
