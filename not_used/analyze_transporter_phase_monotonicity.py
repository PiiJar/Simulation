import os
import pandas as pd

def find_latest_logs_dir(output_root):
    subdirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    subdirs = [d for d in subdirs if d.startswith('202')]
    if not subdirs:
        raise FileNotFoundError("Yhtään output-kansiota ei löytynyt.")
    latest = sorted(subdirs)[-1]
    return os.path.join(output_root, latest, "logs")

def find_latest_output_dir(output_root):
    subdirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    subdirs = [d for d in subdirs if d.startswith('202')]
    if not subdirs:
        raise FileNotFoundError("Yhtään output-kansiota ei löytynyt.")
    latest = sorted(subdirs)[-1]
    return os.path.join(output_root, latest)

def analyze_phase_monotonicity(output_root="output"):
    logs_dir = find_latest_logs_dir(output_root)
    output_dir = find_latest_output_dir(output_root)
    movement_file = os.path.join(logs_dir, "transporters_movement.csv")
    tasks_file = os.path.join(logs_dir, "transporter_tasks_stretched.csv")
    matrix_file = os.path.join(logs_dir, "transporter_tasks_from_matrix.csv")
    program_dir = os.path.join(output_dir, "optimized_programs")

    df = pd.read_csv(movement_file)
    tasks_df = pd.read_csv(tasks_file)
    matrix_df = pd.read_csv(matrix_file)

    # Käydään läpi jokainen nostin erikseen
    for transporter_id in sorted(df['Transporter'].unique()):
        t_df = df[df['Transporter'] == transporter_id].sort_values(['Batch', 'Start_Time', 'Phase'])
        prev_end = None
        prev_phase = -1
        prev_batch = None
        for idx, row in t_df.iterrows():
            batch = row['Batch']
            phase = row['Phase']
            start = row['Start_Time']
            end = row['End_Time']
            movement_id = row.get('Movement_ID', idx+1)
            virhe = None
            if prev_batch == batch:
                if not (phase == prev_phase + 1 or (prev_phase == 4 and phase == 0)):
                    virhe = f"[VIRHE] Nostin {transporter_id} | Batch {batch} | Movement_ID {movement_id}: Vaihehyppy {prev_phase} -> {phase} rivillä {idx}"
            if prev_end is not None and start < prev_end:
                virhe = f"[VIRHE] Nostin {transporter_id} | Batch {batch} | Movement_ID {movement_id}: Päällekkäisyys, edellinen loppu {prev_end}, seuraava alku {start} rivillä {idx}"
            if virhe:
                print(virhe)
                # Etsi täsmällinen tehtävä _stretched-listalta
                match_stretched = tasks_df[(tasks_df['Batch'] == batch) & (tasks_df['Transporter_id'] == transporter_id) & (tasks_df['Stage'] == phase) & (tasks_df['Lift_time'] == start)]
                print("  _stretched tehtävä:")
                if not match_stretched.empty:
                    print(match_stretched.to_string(index=False))
                else:
                    print("    Ei täsmäävää riviä.")
                # Etsi täsmällinen tehtävä from_matrix-listalta
                match_matrix = matrix_df[(matrix_df['Batch'] == batch) & (matrix_df['Transporter_id'] == transporter_id) & (matrix_df['Stage'] == phase) & (matrix_df['Lift_time'] == start)]
                print("  from_matrix tehtävä:")
                if not match_matrix.empty:
                    print(match_matrix.to_string(index=False))
                else:
                    print("    Ei täsmäävää riviä.")
                # Etsi käsittelyohjelmasta täsmällinen vaihe
                program = None
                stage = None
                if not match_stretched.empty:
                    program = match_stretched.iloc[0]['Treatment_program']
                    stage = match_stretched.iloc[0]['Stage']
                elif not match_matrix.empty:
                    program = match_matrix.iloc[0]['Treatment_program']
                    stage = match_matrix.iloc[0]['Stage']
                if program is not None and stage is not None:
                    fname = f"Batch_{int(batch):03d}_Treatment_program_{int(program):03d}.csv"
                    prog_file = os.path.join(program_dir, fname)
                    if os.path.exists(prog_file):
                        prog_df = pd.read_csv(prog_file)
                        row_prog = prog_df[prog_df['Stage'] == stage]
                        if not row_prog.empty:
                            r = row_prog.iloc[0]
                            print(f"  Käsittelyohjelma: Stage={stage} MinStat={r.get('MinStat','')} MaxStat={r.get('MaxStat','')} MinTime={r.get('MinTime','')} MaxTime={r.get('MaxTime','')} CalcTime={r.get('CalcTime','')}")
                        else:
                            print("  Käsittelyohjelmasta ei löytynyt vastaavaa stagea.")
                    else:
                        print(f"  Käsittelyohjelmatiedostoa ei löytynyt: {prog_file}")
                else:
                    print("  Ei löytynyt täsmäävää tehtävää käsittelyohjelman hakuun.")
            prev_end = end
            prev_phase = phase
            prev_batch = batch

def report_task_context(tasks_df, matrix_df, batch, transporter_id, phase, start):
    # Etsi _stretched ja from_matrix -listoilta vastaavat rivit
    match_stretched = tasks_df[(tasks_df['Batch'] == batch) & (tasks_df['Transporter_id'] == transporter_id)]
    match_matrix = matrix_df[(matrix_df['Batch'] == batch) & (matrix_df['Transporter_id'] == transporter_id)]
    print("  _stretched tehtävät (batch, transporter):")
    print(match_stretched.to_string(index=False, max_rows=5))
    print("  from_matrix tehtävät (batch, transporter):")
    print(match_matrix.to_string(index=False, max_rows=5))

def report_program_context(program_dir, batch, phase, tasks_df, transporter_id, start):
    # Etsi käsittelyohjelman vaihe
    # Oletetaan Treatment_program on sama kaikissa batchin tehtävissä
    match = tasks_df[(tasks_df['Batch'] == batch) & (tasks_df['Transporter_id'] == transporter_id)]
    if not match.empty:
        program = match.iloc[0]['Treatment_program']
        stage = match.iloc[0]['Stage']
        fname = f"Batch_{int(batch):03d}_Treatment_program_{int(program):03d}.csv"
        prog_file = os.path.join(program_dir, fname)
        if os.path.exists(prog_file):
            prog_df = pd.read_csv(prog_file)
            row = prog_df[prog_df['Stage'] == stage]
            if not row.empty:
                r = row.iloc[0]
                print(f"  Käsittelyohjelma: Stage={stage} MinStat={r.get('MinStat','')} MaxStat={r.get('MaxStat','')} MinTime={r.get('MinTime','')} MaxTime={r.get('MaxTime','')} CalcTime={r.get('CalcTime','')}")
            else:
                print("  Käsittelyohjelmasta ei löytynyt vastaavaa stagea.")
        else:
            print(f"  Käsittelyohjelmatiedostoa ei löytynyt: {prog_file}")
    else:
        print("  Ei löytynyt täsmäävää tehtävää käsittelyohjelman hakuun.")

if __name__ == "__main__":
    analyze_phase_monotonicity()
