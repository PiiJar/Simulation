import pandas as pd
import os
from simulation_logger import get_logger

def update_programs(output_dir, adjustment_file="calc_time_adjustments.csv"):
    """Päivittää eräkohtaiset ohjelmatiedostot calc_time_adjustments.csv:n mukaan"""
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    logger.log_phase("Updating program files started")
    print("🛠️ Päivitetään ohjelmatiedostoja...")
    adjustment_path = os.path.join(output_dir, "logs", adjustment_file)
    if not os.path.exists(adjustment_path):
        logger.log_error(f"Adjustment file not found: {adjustment_file}")
        print(f"⚠️  Ei päivityksiä tehtäväksi - tiedosto puuttuu: {adjustment_file}")
        return
    df = pd.read_csv(adjustment_path)
    # Pakota kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Program", "Stage"]:
        if col in df.columns:
            df[col] = df[col].astype(int)
    for col in ["Adjustment"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: int(round(x)))
    if len(df) == 0:
        logger.log_phase("No CalcTime adjustments needed")
        print("✅ Ei päivityksiä tehtäväksi - ei aikamuutoksia")
        return
    logger.log_data(f"Processing {len(df)} CalcTime adjustments")
    print(f"📊 Käsitellään {len(df)} CalcTime-päivitystä")
    grouped = df.groupby(["Batch", "Program"])
    for (batch, program), group in grouped:
        batch_str = str(int(batch)).zfill(3)  # esim. "001"
        source_file = f"Treatment_program_batch_{batch_str}.csv"
        source_path = os.path.join(output_dir, "original_programs", source_file)
        if not os.path.exists(source_path):
            logger.log_error(f"Source program not found: {source_file}")
            print(f"❌ Lähdeohjelmaa ei löydy: {source_file}")
            continue
        logger.log_data(f"Updating batch {batch} program {program} with {len(group)} adjustments")
        print(f"   📦 Päivitetään erä {batch} ({len(group)} muutosta)")
        program_df = pd.read_csv(source_path)
        # Pakota kaikki ohjelma-, vaihe- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
        for col in ["Stage"]:
            if col in program_df.columns:
                program_df[col] = program_df[col].astype(int)
        for col in ["CalcTime"]:
            if col in program_df.columns:
                program_df[col] = program_df[col].apply(lambda x: int(round(x)))
        if pd.api.types.is_string_dtype(program_df["CalcTime"]):
            program_df["CalcTime"] = pd.to_timedelta(program_df["CalcTime"]).dt.total_seconds()
        for _, row in group.iterrows():
            stage = int(row["Stage"])
            add_time = int(row["Adjustment"])
            mask = program_df["Stage"] == stage
            if mask.sum() == 1:
                old_time = program_df.loc[mask, "CalcTime"].iloc[0]
                program_df.loc[mask, "CalcTime"] += add_time
                new_time = program_df.loc[mask, "CalcTime"].iloc[0]
                logger.log_optimization(f"Batch {batch} Program {program} Stage {stage}: {int(old_time)}s → {int(new_time)}s (+{add_time}s)")
                print(f"      🔧 Vaihe {stage}: {int(old_time)}s → {int(new_time)}s (+{add_time}s)")
            else:
                logger.log_error(f"Stage {stage} not found in batch {batch} program {program}")
                print(f"      ⚠️  Vaihe {stage} ei löytynyt erän {batch} ohjelmasta")
        out_dir = os.path.join(output_dir, "updated_programs")
        os.makedirs(out_dir, exist_ok=True)
        output_file = f"Treatment_program_batch_{batch_str}_updated.csv"
        output_path = os.path.join(out_dir, output_file)
        # Pakota vielä ennen tallennusta kaikki ohjelma-, vaihe- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
        for col in ["Stage"]:
            if col in program_df.columns:
                program_df[col] = program_df[col].astype(int)
        for col in ["CalcTime"]:
            if col in program_df.columns:
                program_df[col] = program_df[col].apply(lambda x: int(round(x)))
        program_df.to_csv(output_path, index=False)
        logger.log_io(f"Saved updated program: {output_file}")
        print(f"Tallennettu korjattu {output_file}")
    logger.log_phase("Updating program files completed")
    print("✅ Ohjelmatiedostot päivitetty!")

# Vanha funktio yhteensopivuudelle
def apply_adjustments(output_dir, adjustment_file="calc_time_adjustments.csv"):
    """Vanha funktio - kutsuu uutta update_programs funktiota"""
    return update_programs(output_dir, adjustment_file)

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    apply_adjustments(output_dir)

# Käytä pienellä alkavia kansioita: documentation, initialization, logs
