import os
from datetime import datetime
import pandas as pd
from fpdf import FPDF

def generate_simulation_report(output_dir):
    """
    Luo yksinkertainen Simulation Report PDF-muodossa ja tallentaa sen reports-kansioon.
    """
    # Lenient CSV reader for possibly malformed stations.csv
    def _read_csv_lenient(path: str):
        import csv
        rows = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            cols = [h.strip() for h in header]
            for parts in reader:
                if parts is None:
                    continue
                vals = (parts + [None]*len(cols))[:len(cols)]
                rows.append(dict(zip(cols, vals)))
        df = pd.DataFrame(rows)
        for c in ['Number','Tank','Group','X Position','Dropping_Time','Device_delay']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        return df
    # Otsikko ja metadata
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M:%S')
    # Haetaan asiakas ja laitos customer.json-tiedostosta
    init_dir = os.path.join(output_dir, 'initialization')
    asiakas = ''
    laitos = ''
    try:
        df_cp = get_customer_plant_legacy_format(init_dir)
        asiakas = str(df_cp.iloc[0]['Customer'])
        laitos = str(df_cp.iloc[0]['Plant'])
    except Exception as e:
        print(f"Warning: Could not load customer.json: {e}")
        asiakas = '[Asiakas ei saatavilla]'
        laitos = '[Laitos ei saatavilla]'
    kansio_nimi = os.path.basename(os.path.abspath(output_dir))

    # Luo reports-kansio simulaatiohakemistoon
    reports_dir = os.path.join(output_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f'simulation_report_{kansio_nimi}.pdf')

    pdf = FPDF()
    pdf.set_margins(20, 10, 10)  # Vasen marginaali 20mm, ylä ja oikea 10mm
    pdf.set_auto_page_break(False)
    pdf.add_page()
    # Lisää ylimääräistä tyhjää tilaa ennen otsikkoa, visuaalisen tasapainon parantamiseksi
    pdf.set_y(20)  # oletus ~10mm, nostetaan n. 20mm alas sivun yläreunasta
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 12, 'Simulation Report', ln=1, align='C')

    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, asiakas, ln=1, align='C')
    pdf.cell(0, 10, laitos, ln=1, align='C')
    pdf.cell(0, 10, date_str, ln=1, align='C')

    # --- KUVA ETUSIVULLE ---
    # Kuva syntyy visualisoinnissa nimellä matrix_timeline_page_1.png
    first_page_img = os.path.join(reports_dir, 'matrix_timeline_page_1.png')
    img_height = 0
    kuva_lisatty = False
    if os.path.exists(first_page_img):
        try:
            # Yritä muuntaa PNG → JPEG (poistaa mahdollisen alfa-kanavan, nopeampi upotus)
            try:
                from PIL import Image  # type: ignore
                jpg_path = os.path.join(reports_dir, 'matrix_timeline_page_1.jpg')
                with Image.open(first_page_img) as im:
                    if im.mode in ('RGBA', 'LA'):
                        bg = Image.new('RGB', im.size, (255, 255, 255))
                        bg.paste(im, mask=im.split()[-1])
                        im_to_save = bg
                    else:
                        im_to_save = im.convert('RGB')
                    im_to_save.save(jpg_path, format='JPEG', quality=85)
                cover_image_path = jpg_path
            except Exception:
                cover_image_path = first_page_img

            x = pdf.l_margin
            y = pdf.get_y() + 12
            w = pdf.w - pdf.l_margin - pdf.r_margin
            # Korkeutta ei anneta → FPDF säilyttää kuvasuhteen
            pdf.image(cover_image_path, x=x, y=y, w=w)
            # Päivitetään y-koordinaatti kuvan jälkeen
            from PIL import Image
            with Image.open(cover_image_path) as im:
                img_w, img_h = im.size
                img_height = w * img_h / img_w
            pdf.set_y(y + img_height + 5)
            kuva_lisatty = True
        except Exception as e:
            print(f"[WARN] Cover image insert failed: {e}")
            pdf.ln(15)
    else:
        pdf.ln(15)

    # --- TEKSTI KUVAAN ALLE ---
    pdf.set_font('Arial', '', 11)
    desc = (
        "This simulation models a production line based on provided configuration and batch data. "
        "The system uses as input the plant layout, station properties, available transporters, and detailed treatment programs for each batch. "
        "The simulation explores feasible production schedules by varying the assignment and timing of batches, station usage, and transporter movements, within the operational constraints. "
        "The goal is to identify efficient and realistic production scenarios that respect all process requirements and resource limitations."
    )
    disclaimer = (
        "Please note that this simulation is a theoretical analysis under idealized conditions: "
        "all batches are assumed to be ready for processing at the start, and finished batches are removed from the system without delay. "
        "Real-world factors such as unexpected downtime, material shortages, or operator interventions are not considered in this model."
    )
    for paragraph in [desc, '', disclaimer]:
        if paragraph:
            pdf.multi_cell(0, 7, paragraph, align='L')
        else:
            pdf.ln(2)


    # Sijoitetaan hakemiston nimi etusivun alalaitaan (A4 korkeus 297mm, marginaali 10mm)
    pdf.set_y(297-10-10)  # 10mm marginaali ylhäällä ja alhaalla
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 10, kansio_nimi, 0, 0, 'R')

    # Uusi sivu taulukoille
    pdf.add_page()
    pdf.ln(10)
    # Syötetaulukot (stationit ja käsittelyohjelmat)
    stations_path = os.path.join(output_dir, 'initialization', 'stations.csv')
    programs_path = os.path.join(reports_dir, 'treatment_programs.csv')
    
    # Luo treatment_programs.csv yhdistämällä kaikki treatment_program_*.csv
    init_dir = os.path.join(output_dir, 'initialization')
    treatment_files = [f for f in os.listdir(init_dir) if f.startswith('treatment_program_') and f.endswith('.csv') and not f.startswith('treatment_program_originals')]
    if treatment_files:
        dfs = []
        for f in treatment_files:
            df = pd.read_csv(os.path.join(init_dir, f))
            dfs.append(df)
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df.to_csv(programs_path, index=False)
    
    # Load stations from JSON
    from load_stations_json import load_stations_from_json
    df_st = load_stations_from_json(init_dir)
    # Poista Type-sarake jos löytyy
    if 'Station_type' in df_st.columns:
        df_st = df_st.drop(columns=['Station_type'])
    # Lisää Transporter-sarake
    # Käytä cp_sat-esi-prosessoituja transporter-alueita legacy-tiedoston sijaan
    transporters_path = os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv')
    if os.path.exists(transporters_path):
        df_trans = pd.read_csv(transporters_path)
        transporter_list = []
        for _, row in df_st.iterrows():
            number = row['Number']
            lifts = []
            sinks = []
            for _, t_row in df_trans.iterrows():
                tid = int(t_row['Transporter_id'])
                if int(t_row['Min_Lift_Station']) <= number <= int(t_row['Max_Lift_Station']):
                    lifts.append(tid)
                if int(t_row['Min_Sink_Station']) <= number <= int(t_row['Max_Sink_Station']):
                    sinks.append(tid)
            parts = []
            for tid in sorted(set(lifts + sinks)):
                has_lift = tid in lifts
                has_sink = tid in sinks
                if has_lift and has_sink:
                    parts.append(f"{tid}L-{tid}S")
                elif has_lift:
                    parts.append(f"{tid}L")
                elif has_sink:
                    parts.append(f"{tid}S")
            transporter_str = " / ".join(parts)
            transporter_list.append(transporter_str)
        df_st.insert(df_st.columns.get_loc('Name'), 'Transporter', transporter_list)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Stations', ln=1, align='L')
    pdf.set_font('Arial', '', 10)
    # Add English explanation below the Stations heading
    stations_expl = (
        "The Stations table lists all surface treatment line stations and their key properties. "
        "Columns show the station number, group, name, x-coordinate, draining and device delays, and hoist/lift restrictions. "
        "Device delay combines all possible equipment delays affecting lift and sink times, such as covers or transfer devices.\n\n"
        "The Transporter column indicates which hoists (L = lift, S = sink) can operate at each station. "
        "For example, '1L-1S / 2L' means the station can be both lifted and sunk by hoist 1, and lifted by hoist 2. "
        "The column uses the format '<hoist>L-<hoist>S / <hoist>L...', where L = lift and S = sink permission for each hoist."
    )
    pdf.multi_cell(0, 6, stations_expl)
    pdf.ln(8)  # Add vertical space before the table
    original_colnames = list(df_st.columns)
    # Muuta sarakkeiden nimiä näyttöä varten
    name_mapping = {
        'Dropping_Time': 'Dropping (s)',
        'Device_delay': 'Device delay (s)'
    }
    display_colnames = [name_mapping.get(c, c) for c in original_colnames]
    # Laske sarakkeiden leveydet sekä nimien että datan perusteella käyttäen alkuperäisiä nimiä
    colwidths = []
    for c in original_colnames:
        name_width = pdf.get_string_width(str(display_colnames[original_colnames.index(c)])) + 6
        data_widths = []
        for _, row in df_st.iterrows():
            if c == 'Dropping_Time':
                val_str = f"{row[c]:.1f}"
            else:
                val_str = str(row[c])
            data_widths.append(pdf.get_string_width(val_str) + 6)
        max_data_width = max(data_widths) if data_widths else 0
        colwidths.append(max(name_width, max_data_width))
    # Aseta Dropping (s) ja Device delay (s) saman levyisiksi
    dropping_idx = display_colnames.index('Dropping (s)')
    device_idx = display_colnames.index('Device delay (s)')
    max_width = max(colwidths[dropping_idx], colwidths[device_idx])
    colwidths[dropping_idx] = max_width
    colwidths[device_idx] = max_width
    # Määritä asemoinnit: Group, X Position, Dropping (s), Device delay (s) oikeaan
    aligns = ['L'] * len(display_colnames)
    right_align_cols = ['Group', 'X Position', 'Dropping (s)', 'Device delay (s)']
    center_align_cols = ['Number', 'Group']
    for i, c in enumerate(display_colnames):
        if c in right_align_cols:
            aligns[i] = 'R'
        elif c in center_align_cols:
            aligns[i] = 'C'
    # Sarakkeiden nimet keskelle ja lihavoitu, vaalea harmaa tausta
    pdf.set_fill_color(220, 220, 220)  # Vaalea harmaa
    pdf.set_font('Arial', 'B', 10)
    for i, (c, w) in enumerate(zip(display_colnames, colwidths)):
        pdf.cell(w, 8, str(c), border=1, align='C', fill=True)
    pdf.ln()
    pdf.set_font('Arial', '', 10)
    # Data rivit zebra stripes
    for row_idx, (_, row) in enumerate(df_st.iterrows()):
        if row_idx % 2 == 0:
            pdf.set_fill_color(245, 245, 245)  # Hyvin vaalea harmaa
            fill = True
        else:
            fill = False
        for i, (c, w) in enumerate(zip(original_colnames, colwidths)):
            if c == 'Dropping_Time':
                val_str = f"{row[c]:.1f}"
            elif c == 'Device_delay':
                val_str = f"{row[c]:.1f}"
            else:
                val_str = str(row[c])
            pdf.cell(w, 8, val_str, border=1, align=aligns[i], fill=fill)
        pdf.ln()
    # Uusi sivu Treatment Programs -taulukolle
    pdf.add_page()
    pdf.ln(10)
    if os.path.exists(programs_path):
        df_prog = pd.read_csv(programs_path)
        cols = ['Stage', 'MinStat', 'MaxStat', 'MinTime', 'MaxTime']
        df_prog_unique = df_prog[cols].drop_duplicates()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Treatment Programs', ln=1)
        pdf.set_font('Arial', '', 10)
        colnames = cols
        # Laske sarakkeiden leveydet sekä nimien että datan perusteella
        colwidths = []
        for c in colnames:
            name_width = pdf.get_string_width(str(c)) + 6
            data_widths = [pdf.get_string_width(str(row[c])) + 6 for _, row in df_prog_unique.iterrows()]
            max_data_width = max(data_widths) if data_widths else 0
            colwidths.append(max(name_width, max_data_width))
        for c, w in zip(colnames, colwidths):
            pdf.cell(w, 8, str(c), border=1)
        pdf.ln()
        for _, row in df_prog_unique.iterrows():
            for c, w in zip(colnames, colwidths):
                pdf.cell(w, 8, str(row[c]), border=1)
            pdf.ln()
        pdf.ln(5)
    pdf.output(pdf_path)
    print(f"📝 Simulation report PDF generated: {pdf_path}")
