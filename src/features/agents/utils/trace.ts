export function isLogThoughtTool(toolName: string) {
  const normalized = toolName.toLowerCase().replace(/[\s_-]+/g, '');
  return normalized.includes('logthought');
}

export function truncateText(value: unknown, max: number) {
  const text = typeof value === 'string' ? value : String(value ?? '');
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

export function prettifyToolName(toolName: string) {
  return toolName
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function tryParseJson(value: string) {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}
