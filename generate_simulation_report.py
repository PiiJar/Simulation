import os
from datetime import datetime
import pandas as pd
from fpdf import FPDF

def generate_simulation_report(output_dir):
    """
    Luo yksinkertainen Simulation Report PDF-muodossa ja tallentaa sen reports-kansioon.
    """
    # Otsikko ja metadata
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M:%S')
    # Haetaan asiakas ja laitos initialization/customer_and_plant.csv-tiedostosta
    init_dir = os.path.join(output_dir, 'initialization')
    asiakas = ''
    laitos = ''
    try:
        df_cp = pd.read_csv(os.path.join(init_dir, 'customer_and_plant.csv'))
        asiakas = str(df_cp.iloc[0]['Customer'])
        laitos = str(df_cp.iloc[0]['Plant'])
    except Exception:
        asiakas = '[Asiakas ei saatavilla]'
        laitos = '[Laitos ei saatavilla]'
    kansio_nimi = os.path.basename(os.path.abspath(output_dir))

    # Luo reports-kansio simulaatiohakemistoon
    reports_dir = os.path.join(output_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f'simulation_report_{kansio_nimi}.pdf')

    pdf = FPDF()
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 12, 'Simulation Report', ln=1, align='C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, asiakas, ln=1, align='C')
    pdf.cell(0, 10, laitos, ln=1, align='C')
    pdf.cell(0, 10, date_str, ln=1, align='C')

    # Sijoitetaan hakemiston nimi etusivun alalaitaan (A4 korkeus 297mm, marginaali 10mm)
    pdf.set_y(297-10-10)  # 10mm marginaali ylhäällä ja alhaalla
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 10, kansio_nimi, 0, 0, 'R')

    # Uusi sivu taulukoille
    pdf.add_page()
    pdf.ln(10)
    # Syötetaulukot (stationit ja käsittelyohjelmat)
    stations_path = os.path.join(output_dir, 'stations.csv')
    programs_path = os.path.join(output_dir, 'treatment_programs.csv')
    if os.path.exists(stations_path):
        df_st = pd.read_csv(stations_path)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Stations', ln=1)
        pdf.set_font('Arial', '', 10)
        colnames = list(df_st.columns)
        colwidths = [pdf.get_string_width(str(c))+6 for c in colnames]
        for c, w in zip(colnames, colwidths):
            pdf.cell(w, 8, str(c), border=1)
        pdf.ln()
        for _, row in df_st.iterrows():
            for c, w in zip(colnames, colwidths):
                pdf.cell(w, 8, str(row[c]), border=1)
            pdf.ln()
        pdf.ln(5)
    if os.path.exists(programs_path):
        df_prog = pd.read_csv(programs_path)
        cols = ['Stage', 'MinStat', 'MaxStat', 'MinTime', 'MaxTime']
        df_prog_unique = df_prog[cols].drop_duplicates()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Treatment Programs', ln=1)
        pdf.set_font('Arial', '', 10)
        colnames = cols
        colwidths = [pdf.get_string_width(str(c))+6 for c in colnames]
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
