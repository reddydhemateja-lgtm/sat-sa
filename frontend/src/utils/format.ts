export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${hh}:${mm}`;
  } catch {
    return iso;
  }
}

export function humanizeCategory(c: string): string {
  return c
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

export function priorityTone(p: string): 'critical' | 'high' | 'warning' | 'neutral' {
  switch (p) {
    case 'HIGH':
      return 'critical';
    case 'MEDIUM':
      return 'warning';
    case 'LOW':
      return 'info' as unknown as 'neutral';
    default:
      return 'neutral';
  }
}

export function statusTone(s: string): 'critical' | 'warning' | 'success' | 'info' | 'neutral' {
  switch (s) {
    case 'OPEN':
      return 'info';
    case 'CONFIRMED':
      return 'critical';
    case 'REJECTED':
      return 'success';
    case 'FURTHER_REVIEW':
      return 'warning';
    default:
      return 'neutral';
  }
}

export function categoryTone(c: string): 'critical' | 'info' | 'warning' | 'neutral' {
  switch (c) {
    case 'EXECUTION_GAP':
      return 'critical';
    case 'NEGATIVE_SPACE':
      return 'info';
    case 'ANOMALY':
      return 'warning';
    default:
      return 'neutral';
  }
}