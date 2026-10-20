"""Simulasi berbasis agen (ABM) konsumsi energi gedung + parameter sweep paralel.

Ini adalah beban kerja "HPC": ratusan/ribuan skenario independen (embarrassingly parallel)
dijalankan serentak dengan multiprocessing di satu node, atau banyak core via SLURM.

Pertanyaan kebijakan: berapa setpoint AC dan jeda mematikan AC (setelah ruangan kosong)
yang menghemat listrik terbanyak tanpa mengorbankan kenyamanan?
"""
import argparse, itertools, os
from multiprocessing import Pool
import numpy as np
import pandas as pd

N_ROOMS, N_PEOPLE, STEP_MIN, DAYS = 12, 150, 15, 5
STEPS_PER_DAY = 24 * 60 // STEP_MIN


def simulate(args):
    setpoint, off_delay_min, replica = args
    rng = np.random.default_rng(replica * 1000 + int(setpoint * 10) + off_delay_min)
    steps = DAYS * STEPS_PER_DAY
    # --- agen: tiap orang punya ruangan, jam datang & pulang
    room_of = rng.integers(0, N_ROOMS, N_PEOPLE)
    arrive = rng.normal(8.5, .8, N_PEOPLE)
    leave = arrive + rng.normal(7, 1.2, N_PEOPLE)
    present = np.zeros((steps, N_ROOMS), dtype=int)
    for d in range(DAYS):
        for p in range(N_PEOPLE):
            if rng.random() < .1:          # tidak hadir hari itu
                continue
            a = int(d * STEPS_PER_DAY + arrive[p] * 60 / STEP_MIN)
            b = int(d * STEPS_PER_DAY + leave[p] * 60 / STEP_MIN)
            present[a:b, room_of[p]] += 1
    # --- lingkungan
    hours = (np.arange(steps) % STEPS_PER_DAY) * STEP_MIN / 60
    t_out = 28 + 5 * np.sin((hours - 9) / 24 * 2 * np.pi)
    t_in = np.full(N_ROOMS, 28.0)
    last_occ = np.full(N_ROOMS, -10**9)
    energy_kwh = discomfort_min = occupied_min = 0.0
    for s in range(steps):
        occ = present[s]
        last_occ[occ > 0] = s
        ac_on = (s - last_occ) * STEP_MIN <= off_delay_min
        t_in += 0.1 * (t_out[s] - t_in) + 0.15 * occ        # model RC + kalor tubuh
        cool = ac_on & (t_in > setpoint)
        t_in[cool] += 0.6 * (setpoint - t_in[cool])
        p_kw = np.where(ac_on, 0.4 + 0.27 * max(t_out[s] - setpoint, 0), 0.05)
        energy_kwh += p_kw.sum() * STEP_MIN / 60
        occ_mask = occ > 0
        occupied_min += occ_mask.sum() * STEP_MIN
        discomfort_min += ((t_in > 27.0) & occ_mask).sum() * STEP_MIN
    return {"setpoint": setpoint, "off_delay_min": off_delay_min, "replica": replica,
            "energy_kwh": energy_kwh,
            "discomfort_pct": 100 * discomfort_min / max(occupied_min, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", type=int, default=10)
    ap.add_argument("--workers", type=int,
                    default=int(os.environ.get("SLURM_CPUS_PER_TASK", os.cpu_count())))
    ap.add_argument("--out", default="results/abm_sweep.csv")
    a = ap.parse_args()
    jobs = list(itertools.product([23, 24, 25, 26, 27, 28], [0, 15, 30, 60, 120], range(a.replicas)))
    print(f"{len(jobs)} skenario | {a.workers} worker")
    with Pool(a.workers) as pool:
        rows = pool.map(simulate, jobs, chunksize=4)
    df = pd.DataFrame(rows)
    df.to_csv(a.out, index=False)
    agg = df.groupby(["setpoint", "off_delay_min"])[["energy_kwh", "discomfort_pct"]].mean().reset_index()
    base = agg[(agg.setpoint == 23) & (agg.off_delay_min == 120)].energy_kwh.iloc[0]
    ok = agg[agg.discomfort_pct <= 10].copy()
    ok["saving_pct"] = 100 * (base - ok.energy_kwh) / base
    print("\nKebijakan terbaik (waktu tidak nyaman <= 10%), hemat vs baseline 23C/120 mnt:")
    print(ok.sort_values("energy_kwh").head(5).round(2).to_string(index=False))
