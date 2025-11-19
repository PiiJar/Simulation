#!/usr/bin/env python3
"""
Ajaa pattern mining -analyysin viimeisimmän simulaation tuloksille.
Käyttö: python run_pattern_mining_standalone.py
"""

import os
import sys
from pathlib import Path

def find_latest_output():
    """Etsi viimeisin output-kansio."""
    output_base = Path("output")
    if not output_base.exists():
        print("❌ output-kansiota ei löydy")
        return None
    
    # Etsi kaikki simulaatiokansiot
    dirs = sorted(output_base.glob("900135*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dirs:
        print("❌ Ei simulaatiokansiota output-hakemistossa")
        return None
    
    latest = dirs[0]
    print(f"📁 Käytetään kansiota: {latest.name}")
    return str(latest)

def main():
    # Etsi viimeisin output
    output_dir = find_latest_output()
    if not output_dir:
        sys.exit(1)
    
    # Tarkista että cp_sat_transporter_schedule.csv löytyy
    schedule_file = os.path.join(output_dir, "cp_sat", "cp_sat_transporter_schedule.csv")
    if not os.path.exists(schedule_file):
        print(f"❌ Ei löydy: {schedule_file}")
        sys.exit(1)
    
    print(f"✓ Löytyi: {schedule_file}")
    print()
    
    # Importtaa pattern mining ja aja se
    try:
        from pattern_mining import find_cyclic_patterns
        
        print("🔍 Ajetaan pattern mining...")
        print("=" * 70)
        print()
        
        patterns = find_cyclic_patterns(output_dir, max_cycle_duration=7200, require_complete=True)
        
        print()
        print("=" * 70)
        
        if patterns and len(patterns) > 0:
            print(f"✓ LÖYTYI {len(patterns)} PATTERNIA!")
            for i, p in enumerate(patterns):
                print(f"\nPattern {i+1}:")
                print(f"  Start time: {p.start_time}s")
                print(f"  End time: {p.end_time}s")
                print(f"  Duration: {p.duration}s")
                print(f"  Stages covered: {p.stages_covered}")
                print(f"  Complete: {p.is_complete}")
                print(f"  Num transporters: {len(p.transporter_sequences)}")
                for t_id, seq in p.transporter_sequences.items():
                    print(f"    T{t_id}: {len(seq)} tasks, stages: {[s[0] for s in seq[:10]]}" + ("..." if len(seq) > 10 else ""))
        else:
            print("❌ PATTERNIA EI LÖYTYNYT")
            print("  (find_cyclic_patterns palautti tyhjän listan)")
            
        return 0
        
    except ImportError as e:
        print(f"❌ Import-virhe: {e}")
        print()
        print("Tarkista että pattern_mining.py löytyy samasta hakemistosta.")
        return 1
    except Exception as e:
        print(f"❌ Virhe pattern mining -analyysissä: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
