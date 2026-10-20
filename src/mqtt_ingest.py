"""Subscriber MQTT: menerima telemetri dari node ESP32 dan menambahkannya ke CSV.
Jalankan: python src/mqtt_ingest.py --host localhost
"""
import argparse, csv, json, os
from datetime import datetime
import paho.mqtt.client as mqtt

OUT = "data/live_data.csv"
FIELDS = ["timestamp", "room", "pm25", "temp_c", "humidity", "occupancy", "power_w"]


def on_message(client, userdata, msg):
    room = msg.topic.split("/")[1]
    d = json.loads(msg.payload)
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        w.writerow([d.get("ts", datetime.now().isoformat(timespec="seconds")), room,
                    d["pm25"], d["temp_c"], d["humidity"], d["occupancy"], d["power_w"]])
    print(room, d)


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="localhost")
    a = p.parse_args()
    c = mqtt.Client(); c.on_message = on_message
    c.connect(a.host, 1883); c.subscribe("building/+/telemetry")
    print("Menunggu data..."); c.loop_forever()
