"""Prakiraan PM2.5 1 jam ke depan dari data sensor IoT (regresi ridge fitur lag, numpy murni)."""
import numpy as np, pandas as pd

LAGS, HORIZON = 12, 12          # 12 x 5 menit = 1 jam
df = pd.read_csv("data/sensor_data.csv", parse_dates=["timestamp"])
d = df[df.room == df.room.iloc[0]].set_index("timestamp")
pm = d.pm25.values
hr = np.asarray(d.index.hour + d.index.minute / 60)

X, y = [], []
for i in range(LAGS, len(pm) - HORIZON):
    X.append(np.r_[pm[i - LAGS:i], np.sin(hr[i] / 24 * 2 * np.pi), np.cos(hr[i] / 24 * 2 * np.pi), 1])
    y.append(pm[i + HORIZON - 1])
X, y = np.array(X), np.array(y)
split = int(.8 * len(X))
w = np.linalg.solve(X[:split].T @ X[:split] + 1.0 * np.eye(X.shape[1]), X[:split].T @ y[:split])
pred = X[split:] @ w
print(f"MAE model      : {np.abs(pred - y[split:]).mean():.2f} ug/m3")
print(f"MAE persistence: {np.abs(X[split:, LAGS - 1] - y[split:]).mean():.2f} ug/m3")
np.save("results/pm25_pred.npy", np.c_[y[split:], pred])
print(f"Waktu prediksi > 55.4 ug/m3 (tidak sehat): {(pred > 55.4).mean() * 100:.1f}%")
