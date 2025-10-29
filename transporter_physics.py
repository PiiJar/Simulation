# Tämä tiedosto sisältää kaikki transporter-liikkeiden fysiikkalogiikan funktiot
# (aiemmin hoist_physics.py)

import numpy as np

def calculate_physics_transfer_time(from_station_row, to_station_row, transporter_row):
    """
    Laskee siirtoajan asemien välillä fysiikkapohjaisesti.
    from_station_row, to_station_row: pandas DataFrame -rivit, joissa on X-koordinaatit
    transporter_row: pandas DataFrame -rivi, jossa on transporter-parametrit
    """
    x1 = float(from_station_row['X Position'])
    x2 = float(to_station_row['X Position'])
    distance = abs(x2 - x1)
    # Lue oikeat sarakkeet Transporters.csv:n otsikon mukaan
    max_speed = float(transporter_row.get('Max_speed (mm/s)', 0))
    acc_time = float(transporter_row.get('Acceleration_time (s)', 0))
    dec_time = float(transporter_row.get('Deceleration_time (s)', 0))
    if distance == 0 or max_speed == 0 or acc_time == 0 or dec_time == 0:
        return 0.0
    # Kiihtyvyys ja hidastus (mm/s^2)
    accel = max_speed / acc_time
    decel = max_speed / dec_time
    t_accel = max_speed / accel
    t_decel = max_speed / decel
    s_accel = 0.5 * accel * t_accel ** 2
    s_decel = 0.5 * decel * t_decel ** 2
    if distance < s_accel + s_decel:
        # Kolmion muotoinen nopeusprofiili (ei saavuteta maksiminopeutta)
        # Oikea kaava: t_accel = sqrt(distance / accel), t_decel = sqrt(distance / decel)
        t_accel = np.sqrt(distance / accel)
        t_decel = np.sqrt(distance / decel)
        return round(t_accel + t_decel, 1)
    else:
        # Trapezoidinen profiili
        s_const = distance - s_accel - s_decel
        t_const = s_const / max_speed
        return round(t_accel + t_const + t_decel, 1)

def calculate_lift_time(station_row, transporter_row):
    device_delay = float(station_row.get('Device_delay', 0))
    dropping_time = float(station_row.get('Dropping_Time', 0))
    z_total = float(transporter_row.get('Z_total_distance (mm)', 0))
    z_slow = float(transporter_row.get('Z_slow_distance_wet (mm)', 0))
    z_slow_end = float(transporter_row.get('Z_slow_end_distance (mm)', 0))
    z_slow_speed = float(transporter_row.get('Z_slow_speed (mm/s)', 1))
    z_fast_speed = float(transporter_row.get('Z_fast_speed (mm/s)', 1))
    slow_up_1 = z_slow / z_slow_speed
    fast_up = (z_total - z_slow - z_slow_end) / z_fast_speed
    slow_up_2 = z_slow_end / z_slow_speed
    lift_time = device_delay + slow_up_1 + fast_up + slow_up_2 + dropping_time
    return round(lift_time, 1)

def calculate_sink_time(station_row, transporter_row):
    device_delay = float(station_row.get('Device_delay', 0))
    z_total = float(transporter_row.get('Z_total_distance (mm)', 0))
    z_slow = float(transporter_row.get('Z_slow_distance_wet (mm)', 0))
    z_slow_speed = float(transporter_row.get('Z_slow_speed (mm/s)', 1))
    z_fast_speed = float(transporter_row.get('Z_fast_speed (mm/s)', 1))
    fast_down = (z_total - z_slow) / z_fast_speed
    slow_down = z_slow / z_slow_speed
    sink_time = device_delay + fast_down + slow_down
    return round(sink_time, 1)
