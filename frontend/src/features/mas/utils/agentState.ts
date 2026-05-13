// Provides agent state helpers.
import type { AgentRunningStatus } from '../components/MasDetailSplitView';

// Builds initial agent status.
export function buildInitialAgentStatus(agentNames: string[]) {
  const next: AgentRunningStatus = {};
  for (const agentName of agentNames) {
    next[agentName] = 'waiting';
  }
  return next;
}
