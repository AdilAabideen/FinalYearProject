import type { AgentRunningStatus } from '../components/MasDetailSplitView';

export function buildInitialAgentStatus(agentNames: string[]) {
  const next: AgentRunningStatus = {};
  for (const agentName of agentNames) {
    next[agentName] = 'waiting';
  }
  return next;
}
