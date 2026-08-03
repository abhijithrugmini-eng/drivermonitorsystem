import { useEffect, useState } from 'react';
import StatusDot from '../shared/StatusDot';

function useTicker(intervalMs) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}

function formatUpdatedAgo(lastUpdatedAt) {
  if (!lastUpdatedAt) return '—';
  const seconds = Math.max(0, Math.round((Date.now() - lastUpdatedAt) / 1000));
  return `${seconds}s ago`;
}

export default function TopBar({
  regions = [],
  routes = [],
  regionFilter,
  routeFilter,
  onRegionChange,
  onRouteChange,
  connectionStatus,
  lastUpdatedAt,
}) {
  useTicker(1000);

  return (
    <header className="top-bar">
      <div className="top-bar__filters">
        <label className="top-bar__filter">
          Region:
          <select value={regionFilter} onChange={(e) => onRegionChange(e.target.value)}>
            <option value="All">All</option>
            {regions.map((region) => (
              <option key={region} value={region}>
                {region}
              </option>
            ))}
          </select>
        </label>
        <label className="top-bar__filter">
          Route:
          <select value={routeFilter} onChange={(e) => onRouteChange(e.target.value)}>
            <option value="All">All</option>
            {routes.map((route) => (
              <option key={route} value={route}>
                {route}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="top-bar__status">
        <StatusDot status={connectionStatus} />
        <span className="top-bar__updated">updated {formatUpdatedAgo(lastUpdatedAt)}</span>
      </div>
    </header>
  );
}
