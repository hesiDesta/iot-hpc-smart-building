# Smart Building IoT + HPC: Efisiensi Energi dan Kualitas Udara Kampus

Studi kasus berdasarkan seminar *"Bridging Global Infrastructure to Address Local Challenges with HPC"*
(Asst. Prof. Dr. Worawan Diaz Carbalo, Thammasat University). Proyek ini memakai dua contoh
penerapan HPC dari seminar, yaitu **efisiensi energi gedung** (simulasi berbasis agen) dan
**prediksi kualitas udara PM2.5**, lalu menghubungkannya dengan data nyata dari sensor **IoT**.

## 1. Latar belakang masalah lokal
Gedung kampus di daerah tropis menghabiskan listrik terbesar untuk pendingin ruangan (AC). Pada musim
kabut asap, kualitas udara dalam ruangan juga menurun, sehingga pengelola sering menaikkan ventilasi/AC
tanpa data. Pertanyaan yang ingin dijawab:

1. Berapa *setpoint* AC dan jeda mematikan AC (setelah ruangan kosong) yang paling hemat tanpa
   mengorbankan kenyamanan?
2. Bisakah PM2.5 satu jam ke depan diprakirakan agar pengelola bisa bertindak lebih awal?

## 2. Peran IoT dan HPC
| Lapisan | Komponen | Fungsi |
|---|---|---|
| Edge (IoT) | ESP32 + PMS5003 + DHT22 + PIR (+ PZEM-004T) | Mengukur PM2.5, suhu, kelembapan, okupansi, daya |
| Transport | MQTT (Wi-Fi) | Mengirim telemetri JSON ke server |
| Ingest | `mqtt_ingest.py` | Menyimpan data ke CSV |
| HPC | `abm_energy.py` + SLURM | Ratusan/ribuan skenario simulasi paralel |
| Analitik | `forecast_pm25.py` | Prakiraan PM2.5 +1 jam |
| Presentasi | `visualize.py` | Dashboard hasil |

```
ESP32 --MQTT--> broker --> mqtt_ingest.py --> CSV --+--> abm_energy.py (SLURM, N core) --> kebijakan optimal
                                                    +--> forecast_pm25.py --> peringatan dini
                                                    +--> visualize.py --> dashboard.png
```

## 3. Kaitan dengan materi seminar
- **Alur kerja HPC (bab 4):** identifikasi masalah, kumpulkan data (IoT), pilih model (ABM + regresi),
  tulis skrip, ajukan sumber daya (`#SBATCH`), jalankan lewat job scheduler, unduh dan visualisasikan hasil.
- **Peran integrator (bab 5):** proyek ini menghubungkan perangkat keras, jaringan, data, model,
  dan pengambilan keputusan dalam satu alur.
- **Tahapan kompetensi (bab 6):** Learner (sensor, jaringan), Practitioner (menjalankan di HPC),
  Innovator (kebijakan energi untuk kampus sendiri).

## 4. Struktur proyek
```
firmware/esp32_sensor_node/   Kode Arduino ESP32 (sensor -> MQTT)
src/sensor_simulator.py       Simulator data sensor (tanpa perangkat keras) / publisher MQTT
src/mqtt_ingest.py            Subscriber MQTT -> CSV
src/abm_energy.py             Simulasi agen + parameter sweep paralel (inti HPC)
src/forecast_pm25.py          Prakiraan PM2.5 (ridge regression, lag features)
src/visualize.py              Dashboard matplotlib
hpc/submit_sweep.slurm        Skrip pengiriman job SLURM
run_all.sh                    Jalankan seluruh pipeline secara lokal
```

## 5. Cara menjalankan
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run_all.sh                       # lokal, memakai data simulasi
```
**Dengan perangkat keras:** isi Wi-Fi/MQTT di `.ino`, unggah ke ESP32, jalankan broker
(`mosquitto`), lalu `python src/mqtt_ingest.py --host localhost`.
**Tanpa perangkat keras tetapi ingin menguji MQTT:** `python src/sensor_simulator.py --mqtt localhost`.

**Di superkomputer (SLURM):**
```bash
git clone <repo> && cd iot-hpc-smart-building
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
sbatch hpc/submit_sweep.slurm
squeue -u $USER                    # pantau antrean
```
Lalu unduh `results/` (misalnya dengan `scp`) dan jalankan `python src/visualize.py` di laptop.

## 6. Hasil contoh (data simulasi, 10 replika, 300 skenario)
| Setpoint | Jeda mati AC | Energi (kWh/5 hari) | Waktu tidak nyaman | Hemat vs baseline |
|---|---|---|---|---|
| 25 C | 0 mnt | 1261 | 1,6% | 34% |
| 25 C | 30 mnt | 1326 | 0,9% | 31% |
| 24 C | 0 mnt | 1422 | 0,0% | 26% |

Baseline: 23 C dengan AC mati 120 menit setelah ruangan kosong. Dengan ratusan replika di HPC, rata-rata
dan interval kepercayaan menjadi jauh lebih stabil. Inilah alasan pekerjaan ini cocok dijalankan
di superkomputer.

## 7. Keterbatasan (penting dibaca)
- Data dan model fisika bangunan **disederhanakan dan disimulasikan**. Angka penghematan bukan klaim
  nyata. Kalibrasi dengan data sensor kampus Anda sebelum dipakai untuk kebijakan.
- Model PM2.5 hanya sedikit lebih baik dari baseline persistence (MAE 1,98 vs 2,04). Pada data nyata,
  tambahkan fitur cuaca, titik api (hotspot), dan arah angin, atau gunakan model lanjutan (GBM/LSTM di GPU).
- Pembacaan daya di firmware masih `TODO` (PZEM-004T). Sensor PMS5003 perlu kalibrasi terhadap alat referensi.

## 8. Pengembangan lanjutan
Dashboard realtime (Grafana + InfluxDB), deteksi anomali AC lupa dimatikan, pelatihan model PM2.5
di GPU, LoRaWAN untuk node yang jauh dari Wi-Fi, dan penggabungan CFD ruangan (seperti proyek
Cool Logic) untuk menata ulang aliran udara.

## Lisensi
MIT
