// Formats MAS date time.
// Provides format helpers.
export function formatMasDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

// Handles split MAS test case.
export function splitMasTestCaseName(name: string) {
  return name.split('-', 1)[0];
}

// Formats MAS agent name.
export function formatMasAgentName(agentName: string) {
  return agentName
    .replace(/_agent$/, '')
    .replace('general', 'General')
    .replace('esi345', 'ESI3,4,5')
    .replace('esi2', 'ESI2')
    .replace('esi1', 'ESI1')
    .replace('vitals', 'Vitals')
    .replace('doctor', 'Doctor');
}
