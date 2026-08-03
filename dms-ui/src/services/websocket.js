import { API_BASE_URL } from './api';

const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

// Push-only channel: {type: "alert_created" | "alert_updated", alert: {...}}
// Auto-reconnects with simple exponential backoff on close.
export function createAlertsSocket(onMessage, onStatusChange) {
  let socket = null;
  let reconnectAttempt = 0;
  let reconnectTimer = null;
  let closedByCaller = false;

  function connect() {
    onStatusChange?.('connecting');
    socket = new WebSocket(`${WS_BASE_URL}/ws/alerts`);

    socket.onopen = () => {
      reconnectAttempt = 0;
      onStatusChange?.('live');
    };

    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch (err) {
        console.error('Failed to parse alert message', err);
      }
    };

    socket.onclose = () => {
      onStatusChange?.('offline');
      if (!closedByCaller) scheduleReconnect();
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  function scheduleReconnect() {
    const delay = Math.min(1000 * 2 ** reconnectAttempt, 10000);
    reconnectAttempt += 1;
    reconnectTimer = setTimeout(connect, delay);
  }

  connect();

  return {
    close() {
      closedByCaller = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    },
  };
}
