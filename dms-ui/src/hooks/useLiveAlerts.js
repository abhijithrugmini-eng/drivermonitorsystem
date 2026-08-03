import { useCallback, useEffect, useRef, useState } from 'react';
import { acknowledgeAlert, getAlertDetail, getAlerts, getVehicles, sendAdvisory } from '../services/api';
import { createAlertsSocket } from '../services/websocket';

function upsertAlert(alerts, incoming) {
  const idx = alerts.findIndex((a) => a.id === incoming.id);
  if (idx === -1) return [incoming, ...alerts];
  const next = alerts.slice();
  next[idx] = incoming;
  return next;
}

function toSummaryShape(detail) {
  const { trip_details, evidence, location, vehicle_details, in_cabin_response, recommended_action, ...summary } = detail;
  return summary;
}

export function useLiveAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [selectedAlertId, setSelectedAlertId] = useState(null);
  const [alertDetail, setAlertDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);

  const selectedAlertIdRef = useRef(selectedAlertId);
  selectedAlertIdRef.current = selectedAlertId;

  const refreshDetail = useCallback(async (id) => {
    if (!id) return;
    setDetailLoading(true);
    try {
      const detail = await getAlertDetail(id);
      setAlertDetail(detail);
    } catch (err) {
      console.error('Failed to load alert detail', err);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [alertList, vehicleList] = await Promise.all([getAlerts('active'), getVehicles()]);
        if (cancelled) return;
        setAlerts(alertList);
        setVehicles(vehicleList);
        if (alertList.length > 0) setSelectedAlertId(alertList[0].id);
        setLastUpdatedAt(Date.now());
      } catch (err) {
        console.error('Failed to load initial fleet data', err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const socket = createAlertsSocket((message) => {
      if (message.type !== 'alert_created' && message.type !== 'alert_updated') return;
      setAlerts((prev) => upsertAlert(prev, message.alert));
      setLastUpdatedAt(Date.now());
      if (selectedAlertIdRef.current === message.alert.id) {
        refreshDetail(message.alert.id);
      } else if (!selectedAlertIdRef.current) {
        setSelectedAlertId(message.alert.id);
      }
    }, setConnectionStatus);

    return () => socket.close();
  }, [refreshDetail]);

  useEffect(() => {
    if (selectedAlertId) refreshDetail(selectedAlertId);
    else setAlertDetail(null);
  }, [selectedAlertId, refreshDetail]);

  const selectAlert = useCallback((id) => setSelectedAlertId(id), []);

  const acknowledge = useCallback(async (id) => {
    const updated = await acknowledgeAlert(id);
    setAlerts((prev) => upsertAlert(prev, toSummaryShape(updated)));
    setAlertDetail(updated);
    setLastUpdatedAt(Date.now());
  }, []);

  const advise = useCallback(async (id, message) => {
    const updated = await sendAdvisory(id, message);
    setAlerts((prev) => upsertAlert(prev, toSummaryShape(updated)));
    setAlertDetail(updated);
    setLastUpdatedAt(Date.now());
  }, []);

  const activeAlerts = alerts.filter((a) => a.status === 'ACTIVE');
  const ackLatencies = alerts.map((a) => a.driver_ack_latency_seconds).filter((v) => v != null);
  const avgResponseTimeSeconds = ackLatencies.length
    ? ackLatencies.reduce((sum, v) => sum + v, 0) / ackLatencies.length
    : null;

  return {
    alerts,
    vehicles,
    summary: {
      vehiclesActive: vehicles.length,
      criticalAlerts: activeAlerts.filter((a) => a.severity === 'CRITICAL').length,
      unacknowledged: activeAlerts.length,
      avgResponseTimeSeconds,
    },
    selectedAlertId,
    alertDetail,
    detailLoading,
    connectionStatus,
    lastUpdatedAt,
    selectAlert,
    acknowledge,
    sendAdvisory: advise,
  };
}
