import pandas as pd
import os
from simulation_logger import get_logger

def generate_transporter_tasks(output_dir):
    """Luo kuljetintehtävät line_matrix_original.csv:n perusteella ja lisää Shift-sarake (aluksi 0)."""
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Call init_logger(output_dir) before using generate_transporter_tasks.")
    print("Vaihe alkaa: Kuljetintehtävien generointi")
    logger.log_phase("Kuljetintehtävien generointi alkaa")
    
    matrix_file = os.path.join(output_dir, "line_matrix_original.csv")
    if not os.path.exists(matrix_file):
        logger.log_error(f"line_matrix_original.csv ei löydy: {matrix_file}")
        print("Virhe: line_matrix_original.csv ei löydy")
        raise FileNotFoundError(f"line_matrix_original.csv ei löydy: {matrix_file}")
    
    logger.log_io(f"Luetaan line_matrix_original.csv: {matrix_file}")
    try:
        df = pd.read_csv(matrix_file)
        logger.log_data(f"Ladattu {len(df)} vaihetta, {df['Batch'].nunique()} erää")
        df = df.sort_values(["Batch", "Stage"]).reset_index(drop=True)
        tasks = []
        for idx, row in df.iterrows():
            tasks.append({
                "Batch": int(row["Batch"]),
                "Treatment_program": int(row["Treatment_program"]),
                "Stage": int(row["Stage"]),
                "Lift_stat": int(row["Station"]),
                "Lift_time": float(row["ExitTime"]),
                "Sink_stat": int(df.iloc[idx + 1]["Station"]) if idx + 1 < len(df) and row["Batch"] == df.iloc[idx + 1]["Batch"] else None,
                "Sink_time": float(df.iloc[idx + 1]["EntryTime"]) if idx + 1 < len(df) and row["Batch"] == df.iloc[idx + 1]["Batch"] else None,
                "Shift": 0.0
            })
        # Poista viimeinen tehtävä jokaisesta batchista (koska sillä ei ole seuraavaa vaihetta)
        tasks = [t for t in tasks if t["Sink_stat"] is not None]
        tasks_df = pd.DataFrame(tasks)
        # Varmistetaan sarakejärjestys ja Shift-nimi
        cols = ["Batch", "Treatment_program", "Stage", "Lift_stat", "Lift_time", "Sink_stat", "Sink_time", "Shift"]
        tasks_df = tasks_df[cols]
    except Exception as e:
        logger.log_error(f"Kuljetintehtävien generointi epäonnistui: {e}")
        print(f"Virhe: kuljetintehtävien generointi epäonnistui: {e}")
        raise

    os.makedirs(output_dir, exist_ok=True)
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Tallenna kaikkiin vaiheisiin Shift-sarake (aluksi 0)
    raw_file = os.path.join(logs_dir, "transporter_tasks_raw.csv")
    tasks_df.to_csv(raw_file, index=False)
    logger.log_io(f"Kuljetintehtävät tallennettu: {raw_file}")

    ordered_df = tasks_df.sort_values(["Batch", "Lift_time"]).reset_index(drop=True)
    ordered_df = ordered_df[cols]
    ordered_file = os.path.join(logs_dir, "transporter_tasks_ordered.csv")
    ordered_df.to_csv(ordered_file, index=False)
    logger.log_io(f"Kuljetintehtävät tallennettu (batch ja aika): {ordered_file}")

    resolved_df = ordered_df.copy()[cols]
    resolved_file = os.path.join(logs_dir, "transporter_tasks_resolved.csv")
    resolved_df.to_csv(resolved_file, index=False)
    logger.log_io(f"Kuljetintehtävät tallennettu (resolved): {resolved_file}")

    # Stretched-vaiheessa Shift-sarake päivitetään myöhemmin stretch-skriptissä
    try:
        stretched_df = resolved_df.copy()[cols]
        stretched_df["Shift"] = 0.0  # Varmistetaan Shift-sarake
        n = len(stretched_df)
        SHIFT_GAP = 5.0
        for i in range(n-1):
            row_a = stretched_df.iloc[i]
            row_b = stretched_df.iloc[i+1]
            if row_a["Batch"] != row_b["Batch"]:
                continue
            actual_gap = row_b["Lift_time"] - row_a["Sink_time"]
            if actual_gap < SHIFT_GAP:
                shift = SHIFT_GAP - actual_gap
                stretched_df.at[i+1, "Shift"] = shift
                for j in range(i+1, n):
                    if stretched_df.loc[j, "Batch"] == row_b["Batch"]:
                        stretched_df.at[j, "Lift_time"] += shift
                        stretched_df.at[j, "Sink_time"] += shift
        stretched_file = os.path.join(logs_dir, "transporter_tasks_stretched.csv")
        stretched_df.to_csv(stretched_file, index=False)
        logger.log_io(f"Kuljetintehtävät tallennettu (stretched, Shift laskettu): {stretched_file}")
    except Exception as e:
        logger.log_error(f"Stretched-vaiheen Shift-laskenta epäonnistui: {e}")
        print(f"Virhe: stretched-vaiheen Shift-laskenta epäonnistui: {e}")
        raise

    logger.log_phase(f"Kuljetintehtävien generointi valmis: {len(tasks_df)} tehtävää")
    print("Vaihe valmis: Kuljetintehtävien generointi")
    return tasks_df, ordered_df, resolved_df, stretched_df

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    generate_transporter_tasks(output_dir)

