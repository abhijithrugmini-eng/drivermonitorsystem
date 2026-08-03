# Fleet Simulator Specification

## Goal
Build a lightweight simulator capable of generating realistic truck GPS and telematics data for demonstrating fleet management capabilities.
The simulator should mimic trucks moving along predefined road routes and continuously publish location updates and telemetry events.

---

## Functional Requirements

### 1. Truck Simulation
- Simulate one or more trucks.
- Each truck has:
  - Truck ID
  - Driver ID (optional)
  - Current GPS position
  - Speed
  - Heading
  - Status (Moving, Stopped, Idle)

---

### 2. Route Simulation
- A truck follows a predefined route.
- Routes consist of a sequence of GPS coordinates.
- Support multiple sample routes:
  - Busy highway
  - Medium traffic highway
  - Remote highway

The simulator should move the truck smoothly between coordinates.

---

### 3. GPS Updates
Generate GPS updates every configurable interval (default: 1 second).
Each update contains:
```json
{
  "truckId": "TRUCK-001",
  "timestamp": "...",
  "latitude": 40.12345,
  "longitude": -89.12345,
  "speed": 72,
  "heading": 180,
  "status": "MOVING"
}
```

---

### 4. Telematics Events
Generate simple events such as:
- Engine Started
- Engine Stopped
- Speed Changed
- Entered Geofence
- Exited Geofence
- Fuel Low
- Idle
- Route Completed

Events should be configurable and may be generated randomly or based on truck state.

---

### 5. Simulation Controls
The simulator should expose the following operations:
- Start Simulation
- Stop Simulation
- Pause Simulation
- Resume Simulation
- Change Simulation Speed
- Add Truck
- Remove Truck

---

## Interfaces

### Simulator API
```text
start()
stop()
pause()
resume()
addTruck(truckConfig)
removeTruck(truckId)
loadRoute(routeId)
setSimulationSpeed(multiplier)
```

---

### GPS Publisher
```text
publishLocation(locationUpdate)
```
Called whenever the truck position changes.

---

### Event Publisher
```text
publishEvent(event)
```
Called whenever a telematics event occurs.

---

## Configuration
Support a simple configuration file.

Example:
```yaml
simulationSpeed: 5
gpsInterval: 1000
defaultSpeed: 80
numberOfTrucks: 20
routes:
  - la-lasvegas
  - dallas-houston
  - us50-nevada
```

---

## Non-functional Requirements
- Support at least 100 simulated trucks.
- Movement should appear smooth on a map.
- Simulator should be deterministic when using the same random seed.
- Components should be independent so that GPS, telemetry, and UI can evolve separately.

---

## Future Enhancements
- Traffic simulation
- Weather simulation
- Driver behavior profiles
- Historical trip replay
- Kafka/MQTT integration
- Vehicle diagnostics
