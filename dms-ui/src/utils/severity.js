// Single source of truth for severity colors + violation-type icon/label —
// CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue per specs/🎯_COMPLETE_DESIGN_PACKAGE.md

export const SEVERITY_COLORS = {
  CRITICAL: { bg: '#fdecea', border: '#e5484d', text: '#a4201c', banner: '#e5484d' },
  HIGH: { bg: '#fff4e6', border: '#f2994a', text: '#94540a', banner: '#f2994a' },
  MEDIUM: { bg: '#fffbe0', border: '#e0b400', text: '#7a6100', banner: '#e0b400' },
  LOW: { bg: '#eaf2ff', border: '#3b82f6', text: '#1d4ed8', banner: '#3b82f6' },
};

export const VIOLATION_META = {
  DROWSINESS_PATTERN: { icon: '😴', label: 'Drowsiness' },
  PHONE_USAGE: { icon: '📱', label: 'Phone usage' },
  DISTRACTION_PATTERN: { icon: '👀', label: 'Distraction' },
  CONTINUOUS_DRIVE: { icon: '🕐', label: 'Continuous drive' },
};

export function severityColors(severity) {
  return SEVERITY_COLORS[severity] || SEVERITY_COLORS.LOW;
}

export function violationMeta(violationType) {
  return VIOLATION_META[violationType] || { icon: '⚠', label: violationType };
}
