import { NodeTypes } from '@xyflow/react';
import { TriggerNode } from './TriggerNode';
import { ConditionNode } from './ConditionNode';
import { ActionNode } from './ActionNode';

export * from './types';
export * from './dagUtils';
export * from './TriggerNode';
export * from './ConditionNode';
export * from './ActionNode';

export const automationNodeTypes: NodeTypes = {
  trigger: TriggerNode as any,
  condition: ConditionNode as any,
  action: ActionNode as any,
  default: TriggerNode as any,
};
