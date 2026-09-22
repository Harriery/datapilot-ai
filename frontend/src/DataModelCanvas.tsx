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

  source:
    | "local"
    | "user";
};


type Props = {
  studio: DataModelStudioData;
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

      <Handle
        type="target"
        position={Position.Left}
        className="model-canvas-handle"
      />

      <Handle
        type="source"
        position={Position.Right}
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

        position: {
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

        position: {
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


function createEdges(
  relationships:
    DataModelRelationship[],
): Edge[] {

  return relationships.map(
    (
      relationship,
      index,
    ) => ({
      id:
        `relationship-${index}`,

      source:
        relationship.from_table,

      target:
        relationship.to_table,

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
    })
  );
}


function DataModelCanvas({
  studio,
}: Props) {

  const initialNodes =
    useMemo(
      () =>
        createNodes(
          studio.tables
        ),
      [studio.tables]
    );


  const initialEdges =
    useMemo(
      () =>
        createEdges(
          studio.relationships
        ),
      [studio.relationships]
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


  useEffect(() => {
    setNodes(
      createNodes(
        studio.tables
      )
    );
  }, [
    studio.tables,
    setNodes,
  ]);


  useEffect(() => {
    setEdges(
      createEdges(
        studio.relationships
      )
    );
  }, [
    studio.relationships,
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


          <span className="model-canvas-toolbar-hint">
            Drag tables using ⋮⋮
          </span>

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
            }}

            onPaneClick={() => {
              setSelectedTableId(
                null
              );
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

    </div>
  );
}


export default DataModelCanvas;