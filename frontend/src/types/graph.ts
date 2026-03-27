export interface GraphNode {
    id: string;
    type: string;
    label: string;
    detail?: string | null;
    meta?: Record<string, unknown>;
}

export interface GraphEdge {
    from: string;
    to: string;
    relation: string;
    meta?: Record<string, unknown>;
}

export interface GraphSnapshot {
    nodes: GraphNode[];
    edges: GraphEdge[];
    meta: {
        counts: Record<string, number>;
        requested_by?: string | null;
        pagination?: {
            limit: number;
            offset: number;
            total_nodes: number;
            returned_nodes: number;
        };
    };
}
