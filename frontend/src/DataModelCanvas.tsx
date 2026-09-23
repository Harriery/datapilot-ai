import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

import DataModelTableEditor
  from "./DataModelTableEditor";

import DataModelRelationshipEditor
  from "./DataModelRelationshipEditor";
  
type DataModelColumn = {
  name: string;

  source_column: string | null;

  role:
    | "key"
    | "foreign_key"
    | "dimension"
    | "measure"
    | "attribute"
    | "time";

  aggregation:
    | "count"
    | "sum"
    | "mean"
    | "min"
    | "max"
    | null;
};


type DataModelTable = {
  name: string;

  table_type:
    | "fact"
    | "dimension"
    | "bridge";

  columns: DataModelColumn[];
};


type DataModelRelationship = {
  from_table: string;
  from_column: string;

  to_table: string;
  to_column: string;

  cardinality:
    | "many_to_one"
    | "one_to_many"
    | "one_to_one";

  active: boolean;
};


export type DataModelStudioData = {
  tables: DataModelTable[];

  relationships:
    DataModelRelationship[];

  node_positions?: Record<
    string,
    {
      x: number;
      y: number;
    }
  >;

  source:
    | "local"
    | "user";
};


type Props = {
  studio: DataModelStudioData;

  onSaveStudio: (
    studio: DataModelStudioData
  ) => Promise<void>;

  saving: boolean;
};


type TableNodeData = {
  table: DataModelTable;
};


type TableFlowNode = Node<
  TableNodeData,
  "tableNode"
>;


function getRoleLabel(
  role: DataModelColumn["role"],
) {
  switch (role) {
    case "key":
      return "KEY";

    case "foreign_key":
      return "FK";

    case "measure":
      return "MEASURE";

    case "dimension":
      return "DIMENSION";

    case "attribute":
      return "ATTRIBUTE";

    case "time":
      return "TIME";
  }
}


function getRelationshipLabel(
  cardinality:
    DataModelRelationship["cardinality"],
) {
  if (cardinality === "many_to_one") {
    return "*  →  1";
  }

  if (cardinality === "one_to_many") {
    return "1  →  *";
  }

  return "1  →  1";
}


function TableNode({
  data,
  selected,
}: NodeProps<TableFlowNode>) {

  const [
    expanded,
    setExpanded,
  ] = useState(false);


  const table =
    data.table;


  return (
    <article
      className={
        `model-canvas-table ${
          expanded
            ? "expanded"
            : ""
        } ${
          selected
            ? "selected"
            : ""
        }`
      }
    >

      {/* LEFT */}
      <Handle
        id="target-left"
        type="target"
        position={Position.Left}
        className="model-canvas-handle"
      />

      <Handle
        id="source-left"
        type="source"
        position={Position.Left}
        className="model-canvas-handle"
      />


      {/* RIGHT */}
      <Handle
        id="target-right"
        type="target"
        position={Position.Right}
        className="model-canvas-handle"
      />

      <Handle
        id="source-right"
        type="source"
        position={Position.Right}
        className="model-canvas-handle"
      />


      {/* TOP */}
      <Handle
        id="target-top"
        type="target"
        position={Position.Top}
        className="model-canvas-handle"
      />

      <Handle
        id="source-top"
        type="source"
        position={Position.Top}
        className="model-canvas-handle"
      />


      {/* BOTTOM */}
      <Handle
        id="target-bottom"
        type="target"
        position={Position.Bottom}
        className="model-canvas-handle"
      />

      <Handle
        id="source-bottom"
        type="source"
        position={Position.Bottom}
        className="model-canvas-handle"
      />


      <div className="model-canvas-table-header">

        {/* Sadece buradan sürüklenecek */}
        <span
          className="model-canvas-drag-handle"
          title="Drag table"
        >
          ⋮⋮
        </span>


        <button
          type="button"
          className="model-canvas-table-open nodrag"
          onClick={() =>
            setExpanded(
              (previous) =>
                !previous
            )
          }
        >

          <span>
            <strong>
              {table.name}
            </strong>

            <small>
              {table.columns.length} columns
            </small>
          </span>


          <span
            className={
              `model-canvas-table-type ${
                table.table_type
              }`
            }
          >
            {
              table.table_type
                .toUpperCase()
            }
          </span>


          <span className="model-canvas-chevron">
            {expanded
              ? "−"
              : "+"}
          </span>

        </button>

      </div>


      {expanded && (
        <div className="model-canvas-columns">

          {table.columns.length > 0 ? (
            table.columns.map(
              (column) => (
                <div
                  key={
                    `${table.name}-${column.name}`
                  }
                  className="model-canvas-column"
                >

                  <span>
                    {column.name}
                  </span>

                  <small>
                    {
                      getRoleLabel(
                        column.role
                      )
                    }
                  </small>

                </div>
              )
            )
          ) : (
            <div className="model-canvas-empty-columns">
              No columns
            </div>
          )}

        </div>
      )}

    </article>
  );
}


const nodeTypes = {
  tableNode: TableNode,
};


function createNodes(
  tables: DataModelTable[],
  positions: DataModelStudioData["node_positions"] = {},
): TableFlowNode[] {

  const factTables =
    tables.filter(
      (table) =>
        table.table_type ===
        "fact"
    );

  const otherTables =
    tables.filter(
      (table) =>
        table.table_type !==
        "fact"
    );


  const nodes:
    TableFlowNode[] = [];


  factTables.forEach(
    (table, index) => {

      nodes.push({
        id: table.name,

        type: "tableNode",

        /*
         * Sadece bu class üzerinden
         * node drag yapılacak.
         */
        dragHandle:
          ".model-canvas-drag-handle",

        position:
          positions?.[table.name] ?? {
            x: 80,
            y:
              100 +
              index * 220,
          },

        data: {
          table,
        },
      });
    }
  );


  otherTables.forEach(
    (table, index) => {

      const columnIndex =
        index % 2;

      const rowIndex =
        Math.floor(
          index / 2
        );

      nodes.push({
        id: table.name,

        type: "tableNode",

        dragHandle:
          ".model-canvas-drag-handle",

        position:
          positions?.[table.name] ?? {
            x:
              500 +
              columnIndex *
                320,

            y:
              60 +
              rowIndex *
                180,
          },

        data: {
          table,
        },
      });
    }
  );


  return nodes;
}


function getRelationshipHandles(
  sourceNode: TableFlowNode,
  targetNode: TableFlowNode,
) {
  const sourceWidth =
    sourceNode.measured?.width ?? 220;

  const sourceHeight =
    sourceNode.measured?.height ?? 70;

  const targetWidth =
    targetNode.measured?.width ?? 220;

  const targetHeight =
    targetNode.measured?.height ?? 70;


  const sourceCenterX =
    sourceNode.position.x +
    sourceWidth / 2;

  const sourceCenterY =
    sourceNode.position.y +
    sourceHeight / 2;


  const targetCenterX =
    targetNode.position.x +
    targetWidth / 2;

  const targetCenterY =
    targetNode.position.y +
    targetHeight / 2;


  const dx =
    targetCenterX -
    sourceCenterX;

  const dy =
    targetCenterY -
    sourceCenterY;


  /*
   * Yatay fark daha büyükse
   * LEFT / RIGHT kullan.
   */
  if (
    Math.abs(dx) >=
    Math.abs(dy)
  ) {
    if (dx >= 0) {
      return {
        sourceHandle:
          "source-right",

        targetHandle:
          "target-left",
      };
    }

    return {
      sourceHandle:
        "source-left",

      targetHandle:
        "target-right",
    };
  }


  /*
   * Dikey fark daha büyükse
   * TOP / BOTTOM kullan.
   */
  if (dy >= 0) {
    return {
      sourceHandle:
        "source-bottom",

      targetHandle:
        "target-top",
    };
  }


  return {
    sourceHandle:
      "source-top",

    targetHandle:
      "target-bottom",
  };
}


function createEdges(
  relationships:
    DataModelRelationship[],

  nodes:
    TableFlowNode[],
): Edge[] {

  return relationships.map(
    (
      relationship,
      index,
    ) => {

      const sourceNode =
        nodes.find(
          (node) =>
            node.id ===
            relationship.from_table
        );


      const targetNode =
        nodes.find(
          (node) =>
            node.id ===
            relationship.to_table
        );


      const handles =
        sourceNode &&
        targetNode
          ? getRelationshipHandles(
              sourceNode,
              targetNode,
            )
          : {
              sourceHandle:
                "source-right",

              targetHandle:
                "target-left",
            };


      return {
        id:
          `relationship-${index}`,
        className:
          relationship.active
            ? "model-edge-active"
            : "model-edge-inactive",

        source:
          relationship.from_table,

        target:
          relationship.to_table,

        sourceHandle:
          handles.sourceHandle,

        targetHandle:
          handles.targetHandle,

        type:
          "smoothstep",

        label:
          getRelationshipLabel(
            relationship.cardinality
          ),

        data: {
          from_column:
            relationship.from_column,

          to_column:
            relationship.to_column,

          cardinality:
            relationship.cardinality,

          active:
            relationship.active,
        },
      };
    }
  );
}


function DataModelCanvas({
  studio,
  onSaveStudio,
  saving,
}: Props) {

  const initialNodes =
    useMemo(
      () =>
        createNodes(
          studio.tables,
          studio.node_positions,
        ),
      [
        studio.tables,
        studio.node_positions,
      ]
    );


  const initialEdges =
    useMemo(
      () =>
        createEdges(
          studio.relationships,
          initialNodes,
        ),
      [
        studio.relationships,
        initialNodes,
      ]
    );


  const [
    nodes,
    setNodes,
    onNodesChange,
  ] = useNodesState<TableFlowNode>(
    initialNodes
  );


  const [
    edges,
    setEdges,
    onEdgesChange,
  ] = useEdgesState<Edge>(
    initialEdges
  );


  const [
    flowInstance,
    setFlowInstance,
  ] = useState<
    ReactFlowInstance<
      TableFlowNode,
      Edge
    > | null
  >(null);


  const [
    searchText,
    setSearchText,
  ] = useState("");


  const [
    selectedTableId,
    setSelectedTableId,
  ] = useState<string | null>(
    null
  );

  const [
    selectedRelationshipIndex,
    setSelectedRelationshipIndex,
  ] = useState<number | null>(null);
  
  const [
    editingRelationshipIndex,
    setEditingRelationshipIndex,
  ] = useState<number | null>(
    null
  );

  useEffect(() => {
    setNodes(
      createNodes(
        studio.tables,
        studio.node_positions,
      )
    );
  }, [
    studio.tables,
    studio.node_positions,
    setNodes,
  ]);


  useEffect(() => {
    setEdges(
      createEdges(
        studio.relationships,
        nodes,
      )
    );
  }, [
    studio.relationships,
    nodes,
    setEdges,
  ]);


  const filteredTables =
    studio.tables.filter(
      (table) =>
        table.name
          .toLowerCase()
          .includes(
            searchText
              .trim()
              .toLowerCase()
          )
    );

  const [
    tableEditorOpen,
    setTableEditorOpen,
  ] = useState(false);

  const [
    editingTableName,
    setEditingTableName,
  ] = useState<string | null>(
    null
  );
  const [
    relationshipEditorOpen,
    setRelationshipEditorOpen,
  ] = useState(false);

  function focusTable(
    tableName: string,
  ) {
    setSelectedTableId(
      tableName
    );


    setNodes(
      (currentNodes) =>
        currentNodes.map(
          (node) => ({
            ...node,

            selected:
              node.id ===
              tableName,
          })
        )
    );


    if (!flowInstance) {
      return;
    }


    const targetNode =
      flowInstance.getNode(
        tableName
      );


    if (!targetNode) {
      return;
    }


    flowInstance.fitView({
      nodes: [
        targetNode,
      ],

      padding: 1.2,

      minZoom: 0.8,
      maxZoom: 1.25,

      duration: 400,
    });
  }


  return (
  <>
    <div className="model-studio-workspace">

      {/* ==================================================
          TABLE BROWSER
          ================================================== */}

      <aside className="model-table-browser">

        <div className="model-table-browser-header">

          <div>
            <span className="workspace-overview-label">
              TABLES
            </span>

            <strong>
              {studio.tables.length} tables
            </strong>
          </div>

        </div>


        <input
          type="search"
          className="model-table-search"
          placeholder="Search table..."
          value={searchText}
          onChange={(event) =>
            setSearchText(
              event.target.value
            )
          }
        />


        <div className="model-table-list">

          {filteredTables.map(
            (table) => (

              <button
                key={table.name}
                type="button"
                className={
                  `model-table-list-item ${
                    selectedTableId ===
                    table.name
                      ? "active"
                      : ""
                  }`
                }
                onClick={() =>
                  focusTable(
                    table.name
                  )
                }
              >

                <span>
                  <strong>
                    {table.name}
                  </strong>

                  <small>
                    {table.columns.length}
                    {" "}
                    columns
                  </small>
                </span>


                <span
                  className={
                    `model-table-list-type ${
                      table.table_type
                    }`
                  }
                >
                  {
                    table.table_type ===
                    "dimension"
                      ? "DIM"
                      : table.table_type
                          .toUpperCase()
                  }
                </span>

              </button>

            )
          )}


          {filteredTables.length === 0 && (
            <div className="model-table-list-empty">
              No table found.
            </div>
          )}

        </div>

      </aside>


      {/* ==================================================
          CANVAS
          ================================================== */}

      <div className="model-canvas-column-layout">

        <div className="model-canvas-toolbar">

          <div>
            <strong>
              Model canvas
            </strong>

            <span>
              {studio.relationships.length}
              {" "}
              relationships
            </span>
          </div>


          <div className="model-canvas-toolbar-actions">

            <span className="model-canvas-toolbar-hint">
              Drag tables using ⋮⋮
            </span>

            <button
              type="button"
              className="model-canvas-action-button"
              onClick={() => {
                setEditingTableName(
                  null
                );
              
                setTableEditorOpen(
                  true
                );
              }}
            >
              + Table
            </button>

            <button
              type="button"
              className="model-canvas-action-button"
              disabled={
                !selectedTableId
              }
              onClick={() =>
                setEditingTableName(
                  selectedTableId
                )
              }
            >
              Edit table
            </button>  

            <button
              type="button"
              className="model-canvas-action-button"
              onClick={() => {
                setEditingRelationshipIndex(
                  null
                );
              
                setRelationshipEditorOpen(
                  true
                );
              }}
              disabled={
                studio.tables.length < 2
              }
            >
              + Relationship
            </button>

          </div>

        </div>


        <div className="model-canvas">

          <ReactFlow<
            TableFlowNode,
            Edge
          >
            nodes={nodes}
            edges={edges}

            nodeTypes={nodeTypes}

            onInit={
              setFlowInstance
            }

            onNodesChange={
              onNodesChange
            }

            onEdgesChange={
              onEdgesChange
            }

            onNodeClick={(
              _event,
              node,
            ) => {
              setSelectedTableId(
                node.id
              );

              setSelectedRelationshipIndex(
                null
              );
            }}

            onNodeDragStop={async (
              _event,
              node,
            ) => {
              const nextPositions = {
                ...(studio.node_positions ?? {}),
                [node.id]: {
                  x: node.position.x,
                  y: node.position.y,
                },
              };

              await onSaveStudio({
                ...studio,
                source: "user",
                node_positions:
                  nextPositions,
              });
            }}

            onPaneClick={() => {
              setSelectedTableId(
                null
              );
            
              setSelectedRelationshipIndex(
                null
              );
            }}

            onEdgeClick={(
              _event,
              edge,
            ) => {
              const index =
                Number(
                  edge.id.replace(
                    "relationship-",
                    ""
                  )
                );
              
              if (!Number.isNaN(index)) {
                setSelectedRelationshipIndex(
                  index
                );

                setSelectedTableId(
                  null
                );
              }
            }}

            nodesConnectable={false}

            deleteKeyCode={null}

            fitView

            fitViewOptions={{
              padding: 0.3,
              duration: 350,
            }}

            minZoom={0.3}
            maxZoom={1.8}

            proOptions={{
              hideAttribution: true,
            }}
          >

            <Background
              gap={18}
              size={1}
            />

            <Controls
              showInteractive={false}
            />

            <MiniMap
              pannable
              zoomable
            />

          </ReactFlow>

        </div>

      </div>

      <aside className="model-inspector">
        <div className="model-inspector-header">
          <span className="workspace-overview-label">
            INSPECTOR
          </span>

          <strong>
            {selectedTableId
              ? "Table"
              : selectedRelationshipIndex !== null
                ? "Relationship"
                : "Selection"}
          </strong>
        </div>

        {selectedTableId ? (() => {
          const table =
            studio.tables.find(
              (item) =>
                item.name === selectedTableId
            );

          if (!table) {
            return (
              <p className="model-inspector-empty">
                Select a table or relationship.
              </p>
            );
          }

          const connectedRelationships =
            studio.relationships.filter(
              (relationship) =>
                relationship.from_table === table.name ||
                relationship.to_table === table.name
            ).length;

          return (
            <div className="model-inspector-content">
              <div className="model-inspector-detail">
                <span>Name</span>
                <strong>{table.name}</strong>
              </div>

              <div className="model-inspector-detail">
                <span>Type</span>
                <strong>{table.table_type}</strong>
              </div>

              <div className="model-inspector-detail">
                <span>Columns</span>
                <strong>{table.columns.length}</strong>
              </div>

              <div className="model-inspector-detail">
                <span>Relationships</span>
                <strong>{connectedRelationships}</strong>
              </div>

              <div className="model-inspector-columns">
                {table.columns.map(
                  (column) => (
                    <div key={column.name}>
                      <span>{column.name}</span>
                      <small>
                        {getRoleLabel(column.role)}
                      </small>
                    </div>
                  )
                )}
              </div>

              <button
                type="button"
                className="model-canvas-action-button"
                onClick={() => {
                  setEditingTableName(
                    table.name
                  );
                }}
              >
                Edit table
              </button>
            </div>
          );
        })() : selectedRelationshipIndex !== null &&
          studio.relationships[
            selectedRelationshipIndex
          ] ? (() => {
            const relationship =
              studio.relationships[
                selectedRelationshipIndex
              ];

            return (
              <div className="model-inspector-content">
                <div className="model-inspector-detail">
                  <span>From</span>
                  <strong>
                    {relationship.from_table}.
                    {relationship.from_column}
                  </strong>
                </div>

                <div className="model-inspector-detail">
                  <span>To</span>
                  <strong>
                    {relationship.to_table}.
                    {relationship.to_column}
                  </strong>
                </div>

                <div className="model-inspector-detail">
                  <span>Cardinality</span>
                  <strong>
                    {getRelationshipLabel(
                      relationship.cardinality
                    )}
                  </strong>
                </div>

                <div className="model-inspector-detail">
                  <span>Status</span>
                  <strong>
                    {relationship.active
                      ? "Active"
                      : "Inactive"}
                  </strong>
                </div>

                <div className="model-inspector-actions">
                  <button
                    type="button"
                    className="model-canvas-action-button"
                    onClick={() => {
                      setEditingRelationshipIndex(
                        selectedRelationshipIndex
                      );
                      setRelationshipEditorOpen(
                        true
                      );
                    }}
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    className="model-relationship-delete-button"
                    disabled={saving}
                    onClick={async () => {
                      await onSaveStudio({
                        ...studio,
                        source: "user",
                        relationships:
                          studio.relationships.filter(
                            (_item, index) =>
                              index !==
                              selectedRelationshipIndex
                          ),
                      });

                      setSelectedRelationshipIndex(
                        null
                      );
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })() : (
          <p className="model-inspector-empty">
            Select a table or relationship on the canvas.
          </p>
        )}
      </aside>

    </div>
    



    {(
      tableEditorOpen ||
      editingTableName !== null
    ) && (
      <DataModelTableEditor
        key={
          editingTableName ??
          "new-table"
        }
        studio={studio}
        editingTableName={
          editingTableName
        }
        saving={saving}
        onCancel={() => {
          setTableEditorOpen(
            false
          );
        
          setEditingTableName(
            null
          );
        }}
        onSave={async (
          updatedStudio
        ) => {
        
          await onSaveStudio(
            updatedStudio
          );
        
        
          /*
           * Seçili tablo silindiyse
           * eski selection kalmasın.
           */
          if (
            selectedTableId &&
            !updatedStudio.tables.some(
              (table) =>
                table.name ===
                selectedTableId
            )
          ) {
            setSelectedTableId(
              null
            );
          }
        
        
          setTableEditorOpen(
            false
          );
        
          setEditingTableName(
            null
          );
        }}
      />
    )}


    {relationshipEditorOpen && (
      <DataModelRelationshipEditor
        key={
          editingRelationshipIndex ??
          "new-relationship"
        }
        studio={studio}
        editingRelationshipIndex={
          editingRelationshipIndex
        }
        saving={saving}
        onCancel={() => {
          setRelationshipEditorOpen(
            false
          );
        
          setEditingRelationshipIndex(
            null
          );
        }}
        onSave={async (
          updatedStudio
        ) => {
          await onSaveStudio(
            updatedStudio
          );
        
          setRelationshipEditorOpen(
            false
          );
        
          setEditingRelationshipIndex(
            null
          );
        }}
      />
    )}
  </>
);

}


export default DataModelCanvas;