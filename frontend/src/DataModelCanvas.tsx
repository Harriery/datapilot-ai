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


      <button
        type="button"
        className="model-canvas-table-header nodrag"
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

        position: {
          x: 80,
          y:
            100 +
            index * 230,
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

        position: {
          x:
            520 +
            columnIndex *
              340,

          y:
            50 +
            rowIndex *
              190,
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


  return (
    <div className="model-canvas">

      <ReactFlow<
        TableFlowNode,
        Edge
      >
        nodes={nodes}
        edges={edges}

        nodeTypes={nodeTypes}

        onNodesChange={
          onNodesChange
        }

        onEdgesChange={
          onEdgesChange
        }

        nodesConnectable={false}

        deleteKeyCode={null}

        fitView

        fitViewOptions={{
          padding: 0.25,
          duration: 350,
        }}

        minZoom={0.25}
        maxZoom={2}

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
  );
}


export default DataModelCanvas;