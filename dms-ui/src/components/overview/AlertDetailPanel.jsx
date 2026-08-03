import { useState } from 'react';
import SeverityBadge from '../shared/SeverityBadge';
import { evidenceUrl } from '../../services/api';
import { severityColors, violationMeta } from '../../utils/severity';

function formatTime(ts) {
  if (!ts) return '—';
  return new Date(ts * 1000).toLocaleTimeString();
}

function formatDuration(seconds) {
  if (seconds == null) return '—';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

export default function AlertDetailPanel({ alert, loading, onAcknowledge, onSendAdvisory, onCallDriver }) {
  const [expanded, setExpanded] = useState(false);

  if (loading && !alert) {
    return (
      <div className="alert-detail alert-detail--empty">
        <p>Loading alert…</p>
      </div>
    );
  }

  if (!alert) {
    return (
      <div className="alert-detail alert-detail--empty">
        <p>Select an alert from the list to see full details.</p>
      </div>
    );
  }

  const meta = violationMeta(alert.violation_type);
  const colors = severityColors(alert.severity);
  const { trip_details: trip, evidence, location, vehicle_details: vehicle, in_cabin_response: cabin, recommended_action: recommended } = alert;

  return (
    <div className={`alert-detail${expanded ? ' alert-detail--expanded' : ''}`}>
      <div className="alert-detail__header" style={{ backgroundColor: colors.bg, borderColor: colors.border }}>
        <div>
          <span className="alert-detail__header-icon">{meta.icon}</span>
          <span className="alert-detail__header-title">
            {meta.label} Alert — {alert.vehicle_registration}
          </span>
          <SeverityBadge severity={alert.severity} />
        </div>
        <button type="button" className="btn btn--ghost" onClick={() => setExpanded((e) => !e)}>
          ✓ {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      <div className="alert-detail__grid">
        <section className="detail-card">
          <h4>Trip Details</h4>
          <p>Driver: {trip.driver_name} {trip.driver_id ? `(ID ${trip.driver_id})` : ''}</p>
          <p>Route: {trip.route || '—'}</p>
          <p>Shift: {trip.shift_label || '—'}</p>
          <p>Speed at event: {trip.speed_at_event_kmh != null ? `${trip.speed_at_event_kmh} km/h` : '—'}</p>
          <p>Trip started: {formatTime(trip.trip_started_at)} ({formatDuration(trip.elapsed_trip_seconds)} ago)</p>
        </section>

        <section className="detail-card">
          <h4>Evidence</h4>
          {evidence.image_url ? (
            <img className="detail-card__evidence-img" src={evidenceUrl(evidence.image_url)} alt="Violation evidence" />
          ) : (
            <div className="detail-card__evidence-placeholder">▶ video clip placeholder</div>
          )}
          <p>Severity: {evidence.severity}</p>
          <p>Frame window: {evidence.frame_window}</p>
          <p>Captured at: {formatTime(evidence.captured_at)}</p>
          <p>Upload status: {evidence.sync_status === 'SYNCED' ? '✓ Synced' : evidence.sync_status}</p>
        </section>

        <section className="detail-card">
          <h4>Current Location</h4>
          <div className="detail-card__map-placeholder">📍 map / pin</div>
          <p>
            {location.lat != null ? `${location.lat}°N, ${location.lon}°E` : '—'}
            {location.waypoint_name ? ` — ${location.distance_to_waypoint_km} km from ${location.waypoint_name}` : ''}
          </p>
        </section>

        <section className="detail-card">
          <h4>Vehicle Details</h4>
          <p>Reg: {vehicle.registration}</p>
          <p>{vehicle.vehicle_type}</p>
          <p>Edge device: {vehicle.edge_device_status}, firmware {vehicle.firmware_version}</p>
        </section>

        <section className="detail-card detail-card--in-cabin">
          <h4>In-Cabin Response</h4>
          <p>🔔 Buzzer fired at {formatTime(cabin.buzzer_fired_at)}</p>
          <p>Driver acknowledged in {cabin.driver_ack_latency_seconds != null ? `${cabin.driver_ack_latency_seconds}s` : '—'}</p>
          <p>
            Speed reduced {cabin.speed_before_kmh ?? '—'} → {cabin.speed_after_kmh ?? '—'} km/h
          </p>
        </section>

        <section className="detail-card">
          <h4>Recommended Action</h4>
          <p>{recommended.text}</p>
          {recommended.advisory_sent_at && <p className="detail-card__advisory-sent">Advisory sent ✓</p>}
          <button type="button" className="btn btn--primary" onClick={() => onSendAdvisory(alert.id)}>
            ➤ Send advisory
          </button>
        </section>
      </div>

      <div className="alert-detail__actions">
        <button type="button" className="btn" onClick={() => onCallDriver(alert.id)}>
          📞 Call driver
        </button>
        <button
          type="button"
          className="btn btn--primary"
          disabled={alert.status !== 'ACTIVE'}
          onClick={() => onAcknowledge(alert.id)}
        >
          ✓ {alert.status === 'ACTIVE' ? 'Acknowledge' : 'Acknowledged'}
        </button>
        <button type="button" className="btn" onClick={() => onSendAdvisory(alert.id)}>
          ➤ Send advisory
        </button>
      </div>
    </div>
  );
}
