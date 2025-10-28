import os
import shutil

def copy_originals_to_optimized(output_dir):
    """
    Kopioi alkuperäiset ohjelmat optimized_programs kansioon.
    Tämä on lähtökohta kaikelle optimoinnille (venytys + lisäoptimointi).
    """
    # Kopioidaan vain original_programs-hakemistosta, ei initializationista
    original_programs_dir = os.path.join(output_dir, "original_programs")
    optimized_programs_dir = os.path.join(output_dir, "optimized_programs")
    os.makedirs(optimized_programs_dir, exist_ok=True)
    for fname in os.listdir(original_programs_dir):
        if fname.endswith('.csv'):
            src = os.path.join(original_programs_dir, fname)
            dst = os.path.join(optimized_programs_dir, fname)
            shutil.copyfile(src, dst)
            # print(f"Kopioitu: {src} -> {dst}")  # Ei testitulosteita vaiheessa 2

if __name__ == "__main__":
    # Selvitetään viimeisin simulaatiokansio automaattisesti
    base_dir = "output"
    all_runs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not all_runs:
        raise RuntimeError("No simulation runs found in output directory.")
    latest_run = sorted(all_runs)[-1]
    output_dir = os.path.join(base_dir, latest_run)
    copy_originals_to_optimized(output_dir)
