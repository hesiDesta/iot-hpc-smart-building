"""Visualisasi hasil di komputer pribadi (langkah terakhir alur kerja HPC)."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv("data/sensor_data.csv", parse_dates=["timestamp"])
sw = pd.read_csv("results/abm_sweep.csv")
pr = np.load("results/pm25_pred.npy")

fig, ax = plt.subplots(2, 2, figsize=(13, 8))
r = df[df.room == "lab_komputer"].set_index("timestamp")
r.power_w.resample("1h").mean().plot(ax=ax[0, 0], color="tab:red")
ax[0, 0].set_title("Daya listrik rata-rata per jam (Lab Komputer)"); ax[0, 0].set_ylabel("Watt")

r[["pm25", "outdoor_pm25"]].plot(ax=ax[0, 1]); ax[0, 1].axhline(55.4, ls="--", c="k", lw=.8)
ax[0, 1].set_title("PM2.5 dalam vs luar ruangan"); ax[0, 1].set_ylabel("ug/m3")

n = 400
ax[1, 0].plot(pr[:n, 0], label="Aktual"); ax[1, 0].plot(pr[:n, 1], label="Prediksi +1 jam")
ax[1, 0].set_title("Prakiraan PM2.5"); ax[1, 0].legend()

agg = sw.groupby(["setpoint", "off_delay_min"])[["energy_kwh", "discomfort_pct"]].mean().reset_index()
sc = ax[1, 1].scatter(agg.energy_kwh, agg.discomfort_pct, c=agg.setpoint,
                      s=20 + agg.off_delay_min / 2, cmap="viridis")
ax[1, 1].axhline(10, ls="--", c="r", lw=.8); plt.colorbar(sc, ax=ax[1, 1], label="Setpoint AC (C)")
ax[1, 1].set_xlabel("Energi (kWh / 5 hari)"); ax[1, 1].set_ylabel("Waktu tidak nyaman (%)")
ax[1, 1].set_title("Parameter sweep ABM (ukuran titik = jeda mati AC)")
plt.tight_layout(); plt.savefig("results/dashboard.png", dpi=130)
print("Tersimpan results/dashboard.png")
