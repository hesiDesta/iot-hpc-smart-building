#!/bin/bash
#SBATCH --job-name=abm-energy
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=00:30:00
#SBATCH --output=abm_%j.out
#SBATCH --error=abm_%j.err
# Sesuaikan partisi/modul dengan superkomputer Anda.
# module load python/3.11
source .venv/bin/activate
python src/sensor_simulator.py --days 7
python src/abm_energy.py --replicas 200 --workers $SLURM_CPUS_PER_TASK
python src/forecast_pm25.py
