import {
  useEffect,
  useMemo,
  useState,
  type DragEvent,
} from "react";

import type {
  AnalysisResultData,
} from "./PersonalAnalysisPlan";


type Props = {
  results: AnalysisResultData[];

  onDeleteAnalysis: (
    analysisId: string
  ) => void;
};


type AnalysisItem = {
  id: string;
  result: AnalysisResultData;
};


type SortMode =
  | "top_value"
  | "bottom_value"
  | "alphabetical"
  | "highest_count"
  | "lowest_count";


const SORT_OPTIONS: {
  value: SortMode;
  label: string;
}[] = [
  {
    value: "top_value",
    label: "Top KPI value",
  },
  {
    value: "bottom_value",
    label: "Bottom KPI value",
  },
  {
    value: "alphabetical",
    label: "Alphabetical",
  },
  {
    value: "highest_count",
    label: "Highest count",
  },
  {
    value: "lowest_count",
    label: "Lowest count",
  },
];


function AnalysisSortSelect({
  value,
  onChange,
}: {
  value: SortMode;
  onChange: (
    value: SortMode
  ) => void;
}) {
  const [
    open,
    setOpen,
  ] = useState(false);

  const selectedLabel =
    SORT_OPTIONS.find(
      (option) =>
        option.value === value
    )?.label ??
    "Sort";

  return (
    <div
      className={
        `analysis-sort-select ${
          open
            ? "open"
            : ""
        }`
      }
    >
      <button
        type="button"
        className="analysis-sort-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() =>
          setOpen(
            (previous) =>
              !previous
          )
        }
      >
        <span>
          {selectedLabel}
        </span>

        <span
          className="analysis-sort-chevron"
          aria-hidden="true"
        >
          ▾
        </span>
      </button>

      {open && (
        <div
          className="analysis-sort-menu"
          role="listbox"
        >
          {SORT_OPTIONS.map(
            (option) => (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={
                  option.value === value
                }
                className={
                  option.value === value
                    ? "analysis-sort-option selected"
                    : "analysis-sort-option"
                }
                onClick={() => {
                  onChange(
                    option.value
                  );

                  setOpen(false);
                }}
              >
                {option.label}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}


const SIZE_CLASSES = [
  "small",
  "large",
] as const;


function getAnalysisId(
  result: AnalysisResultData,
  index: number,
) {
  return (
    result.analysis_id ??
    [
      "legacy",
      result.measure,
      result.dimension ?? "overall",
      index,
    ].join("-")
  );
}


function formatAnalysisNumber(
  value: number | null | undefined,
): string {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 2,
    }
  ).format(value);
}


function AnalysisWorkspace({
  results,
  onDeleteAnalysis,
}: Props) {

  const items = useMemo<AnalysisItem[]>(
    () =>
      results.map(
        (result, index) => ({
          id: getAnalysisId(
            result,
            index,
          ),
          result,
        })
      ),
    [results]
  );


  const [
    libraryOpen,
    setLibraryOpen,
  ] = useState(true);


  const [
    visibleIds,
    setVisibleIds,
  ] = useState<string[]>([]);


  const [
    collapsedIds,
    setCollapsedIds,
  ] = useState<string[]>([]);


  const [
    cardSizes,
    setCardSizes,
  ] = useState<
    Record<string, number>
  >({});


  const [
    sortModes,
    setSortModes,
  ] = useState<
    Record<string, SortMode>
  >({});


  const [
    draggingId,
    setDraggingId,
  ] = useState<string | null>(null);


  const [
    dragOverId,
    setDragOverId,
  ] = useState<string | null>(null);


  useEffect(() => {

    const ids =
      items.map(
        (item) => item.id
      );


    setVisibleIds(
      (previous) => {

        const existing =
          previous.filter(
            (id) =>
              ids.includes(id)
          );

        const added =
          ids.filter(
            (id) =>
              !existing.includes(id)
          );

        return [
          ...existing,
          ...added,
        ];
      }
    );


    setCollapsedIds(
      (previous) =>
        previous.filter(
          (id) =>
            ids.includes(id)
        )
    );


    setCardSizes(
      (previous) => {

        const next:
          Record<string, number> = {};

        for (const id of ids) {
          next[id] =
            previous[id] ?? 1;
        }

        return next;
      }
    );


    setSortModes(
      (previous) => {

        const next:
          Record<string, SortMode> = {};

        for (const id of ids) {
          next[id] =
            previous[id] ??
            "top_value";
        }

        return next;
      }
    );

  }, [items]);


  function toggleCollapsed(
    id: string,
  ) {
    setCollapsedIds(
      (previous) =>
        previous.includes(id)
          ? previous.filter(
              (item) =>
                item !== id
            )
          : [
              ...previous,
              id,
            ]
    );
  }


  function moveVisibleItem(
    draggedId: string,
    targetId: string,
  ) {
    if (draggedId === targetId) {
      return;
    }

    setVisibleIds(
      (previous) => {
        const fromIndex =
          previous.indexOf(draggedId);

        const toIndex =
          previous.indexOf(targetId);

        if (
          fromIndex === -1 ||
          toIndex === -1
        ) {
          return previous;
        }

        const next = [...previous];

        const [movedItem] =
          next.splice(fromIndex, 1);

        next.splice(
          toIndex,
          0,
          movedItem,
        );

        return next;
      }
    );
  }


  function handleDrop(
    event: DragEvent<HTMLElement>,
    targetId: string,
  ) {
    event.preventDefault();

    if (draggingId) {
      moveVisibleItem(
        draggingId,
        targetId,
      );
    }

    setDraggingId(null);
    setDragOverId(null);
  }


  function shrinkCard(
    id: string,
  ) {
    setCardSizes(
      (previous) => ({
        ...previous,

        [id]: Math.max(
          0,
          (previous[id] ?? 1) - 1,
        ),
      })
    );
  }


  function growCard(
    id: string,
  ) {
    setCardSizes(
      (previous) => ({
        ...previous,

        [id]: Math.min(
          1,
          (previous[id] ?? 1) + 1,
        ),
      })
    );
  }


  function removeFromWorkspace(
    id: string,
  ) {
    setVisibleIds(
      (previous) =>
        previous.filter(
          (item) =>
            item !== id
        )
    );
  }


  function addToWorkspace(
    id: string,
  ) {
    setVisibleIds(
      (previous) =>
        previous.includes(id)
          ? previous
          : [
              ...previous,
              id,
            ]
    );
  }


  const visibleItems =
    visibleIds
      .map(
        (id) =>
          items.find(
            (item) =>
              item.id === id
          )
      )
      .filter(
        (
          item,
        ): item is AnalysisItem =>
          item !== undefined
      );


  if (items.length === 0) {
    return null;
  }


  return (
    <section
      className={
        `analysis-workbench ${
          libraryOpen
            ? ""
            : "library-collapsed"
        }`
      }
    >

      <aside className="analysis-library">

        <div className="analysis-library-header">

          {libraryOpen && (
            <div>
              <span className="workspace-overview-label">
                SAVED
              </span>

              <strong>
                Analyses
              </strong>
            </div>
          )}

          <button
            type="button"
            className="analysis-library-toggle"
            onClick={() =>
              setLibraryOpen(
                (previous) =>
                  !previous
              )
            }
            title={
              libraryOpen
                ? "Close saved analyses"
                : "Open saved analyses"
            }
          >
            {libraryOpen
              ? "‹"
              : "›"}
          </button>

        </div>


        {libraryOpen && (
          <div className="analysis-library-list">

            {items.map(
              ({
                id,
                result,
              }) => {

                const visible =
                  visibleIds.includes(
                    id
                  );

                return (
                  <div
                    key={id}
                    className={
                      `analysis-library-item ${
                        visible
                          ? "active"
                          : ""
                      }`
                    }
                  >

                    <button
                      type="button"
                      className="analysis-library-open"
                      onClick={() =>
                        visible
                          ? toggleCollapsed(id)
                          : addToWorkspace(id)
                      }
                    >
                      <span>
                        <strong>
                          {result.measure}
                          {result.dimension
                            ? ` by ${result.dimension}`
                            : ""}
                        </strong>

                        <small>
                          {result.kpi_code
                            ? "Semantic analysis"
                            : "Local analysis"}
                        </small>
                      </span>

                      <span
                        className="analysis-library-status"
                      >
                        {visible
                          ? "✓"
                          : "+"}
                      </span>
                    </button>


                    {result.analysis_id && (
                      <button
                        type="button"
                        className="analysis-library-delete"
                        title="Delete analysis"
                        onClick={() =>
                          onDeleteAnalysis(
                            result.analysis_id!
                          )
                        }
                      >
                        ×
                      </button>
                    )}

                  </div>
                );

              }
            )}

          </div>
        )}

      </aside>


      <div className="analysis-board">

        {visibleItems.length === 0 && (
          <div className="analysis-board-empty">
            <strong>
              Analysis workspace is empty
            </strong>

            <p>
              Choose an analysis from the
              Saved Analyses panel.
            </p>
          </div>
        )}


        {visibleItems.map(
          ({
            id,
            result,
          }) => {

            const collapsed =
              collapsedIds.includes(
                id
              );

            const sizeIndex =
              Math.min(
                cardSizes[id] ?? 1,
                1
              );

            const size =
              SIZE_CLASSES[
                sizeIndex
              ];

            const semantic =
              Boolean(
                result.kpi_code
              );

            const sortMode =
              sortModes[id] ??
              "top_value";

            const sortedRows = [
              ...result.grouped_results,
            ].sort(
              (left, right) => {
                if (
                  sortMode ===
                  "alphabetical"
                ) {
                  return String(
                    left.value ?? ""
                  ).localeCompare(
                    String(
                      right.value ?? ""
                    )
                  );
                }

                if (
                  sortMode ===
                  "highest_count"
                ) {
                  return (
                    right.count -
                    left.count
                  );
                }

                if (
                  sortMode ===
                  "lowest_count"
                ) {
                  return (
                    left.count -
                    right.count
                  );
                }

                const leftValue =
                  semantic
                    ? left.metric_value
                    : left.mean;

                const rightValue =
                  semantic
                    ? right.metric_value
                    : right.mean;

                const safeLeft =
                  leftValue ??
                  Number.NEGATIVE_INFINITY;

                const safeRight =
                  rightValue ??
                  Number.NEGATIVE_INFINITY;

                return (
                  sortMode ===
                  "bottom_value"
                    ? safeLeft - safeRight
                    : safeRight - safeLeft
                );
              }
            );

            const rowLimit =
              sizeIndex === 0
                ? 0
                : 10;

            const visibleRows =
              sortedRows.slice(
                0,
                rowLimit
              );


            return (
              <article
                key={id}
                onDragOver={(event) => {
                  event.preventDefault();

                  if (
                    draggingId &&
                    draggingId !== id
                  ) {
                    setDragOverId(id);
                  }
                }}
                onDragLeave={() => {
                  if (dragOverId === id) {
                    setDragOverId(null);
                  }
                }}
                onDrop={(event) =>
                  handleDrop(
                    event,
                    id,
                  )
                }
                className={
                  `analysis-board-card ${
                    `size-${size}`
                  } ${
                    collapsed
                      ? "collapsed"
                      : ""
                  } ${
                    dragOverId === id
                      ? "drag-over"
                      : ""
                  } ${
                    draggingId === id
                      ? "dragging"
                      : ""
                  }`
                }
              >

                <header className="analysis-board-card-header">
                  <span
                    className="analysis-drag-handle"
                    draggable
                    title="Drag to reorder"
                    onDragStart={(event) => {
                      setDraggingId(id);

                      event.dataTransfer.effectAllowed =
                        "move";

                      event.dataTransfer.setData(
                        "text/plain",
                        id,
                      );
                    }}
                    onDragEnd={() => {
                      setDraggingId(null);
                      setDragOverId(null);
                    }}
                  >
                    ⋮⋮
                  </span>

                  <button
                    type="button"
                    className="analysis-board-card-title"
                    onClick={() =>
                      toggleCollapsed(
                        id
                      )
                    }
                    aria-expanded={
                      !collapsed
                    }
                  >
                    <span>
                      {collapsed
                        ? "▸"
                        : "▾"}
                    </span>

                    <strong>
                      {result.measure}
                      {result.dimension
                        ? ` by ${result.dimension}`
                        : ""}
                    </strong>
                  </button>


                  <div className="analysis-board-card-actions">

                    <button
                      type="button"
                      disabled={
                        sizeIndex === 0
                      }
                      onClick={() =>
                        shrinkCard(id)
                      }
                      title="Show less detail"
                    >
                      −
                    </button>

                    <button
                      type="button"
                      disabled={
                        sizeIndex === 1
                      }
                      onClick={() =>
                        growCard(id)
                      }
                      title="Show more detail"
                    >
                      +
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        removeFromWorkspace(
                          id
                        )
                      }
                      title="Remove from workspace"
                    >
                      ×
                    </button>

                  </div>

                </header>


                <div className="analysis-card-body">

                  <div className="analysis-card-body-inner">

                    <div
                      className={
                        semantic
                          ? "analysis-card-summary semantic"
                          : "analysis-card-summary"
                      }
                    >

                      <div>
                        <span>
                          {semantic
                            ? "Records"
                            : "Count"}
                        </span>

                        <strong>
                          {formatAnalysisNumber(
                            result
                              .overall
                              .count
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          {semantic
                            ? "KPI value"
                            : "Mean"}
                        </span>

                        <strong>
                          {formatAnalysisNumber(
                            semantic
                              ? result
                                  .overall
                                  .metric_value
                              : result
                                  .overall
                                  .mean
                          )}
                        </strong>
                      </div>

                      {semantic ? (
                        <>
                          <div>
                            <span>
                              Groups
                            </span>

                            <strong>
                              {formatAnalysisNumber(
                                result
                                  .grouped_results
                                  .length
                              )}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Dimension
                            </span>

                            <strong className="analysis-summary-text">
                              {result.dimension ??
                                "Overall"}
                            </strong>
                          </div>
                        </>
                      ) : (
                        <>
                          <div>
                            <span>
                              Min
                            </span>

                            <strong>
                              {formatAnalysisNumber(
                                result
                                  .overall
                                  .min
                              )}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Max
                            </span>

                            <strong>
                              {formatAnalysisNumber(
                                result
                                  .overall
                                  .max
                              )}
                            </strong>
                          </div>
                        </>
                      )}

                    </div>


                    {result.grouped_results.length > 0 && (
                      <div className="analysis-card-table-section">

                        <div className="analysis-table-toolbar">
                          <span>
                            Showing {
                              Math.min(
                                rowLimit,
                                result
                                  .grouped_results
                                  .length
                              )
                            } of {
                              result
                                .grouped_results
                                .length
                            } groups
                          </span>

                          <div className="analysis-sort-control">
                            <span>
                              Sort
                            </span>

                            <AnalysisSortSelect
                              value={sortMode}
                              onChange={(nextMode) =>
                                setSortModes(
                                  (previous) => ({
                                    ...previous,
                                    [id]:
                                      nextMode,
                                  })
                                )
                              }
                            />
                          </div>
                        </div>

                        <div className="analysis-card-table-wrap">

                          <table className="analysis-card-table">

                            <thead>
                              <tr>
                                <th>
                                  {
                                    result.dimension ??
                                    "Value"
                                  }
                                </th>

                                <th>
                                  Count
                                </th>

                                <th>
                                  {semantic
                                    ? "KPI value"
                                    : "Mean"}
                                </th>

                                {!semantic && (
                                  <>
                                    <th>Min</th>
                                    <th>Max</th>
                                  </>
                                )}
                              </tr>
                            </thead>

                            <tbody>

                              {visibleRows.map(
                                (
                                  row,
                                  index,
                                ) => (
                                  <tr
                                    key={
                                      String(
                                        row.value
                                      ) +
                                      "-" +
                                      index
                                    }
                                  >
                                    <td>
                                      {
                                        row.value ===
                                        null
                                          ? "Missing"
                                          : String(
                                              row.value
                                            )
                                      }
                                    </td>

                                    <td>
                                      {formatAnalysisNumber(
                                        row.count
                                      )}
                                    </td>

                                    <td>
                                      {formatAnalysisNumber(
                                        semantic
                                          ? row.metric_value
                                          : row.mean
                                      )}
                                    </td>

                                    {!semantic && (
                                      <>
                                        <td>
                                          {formatAnalysisNumber(
                                            row.min
                                          )}
                                        </td>

                                        <td>
                                          {formatAnalysisNumber(
                                            row.max
                                          )}
                                        </td>
                                      </>
                                    )}
                                  </tr>
                                )
                              )}

                            </tbody>

                          </table>

                        </div>

                      </div>
                    )}

                  </div>

                </div>

              </article>
            );
          }
        )}

      </div>

    </section>
  );
}


export default AnalysisWorkspace;
