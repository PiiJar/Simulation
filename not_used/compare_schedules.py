import pandas as pd

# Polut tiedostoihin (päivitä tarvittaessa)
matrix_path = "output/2025-10-25_09-17-14/logs/line_matrix_stretched.csv"
opt_path = "output/2025-10-25_09-17-14/logs/transporter_tasks_optimized.csv"

# Lue tiedostot
df_matrix = pd.read_csv(matrix_path)
df_opt = pd.read_csv(opt_path)

# Valitse ja uudelleennimeä vertailtavat sarakkeet
df_matrix_cmp = df_matrix[["Batch", "Stage", "EntryTime", "ExitTime"]].copy()
df_matrix_cmp = df_matrix_cmp.rename(columns={"EntryTime": "Entry_matrix", "ExitTime": "Exit_matrix"})

df_opt_cmp = df_opt[["Batch", "Stage", "Sink_time", "Lift_time"]].copy()
df_opt_cmp = df_opt_cmp.rename(columns={"Sink_time": "Entry_opt", "Lift_time": "Exit_opt"})

# Yhdistä batchin ja stagen perusteella
merged = pd.merge(df_matrix_cmp, df_opt_cmp, on=["Batch", "Stage"], how="outer")

# Laske erot
diff_cols = []
for col in ["Entry", "Exit"]:
    merged[f"{col}_diff"] = merged[f"{col}_opt"] - merged[f"{col}_matrix"]
    diff_cols.append(f"{col}_diff")

# Järjestä taulukko
merged = merged.sort_values(["Batch", "Stage"]).reset_index(drop=True)

# Tulosta koko taulukko ja tallenna CSV/HTML
display_cols = ["Batch", "Stage", "Entry_matrix", "Entry_opt", "Entry_diff", "Exit_matrix", "Exit_opt", "Exit_diff"]
print(merged[display_cols].to_string(index=False))

# Tallennus
diff_path = "output/2025-10-25_09-17-14/logs/schedule_comparison.csv"
merged[display_cols].to_csv(diff_path, index=False)
print(f"\nTallennettu vertailutaulukko: {diff_path}")
