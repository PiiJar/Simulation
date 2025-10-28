import os
import shutil
from datetime import datetime
from glob import glob

def create_simulation_directory(base_dir="output"):
    """
    Luo simulaatiokansion, kopioi tarvittavat kansiot ja alustaa logitiedoston INIT-tapahtumilla.
    Palauttaa luodun simulaatiokansion polun.
    """
    # Lue asiakas ja laitos
    customer = "Customer"
    plant = "Plant"
    customer_plant_path = os.path.join("initialization", "customer_and_plant.csv")
    if os.path.exists(customer_plant_path):
        import pandas as pd
        df_cp = pd.read_csv(customer_plant_path)
        if not df_cp.empty:
            customer = str(df_cp.iloc[0]["Customer"]).strip().replace(" ", "_")
            plant = str(df_cp.iloc[0]["Plant"]).strip().replace(" ", "_")
    # Luo aikaleimapohjainen kansio
    now = datetime.now()
    name = f"{customer}_{plant}_" + now.strftime("%Y-%m-%d_%H-%M-%S")
    full_path = os.path.join(base_dir, name)
    os.makedirs(full_path, exist_ok=True)

    # Luo initialization/treatment_program_originals, jos ei ole olemassa
    tpo_dir = os.path.join("initialization", "treatment_program_originals")
    os.makedirs(tpo_dir, exist_ok=True)

    # Luo cp_sat ja treatment_program_optimized simulaatiokansion alle
    cp_sat_dir = os.path.join(full_path, "cp_sat")
    tpo_optimized_dir = os.path.join(cp_sat_dir, "treatment_program_optimized")
    os.makedirs(tpo_optimized_dir, exist_ok=True)

    # Luo logs-kansio
    logs_dir = os.path.join(full_path, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Preprocessing phase: copy initialization and programs (as original_programs)
    for src, dst_name in [
        ("initialization", "initialization"),
        ("programs", "original_programs")
    ]:
        if os.path.exists(src):
            dst = os.path.join(full_path, dst_name)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # Varmista että Transporters_start_positions.csv kopioituu initialization-kansioon
    src_start_positions = os.path.join("initialization", "Transporters_start_positions.csv")
    dst_start_positions = os.path.join(full_path, "initialization", "Transporters_start_positions.csv")
    if os.path.exists(src_start_positions):
        shutil.copy2(src_start_positions, dst_start_positions)

    # Luo simulation_log.csv ja kirjaa STEP- ja INIT-tapahtumat
    log_file = os.path.join(logs_dir, "simulation_log.csv")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("Timestamp,Type,Description\n")
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp},STEP,STEP 1 STARTED: SIMULATION DIRECTORY CREATION\n")
        f.write(f"{timestamp},INIT,Simulation started in folder {full_path}\n")
        # initialization
        init_dir = os.path.join(full_path, "initialization")
        init_files = glob(os.path.join(init_dir, "*")) if os.path.exists(init_dir) else []
        f.write(f"{timestamp},INIT,Initialization files count: {len(init_files)}\n")
        for file in init_files:
            f.write(f"{timestamp},INIT,Initialization file: {os.path.basename(file)}\n")
        # documentation
        doc_dir = os.path.join(full_path, "documentation")
        doc_files = glob(os.path.join(doc_dir, "*")) if os.path.exists(doc_dir) else []
        f.write(f"{timestamp},INIT,Documentation files count: {len(doc_files)}\n")
        for file in doc_files:
            f.write(f"{timestamp},INIT,Documentation file: {os.path.basename(file)}\n")
        f.write(f"{timestamp},STEP,STEP 1 COMPLETED: SIMULATION DIRECTORY READY\n")

    # Luo reports-kansio
    reports_dir = os.path.join(full_path, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    # Poistettu: original_programs-kansion ja eräkohtaisten ohjelmien luonti (tämä tehdään vaiheessa 2)
    # Tulosta vain aloitus ja lopetus
    return full_path

# Esimerkkikutsu
if __name__ == "__main__":
    create_simulation_directory()
