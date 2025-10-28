import pandas as pd
import os

# Polut tiedostoihin (päivitä tarvittaessa)
output_dir = "output/2025-10-25_07-56-41/logs"
opt_file = os.path.join(output_dir, "transporter_tasks_optimized.csv")
mat_file = os.path.join(output_dir, "line_matrix_stretched.csv")

# Lue tiedostot
opt = pd.read_csv(opt_file)
mat = pd.read_csv(mat_file)

# Luo matriisista tehtävälista: batch, stage, lift_stat, sink_stat, lift_time, sink_time, matriisi_siirtoaika
rows = []
for idx, row in opt.iterrows():
    batch = row["Batch"]
    stage = row["Stage"]
    lift_stat = row["Lift_stat"]
    sink_stat = row["Sink_stat"]
    # Lift_time: ExitTime, jossa sama batch, stage, station=lift_stat
    lift_match = mat[(mat["Batch"] == batch) & (mat["Stage"] == stage) & (mat["Station"] == lift_stat)]
    if not lift_match.empty:
        lift_time = lift_match.iloc[0]["ExitTime"]
    else:
        lift_time = None
    # Sink_time: EntryTime, jossa sama batch, stage+1, station=sink_stat
    sink_match = mat[(mat["Batch"] == batch) & (mat["Stage"] == stage+1) & (mat["Station"] == sink_stat)]
    if not sink_match.empty:
        sink_time = sink_match.iloc[0]["EntryTime"]
    else:
        sink_time = None
    mat_siirtoaika = sink_time - lift_time if lift_time is not None and sink_time is not None else None
    opt_siirtoaika = row["Phase_1"]
    rows.append({
        "Batch": batch,
        "Stage": stage,
        "Lift_stat": lift_stat,
        "Sink_stat": sink_stat,
        "Opt_siirtoaika": opt_siirtoaika,
        "Matriisi_siirtoaika": mat_siirtoaika,
        "Erotus": opt_siirtoaika - mat_siirtoaika if mat_siirtoaika is not None else None
    })

# Tallenna vertailu
out_df = pd.DataFrame(rows)
out_df.to_csv(os.path.join(output_dir, "siirtoaikavertailu.csv"), index=False)
print("Vertailu tallennettu tiedostoon siirtoaikavertailu.csv")
