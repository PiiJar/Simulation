# Tämä tiedosto on siirretty ja nimetty uudelleen.
# Uusi nimi: generate_transporter_tasks_original.py
# Päivitä kaikki importit ja funktiokutsut käyttämään uutta nimeä.

"""
Fysiikkapohjainen siirtoajan laskenta nostintehtäville.

Korvaa vakioarvoisen 40 sekunnin siirtoajan realistisella
fysiikan mukaisella laskennalla, joka huomioi:
- Etäisyyden (kiihtyvyys, nopeus, hidastus)
- Korkeuden muutoksen (ylös/alas liikuttaminen)
- Nostimen kiihtyvyydet ja maksimifresit
- Parametrit luetaan Initialization/Transporters.csv tiedostosta
"""

import math
import pandas as pd
import os

def load_transporter_parameters(transporter_id=1):
    """Lataa nostimen parametrit Transporters.csv tiedostosta"""
    try:
        transporters_file = os.path.join("initialization", "transporters.csv")
        df = pd.read_csv(transporters_file)
        
        # Etsi oikea nostin
        transporter = df[df["Transporter_id"] == transporter_id]
        if transporter.empty:
            print(f"⚠️  Nostinta {transporter_id} ei löydy, käytetään oletusarvoja")
            return get_default_parameters()
        
        params = transporter.iloc[0]
        
        return {
            # Vaakasuuntainen liike (muunnetaan mm/s -> m/s)
            "max_speed_horizontal": params["Max_speed (mm/s)"] / 1000.0,  # mm/s -> m/s
            "acceleration_time": params["Acceleration_time (s)"],
            "deceleration_time": params["Deceleration_time (s)"],
            
            # Pystysuuntainen liike (Z-akseli)
            "z_total_distance": params["Z_total_distance (mm)"] / 1000.0,  # mm -> m
            "z_slow_distance_dry": params["Z_slow_distance_dry (mm)"] / 1000.0,  # mm -> m
            "z_slow_distance_wet": params["Z_slow_distance_wet (mm)"] / 1000.0,  # mm -> m
            "z_slow_end_distance": params["Z_slow_end_distance (mm)"] / 1000.0,  # mm -> m
            "z_fast_speed": params["Z_fast_speed (mm/s)"] / 1000.0,  # mm/s -> m/s
            "z_slow_speed": params["Z_slow_speed (mm/s)"] / 1000.0,  # mm/s -> m/s
        }
        
    except Exception as e:
        print(f"⚠️  Virhe Transporters.csv latauksessa: {e}")
        return get_default_parameters()

def get_default_parameters():
    """Oletusparametrit jos tiedostoa ei löydy"""
    return {
        "max_speed_horizontal": 0.3,  # 300 mm/s -> 0.3 m/s
        "acceleration_time": 2.0,
        "deceleration_time": 2.0,
        "z_total_distance": 2.0,  # 2000 mm -> 2.0 m
        "z_slow_distance_dry": 0.3,  # 300 mm -> 0.3 m
        "z_slow_distance_wet": 1.5,  # 1500 mm -> 1.5 m
        "z_slow_end_distance": 0.15,  # 150 mm -> 0.15 m
        "z_fast_speed": 0.2,  # 200 mm/s -> 0.2 m/s
        "z_slow_speed": 0.1,  # 100 mm/s -> 0.1 m/s
    }

def load_station_info(station_number):
    """Lataa aseman tiedot Stations.csv:stä"""
    try:
        stations_file = os.path.join("initialization", "stations.csv")
        df = pd.read_csv(stations_file)
        
        station_data = df[df["Number"] == station_number]
        if station_data.empty:
            print(f"⚠️  Asemaa {station_number} ei löydy")
            return {"device_delay": 0.0, "station_type": 1, "dropping_time": 0.0}  # Oletus: märkä asema
        
        station = station_data.iloc[0]
        return {
            "device_delay": station["Device_delay"],
            "station_type": station["Station_type"],  # 0=kuiva, 1=märkä
            "dropping_time": station["Dropping_Time"]
        }
        
    except Exception as e:
        print(f"⚠️  Virhe Stations.csv latauksessa: {e}")
        return {"device_delay": 0.0, "station_type": 1, "dropping_time": 0.0}

def calculate_vertical_lift(station_number, transporter_id=1):
    """
    Laskee nostooperaation ajan (vaihe 2).
    
    Args:
        station_number: Aseman numero jolta nostetaan
        transporter_id: Nostimen tunniste
        
    Returns:
        float: Nostoaika sekunneissa
    """
    params = load_transporter_parameters(transporter_id)
    station_info = load_station_info(station_number)
    
    # 1. Device_delay
    device_delay = station_info["device_delay"]
    
    # 2. Asematyypin mukainen hitaan nopeuden matka
    if station_info["station_type"] == 0:  # Kuiva asema
        slow_distance = params["z_slow_distance_dry"]
    else:  # Märkä asema
        slow_distance = params["z_slow_distance_wet"]
    
    # 3. Nopean nopeuden matka (kokonaismatka - hitaat matkat)
    fast_distance = params["z_total_distance"] - slow_distance - params["z_slow_end_distance"]
    
    # 4. Aikojen laskenta
    slow_start_time = slow_distance / params["z_slow_speed"] if params["z_slow_speed"] > 0 else 0
    fast_time = fast_distance / params["z_fast_speed"] if params["z_fast_speed"] > 0 else 0
    slow_end_time = params["z_slow_end_distance"] / params["z_slow_speed"] if params["z_slow_speed"] > 0 else 0
      # 5. Asemakohtainen valutusaika (Dropping_Time)
    draining_time = station_info["dropping_time"]
    
    total_time = device_delay + slow_start_time + fast_time + slow_end_time + draining_time
    return total_time

def calculate_vertical_sink(station_number, transporter_id=1):
    """
    Laskee laskuoperaation ajan (vaihe 4).
    Sisältää kohde-aseman Device_delay + Z-liike alas (EI valutusta).
    
    Args:
        station_number: Aseman numero jolle lasketaan
        transporter_id: Nostimen tunniste
        
    Returns:
        float: Laskuaika sekunneissa
    """
    params = load_transporter_parameters(transporter_id)
    station_info = load_station_info(station_number)
    
    # 1. Kohde-aseman Device_delay
    device_delay = station_info["device_delay"]
    
    # 2. Nopean nopeuden matka (kokonaismatka - hitaat matkat lopussa)
    if station_info["station_type"] == 0:  # Kuiva asema
        slow_distance = params["z_slow_distance_dry"]
    else:  # Märkä asema
        slow_distance = params["z_slow_distance_wet"]
    
    fast_distance = params["z_total_distance"] - slow_distance
    
    # 3. Aikojen laskenta (EI valutusta)
    fast_time = fast_distance / params["z_fast_speed"] if params["z_fast_speed"] > 0 else 0
    slow_time = slow_distance / params["z_slow_speed"] if params["z_slow_speed"] > 0 else 0
    
    total_time = device_delay + fast_time + slow_time
    return total_time

def complete_transfer_task(from_x, to_x, from_station=None, to_station=None, transporter_id=1, return_phases=False):
    """
    Laskee täydellisen siirtoajan nostimelle fysiikkaa hyödyntäen.
    
    Sisältää kaikki nostinoperaation vaiheet:
    1. Nosto ylös lähtöasemalta (Z-akseli)
    2. Vaakasuuntainen siirto (X-akseli)
    3. Lasku alas kohdeasemalle (Z-akseli)
    4. Asettumisaika (Phase_4, tällä hetkellä 0)
    
    Args:
        from_x, to_x: X-sijainnit millimetreinä
        from_station, to_station: Asemien numerot (Z-liikkeen laskentaa varten)
        transporter_id: Nostimen tunniste
        return_phases: Jos True, palauttaa (total_time, phase_1, phase_2, phase_3, phase_4)
    
    Returns:
        float tai tuple: kokonaissiirtoaika sekunneissa tai vaiheajat
    """
    
    # Lataa nostimen parametrit
    params = load_transporter_parameters(transporter_id)
      # 1. NOSTO YLÖS (Z-akseli) - PHASE_1
    if from_station is not None:
        phase_1 = calculate_vertical_lift(from_station, transporter_id)
    else:
        # Oletusarvo märkälle asemalle jos asemaa ei ole annettu
        phase_1 = 2.0  # sekuntia

    # 2. VAAKASUUNTAINEN SIIRTO (X-akseli) - PHASE_2
    distance = abs(to_x - from_x) / 1000.0  # mm -> m
    
    if distance <= 0:
        phase_2 = 0
    else:
        max_speed = params["max_speed_horizontal"]
        accel_time = params["acceleration_time"]
        decel_time = params["deceleration_time"]
        
        # Lasketaan kiihtyvyys nopeudesta ja ajasta
        acceleration = max_speed / accel_time if accel_time > 0 else 1.0
        
        # Kiihdytys- ja hidastusmatkat
        accel_distance = 0.5 * acceleration * accel_time * accel_time
        decel_distance = 0.5 * acceleration * decel_time * decel_time
        
        if distance <= (accel_distance + decel_distance):
            # Lyhyt matka: ei ehdi täyteen vauhtiin
            # Yksinkertaistettu: oletetaan symmetrinen kiihdytys/hidastus
            total_accel_time = math.sqrt(2 * distance / acceleration)
            phase_2 = total_accel_time
        else:
            # Pitkä matka: kiihdytys + tasainen + hidastus
            constant_distance = distance - accel_distance - decel_distance
            constant_time = constant_distance / max_speed
            phase_2 = accel_time + constant_time + decel_time

    # 3. LASKU ALAS (Z-akseli) - PHASE_3
    if to_station is not None:
        phase_3 = calculate_vertical_sink(to_station, transporter_id)
    else:
        # Oletusarvo märkälle asemalle jos asemaa ei ole annettu
        phase_3 = 1.5  # sekuntia

    # 4. ASETTUMISAIKA (Phase_4) - tällä hetkellä ei käytetä
    phase_4 = 0.0  # Voidaan lisätä myöhemmin tarvittaessa

    # KOKONAISAIKA: Nosto + Siirto + Lasku + Asettuminen (tapahtuvat peräkkäin)
    total_time = phase_1 + phase_2 + phase_3 + phase_4
    
    if return_phases:
        return total_time, phase_1, phase_2, phase_3, phase_4
    else:
        return total_time
