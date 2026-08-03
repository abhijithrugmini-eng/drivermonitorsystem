import { severityColors } from '../../utils/severity';

export default function SeverityBadge({ severity }) {
  const colors = severityColors(severity);
  return (
    <span
      className="severity-badge"
      style={{ backgroundColor: colors.bg, color: colors.text, borderColor: colors.border }}
    >
      {severity}
    </span>
  );
}
