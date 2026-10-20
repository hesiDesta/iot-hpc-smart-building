#!/bin/bash
set -e
python src/sensor_simulator.py --days 7
python src/abm_energy.py --replicas 10
python src/forecast_pm25.py
python src/visualize.py
