import pandas as pd
import os

def order_tasks(output_dir):
    """
    Järjestää transporter_tasks_raw.csv:n nostoajan (Lift_time) mukaan nousevaan järjestykseen ja tallentaa uuden tiedoston transporter_tasks_ordered.csv.
    """
    # STEP-tyyppinen aloitusviesti terminaaliin ja lokiin
    from simulation_logger import get_logger
    logger = get_logger()
    logger.log("STEP", "STEP 5 STARTED: ORDER TASKS")
    tasks_csv = os.path.join(output_dir, "logs", "transporter_tasks_raw.csv")
    ordered_csv = os.path.join(output_dir, "logs", "transporter_tasks_ordered.csv")
    df = pd.read_csv(tasks_csv)
    # Pakota kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in df.columns:
            df[col] = df[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: int(round(x)))
    
    # ⭐ KRIITTINEN KORJAUS: Järjestä nostinkohtaisesti aikajärjestykseen!
    # Muuten eri nostimien tehtävät sekoittuvat ja aiheuttavat timeline-paradokseja
    df_ordered = df.sort_values(["Transporter_id", "Lift_time"]).reset_index(drop=True)
    logger.log("INFO", f"Järjestetty {len(df)} tehtävää nostinkohtaisesti aikajärjestykseen")
    
    # Pakota vielä ennen tallennusta kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in df_ordered.columns:
            df_ordered[col] = df_ordered[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in df_ordered.columns:
            df_ordered[col] = df_ordered[col].apply(lambda x: int(round(x)))
    df_ordered.to_csv(ordered_csv, index=False)
    # STEP-tyyppinen lopetusviesti terminaaliin ja lokiin
    logger.log("STEP", "STEP 5 COMPLETED: ORDER TASKS")
    return ordered_csv
