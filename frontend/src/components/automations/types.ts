import { Node, Edge } from '@xyflow/react';
import type { CrmAutomationRecord } from '@/types/crm';

export interface AutomationNodeData extends Record<string, unknown> {
  label: string;
  nodeType?: 'trigger' | 'condition' | 'action';
  automation: CrmAutomationRecord;
  condition_config?: {
    field?: string;
    operator?: string;
    value?: string;
  };
}

export type AutomationWorkflowNode = Node<AutomationNodeData, 'trigger' | 'condition' | 'action' | 'default'>;

export type AutomationWorkflowEdge = Edge<{
  condition_type?: string;
  condition_key?: string | null;
  condition_value?: string | null;
  source_node_id?: string;
  target_node_id?: string;
  [key: string]: unknown;
}>;
