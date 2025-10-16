"""
Yhteinen fysiikkalogiikka transporter (nostin) siirto-, nosto- ja laskuaikojen laskentaan.
Käytetään kaikissa tuotantolinjan vaiheissa, jotta tulokset ovat yhtenevät.
"""
import numpy as np

TRANSFER_TIME_DEFAULT = 40  # Oletussiirtoaika, jos laskenta epäonnistuu

def calculate_physics_transfer_time(from_x, to_x, max_speed, acc_time, dec_time):
    """
    Laskee siirtoajan kahden aseman välillä fysiikkapohjaisesti.
    - from_x, to_x: asemien X-koordinaatit
    - max_speed: transporter-maksimi X-nopeus (mm/s)
    - acc_time: kiihtyvyyteen käytetty aika (s)
    - dec_time: hidastuvuuteen käytetty aika (s)
    Palauttaa siirtoaika sekunteina.
    """
    try:
        distance = abs(to_x - from_x)
        if distance == 0:
            return 0.0
        acceleration = max_speed / acc_time if acc_time > 0 else 0
        deceleration = max_speed / dec_time if dec_time > 0 else 0
        d_accel = 0.5 * acceleration * acc_time**2
        d_decel = 0.5 * deceleration * dec_time**2
        if d_accel + d_decel >= distance:
            # Lyhyt matka: ei ehdi saavuttaa maksiminopeutta
            combined_factor = 0.5 * acceleration * (1 + (acc_time/dec_time)) if dec_time > 0 else 0.5 * acceleration
            t_accel_actual = np.sqrt(distance / combined_factor) if combined_factor > 0 else 0
            t_decel_actual = (acc_time / dec_time) * t_accel_actual if dec_time > 0 else 0
            t_constant = 0
        else:
            t_accel_actual = acc_time
            t_decel_actual = dec_time
            d_accel_actual = d_accel
            d_decel_actual = d_decel
            d_constant = distance - d_accel_actual - d_decel_actual
            t_constant = d_constant / max_speed if max_speed > 0 else 0
        total_time = t_accel_actual + t_constant + t_decel_actual
        return total_time
    except Exception:
        return TRANSFER_TIME_DEFAULT

def calculate_lift_time(station_row, transporter_row):
    """
    Laskee nostoaika (ylös) annetulla asemalla ja transporter-parametreilla.
    """
    device_delay = float(station_row.get('Device_delay', 0))
    dropping_time = float(station_row.get('Dropping_Time', 0))
    z_total = float(transporter_row.get('Z_total_distance (mm)', 0))
    z_slow = float(transporter_row.get('Z_slow_distance_wet (mm)', 0))
    z_slow_end = float(transporter_row.get('Z_slow_end_distance (mm)', 0))
    z_slow_speed = float(transporter_row.get('Z_slow_speed (mm/s)', 1))
    z_fast_speed = float(transporter_row.get('Z_fast_speed (mm/s)', 1))
    slow_up_1 = z_slow / z_slow_speed if z_slow_speed > 0 else 0
    fast_up = (z_total - z_slow - z_slow_end) / z_fast_speed if z_fast_speed > 0 else 0
    slow_up_2 = z_slow_end / z_slow_speed if z_slow_speed > 0 else 0
    lift_time = device_delay + slow_up_1 + fast_up + slow_up_2 + dropping_time
    return lift_time

def calculate_sink_time(station_row, transporter_row):
    """
    Laskee laskuaika (alas) annetulla asemalla ja transporter-parametreilla.
    """
    device_delay = float(station_row.get('Device_delay', 0))
    z_total = float(transporter_row.get('Z_total_distance (mm)', 0))
    z_slow = float(transporter_row.get('Z_slow_distance_wet (mm)', 0))
    z_slow_speed = float(transporter_row.get('Z_slow_speed (mm/s)', 1))
    z_fast_speed = float(transporter_row.get('Z_fast_speed (mm/s)', 1))
    fast_down = (z_total - z_slow) / z_fast_speed if z_fast_speed > 0 else 0
    slow_down = z_slow / z_slow_speed if z_slow_speed > 0 else 0
    sink_time = device_delay + fast_down + slow_down
    return sink_time
