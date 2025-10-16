import os
import pandas as pd
import shutil

def process_production_batches(output_dir):
    """
    Käsittelee Production.csv:n ja luo original_programs-kansioon 
    eräkohtaiset ohjelmatiedostot CalcTime-sarakkeella.
    """
    print("Käsitellään tuotantoerien ohjelmatiedostot...")
    
    # Lue Production.csv
    production_file = os.path.join(output_dir, "initialization", "Production.csv")
    if not os.path.exists(production_file):
        print(f"Production.csv ei löydy: {production_file}")
        return
    
    production_df = pd.read_csv(production_file)
    print(f"Luettu {len(production_df)} tuotantoerää")
    
    # Varmista että original_programs-kansio on olemassa
    original_programs_dir = os.path.join(output_dir, "original_programs")
    os.makedirs(original_programs_dir, exist_ok=True)
    
    # Käsittele jokainen erä
    for index, row in production_df.iterrows():
        batch = str(row['Batch']).zfill(3)  # Esim. "001"
        treatment_program = str(row['Treatment_program']).zfill(3)  # Esim. "001" (aina Production.csv:stä)
        start_time = row['Start_time']
        
        # Etsi lähtöohjelmatiedosto Initialization-kansiosta
        source_program_file = os.path.join(output_dir, "initialization", f"Treatment_program_{treatment_program}.csv")
        
        if not os.path.exists(source_program_file):
            print(f"Ohjelmatiedostoa ei löydy: Treatment_program_{treatment_program}.csv")
            continue
        
        # Lue lähtöohjelma
        program_df = pd.read_csv(source_program_file)
        
        # Lisää CalcTime-sarake MinTime-arvoilla
        if 'CalcTime' not in program_df.columns:
            program_df['CalcTime'] = program_df['MinTime']
            print(f"Lisätty CalcTime-sarake (=MinTime) erän {batch} ohjelmaan")
        
        # Tallenna eräkohtainen ohjelmatiedosto oikealla nimellä
        output_file = os.path.join(original_programs_dir, f"Batch_{batch}_Treatment_program_{treatment_program}.csv")
        program_df.to_csv(output_file, index=False)
        print(f"Luotu: Batch_{batch}_Treatment_program_{treatment_program}.csv (ohjelma {treatment_program}, aloitus {start_time})")
    
    print("Tuotantoerien ohjelmatiedostot luotu!")
    return production_df

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = "output/test"
    process_production_batches(output_dir)
