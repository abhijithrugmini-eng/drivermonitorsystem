import { severityColors, violationMeta } from '../../utils/severity';

function AlertRow({ alert, selected, onSelect }) {
  const meta = violationMeta(alert.violation_type);
  const isResolved = alert.status !== 'ACTIVE';
  const colors = severityColors(alert.severity);

  const style = isResolved
    ? {}
    : {
        backgroundColor: selected ? colors.bg : 'transparent',
        borderLeftColor: colors.border,
      };

  return (
    <button
      type="button"
      className={`alert-row${selected ? ' alert-row--selected' : ''}${isResolved ? ' alert-row--resolved' : ''}`}
      style={style}
      onClick={() => onSelect(alert.id)}
    >
      <span className="alert-row__icon">{isResolved ? '✓' : meta.icon}</span>
      <span className="alert-row__body">
        <span className="alert-row__title">{meta.label}</span>
        <span className="alert-row__meta">
          {alert.vehicle_registration}
          {alert.route ? ` · ${alert.route}` : ''}
        </span>
      </span>
      <span className="alert-row__time">{isResolved ? 'resolved' : alert.time_ago}</span>
    </button>
  );
}

export default function LiveAlertsList({ alerts, selectedId, onSelect }) {
  return (
    <div className="live-alerts">
      <div className="panel-header">Live Alerts</div>
      <div className="live-alerts__list">
        {alerts.length === 0 && <div className="live-alerts__empty">No alerts yet.</div>}
        {alerts.map((alert) => (
          <AlertRow key={alert.id} alert={alert} selected={alert.id === selectedId} onSelect={onSelect} />
        ))}
      </div>
      <div className="live-alerts__footnote">(scrollable list)</div>
    </div>
  );
}
