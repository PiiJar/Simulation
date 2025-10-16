"""
Pullonkaulojen kirjausjärjestelmä
==================================

Kirjaa havaittuja pullonkauloja simuloinnin aikana, erityisesti:
- Asemakonflikti-tilanteet
- Production-tiedoston muutokset
- Aikataulusiirrot

Tallentaa tiedot CSV-muodossa analysis-kansioon.
"""

import pandas as pd
import os
from datetime import datetime
from simulation_logger import get_logger

class BottleneckLogger:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.analysis_dir = os.path.join(output_dir, "Analysis")
        os.makedirs(self.analysis_dir, exist_ok=True)
        
        # Pullonkaulojen lista
        self.bottlenecks = []
        
        self.logger = get_logger()
        if self.logger:
            self.logger.log("STEP", "BOTTLENECK LOGGER INITIALIZED")
    
    def log_station_conflict(self, station, batch1, batch2, conflict_time, resolution_action, time_shift=0):
        """
        Kirjaa asemakonfliktia ja sen ratkaisua
        
        Args:
            station (int): Konfliktin asema
            batch1 (int): Ensimmäinen erä konfliktissa
            batch2 (int): Toinen erä konfliktissa
            conflict_time (float): Aika jolloin konflikti havaittiin
            resolution_action (str): Mitä tehtiin konfliktin ratkaisemiseksi
            time_shift (float): Kuinka paljon aikaa siirrettiin (sekunneissa)
        """
        # Käsittele batch-arvot - voivat olla numeroita tai "multiple" stringi
        def safe_batch_conversion(batch_val):
            try:
                return int(batch_val)
            except (ValueError, TypeError):
                return str(batch_val)
        
        bottleneck = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Type': 'Station_Conflict',
            'Station': int(station),
            'Batch_1': safe_batch_conversion(batch1),
            'Batch_2': safe_batch_conversion(batch2),
            'Conflict_Time': float(conflict_time),
            'Resolution_Action': str(resolution_action),
            'Time_Shift_Seconds': float(time_shift),
            'Description': f"Asema {station} konfliktia erät {batch1} ja {batch2}, ratkaisu: {resolution_action}"
        }
        
        self.bottlenecks.append(bottleneck)
        
        if self.logger:
            self.logger.log("BOTTLENECK", 
                f"Station {station} conflict: Batch {batch1} vs {batch2} at {conflict_time:.1f}s, "
                f"resolution: {resolution_action}, shift: {time_shift:.1f}s")
    
    def log_production_adjustment(self, batch, treatment_program, original_start, new_start, reason):
        """
        Kirjaa Production.csv:n aloitusajan muutosta
        
        Args:
            batch (int): Erä
            treatment_program (int): Käsittelyohjelma
            original_start (float): Alkuperäinen aloitusaika
            new_start (float): Uusi aloitusaika
            reason (str): Syy muutokseen
        """
        time_shift = new_start - original_start
        
        bottleneck = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Type': 'Production_Adjustment',
            'Station': 0,  # Ei liity tiettyyn asemaan
            'Batch_1': int(batch),
            'Batch_2': 0,  # Ei toista erää
            'Conflict_Time': float(original_start),
            'Resolution_Action': f"Start_time: {original_start:.1f}s -> {new_start:.1f}s",
            'Time_Shift_Seconds': float(time_shift),
            'Description': f"Erä {batch} program {treatment_program} aloitusaika muutettu: {reason}"
        }
        
        self.bottlenecks.append(bottleneck)
        
        if self.logger:
            self.logger.log("BOTTLENECK", 
                f"Production adjustment: Batch {batch} program {treatment_program}, "
                f"start {original_start:.1f}s -> {new_start:.1f}s, reason: {reason}")
    
    def log_transporter_conflict(self, transporter_id, batch1, batch2, conflict_start, conflict_end, resolution_action, time_shift=0):
        """
        Kirjaa nostinkonfliktia ja sen ratkaisua
        
        Args:
            transporter_id (int): Konfliktin nostin
            batch1 (int): Ensimmäinen erä konfliktissa
            batch2 (int): Toinen erä konfliktissa
            conflict_start (float): Konfliktin alkuaika
            conflict_end (float): Konfliktin loppuaika
            resolution_action (str): Mitä tehtiin konfliktin ratkaisemiseksi
            time_shift (float): Kuinka paljon aikaa siirrettiin (sekunneissa)
        """
        conflict_duration = conflict_end - conflict_start
        
        # Käsittele batch-arvot - voivat olla numeroita tai "multiple" stringi
        def safe_batch_conversion(batch_val):
            try:
                return int(batch_val)
            except (ValueError, TypeError):
                return str(batch_val)
        
        bottleneck = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Type': 'Transporter_Conflict',
            'Station': int(transporter_id),  # Käytetään Station-kenttää nostimelle
            'Batch_1': safe_batch_conversion(batch1),
            'Batch_2': safe_batch_conversion(batch2),
            'Conflict_Time': float(conflict_start),
            'Resolution_Action': str(resolution_action),
            'Time_Shift_Seconds': float(time_shift),
            'Description': f"Nostin {transporter_id} konfliktia erät {batch1} ja {batch2}, kesto: {conflict_duration:.1f}s, ratkaisu: {resolution_action}"
        }
        
        self.bottlenecks.append(bottleneck)
        
        if self.logger:
            self.logger.log("BOTTLENECK", 
                f"Transporter {transporter_id} conflict: Batch {batch1} vs {batch2} at {conflict_start:.1f}s-{conflict_end:.1f}s, "
                f"resolution: {resolution_action}, shift: {time_shift:.1f}s")

    def log_capacity_bottleneck(self, station, queue_length, wait_time, description):
        """
        Kirjaa kapasiteetin pullonkaulaa
        
        Args:
            station (int): Pullonkaulan asema
            queue_length (int): Jonon pituus
            wait_time (float): Odotusaika
            description (str): Kuvaus tilanteesta
        """
        bottleneck = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Type': 'Capacity_Bottleneck',
            'Station': int(station),
            'Batch_1': 0,
            'Batch_2': 0,
            'Conflict_Time': 0,
            'Resolution_Action': f"Queue length: {queue_length}, wait: {wait_time:.1f}s",
            'Time_Shift_Seconds': float(wait_time),
            'Description': f"Asema {station} kapasiteetti pullonkaula: {description}"
        }
        
        self.bottlenecks.append(bottleneck)
        
        if self.logger:
            self.logger.log("BOTTLENECK", 
                f"Capacity bottleneck at station {station}: queue {queue_length}, "
                f"wait {wait_time:.1f}s - {description}")
    
    def save_bottlenecks(self):
        """
        Tallentaa pullonkaulat CSV-tiedostoon
        """
        if not self.bottlenecks:
            if self.logger:
                self.logger.log("INFO", "No bottlenecks detected - simulation runs smoothly")
            return
        
        # Luo DataFrame
        df = pd.DataFrame(self.bottlenecks)
        
        # Järjestä aikajärjestykseen
        df = df.sort_values('Timestamp').reset_index(drop=True)
        
        # Tallenna
        bottlenecks_file = os.path.join(self.analysis_dir, "bottlenecks_detected.csv")
        df.to_csv(bottlenecks_file, index=False)
        
        if self.logger:
            self.logger.log("SAVE", f"Bottlenecks saved: {os.path.basename(bottlenecks_file)} ({len(df)} entries)")
        
        # Luo myös yhteenveto
        self._create_summary()
        
        return bottlenecks_file
    
    def _create_summary(self):
        """
        Luo yhteenveto pullonkauloista
        """
        if not self.bottlenecks:
            return
        
        df = pd.DataFrame(self.bottlenecks)
        
        # Ryhmitä tyypin mukaan
        summary = []
        
        for bottleneck_type in df['Type'].unique():
            type_df = df[df['Type'] == bottleneck_type]
            
            summary.append({
                'Bottleneck_Type': bottleneck_type,
                'Count': len(type_df),
                'Total_Time_Shift': type_df['Time_Shift_Seconds'].sum(),
                'Average_Time_Shift': type_df['Time_Shift_Seconds'].mean(),
                'Max_Time_Shift': type_df['Time_Shift_Seconds'].max(),
                'Most_Affected_Station': type_df['Station'].mode().iloc[0] if len(type_df['Station'].mode()) > 0 else 0
            })
        
        summary_df = pd.DataFrame(summary)
        summary_file = os.path.join(self.analysis_dir, "bottlenecks_summary.csv")
        summary_df.to_csv(summary_file, index=False)
        
        if self.logger:
            self.logger.log("SAVE", f"Bottleneck summary saved: {os.path.basename(summary_file)}")

# Globaali instanssi
_bottleneck_logger = None

def init_bottleneck_logger(output_dir):
    """
    Alustaa pullonkaula-loggerin
    """
    global _bottleneck_logger
    _bottleneck_logger = BottleneckLogger(output_dir)
    return _bottleneck_logger

def get_bottleneck_logger():
    """
    Palauttaa pullonkaula-loggerin instanssin
    """
    global _bottleneck_logger
    return _bottleneck_logger

def log_station_conflict(station, batch1, batch2, conflict_time, resolution_action, time_shift=0):
    """
    Kirjaa asemakonfliktia (pikanäppäin)
    """
    logger = get_bottleneck_logger()
    if logger:
        logger.log_station_conflict(station, batch1, batch2, conflict_time, resolution_action, time_shift)

def log_transporter_conflict(transporter_id, batch1, batch2, conflict_start, conflict_end, resolution_action, time_shift=0):
    """
    Kirjaa nostinkonfliktia (pikanäppäin)
    """
    logger = get_bottleneck_logger()
    if logger:
        logger.log_transporter_conflict(transporter_id, batch1, batch2, conflict_start, conflict_end, resolution_action, time_shift)

def log_production_adjustment(batch, treatment_program, original_start, new_start, reason):
    """
    Kirjaa Production.csv:n muutosta (pikanäppäin)
    """
    logger = get_bottleneck_logger()
    if logger:
        logger.log_production_adjustment(batch, treatment_program, original_start, new_start, reason)

def save_bottlenecks():
    """
    Tallentaa pullonkaulat (pikanäppäin)
    """
    logger = get_bottleneck_logger()
    if logger:
        return logger.save_bottlenecks()
    return None
