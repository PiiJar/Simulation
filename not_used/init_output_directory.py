import os
from datetime import datetime
import shutil
import pandas as pd

def init_output_directory(base_dir="output"):
    now = datetime.now()
    name = now.strftime("%Y-%m-%d_%H-%M-%S")
    full_path = os.path.join(base_dir, name)
    os.makedirs(full_path, exist_ok=True)
    
    # Käytä pienellä alkavia kansioita: documentation, initialization, logs
    # Luo logs-kansio välivaiheiden CSV-tiedostoille
    logs_dir = os.path.join(full_path, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    print(f"Luotu logs-kansio: {logs_dir}")
      # Kopioi koko initialization-kansio simulointikansioon
    if os.path.exists("initialization"):
        dest_initialization = os.path.join(full_path, "initialization")
        if os.path.exists(dest_initialization):
            shutil.rmtree(dest_initialization)
        shutil.copytree("initialization", dest_initialization)
        print(f"Kopioitu initialization-kansio")
    
    # Kopioi koko documentation-kansio simulointikansioon
    if os.path.exists("documentation"):
        dest_documentation = os.path.join(full_path, "documentation")
        if os.path.exists(dest_documentation):
            shutil.rmtree(dest_documentation)
        shutil.copytree("documentation", dest_documentation)
        print(f"Kopioitu documentation-kansio")
    
    # Kopioi programs-kansio ja nimeä se original_programs-kansioksi
    if os.path.exists("programs"):
        dest_programs = os.path.join(full_path, "original_programs")
        if os.path.exists(dest_programs):
            shutil.rmtree(dest_programs)
        shutil.copytree("programs", dest_programs)
        print(f"Kopioitu programs-kansio nimellä original_programs")
    
    print(f"Tuloskansio luotu: {full_path}")
    return full_path

def create_simulation_directory(base_dir="output"):
    """
    Luo simulaatiokansion ja kopioi tarvittavat kansiot sekä alustaa logit.
    Palauttaa luodun simulaatiokansion polun.
    """
    from glob import glob
    now = datetime.now()
    name = now.strftime("%Y-%m-%d_%H-%M-%S")
    full_path = os.path.join(base_dir, name)
    os.makedirs(full_path, exist_ok=True)
    # Käytä pienellä alkavia kansioita: documentation, initialization, logs
    # Luo logs-kansio välivaiheiden CSV-tiedostoille
    logs_dir = os.path.join(full_path, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    print(f"Luotu logs-kansio: {logs_dir}")
    # Kopioi koko initialization-kansio simulointikansioon
    if os.path.exists("initialization"):
        dest_initialization = os.path.join(full_path, "initialization")
        if os.path.exists(dest_initialization):
            shutil.rmtree(dest_initialization)
        shutil.copytree("initialization", dest_initialization)
        print(f"Kopioitu initialization-kansio")
    # Kopioi koko documentation-kansio simulointikansioon
    if os.path.exists("documentation"):
        dest_documentation = os.path.join(full_path, "documentation")
        if os.path.exists(dest_documentation):
            shutil.rmtree(dest_documentation)
        shutil.copytree("documentation", dest_documentation)
        print(f"Kopioitu documentation-kansio")
    # Kopioi programs-kansio ja nimeä se original_programs-kansioksi
    if os.path.exists("programs"):
        dest_programs = os.path.join(full_path, "original_programs")
        if os.path.exists(dest_programs):
            shutil.rmtree(dest_programs)
        shutil.copytree("programs", dest_programs)
        print(f"Kopioitu programs-kansio nimellä original_programs")
    # Luo simulation_log.csv ja kirjaa INIT-tapahtumat
    log_file = os.path.join(logs_dir, "simulation_log.csv")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("Timestamp,Type,Description\n")
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp},INIT,Simulation started in folder {full_path}\n")
        # Kirjaa initialization-tiedostot
        init_files = glob(os.path.join(dest_initialization, "*")) if os.path.exists("initialization") else []
        f.write(f"{timestamp},INIT,Initialization files count: {len(init_files)}\n")
        for file in init_files:
            f.write(f"{timestamp},INIT,Initialization file: {os.path.basename(file)}\n")
        doc_files = glob(os.path.join(dest_documentation, "*")) if os.path.exists("documentation") else []
        f.write(f"{timestamp},INIT,Documentation files count: {len(doc_files)}\n")
        for file in doc_files:
            f.write(f"{timestamp},INIT,Documentation file: {os.path.basename(file)}\n")
    print(f"Alustettu simulation_log.csv: {log_file}")
    print(f"Tuloskansio luotu: {full_path}")
    return full_path
