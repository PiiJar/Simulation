import pandas as pd
import os
import matplotlib.pyplot as plt

def repair_report_data(output_dir):
    """
    Kerää ja valmistelee simulaatiotiedoista raporttia varten tietoja.
    Erityisesti lasketaan nostinkohtaisesti vaiheaikojen summat ajanjaksolta
    ensimmäisen vaiheen 2 alusta viimeisen vaiheen 4 loppuun.

    Args:
        output_dir (str): Simulaatiokansion polku

    Returns:
        pd.DataFrame: Valmistellut raporttitiedot
    """
    logs_dir = os.path.join(output_dir, "logs")
    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    # Lue movement tiedosto
    movement_file = os.path.join(logs_dir, "transporters_movement.csv")
    if not os.path.exists(movement_file):
        raise FileNotFoundError(f"Movement file not found: {movement_file}")

    df = pd.read_csv(movement_file)

    # Varmista että tarvittavat sarakkeet ovat olemassa
    required_cols = ['Transporter', 'Phase', 'Start_Time', 'End_Time']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in movement file")

    # Muunna ajat sekunneiksi jos tarpeen
    df['Start_Time'] = pd.to_numeric(df['Start_Time'], errors='coerce')
    df['End_Time'] = pd.to_numeric(df['End_Time'], errors='coerce')
    df['Phase'] = pd.to_numeric(df['Phase'], errors='coerce')

    # Poista rivit joissa on NaN arvoja
    df = df.dropna(subset=['Transporter', 'Phase', 'Start_Time', 'End_Time'])

    results = []

    # Käy läpi jokainen nostin
    for transporter in sorted(df['Transporter'].unique()):
        transporter_df = df[df['Transporter'] == transporter].copy()

        # Löydä ensimmäinen vaihe 2 alku ja viimeinen vaihe 4 loppu
        phase_2_starts = transporter_df[transporter_df['Phase'] == 2]['Start_Time']
        phase_4_ends = transporter_df[transporter_df['Phase'] == 4]['End_Time']

        if len(phase_2_starts) == 0 or len(phase_4_ends) == 0:
            continue  # Ei vaiheita 2 tai 4, ohita tämä nostin

        first_phase_2_start = phase_2_starts.min()
        last_phase_4_end = phase_4_ends.max()

        # Suodata vain tämä ajanjakso
        period_df = transporter_df[
            (transporter_df['Start_Time'] >= first_phase_2_start) &
            (transporter_df['End_Time'] <= last_phase_4_end)
        ]

        # Laske vaiheiden summat
        phase_sums = {}
        for phase in [0, 1, 2, 3, 4]:
            phase_data = period_df[period_df['Phase'] == phase]
            total_duration = (phase_data['End_Time'] - phase_data['Start_Time']).sum()
            phase_sums[f'Sum_Phase_{phase}'] = int(total_duration)

        # Kokonaisaika
        total_time = last_phase_4_end - first_phase_2_start

        result_row = {
            'Transporter': int(transporter),
            'Total_Time': int(total_time),
            **phase_sums
        }

        results.append(result_row)

    # Luo DataFrame ja tallenna
    result_df = pd.DataFrame(results)
    output_file = os.path.join(reports_dir, "transporter_phases.csv")
    result_df.to_csv(output_file, index=False)

    print(f"Raporttitiedot tallennettu: {output_file}")
    return result_df

def create_phase_pie_charts(output_dir):
    """
    Luo nostinkohtaiset piirakkakuvastot vaiheiden prosenttiosuuksista.

    Args:
        output_dir (str): Simulaatiokansion polku
    """
    reports_dir = os.path.join(output_dir, "reports")

    # Lue transporter_phases.csv
    phases_file = os.path.join(reports_dir, "transporter_phases.csv")
    if not os.path.exists(phases_file):
        print(f"Warning: {phases_file} not found, skipping pie charts")
        return

    df = pd.read_csv(phases_file)

    # Vaihesarakkeet
    phase_cols = ['Sum_Phase_0', 'Sum_Phase_1', 'Sum_Phase_2', 'Sum_Phase_3', 'Sum_Phase_4']
    phase_labels = ['Idle', 'Move to Lift', 'Lifting', 'Move to Sink', 'Sinking']

    # Luo piirakka jokaiselle nostimelle
    for _, row in df.iterrows():
        transporter = int(row['Transporter'])

        # Kerää vaiheiden arvot
        values = [row[col] for col in phase_cols]

        # Suodata pois nolla-arvot mutta säilytä järjestys
        filtered_labels = []
        filtered_values = []
        for i, (label, value) in enumerate(zip(phase_labels, values)):
            if value > 0:
                filtered_labels.append(label)
                filtered_values.append(value)

        if not filtered_values:
            continue  # Ei dataa tälle nostimelle

        # Luo piirakka
        plt.figure(figsize=(8, 6))
        plt.pie(filtered_values, labels=filtered_labels, autopct='%1.1f%%', startangle=90, counterclock=False)
        plt.title(f'Transporter {transporter} - Phase Distribution')
        plt.axis('equal')  # Tasainen ympyrä

        # Tallenna kuva
        chart_file = os.path.join(reports_dir, f"transporter_{transporter}_phases_pie.png")
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Piirakkakuva tallennettu: {chart_file}")

def repair_report_data(output_dir):
    """
    Kerää ja valmistelee simulaatiotiedoista raporttia varten tietoja.
    Erityisesti lasketaan nostinkohtaisesti vaiheaikojen summat ajanjaksolta
    ensimmäisen vaiheen 2 alusta viimeisen vaiheen 4 loppuun.

    Args:
        output_dir (str): Simulaatiokansion polku

    Returns:
        pd.DataFrame: Valmistellut raporttitiedot
    """
    logs_dir = os.path.join(output_dir, "logs")
    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    # Lue movement tiedosto
    movement_file = os.path.join(logs_dir, "transporters_movement.csv")
    if not os.path.exists(movement_file):
        raise FileNotFoundError(f"Movement file not found: {movement_file}")

    df = pd.read_csv(movement_file)

    # Varmista että tarvittavat sarakkeet ovat olemassa
    required_cols = ['Transporter', 'Phase', 'Start_Time', 'End_Time']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in movement file")

    # Muunna ajat sekunneiksi jos tarpeen
    df['Start_Time'] = pd.to_numeric(df['Start_Time'], errors='coerce')
    df['End_Time'] = pd.to_numeric(df['End_Time'], errors='coerce')
    df['Phase'] = pd.to_numeric(df['Phase'], errors='coerce')

    # Poista rivit joissa on NaN arvoja
    df = df.dropna(subset=['Transporter', 'Phase', 'Start_Time', 'End_Time'])

    results = []

    # Käy läpi jokainen nostin
    for transporter in sorted(df['Transporter'].unique()):
        transporter_df = df[df['Transporter'] == transporter].copy()

        # Löydä ensimmäinen vaihe 2 alku ja viimeinen vaihe 4 loppu
        phase_2_starts = transporter_df[transporter_df['Phase'] == 2]['Start_Time']
        phase_4_ends = transporter_df[transporter_df['Phase'] == 4]['End_Time']

        if len(phase_2_starts) == 0 or len(phase_4_ends) == 0:
            continue  # Ei vaiheita 2 tai 4, ohita tämä nostin

        first_phase_2_start = phase_2_starts.min()
        last_phase_4_end = phase_4_ends.max()

        # Suodata vain tämä ajanjakso
        period_df = transporter_df[
            (transporter_df['Start_Time'] >= first_phase_2_start) &
            (transporter_df['End_Time'] <= last_phase_4_end)
        ]

        # Laske vaiheiden summat
        phase_sums = {}
        for phase in [0, 1, 2, 3, 4]:
            phase_data = period_df[period_df['Phase'] == phase]
            total_duration = (phase_data['End_Time'] - phase_data['Start_Time']).sum()
            phase_sums[f'Sum_Phase_{phase}'] = int(total_duration)

        # Kokonaisaika
        total_time = last_phase_4_end - first_phase_2_start

        result_row = {
            'Transporter': int(transporter),
            'Total_Time': int(total_time),
            **phase_sums
        }

        results.append(result_row)

    # Luo DataFrame ja tallenna
    result_df = pd.DataFrame(results)
    output_file = os.path.join(reports_dir, "transporter_phases.csv")
    result_df.to_csv(output_file, index=False)

    print(f"Raporttitiedot tallennettu: {output_file}")

    # Luo piirakkakuvastot
    create_phase_pie_charts(output_dir)

    return result_df

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python repair_report_data.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]
    repair_report_data(output_dir)