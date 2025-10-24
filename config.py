#!/usr/bin/env python3
"""
Configuration for Simulation Pipeline
======================================

Global settings for the simulation.
"""

# ==========================================
# OPTIMIZATION SETTINGS
# ==========================================

# Use CP-SAT (Google OR-Tools) for VAIHE 5 optimization
# True  = CP-SAT Job Shop Scheduling (optimal makespan, slower ~1-60s)
# False = Traditional greedy algorithm (fast ~1s, suboptimal)
USE_CPSAT_OPTIMIZATION = True

# Maximum time for CP-SAT optimization (seconds)
# Longer time may find better solutions for complex problems
CPSAT_TIME_LIMIT = 60

# ==========================================
# LEGACY SETTINGS (kept for compatibility)
# ==========================================

# Shift gap between transporter tasks (used by old greedy algorithm)
# Not used when USE_CPSAT_OPTIMIZATION = True
SHIFT_GAP = 0


def get_shift_gap():
    """
    Returns the shift gap for transporter tasks.
    Used by legacy greedy algorithm (stretch_transporter_tasks.py).
    """
    return SHIFT_GAP
