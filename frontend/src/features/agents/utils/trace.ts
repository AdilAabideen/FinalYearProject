// Checks log thought tool.
// Provides trace helpers.
export function isLogThoughtTool(toolName: string) {
  const normalized = toolName.toLowerCase().replace(/[\s_-]+/g, '');
  return normalized.includes('logthought');
}

// Handles truncate text.
export function truncateText(value: unknown, max: number) {
  const text = typeof value === 'string' ? value : String(value ?? '');
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

// Handles prettify tool name.
export function prettifyToolName(toolName: string) {
  return toolName
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
// Maps logic.
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

// Handles try parse JSON.
export function tryParseJson(value: string) {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}
