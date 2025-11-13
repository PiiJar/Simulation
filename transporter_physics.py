# Tämä tiedosto sisältää kaikki transporter-liikkeiden fysiikkalogiikan funktiot
# (aiemmin hoist_physics.py)

import numpy as np

def _num(val, default=0.0):
    """Convert to float and coalesce NaN/None/invalid to default."""
    try:
        x = float(val)
        if np.isnan(x):
            return float(default)
        return x
    except Exception:
        return float(default)

def calculate_physics_transfer_time(from_station_row, to_station_row, transporter_row):
    """
    Laskee siirtoajan asemien välillä fysiikkapohjaisesti.
    Tukee sekä 2D (X) että 3D (X+Y) liikettä.
    from_station_row, to_station_row: pandas DataFrame -rivit, joissa on X ja Y koordinaatit
    transporter_row: pandas DataFrame -rivi, jossa on transporter-parametrit
    """
    x1 = _num(from_station_row.get('X Position'), 0.0)
    x2 = _num(to_station_row.get('X Position'), 0.0)
    y1 = _num(from_station_row.get('Y Position'), 0.0)
    y2 = _num(to_station_row.get('Y Position'), 0.0)
    
    x_distance = abs(x2 - x1)
    y_distance = abs(y2 - y1)
    
    # X-suunnan aika
    x_max_speed = _num(transporter_row.get('X_max_speed (mm/s)'), 0.0)
    x_acc_time = _num(transporter_row.get('X_acceleration_time (s)'), 0.0)
    x_dec_time = _num(transporter_row.get('X_deceleration_time (s)'), 0.0)
    
    x_time = 0.0
    if x_distance > 0 and x_max_speed > 0 and x_acc_time > 0 and x_dec_time > 0:
        x_accel = x_max_speed / x_acc_time
        x_decel = x_max_speed / x_dec_time
        t_accel = x_max_speed / x_accel
        t_decel = x_max_speed / x_decel
        s_accel = 0.5 * x_accel * t_accel ** 2
        s_decel = 0.5 * x_decel * t_decel ** 2
        
        if x_distance < s_accel + s_decel:
            # Kolmion muotoinen nopeusprofiili
            t_accel = np.sqrt(x_distance / x_accel)
            t_decel = np.sqrt(x_distance / x_decel)
            x_time = t_accel + t_decel
        else:
            # Trapezoidinen profiili
            s_const = x_distance - s_accel - s_decel
            t_const = s_const / x_max_speed
            x_time = t_accel + t_const + t_decel
    
    # Y-suunnan aika (vain 3D-nostimille)
    y_max_speed = _num(transporter_row.get('Y_max_speed (mm/s)'), 0.0)
    y_acc_time = _num(transporter_row.get('Y_acceleration_time (s)'), 0.0)
    y_dec_time = _num(transporter_row.get('Y_deceleration_time (s)'), 0.0)
    
    y_time = 0.0
    if y_distance > 0 and y_max_speed > 0 and y_acc_time > 0 and y_dec_time > 0:
        y_accel = y_max_speed / y_acc_time
        y_decel = y_max_speed / y_dec_time
        t_accel = y_max_speed / y_accel
        t_decel = y_max_speed / y_decel
        s_accel = 0.5 * y_accel * t_accel ** 2
        s_decel = 0.5 * y_decel * t_decel ** 2
        
        if y_distance < s_accel + s_decel:
            # Kolmion muotoinen nopeusprofiili
            t_accel = np.sqrt(y_distance / y_accel)
            t_decel = np.sqrt(y_distance / y_decel)
            y_time = t_accel + t_decel
        else:
            # Trapezoidinen profiili
            s_const = y_distance - s_accel - s_decel
            t_const = s_const / y_max_speed
            y_time = t_accel + t_const + t_decel
    
    # X ja Y liikkeet tapahtuvat samanaikaisesti, joten kokonaisaika on pidempi kahdesta
    total_time = max(x_time, y_time)
    return round(total_time, 1)

def calculate_lift_time(station_row, transporter_row):
    """Nostoajan arviointi.
    Periaate:
    - Käytä kuivaa hidasta matkaa nostossa (dry), märkä hidastettu vaikuttaa uppoamiseen.
    - Rajaa osamatkat [0, z_total] väliin ja varmista, ettei nopean vaiheen matka mene negatiiviseksi.
    - Laitteen viive (Device_delay) ja mahdollinen Dropping_Time vaikuttavat nostoon prosessin määrittelyn mukaisesti.
    """
    device_delay = _num(station_row.get('Device_delay'), 0.0)
    dropping_time = _num(station_row.get('Dropping_Time'), 0.0)
    z_total = _num(transporter_row.get('Z_total_distance (mm)'), 0.0)
    z_slow_dry = _num(transporter_row.get('Z_slow_distance_dry (mm)'), 0.0)
    z_slow_end = _num(transporter_row.get('Z_slow_end_distance (mm)'), 0.0)
    z_slow_speed = _num(transporter_row.get('Z_slow_speed (mm/s)'), 1.0)
    z_fast_speed = _num(transporter_row.get('Z_fast_speed (mm/s)'), 1.0)

    # Clamp distances to physical limits
    z_slow_dry = max(0.0, min(z_slow_dry, z_total))
    z_slow_end = max(0.0, min(z_slow_end, z_total))
    fast_dist = max(0.0, z_total - z_slow_dry - z_slow_end)

    slow_up_1 = z_slow_dry / max(z_slow_speed, 1e-6)
    fast_up = fast_dist / max(z_fast_speed, 1e-6)
    slow_up_2 = z_slow_end / max(z_slow_speed, 1e-6)
    lift_time = device_delay + slow_up_1 + fast_up + slow_up_2 + dropping_time
    return round(lift_time, 1)

def calculate_sink_time(station_row, transporter_row):
    """Uppoamisajan arviointi.
    Periaate:
    - Käytä märkää hidasta matkaa upotuksessa (wet).
    - Rajaa osamatkat [0, z_total] väliin ja varmista, ettei nopean vaiheen matka mene negatiiviseksi.
    - Laitteen viive (Device_delay) vaikuttaa myös upotukseen.
    """
    device_delay = _num(station_row.get('Device_delay'), 0.0)
    z_total = _num(transporter_row.get('Z_total_distance (mm)'), 0.0)
    z_slow_wet = _num(transporter_row.get('Z_slow_distance_wet (mm)'), 0.0)
    z_slow_speed = _num(transporter_row.get('Z_slow_speed (mm/s)'), 1.0)
    z_fast_speed = _num(transporter_row.get('Z_fast_speed (mm/s)'), 1.0)

    # Clamp
    z_slow_wet = max(0.0, min(z_slow_wet, z_total))
    fast_dist = max(0.0, z_total - z_slow_wet)

    fast_down = fast_dist / max(z_fast_speed, 1e-6)
    slow_down = z_slow_wet / max(z_slow_speed, 1e-6)
    sink_time = device_delay + fast_down + slow_down
    return round(sink_time, 1)
