function formatResponseTime(seconds) {
  if (seconds == null) return '—';
  return `${Math.round(seconds)}s`;
}

export default function SummaryCards({ vehiclesActive, criticalAlerts, unacknowledged, avgResponseTimeSeconds }) {
  const cards = [
    { label: 'Vehicles Active', value: vehiclesActive },
    { label: 'Critical Alerts', value: criticalAlerts },
    { label: 'Unacknowledged', value: unacknowledged },
    { label: 'Avg Response Time', value: formatResponseTime(avgResponseTimeSeconds) },
  ];

  return (
    <div className="summary-cards">
      {cards.map((card) => (
        <div className="summary-card" key={card.label}>
          <div className="summary-card__label">{card.label.toUpperCase()}</div>
          <div className="summary-card__value">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
