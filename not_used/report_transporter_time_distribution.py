import os
import pandas as pd



def report_transporter_time_distribution(output_dir):
    # Lue nostimien ajoalueet
    transporters_path = os.path.join(os.path.dirname(os.path.dirname(output_dir)), "initialization", "Transporters.csv")
    transporter_ranges = []
    try:
        df_transp = pd.read_csv(transporters_path)
        for i, row in df_transp.iterrows():
            transporter_ranges.append({
                'id': int(row['Transporter_id']),
                'min_x': float(row['Min_x_position']),
                'max_x': float(row['Max_x_Position'])
            })
    except Exception:
        pass
    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    # Lue asemien sijainnit
    stations_path = os.path.join(os.path.dirname(os.path.dirname(output_dir)), "initialization", "Stations.csv")
    try:
        df_stations = pd.read_csv(stations_path)
        station_numbers = df_stations["Number"].values
        x_positions = df_stations["X Position"].values
        max_x = x_positions.max() + 1000
    except Exception:
        station_numbers = []
        x_positions = []
        max_x = 10000

    # Piirrä asemien visualisointi vaakaviivalle
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 1.2))
    ax.hlines(0, 0, max_x, colors='black', linewidth=1)
    n_transp = max(1, len(transporter_ranges))
    # Allasnumerot aivan viivan yläpuolella
    label_fontsize = 5
    station_label_y = 0.001
    if len(station_numbers) > 0:
        # Selvitä värit: Rinse aina sininen, muut saman nimiset samalla värillä
        station_names = df_stations["Name"].values
        unique_names = []
        color_map = {}
        import matplotlib.pyplot as plt
        cmap = plt.get_cmap('tab20')
        palette = [cmap(i) for i in range(20)]
        color_idx = 0
        for name in station_names:
            if name == 'Rinse':
                color_map[name] = 'royalblue'
            elif name not in color_map:
                color_map[name] = palette[color_idx % len(palette)]
                color_idx += 1
        for num, xpos, name in zip(station_numbers, x_positions, station_names):
            color = color_map.get(name, 'black')
            ax.plot(xpos, 0, 'o', color=color, markersize=4)
            ax.text(xpos, station_label_y, str(num), ha='center', va='bottom', fontsize=label_fontsize, rotation=0, color=color)
    # Nostinviivat ylempänä, mutta numerot samalla etäisyydellä viivasta kuin asemilla
    y_base = 0.005
    y_gap = 0.002
    y_positions = [y_base + i * y_gap for i in range(n_transp)]
    max_y = 0
    for idx, t in enumerate(transporter_ranges):
        y = y_positions[idx]
        ax.hlines(y, t['min_x'], t['max_x'], colors=f'C{idx%10}', linewidth=2, alpha=0.7)
        label_y = y + station_label_y
        ax.text(t['min_x'], label_y, f"{t['id']}", ha='left', va='bottom', fontsize=label_fontsize, color=f'C{idx%10}')
        if label_y > max_y:
            max_y = label_y
    ax.set_xlim(-500, max_x)
    ax.set_ylim(-0.01, max_y + 0.01)
    ax.axis('off')
    stations_img_file = os.path.join(reports_dir, "stations_line.svg")
    plt.tight_layout()
    plt.subplots_adjust(top=0.98, bottom=0.05, left=0.03, right=0.99, hspace=0, wspace=0)
    plt.savefig(stations_img_file, bbox_inches='tight', pad_inches=0.01, transparent=True, format='svg')
    plt.close(fig)
    stations_img_rel = os.path.relpath(stations_img_file, reports_dir)
    # Selvitetään erien määrä Production.csv:stä
    production_path = os.path.join(output_dir, "Production.csv")
    if not os.path.exists(production_path):
        # fallback initialization-kansioon
        production_path = os.path.join(os.path.dirname(os.path.dirname(output_dir)), "initialization", "Production.csv")
    try:
        df_prod = pd.read_csv(production_path)
        batch_count = df_prod["Batch"].nunique()
    except Exception:
        batch_count = None

    # Määrittele detailed_path ja lue df heti alussa
    # Käytetään transporter_movements.csv tiedostoa
    movements_path = os.path.join(output_dir, "logs", "transporters_movement.csv")
    if not os.path.exists(movements_path):
        print(f"[TRANSPORTER REPORT] Tiedostoa ei löydy: {movements_path}")
        return
    df = pd.read_csv(movements_path)

    # Vain vaiheet 0–4, järjestys on taattu tiedostossa
    df = df[df["Phase"].isin([0, 1, 2, 3, 4])].copy()

    # Poistettu terminaalitulostukset vaiheiden laskennasta
    import matplotlib.pyplot as plt
    """
    Luo raportin transporter-kohtaisen ajan jakautumisesta vaiheisiin 0–4 ja tallentaa sen reports-kansioon HTML-muodossa.
    Otsikko: Distribution ja Transporters Phases in Simulation <simulaatiokansio>.
    Taulukko: sarakkeet transporterit, rivit vaiheet.
    """
    detailed_path = os.path.join(output_dir, "logs", "transporters_movement.csv")
    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    simulation_name = os.path.basename(os.path.abspath(output_dir))
    report_file = os.path.join(reports_dir, "transporter_time_distribution.html")

    if not os.path.exists(detailed_path):
        print(f"[TRANSPORTER REPORT] Tiedostoa ei löydy: {detailed_path}")
        return

    df = pd.read_csv(detailed_path)
    # Oletetaan, että sarakkeet: Transporter, Phase, Start_Time, End_Time
    result = {}
    for transporter_id, group in df.groupby("Transporter"):
        group = group[group["Phase"].isin([0, 1, 2, 3, 4])].copy()
        # Kokonaisaika: ensimmäisestä nostosta (Phase 2, Start_Time) viimeiseen laskuun (Phase 4, End_Time)
        phase2 = group[group["Phase"] == 2]
        phase4 = group[group["Phase"] == 4]
        if phase2.empty or phase4.empty:
            continue
        t_start = phase2["Start_Time"].min()
        t_end = phase4["End_Time"].max()
        # Rajaa mukaan vain rivit tältä väliltä
        group = group[(group["Start_Time"] >= t_start) & (group["End_Time"] <= t_end)]
        total_time = t_end - t_start
        for phase in range(0, 5):
            phase_rows = group[group["Phase"] == phase]
            total = (phase_rows["End_Time"] - phase_rows["Start_Time"]).sum()
            result.setdefault(phase, {})[transporter_id] = total
        result.setdefault('total_time', {})[transporter_id] = total_time

    # Muodosta DataFrame: rivit = vaiheet, sarakkeet = transporterit
    phases = list(range(0, 5))
    transporters = sorted({tid for tids in result.values() for tid in tids})
    data = []
    for phase in phases:
        row = [result.get(phase, {}).get(tid, 0.0) for tid in transporters]
        data.append(row)
    phase_label_map = {
        "Phase 0": "Phase 0 / s - Idle",
        "Phase 1": "Phase 1 / s - Drive to Lift Station",
        "Phase 2": "Phase 2 / s - Lift",
        "Phase 3": "Phase 3 / s - Drive to Sink Station",
        "Phase 4": "Phase 4 / s - Sink"
    }
    df_report = pd.DataFrame(data, index=[f"Phase {p}" for p in phases], columns=[f"Transporter {tid}" for tid in transporters])

    # Luo ja tallenna piirakkakaaviot
    pie_img_files = []
    phase_labels = [f"Phase {p}" for p in phases]
    for idx, tid in enumerate(transporters):
        values = [df_report.iloc[p, idx] for p in range(len(phases))]
        fig, ax = plt.subplots()
        ax.pie(values, labels=phase_labels, autopct='%1.1f%%', startangle=90)
        # Ei otsikkoa piirakkakaavioon
        img_file = os.path.join(reports_dir, f"transporter_{tid}_pie.png")
        plt.savefig(img_file, bbox_inches='tight')
        plt.close(fig)
        pie_img_files.append((tid, os.path.relpath(img_file, reports_dir)))


    # Luo HTML-raportti production_reportin tyyliin
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Distribution Report</title>
    <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    h1 {{ color: #2c3e50; text-align: center; }}
    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; }}
    th {{ background-color: #f2f2f2; font-weight: bold; text-align: left; }}
    th:not(:first-child) {{ text-align: center; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    .center {{ text-align: center; }}
    </style>
</head>
<body>
    <h1>Distribution: Transporters Phases in Simulation {simulation_name}</h1>
    <table>
        <thead>
            <tr>
                <th>Phase</th>
                {''.join(f'<th>{col}</th>' for col in df_report.columns)}
            </tr>
        </thead>
        <tbody>
"""
    phase_label_map = {
        "Phase 0": "Phase 0 / s - Idle",
        "Phase 1": "Phase 1 / s - Drive to Lift Station",
        "Phase 2": "Phase 2 / s - Lift",
        "Phase 3": "Phase 3 / s - Drive to Sink Station",
        "Phase 4": "Phase 4 / s - Sink"
    }
    for phase_label, row in df_report.iterrows():
        display_label = phase_label_map.get(phase_label, phase_label)
        html_content += f"            <tr>\n                <td>{display_label}</td>"
        for val in row:
            html_content += f"<td class='center'>{val:.2f}</td>"
        html_content += "</tr>\n"

    # Average tasks per batch -rivi (vaihe 2 tehtävien määrä / erien määrä)
    phase2_counts = []
    for tid in transporters:
        try:
            phase2_count = df[(df["Transporter"] == tid) & (df["Phase"] == 2)].shape[0]
        except Exception:
            phase2_count = 0
        phase2_counts.append(phase2_count)
    if batch_count and batch_count > 0:
        avg_tasks_per_batch = [cnt / batch_count for cnt in phase2_counts]
    else:
        avg_tasks_per_batch = [float('nan')] * len(phase2_counts)
    html_content += f"            <tr>\n                <td>Average tasks per batch</td>"
    for val in avg_tasks_per_batch:
        if pd.isna(val):
            html_content += f"<td class='center'>-</td>"
        else:
            html_content += f"<td class='center'>{val:.2f}</td>"
    html_content += "</tr>\n"

    # Average task duration per transporter (phases 1-4 sum / phase 2 count)
    phase_1_4_sum = df_report.loc[[f"Phase {p}" for p in range(1,5)]].sum()
    avg_task_duration = []
    for i, tid in enumerate(transporters):
        try:
            n_tasks = df[(df["Transporter"] == tid) & (df["Phase"] == 2)].shape[0]
            total_time = phase_1_4_sum.iloc[i]
            avg = total_time / n_tasks if n_tasks > 0 else float('nan')
        except Exception:
            avg = float('nan')
        avg_task_duration.append(avg)
    html_content += f"            <tr>\n                <td>Average task / s</td>"
    for val in avg_task_duration:
        if pd.isna(val):
            html_content += f"<td class='center'>-</td>"
        else:
            html_content += f"<td class='center'>{val:.2f}</td>"
    html_content += "</tr>\n"

    # Kuormitusprosenttirivi
    phase_1_4_sum = df_report.loc[[f"Phase {p}" for p in range(1,5)]].sum()
    phase_0_4_sum = df_report.loc[[f"Phase {p}" for p in range(0,5)]].sum()
    load_percent = 100 * phase_1_4_sum / phase_0_4_sum.replace(0, float('nan'))
    html_content += f"            <tr>\n                <td><b>Workload / %</b></td>"
    for val in load_percent:
        if pd.isna(val):
            html_content += f"<td class='center'>-</td>"
        else:
            html_content += f"<td class='center'><b>{val:.1f}</b></td>"
    html_content += "</tr>\n"

    # Kokonaisaika ja kuormitusprosentti -rivi
    html_content += "            <tr>\n                <td><b>Total time (s)</b></td>"
    for tid in transporters:
        total_time = result['total_time'][tid]
        html_content += f"<td class='center'>{total_time:.2f}</td>"
    html_content += "</tr>\n"

    html_content += "            <tr>\n                <td><b>Utilization (%)</b></td>"
    for tid in transporters:
        total_time = result['total_time'][tid]
        active_time = sum(result.get(phase, {}).get(tid, 0.0) for phase in range(1, 5))  # kaikki aktiivivaiheet
        utilization = 100.0 * active_time / total_time if total_time > 0 else 0.0
        html_content += f"<td class='center'>{utilization:.1f}</td>"
    html_content += "</tr>\n"

    html_content += f"""
        </tbody>
    </table>
    <h2>Phase Distribution Pie Charts</h2>
    <div style='display: flex; flex-wrap: wrap; gap: 40px;'>
    """
    for tid, img_file in pie_img_files:
        html_content += f"<div style='text-align:center;'><h3>Transporter {tid}</h3><img src='{img_file}' style='max-width:300px;'></div>"
    html_content += f"""
    </div>
    <h2 style='margin-bottom:0.2em;'>Stations and Task Area Visualization</h2>
    <div style='width:100%;text-align:center;margin:0;'>
        <img src='{stations_img_rel}' style='width:100%;height:auto;max-width:100%;'>
    </div>
    <div style='margin-top: 30px; font-size: 12px; color: #666;'>
        <p>Report generated by Simulation Pipeline</p>
        <p>Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    return report_file

# Esimerkki kutsusta vaiheessa 7:
# report_transporter_time_distribution(output_dir)
