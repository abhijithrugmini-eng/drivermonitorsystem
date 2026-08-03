const STATUS_LABEL = {
  live: 'Live',
  connecting: 'Connecting…',
  offline: 'Offline',
};

export default function StatusDot({ status }) {
  return (
    <span className={`status-dot status-dot--${status}`}>
      <span className="status-dot__dot" aria-hidden="true" />
      {STATUS_LABEL[status] || 'Unknown'}
    </span>
  );
}
