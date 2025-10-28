#!/usr/bin/env python3
"""
Testiputki - VAIHE 2: Luo original_programs ja käsittelyohjelmat

Tämä vaihe muodostaa eräkohtaiset käsittelyohjelmat kansioon original_programs.

- Lukee initialization/Production.csv-tiedoston ja käy läpi jokaisen erän.
- Kopioi oikean Treatment_program_xxx.csv-tiedoston initialization-kansiosta.
- Nimeää kopion muotoon Batch_xxx_Treatment_program_yyy.csv.
- Lisää CalcTime-sarakkeen (aluksi = MinTime), jos sitä ei ole.
- Palauttaa original_programs-kansion polun.

Käytä aina output_dir-parametria polkujen rakentamiseen.
Kaikki vaiheet kirjaavat etenemisensä simulation_log.csv-tiedostoon.

# Päivitetty 2025-06-24
"""
import os
import sys
from datetime import datetime
from not_used.generate_batch_treatment_programs_original import generate_batch_treatment_programs_original

def create_original_programs(output_dir):
    """
    Luo original_programs-kansio ja kopioi käsittelyohjelmat eräkohtaisesti production.csv:n mukaan.
    """
    return generate_batch_treatment_programs_original(output_dir)

def test_step_2(output_dir):
    """
    VAIHE 2: Luo original_programs ja käsittelyohjelmat
    """
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 2 - KÄSITTELYOHJELMIEN LUONTI - ALKAA")
    result = create_original_programs(output_dir)
    if not result:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: Vaihe 2 epäonnistui!")
        sys.exit(1)
    end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{end}] VAIHE 2 - KÄSITTELYOHJELMIEN LUONTI - VALMIS")

if __name__ == "__main__":
    import argparse
    import glob
    parser = argparse.ArgumentParser(description="VAIHE 2: Luo original_programs ja käsittelyohjelmat")
    parser.add_argument("--output_dir", required=False, help="Simulaatiokansion polku")
    args = parser.parse_args()
    output_dir = args.output_dir

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if output_dir is None:
        output_base = os.path.join(script_dir, "output")
        subdirs = [d for d in glob.glob(os.path.join(output_base, "*")) if os.path.isdir(d)]
        if subdirs:
            output_dir = max(subdirs, key=os.path.getmtime)
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: Ei output-kansioita löytynyt!")
            sys.exit(1)
    else:
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(script_dir, output_dir)

    test_step_2(output_dir)
