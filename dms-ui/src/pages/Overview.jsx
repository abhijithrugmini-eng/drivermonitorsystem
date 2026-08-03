import { useMemo, useState } from 'react';
import TopBar from '../components/layout/TopBar';
import SummaryCards from '../components/overview/SummaryCards';
import LiveAlertsList from '../components/overview/LiveAlertsList';
import AlertDetailPanel from '../components/overview/AlertDetailPanel';
import { useLiveAlerts } from '../hooks/useLiveAlerts';

export default function Overview() {
  const {
    alerts,
    vehicles,
    summary,
    selectedAlertId,
    alertDetail,
    detailLoading,
    connectionStatus,
    lastUpdatedAt,
    selectAlert,
    acknowledge,
    sendAdvisory,
  } = useLiveAlerts();

  const [regionFilter, setRegionFilter] = useState('All');
  const [routeFilter, setRouteFilter] = useState('All');

  const regions = useMemo(() => [...new Set(vehicles.map((v) => v.region).filter(Boolean))], [vehicles]);
  const routes = useMemo(() => [...new Set(alerts.map((a) => a.route).filter(Boolean))], [alerts]);

  const vehiclesByReg = useMemo(() => {
    const map = new Map();
    vehicles.forEach((v) => map.set(v.registration, v));
    return map;
  }, [vehicles]);

  const filteredAlerts = alerts.filter((alert) => {
    if (routeFilter !== 'All' && alert.route !== routeFilter) return false;
    if (regionFilter !== 'All') {
      const vehicle = vehiclesByReg.get(alert.vehicle_registration);
      if (!vehicle || vehicle.region !== regionFilter) return false;
    }
    return true;
  });

  function handleCallDriver() {
    window.alert('Calling driver… (simulated — no telephony integration in this POC)');
  }

  return (
    <div className="overview-page">
      <TopBar
        regions={regions}
        routes={routes}
        regionFilter={regionFilter}
        routeFilter={routeFilter}
        onRegionChange={setRegionFilter}
        onRouteChange={setRouteFilter}
        connectionStatus={connectionStatus}
        lastUpdatedAt={lastUpdatedAt}
      />
      <SummaryCards {...summary} />
      <div className="overview-page__body">
        <LiveAlertsList alerts={filteredAlerts} selectedId={selectedAlertId} onSelect={selectAlert} />
        <AlertDetailPanel
          alert={alertDetail}
          loading={detailLoading}
          onAcknowledge={acknowledge}
          onSendAdvisory={sendAdvisory}
          onCallDriver={handleCallDriver}
        />
      </div>
    </div>
  );
}
