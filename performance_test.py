#!/usr/bin/env python3
"""
Skripti erien määrän lisäämiseksi tuotantoon ja suoritusajan seuraamiseen.
"""

import pandas as pd
import os
import time
import subprocess
from datetime import datetime

def generate_production_with_batches(num_batches):
    """Generoi production.csv tiedoston annetulla erien määrällä."""

    # Alkuperäinen rakenne: 15 erää program 3, 15 erää program 1, 5 erää program 2
    batches = []

    # Program 3: ensimmäiset 15 erää
    program_3_count = min(15, num_batches)
    for i in range(1, program_3_count + 1):
        batches.append({
            'Batch': i,
            'Treatment_program': 3,
            'Start_station': 101,
            'Start_time': '00:00:00',
            'Start_optimized': '00:00:00'
        })

    # Program 1: seuraavat 15 erää
    remaining = num_batches - program_3_count
    program_1_count = min(15, remaining)
    for i in range(program_3_count + 1, program_3_count + program_1_count + 1):
        batches.append({
            'Batch': i,
            'Treatment_program': 1,
            'Start_station': 101,
            'Start_time': '00:00:00',
            'Start_optimized': '00:00:00'
        })

    # Program 2: loput
    remaining = num_batches - program_3_count - program_1_count
    for i in range(program_3_count + program_1_count + 1, num_batches + 1):
        batches.append({
            'Batch': i,
            'Treatment_program': 2,
            'Start_station': 101,
            'Start_time': '00:00:00',
            'Start_optimized': '00:00:00'
        })

    df = pd.DataFrame(batches)
    return df

def run_simulation_and_measure_time(num_batches):
    """Aja simulaatio annetulla erien määrällä ja mittaa aika."""

    print(f"\n=== Testaus {num_batches} erällä ===")

    # Generoi uusi production.csv
    df = generate_production_with_batches(num_batches)
    output_path = '/home/jarmo-piipponen/Development/Simulation/output/production.csv'
    df.to_csv(output_path, index=False)
    print(f"Luotu production.csv {num_batches} erällä")

    # Aja simulaatio ja mittaa aika
    start_time = time.time()

    try:
        # Aseta timeoutit
        env = os.environ.copy()
        env['CPSAT_PHASE1_MAX_TIME'] = '30'  # Lyhyempi timeout testaukseen
        # Aseta aikaraja config.py:stä, ei suoraan ympäristömuuttujalla
        # env['CPSAT_PHASE2_MAX_TIME'] = '60'

        result = subprocess.run([
            '/home/jarmo-piipponen/Development/Simulation/.venv/bin/python',
            '/home/jarmo-piipponen/Development/Simulation/main.py'
        ], capture_output=True, text=True, env=env, timeout=300)  # 5 min timeout

        end_time = time.time()
        duration = end_time - start_time

        print(".2f")
        print(f"Exit code: {result.returncode}")

        if result.returncode == 0:
            print("✓ Simulaatio onnistui")
        else:
            print("✗ Simulaatio epäonnistui")
            print("STDERR:", result.stderr[-500:])  # Viimeiset 500 merkkiä

        return {
            'batches': num_batches,
            'duration': duration,
            'success': result.returncode == 0,
            'exit_code': result.returncode
        }

    except subprocess.TimeoutExpired:
        end_time = time.time()
        duration = end_time - start_time
        print(".2f")
        print("✗ Simulaatio aikakatkaistiin")
        return {
            'batches': num_batches,
            'duration': duration,
            'success': False,
            'exit_code': -1
        }

def main():
    """Pääfunktio suoritusajan testaamiseen eri erien määrillä."""

    # Testattavat erien määrät
    batch_counts = [10, 20, 35, 50, 75, 100, 150, 200]

    results = []

    print("Aloitetaan suoritusajan testaus eri erien määrillä...")
    print("Huom: Tämä voi kestää useita minuutteja!")

    for num_batches in batch_counts:
        result = run_simulation_and_measure_time(num_batches)
        results.append(result)

        # Jos epäonnistui, lopeta
        if not result['success']:
            print(f"Pysäytetään testaus epäonnistumisen vuoksi ({num_batches} erää)")
            break

    # Tulosta yhteenveto
    print("\n" + "="*60)
    print("SUORITUSAJAN TESTAUS TULOKSET")
    print("="*60)

    print("<10")
    print("-" * 50)

    successful_results = [r for r in results if r['success']]

    if successful_results:
        print("<10")
        print("<10")
        print("<10")

        # Laske skaalauskerroin
        if len(successful_results) >= 2:
            first = successful_results[0]['duration']
            last = successful_results[-1]['duration']
            first_batches = successful_results[0]['batches']
            last_batches = successful_results[-1]['batches']

            scaling_factor = (last / first) / (last_batches / first_batches)
            print(".2f")

    # Tallenna tulokset CSV:hen
    results_df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_file = f"/home/jarmo-piipponen/Development/Simulation/performance_test_{timestamp}.csv"
    results_df.to_csv(results_file, index=False)
    print(f"\nTulokset tallennettu: {results_file}")

if __name__ == "__main__":
    main()