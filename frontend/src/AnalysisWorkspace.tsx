import {
  useEffect,
  useMemo,
  useState,
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


const SIZE_CLASSES = [
  "small",
  "medium",
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


  /*
   * Yeni analysis oluştuğunda otomatik olarak
   * workspace'e eklenir.
   *
   * Eski analysis silinmişse local UI state'den
   * de temizlenir.
   */
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
          2,
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

      {/* ==================================================
          SAVED ANALYSES
          ================================================== */}

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
                          Local analysis
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


      {/* ==================================================
          ANALYSIS WORKSPACE
          ================================================== */}

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
              cardSizes[id] ?? 1;

            const size =
              SIZE_CLASSES[
                sizeIndex
              ];


            return (
              <article
                key={id}
                className={
                  `analysis-board-card ${
                    `size-${size}`
                  } ${
                    collapsed
                      ? "collapsed"
                      : ""
                  }`
                }
              >

                <header className="analysis-board-card-header">

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
                      title="Make smaller"
                    >
                      −
                    </button>

                    <button
                      type="button"
                      disabled={
                        sizeIndex === 2
                      }
                      onClick={() =>
                        growCard(id)
                      }
                      title="Make larger"
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
                      title={
                        "Remove from workspace"
                      }
                    >
                      ×
                    </button>

                  </div>

                </header>


                <div className="analysis-card-body">

                  <div className="analysis-card-body-inner">

                    <div className="analysis-card-summary">

                      <div>
                        <span>
                          Count
                        </span>

                        <strong>
                          {
                            result
                              .overall
                              .count
                          }
                        </strong>
                      </div>

                      <div>
                        <span>
                          Mean
                        </span>

                        <strong>
                          {
                            result
                              .overall
                              .mean ??
                            "—"
                          }
                        </strong>
                      </div>

                      <div>
                        <span>
                          Min
                        </span>

                        <strong>
                          {
                            result
                              .overall
                              .min ??
                            "—"
                          }
                        </strong>
                      </div>

                      <div>
                        <span>
                          Max
                        </span>

                        <strong>
                          {
                            result
                              .overall
                              .max ??
                            "—"
                          }
                        </strong>
                      </div>

                    </div>


                    {result.grouped_results.length > 0 && (
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

                              <th>Count</th>
                              <th>Mean</th>
                              <th>Min</th>
                              <th>Max</th>
                            </tr>
                          </thead>

                          <tbody>

                            {result.grouped_results
                              .slice(
                                0,
                                10
                              )
                              .map(
                                (
                                  row,
                                  index,
                                ) => (
                                  <tr
                                    key={
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
                                      {row.count}
                                    </td>

                                    <td>
                                      {row.mean ??
                                        "—"}
                                    </td>

                                    <td>
                                      {row.min ??
                                        "—"}
                                    </td>

                                    <td>
                                      {row.max ??
                                        "—"}
                                    </td>
                                  </tr>
                                )
                              )}

                          </tbody>

                        </table>

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