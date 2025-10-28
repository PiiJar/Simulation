import os
import pandas as pd

TIME_SLICE_SECONDS = 300  # 5 min

def test_step_7(output_dir):
    """
    VAIHE 7: Raporttien muodostus - kuormitusanalyysi ja kaikki raportit
    """
    from simulation_logger import get_logger
    from datetime import datetime
    
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 7 - RAPORTTIEN MUODOSTUS - ALKAA")
    
    logger = get_logger()
    
    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    movement_path = os.path.join(logs_dir, "transporters_movement.csv")
    workload_path = os.path.join(logs_dir, "transporters_workload.csv")


    # Luo esimerkkitiedosto, jos sitä ei ole olemassa
    if not os.path.exists(movement_path):
        # Luo esimerkkidata: StartTime, EndTime, Phase_1, Phase_2, Phase_3, Phase_4
        example_data = [
            {"StartTime": 0, "EndTime": 120, "Phase_1": 30, "Phase_2": 30, "Phase_3": 30, "Phase_4": 30},
            {"StartTime": 150, "EndTime": 400, "Phase_1": 50, "Phase_2": 50, "Phase_3": 50, "Phase_4": 100},
            {"StartTime": 500, "EndTime": 900, "Phase_1": 100, "Phase_2": 100, "Phase_3": 100, "Phase_4": 100},
        ]
        pd.DataFrame(example_data).to_csv(movement_path, index=False)
        # Poistettu ylimääräinen print

    df = pd.read_csv(movement_path)
    # Sarakkeet: Transporter,Batch,Phase,Start_Time,End_Time,From_Station,To_Station,Description,Movement_ID
    df["Start_Time"] = pd.to_numeric(df["Start_Time"], errors="coerce")
    df["End_Time"] = pd.to_numeric(df["End_Time"], errors="coerce")
    df = df.dropna(subset=["Start_Time", "End_Time"]).copy()

    max_time = int(df["End_Time"].max())
    time_slices = list(range(0, max_time + TIME_SLICE_SECONDS, TIME_SLICE_SECONDS))

    rows = []
    # Lasketaan workload vaiheiden 1-4 suoritusaikojen perusteella
    # Phase 0 = odotus, Phase 1-4 = aktiivinen työ
    current_idx = 0
    n_slices = len(time_slices) - 1
    phase_rows = df[df["Phase"].isin([1,2,3,4])].copy()
    phase_rows = phase_rows.sort_values("Start_Time")
    # Luo lista, jossa jokaiselle aikaikkunalle kerätään suoritusaikaa
    busy_times = [0.0 for _ in range(n_slices)]
    for _, row in phase_rows.iterrows():
        phase_start = row["Start_Time"]
        phase_end = row["End_Time"]
        # Käy läpi kaikki aikaikkunat, joihin vaihe osuu
        for i in range(n_slices):
            slice_start = time_slices[i]
            slice_stop = time_slices[i+1]
            # Jos vaihe päättyy ennen ikkunan alkua, siirry seuraavaan vaiheeseen
            if phase_end <= slice_start:
                break
            # Jos vaihe alkaa ikkunan jälkeen, jatka seuraavaan ikkunaan
            if phase_start >= slice_stop:
                continue
            # Laske osuva aika tähän ikkunaan
            overlap_start = max(phase_start, slice_start)
            overlap_end = min(phase_end, slice_stop)
            if overlap_start < overlap_end:
                busy_times[i] += overlap_end - overlap_start

    for i in range(n_slices):
        time_slice_start = time_slices[i]
        time_slice_stop = time_slices[i+1]
        workload = (busy_times[i] / TIME_SLICE_SECONDS) * 100.0
        rows.append({
            "time_slice_start": time_slice_start,
            "time_slice_stop": time_slice_stop,
            "transporter_workload": round(workload, 2)
        })

    workload_df = pd.DataFrame(rows)
    workload_df.to_csv(workload_path, index=False)

    # Visualisointi: palkkikaavio
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 5))
    x = workload_df["time_slice_start"]
    width = TIME_SLICE_SECONDS
    plt.bar(x, workload_df["transporter_workload"], width=width, align="edge", color="#1976d2", edgecolor="black")
    plt.xlabel("Time (s)")
    plt.ylabel("Transporter workload (%)")
    plt.title("Transporter workload over time")
    plt.ylim(0, 100)
    plt.xlim(left=0)
    # Muutetaan x-akselin jako vastaamaan aikaikkunaa
    import numpy as np
    max_x = workload_df["time_slice_stop"].max()
    xticks = np.arange(0, max_x + TIME_SLICE_SECONDS, TIME_SLICE_SECONDS)
    plt.xticks(xticks)
    plt.grid(axis="y")
    plt.tight_layout()
    plot_path = os.path.join(reports_dir, "transporter_workload.png")
    plt.savefig(plot_path)
    plt.close()
    
    # Luo kaikki muut raportit
    from generate_treatment_program_report import generate_treatment_program_report
    from generate_station_report import generate_station_report
    from generate_transporter_report import generate_transporter_report
    from generate_production_report import generate_production_report
    
    try:
        generate_treatment_program_report(output_dir)
    except Exception as e:
        if logger:
            logger.log_error(f"Virhe käsittelyohjelmien raportissa: {e}")
    
    try:
        generate_station_report(output_dir)
    except Exception as e:
        if logger:
            logger.log_error(f"Virhe asematietojen raportissa: {e}")
    
    try:
        generate_transporter_report(output_dir)
    except Exception as e:
        if logger:
            logger.log_error(f"Virhe nostinparametrien raportissa: {e}")
    
    try:
        generate_production_report(output_dir)
    except Exception as e:
        if logger:
            logger.log_error(f"Virhe tuotannon raportissa: {e}")
    
    end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{end}] VAIHE 7 - RAPORTTIEN MUODOSTUS - VALMIS")
