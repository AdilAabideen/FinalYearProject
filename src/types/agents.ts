export type AgentCatalogSummaryDto = {
  name: string;
  title: string;
  description: string;
  tools_count: number;
};

export type AgentCatalogSummary = {
  name: string;
  title: string;
  description: string;
  toolsCount: number;
};

export type ToolCatalogItemDto = {
  name: string;
  description: string;
  args_schema: Record<string, unknown>;
};

export type AgentCatalogDetailDto = {
  name: string;
  title: string;
  description: string;
  input_schema: Record<string, unknown>;
  tools: ToolCatalogItemDto[];
};

export type ToolCatalogItem = {
  name: string;
  description: string;
  argsSchema: Record<string, unknown>;
};

export type AgentCatalogDetail = {
  name: string;
  title: string;
  description: string;
  inputSchema: Record<string, unknown>;
  tools: ToolCatalogItem[];
};
