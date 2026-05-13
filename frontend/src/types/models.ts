// Defines models types.
export type ModelSpecDto = {
  id: string;
  provider: string;
  description?: string | null;
};

export type ModelSpec = {
  id: string;
  provider: string;
  description: string | null;
};

