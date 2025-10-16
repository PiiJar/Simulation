import subprocess
import sys
from init_output_directory import init_output_directory
from process_production import process_production_batches
from generate_matrix import generate_initial_matrix
from generate_transporter_tasks import generate_transporter_tasks
from resolve_station_conflicts import resolve_station_conflicts
from stretch_transporter_tasks import stretch_tasks
from update_programs import update_programs
from generate_matrix_updated import generate_updated_matrix
from update_production_schedule import update_production_schedule
from visualize_comparison import visualize_comparison
from generate_report import generate_simulation_report
from simulation_logger import init_logger

def run_pipeline():
    """Ajaa koko simulaatioputken Production.csv-pohjaisen mallin mukaan"""
    
    print("🚀 Aloitetaan Production.csv-pohjainen simulaatio...")
      # 1. Luo tuloskansio ja kopioi lähtötiedot
    output_dir = init_output_directory()
    print(f"📁 Tuloskansio: {output_dir}")
    
    # Initialize logging system
    logger = init_logger(output_dir)
    logger.log_phase("Production line simulation started")
    logger.log_phase(f"Output directory created: {output_dir}")
    
    try:
        # 2. Käsittele Production.csv ja luo eräkohtaiset ohjelmat
        print("\n📦 2. Käsitellään tuotantoerien ohjelmatiedostot...")
        logger.log_phase("Processing production batch programs")
        production_df = process_production_batches(output_dir)
        logger.log_data(f"Processed {len(production_df)} production batches")
          # 3. Luo alkuperäinen line-matriisi
        print("\n🧮 3. Luodaan alkuperäinen line-matriisi...")
        logger.log_phase("Generating initial line matrix")
        matrix = generate_initial_matrix(output_dir)
        logger.log_calc(f"Generated initial matrix with {len(matrix)} processing stages")
        
        # 4. Luo kuljetintehtävät
        print("\n🚚 4. Luodaan kuljetintehtävät...")
        logger.log_phase("Generating transporter tasks")
        tasks_raw, tasks_sorted = generate_transporter_tasks(output_dir)
        logger.log_calc(f"Generated {len(tasks_raw)} transporter tasks")
        
        # 5. Korjaa konfliktit
        print("\n⚡ 5. Korjataan asemakonflikeja...")
        logger.log_phase("Resolving station conflicts")
        tasks_resolved = resolve_station_conflicts(output_dir)
        logger.log_optimization("Station conflicts resolved")
        
        # 6. Venytä tehtäviä
        print("\n🔧 6. Venytetään tehtäviä siirtovälin mukaan...")
        logger.log_phase("Stretching tasks according to shift gap")
        tasks_stretched = stretch_tasks(output_dir)
        logger.log_optimization("Task stretching completed")          # 7. Päivitä ohjelmatiedostot
        print("\n🛠️ 7. Päivitetään ohjelmatiedostot...")
        logger.log_phase("Updating program files")
        update_programs(output_dir)
        logger.log_data("Program files updated with new CalcTime values")
        
        # 8. Päivitä tuotanto-aikataulu
        print("\n📅 8. Päivitetään tuotanto-aikataulu...")
        logger.log_phase("Updating production schedule")
        update_production_schedule(output_dir)
        logger.log_data("Production schedule updated with optimized start times")
        
        # 9. Luo päivitetty matriisi
        print("\n🧩 9. Luodaan päivitetty line-matriisi...")
        logger.log_phase("Generating updated line matrix")
        generate_updated_matrix(output_dir)
        logger.log_calc("Updated line matrix generated with optimized times")
          # 10. Visualisointi
        print("\n📈 10. Luodaan visualisointi...")
        logger.log_phase("Creating visualization")
        visualize_comparison(output_dir)
        logger.log_visualization("Comparison visualization created")
        
        # 11. Generoi PDF-raportti
        print("\n📊 11. Generoidaan PDF-raportti...")
        logger.log_phase("Generating PDF report")
        generate_simulation_report(output_dir)
        logger.log_io("PDF report generated successfully")        
        logger.log_phase("Simulation completed successfully")
        print(f"\n✅ Simulaatio valmis! Kaikki tulokset: {output_dir}")
        return True
        
    except Exception as e:
        logger.log_error(f"Simulation failed with error: {str(e)}")
        print(f"\n❌ VIRHE simulaatiossa: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_pipeline()
    if success:
        print("🎉 Kaikki vaiheet suoritettu onnistuneesti!")
    else:
        print("❌ Simulaatio epäonnistui.")
        sys.exit(1)
