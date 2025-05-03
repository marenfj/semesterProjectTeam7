# E‑Scooter Emergency Alert System

Course: TTM4115 – Design of Communicating Systems • March 2025

A **Raspberry Pi‑based safety add‑on** that *automatically* detects e‑scooter crashes, warns the rider, and—if the rider does not cancel within 30 seconds—alerts emergency services with GPS coordinates.

---

## 1 . Why it matters

* E‑scooter riders are **10× more likely** to be injured than cyclists.
* Many ride **without helmets** and may be alone when they crash.

Our system closes that gap: faster help, fewer false calls.

---

## 2 . How it works (30 s tour)

```
┌────────────┐   MQTT           ┌──────────────┐
│  Scooter   │ ───────────────► │  Product     │
│  (Pi +     │  sensor report   │  Server      │
│  Sense HAT)│                  │  (Pi broker) │
└────────────┘                  └────┬─────────┘
        ▲  cancel / confirm          │
        └──── user app (phone) ◄─────┘
```

1. **Crash?** Accelerometer > 2 .5 g **or** panic button pressed.
2. Scooter starts beeping/flashing; rider gets 30 s to cancel.
3. If not cancelled, product server:

   * Sends *“emergency confirmed”* to scooter.
   * Stores log and forwards data to ambulance API (simulated).

---

## 3 . Quick start

### 3.1 Clone & install

```bash
git clone https://github.com/marenfj/semesterProjectTeam7.git e-scooter-alert
cd e-scooter-alert
python3 -m venv venv && source venv/bin/activate
pip install stmpy, paho-mqtt, sense-hat
```

### 3.2 Edit basic settings (if needed)

```python
# config snippet
BROKER_ADDRESS = "mqtt20.iik.ntnu.no"
SCOOTER_ID     = "scooter123"
CRASH_THRESHOLD = 2.5          # g‑force
```


### 3.3 Run

Terminal 1 – **Server**

```bash
python server.py
```

Terminal 2 – **Scooter**

```bash
python scooter.py
```

---

## 4 . MQTT topics

| Topic                 | Direction        | Payload                                       |
| --------------------- | ---------------- | --------------------------------------------- |
| `scooter/<ID>/alerts` | Scooter ➜ Server | JSON crash / panic report                     |
| `scooter/<ID>/alerts` | Server ➜ Scooter | `{"server_id":"server123"}` (3 s acknowledge) |
| same                  | Either ➜ Server  | `{"cancel_emergency":"cancel_emergency"}`     |

---

## 5 . State machines in plain words

### 5.1 Scooter

`Sleep → Listening → EmergencyTriggered`

* *Sleep*: waiting to be rented (LED green).
* *Listening*: rider active; watching sensors & panic button.
* *EmergencyTriggered*: alarms on, waiting 30 s for cancel or server reply; then returns to Listening.

### 5.2 Server

`Listening → Pending → RealEmergency`

* *Listening*: idle for scooter reports.
* *Pending*: 3 s timer; cancel resets, timeout means real emergency.
* *RealEmergency*: notifies ambulance & logs; back to Listening.

---

## 6 . Testing checklist

1. **Crash detection accuracy**

   * Shake the scooter 500 times; ≥ 99.9 % should trigger correctly.
2. **Response timer**

   * Measure time from crash to MQTT alert; ≤ 5 s for 98 % of trials.
3. **False‑positive rate**

   * Drop scooter gently 200 times; < 5 % should escalate to server.

---

## 7 . Contributors

Maren F. Johansen • Martine Karlsen • Eirik Slettan • Daniiar Berdikulov • Eivind Schiefloe
