#!/usr/bin/env python3
"""
Production.csv versiointi

Hallinnoi Production.csv:n eri versiot:
1. production_original.csv - alkuperäinen ennen mitään muutoksia
2. production_station_conflicts.csv - asemakonfliktien ratkaisu jälkeen  
3. Production.csv - lopullinen (stretch-vaiheen jälkeen)
"""

import pandas as pd
import os
import shutil
from datetime import datetime

def save_production_original(output_dir):
    """
    Tallentaa alkuperäisen Production.csv:n versiona production_original.csv
    
    Args:
        output_dir (str): Simulaatiokansion polku
    """
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    original_file = os.path.join(output_dir, "initialization", "production_original.csv")
    
    if not os.path.exists(production_file):
        raise FileNotFoundError(f"production.csv ei löydy: {production_file}")
    
    # Kopioi alkuperäinen tiedosto
    shutil.copy2(production_file, original_file)

def save_production_after_conflicts(output_dir):
    """
    Tallentaa Production.csv:n asemakonfliktien ratkaisun jälkeen
    
    Args:
        output_dir (str): Simulaatiokansion polku
    """
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    conflicts_file = os.path.join(output_dir, "initialization", "production_station_conflicts.csv")
    
    if not os.path.exists(production_file):
        raise FileNotFoundError(f"production.csv ei löydy: {production_file}")
    
    # Lataa tiedosto ja varmista että Start_time_seconds vastaa Start_station_check arvoa
    df = pd.read_csv(production_file)
    df["Start_time_seconds"] = pd.to_timedelta(df["Start_station_check"]).dt.total_seconds()
    
    # Tallenna korjattu versio
    df.to_csv(conflicts_file, index=False)
    
        # print(f" Tallennettu korjattu production_station_conflicts.csv ({len(df)} erää)")

def compare_production_versions(output_dir):
    """
    Vertailee Production.csv versioita ja tulostaa muutokset
    
    Args:
        output_dir (str): Simulaatiokansion polku
    """
    print("=" * 80)
    print("PRODUCTION.CSV VERSIOVERTAILU")
    print("=" * 80)
    
    original_file = os.path.join(output_dir, "initialization", "production_original.csv")
    conflicts_file = os.path.join(output_dir, "initialization", "production_station_conflicts.csv")
    current_file = os.path.join(output_dir, "initialization", "production.csv")
    
    versions = {
        "Alkuperäinen": original_file,
        "Konfliktien ratkaisu": conflicts_file,
        "Lopullinen": current_file
    }
    
    dataframes = {}
    
    # Lataa tiedostot
    for version_name, file_path in versions.items():
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            # Tukee sekä vanhaa (Start_time) että uutta (Start_stretch) rakennetta
            if "Start_stretch" in df.columns:
                df["Start_time_seconds"] = pd.to_timedelta(df["Start_stretch"]).dt.total_seconds()
            elif "Start_station_check" in df.columns:
                df["Start_time_seconds"] = pd.to_timedelta(df["Start_station_check"]).dt.total_seconds()
            elif "Start_time" in df.columns:
                df["Start_time_seconds"] = pd.to_timedelta(df["Start_time"]).dt.total_seconds()
            dataframes[version_name] = df
            print(f"📊 {version_name}: {len(df)} erää")
        else:
            print(f"⚠️  {version_name}: Tiedosto ei löydy ({os.path.basename(file_path)})")
    
    if len(dataframes) < 2:
        print("❌ Ei tarpeeksi versioita vertailuun")
        return
    
    print()
    print("🔍 AIKOJEN VERTAILU:")
    print("-" * 80)
    print(f"{'Erä':<5} {'Alkup.(s)':<10} {'Konfliktit(s)':<14} {'Lopull.(s)':<12} {'Konfl-Alk':<10} {'Lop-Konfl':<10}")
    print("-" * 80)
    
    # Vertaile erä kerrallaan
    for version_name, df in dataframes.items():
        if version_name == "Alkuperäinen":
            reference_df = df
            break
    
    for _, row in reference_df.iterrows():
        batch_id = int(row["Batch"])
        original_time = float(row["Start_time_seconds"])
        
        # Etsi samat erät muista versioista
        conflicts_time = None
        final_time = None
        
        if "Konfliktien ratkaisu" in dataframes:
            conflicts_rows = dataframes["Konfliktien ratkaisu"][dataframes["Konfliktien ratkaisu"]["Batch"] == batch_id]
            if len(conflicts_rows) > 0:
                conflicts_time = float(conflicts_rows.iloc[0]["Start_time_seconds"])
        
        if "Lopullinen" in dataframes:
            final_rows = dataframes["Lopullinen"][dataframes["Lopullinen"]["Batch"] == batch_id]
            if len(final_rows) > 0:
                final_time = float(final_rows.iloc[0]["Start_time_seconds"])
        
        # Laske erotukset
        conflicts_diff = conflicts_time - original_time if conflicts_time is not None else None
        final_diff = final_time - conflicts_time if (final_time is not None and conflicts_time is not None) else None
        
        # Formatoi tulostus
        conflicts_str = f"{conflicts_time:.1f}" if conflicts_time is not None else "N/A"
        final_str = f"{final_time:.1f}" if final_time is not None else "N/A"
        conflicts_diff_str = f"{conflicts_diff:.1f}" if conflicts_diff is not None else "N/A"
        final_diff_str = f"{final_diff:.1f}" if final_diff is not None else "N/A"
        
        print(f"{batch_id:<5} {original_time:<10.1f} {conflicts_str:<14} {final_str:<12} {conflicts_diff_str:<10} {final_diff_str:<10}")
    
    print("-" * 80)
    print("=" * 80)

def main():
    """Testifunktio"""
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        # Etsi uusin output-kansio
        output_base = "output"
        if not os.path.exists(output_base):
            print("❌ VIRHE: output-kansiota ei löydy")
            sys.exit(1)
        
        subdirs = [d for d in os.listdir(output_base) 
                  if os.path.isdir(os.path.join(output_base, d)) and "-" in d]
        
        if not subdirs:
            print("❌ VIRHE: Ei löydy timestampattuja kansioita")
            sys.exit(1)
        
        latest_dir = sorted(subdirs)[-1]
        output_dir = os.path.join(output_base, latest_dir)
    
    print(f"📁 Käytetään kansiota: {output_dir}")
    compare_production_versions(output_dir)

if __name__ == "__main__":
    main()
