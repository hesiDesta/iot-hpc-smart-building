"""Simulator node IoT (pengganti ESP32 bila belum punya perangkat keras).

Menghasilkan data: PM2.5, suhu, kelembapan, okupansi (PIR), daya listrik per ruangan.
Mode:
  python src/sensor_simulator.py --days 7              -> tulis data/sensor_data.csv
  python src/sensor_simulator.py --mqtt localhost      -> publish langsung ke broker MQTT
"""
import argparse, json, time
import numpy as np
import pandas as pd

ROOMS = ["lab_komputer", "ruang_kelas_a", "ruang_dosen"]
STEP_MIN = 5


def generate(days=7, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-10-12 00:00", periods=days * 24 * 60 // STEP_MIN,
                        freq=f"{STEP_MIN}min")
    n = len(idx)
    hours = np.asarray(idx.hour + idx.minute / 60)
    weekday = np.asarray(idx.dayofweek < 5)
    # PM2.5 luar ruangan: pola harian + episode kabut asap acak
    outdoor_pm = 25 + 12 * np.sin((hours - 6) / 24 * 2 * np.pi)
    smoke = np.zeros(n)
    for _ in range(max(1, days // 3)):
        s = rng.integers(0, n - 200)
        smoke[s:s + 150] += rng.uniform(40, 90) * np.hanning(150)
    outdoor_pm = np.clip(outdoor_pm + smoke + rng.normal(0, 3, n), 3, None)
    outdoor_t = 28 + 5 * np.sin((hours - 9) / 24 * 2 * np.pi) + rng.normal(0, .3, n)

    frames = []
    for room in ROOMS:
        working = weekday & (hours >= 8) & (hours < 17)
        occ = np.where(working, rng.poisson(12 if "lab" in room else 8, n), 0)
        occ = np.where(~working & (rng.random(n) < .02), 1, occ)
        pm_in = pd.Series(outdoor_pm * 0.6).ewm(alpha=.15).mean().values + rng.normal(0, 1.5, n)
        # AC menyala saat ada orang, dan masih ~1 jam setelah ruangan kosong
        ac_on = np.convolve((occ > 0).astype(float), np.ones(12), "full")[:n] > 0
        temp = np.where(ac_on, 25 + rng.normal(0, .4, n), outdoor_t - 1.5)
        hum = np.clip(60 + (outdoor_t.mean() - temp) * 1.5 + rng.normal(0, 2, n), 30, 95)
        power = np.where(ac_on, 1200 + 40 * occ, 80) + occ * 60 + rng.normal(0, 25, n)
        frames.append(pd.DataFrame({"timestamp": idx, "room": room, "pm25": pm_in.round(1),
                                    "temp_c": temp.round(1), "humidity": hum.round(1),
                                    "occupancy": occ, "power_w": power.round(0),
                                    "outdoor_pm25": outdoor_pm.round(1),
                                    "outdoor_temp": outdoor_t.round(1)}))
    return pd.concat(frames).sort_values(["timestamp", "room"]).reset_index(drop=True)


def publish_live(host, interval=2.0):
    import paho.mqtt.client as mqtt
    df = generate(days=1)
    c = mqtt.Client(); c.connect(host, 1883)
    print(f"Publish ke mqtt://{host}:1883 (Ctrl+C untuk berhenti)")
    for _, r in df.iterrows():
        c.publish(f"building/{r.room}/telemetry", json.dumps(
            {"ts": str(r.timestamp), "pm25": r.pm25, "temp_c": r.temp_c, "humidity": r.humidity,
             "occupancy": int(r.occupancy), "power_w": r.power_w}))
        time.sleep(interval / len(ROOMS))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--out", default="data/sensor_data.csv")
    p.add_argument("--mqtt", help="host broker MQTT; jika diisi, publish live")
    a = p.parse_args()
    if a.mqtt:
        publish_live(a.mqtt)
    else:
        df = generate(a.days)
        df.to_csv(a.out, index=False)
        print(f"Tersimpan {len(df)} baris -> {a.out}")
