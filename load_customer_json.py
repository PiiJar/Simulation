"""
Load customer, plant, and product data from customer.json.

This module provides functions to load customer master data from JSON format
and convert it to the formats needed by the simulation pipeline.
"""

import json
import os
import pandas as pd
from typing import Dict, List, Tuple


def load_customer_json(init_dir: str) -> Tuple[Dict, Dict, List[Dict]]:
    """
    Load customer.json and return customer, plant, and products data.
    
    Args:
        init_dir: Path to initialization directory containing customer.json
    
    Returns:
        Tuple of (customer_dict, plant_dict, products_list)
        - customer_dict: Customer information (id, name, description, contact)
        - plant_dict: Plant information (id, name, location, production_schedule, production_targets)
        - products_list: List of product dictionaries with all properties
    
    Raises:
        FileNotFoundError: If customer.json is not found
        json.JSONDecodeError: If JSON is malformed
    """
    json_path = os.path.join(init_dir, "customer.json")
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"customer.json ei löydy: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    customer = data.get("customer", {})
    plant = data.get("plant", {})
    products = data.get("products", [])
    
    return customer, plant, products


def get_customer_info(init_dir: str) -> Dict:
    """
    Get customer information only.
    
    Args:
        init_dir: Path to initialization directory
    
    Returns:
        Dictionary with customer data (id, name, description, contact)
    """
    customer, _, _ = load_customer_json(init_dir)
    return customer


def get_plant_info(init_dir: str) -> Dict:
    """
    Get plant information only.
    
    Args:
        init_dir: Path to initialization directory
    
    Returns:
        Dictionary with plant data (id, name, location, production_schedule, production_targets)
    """
    _, plant, _ = load_customer_json(init_dir)
    return plant


def get_products(init_dir: str) -> List[Dict]:
    """
    Get list of products.
    
    Args:
        init_dir: Path to initialization directory
    
    Returns:
        List of product dictionaries
    """
    _, _, products = load_customer_json(init_dir)
    return products


def get_customer_plant_legacy_format(init_dir: str) -> pd.DataFrame:
    """
    Get customer and plant info in legacy CSV format for backward compatibility.
    
    Returns a DataFrame with columns:
    - Customer: Formatted as "customer_id - customer_name"
    - Plant: Plant name
    
    This matches the old customer_and_plant.csv format for existing code compatibility.
    
    Args:
        init_dir: Path to initialization directory
    
    Returns:
        DataFrame with Customer and Plant columns (single row)
    """
    customer, plant, _ = load_customer_json(init_dir)
    
    # Format: "900135 - Factory X - Nammo"
    customer_str = f"{customer.get('id', '')} - {customer.get('name', '')}"
    plant_str = plant.get('name', '')
    
    df = pd.DataFrame({
        'Customer': [customer_str],
        'Plant': [plant_str]
    })
    
    return df


def get_products_dataframe(init_dir: str) -> pd.DataFrame:
    """
    Get products as DataFrame for easier data manipulation.
    
    Returns:
        DataFrame with flattened product data including all properties
    """
    _, _, products = load_customer_json(init_dir)
    
    if not products:
        return pd.DataFrame()
    
    # Flatten nested properties
    records = []
    for product in products:
        record = {
            'Product_id': product.get('id'),
            'Plant_id': product.get('plant_id'),
            'Name': product.get('name'),
            'Description': product.get('description'),
        }
        
        # Add properties
        props = product.get('properties', {})
        record['Surface_area_mm2'] = props.get('surface_area_mm2')
        record['Weight_kg'] = props.get('weight_kg')
        record['Treatment_program'] = props.get('treatment_program')
        record['Pieces_per_batch'] = props.get('pieces_per_batch')
        record['Material'] = props.get('material')
        record['Coating_type'] = props.get('coating_type')
        
        # Add dimensions
        dims = product.get('dimensions', {})
        record['Length_mm'] = dims.get('length_mm')
        record['Width_mm'] = dims.get('width_mm')
        record['Height_mm'] = dims.get('height_mm')
        
        # Add quality requirements
        quality = product.get('quality_requirements', {})
        record['Coating_thickness_min_um'] = quality.get('coating_thickness_min_um')
        record['Coating_thickness_max_um'] = quality.get('coating_thickness_max_um')
        record['Surface_finish'] = quality.get('surface_finish')
        
        records.append(record)
    
    return pd.DataFrame(records)


if __name__ == "__main__":
    # Test loading
    import sys
    
    init_dir = "initialization"
    if len(sys.argv) > 1:
        init_dir = sys.argv[1]
    
    print("=" * 80)
    print("Testing customer.json loading")
    print("=" * 80)
    
    try:
        customer, plant, products = load_customer_json(init_dir)
        
        print("\n📋 CUSTOMER:")
        print(f"  ID: {customer.get('id')}")
        print(f"  Name: {customer.get('name')}")
        print(f"  Description: {customer.get('description')}")
        
        print("\n🏭 PLANT:")
        print(f"  ID: {plant.get('id')}")
        print(f"  Name: {plant.get('name')}")
        print(f"  Customer ID: {plant.get('customer_id')}")
        
        schedule = plant.get('production_schedule', {})
        print(f"\n  Production Schedule:")
        print(f"    - Weeks/year: {schedule.get('weeks_per_year')}")
        print(f"    - Days/week: {schedule.get('days_per_week')}")
        print(f"    - Shifts/day: {schedule.get('shifts_per_day')}")
        print(f"    - Hours/shift: {schedule.get('hours_per_shift')}")
        print(f"    - Annual hours: {schedule.get('annual_production_hours')}")
        
        print(f"\n🔧 PRODUCTS ({len(products)}):")
        for prod in products:
            print(f"  - {prod.get('id')}: {prod.get('name')}")
            props = prod.get('properties', {})
            print(f"    Treatment program: {props.get('treatment_program')}")
            print(f"    Pieces/batch: {props.get('pieces_per_batch')}")
            print(f"    Surface area: {props.get('surface_area_mm2')} mm²")
            print(f"    Weight: {props.get('weight_kg')} kg")
        
        print("\n" + "=" * 80)
        print("Legacy format (customer_and_plant.csv compatible):")
        print("=" * 80)
        df_legacy = get_customer_plant_legacy_format(init_dir)
        print(df_legacy.to_string(index=False))
        
        print("\n" + "=" * 80)
        print("Products DataFrame:")
        print("=" * 80)
        df_products = get_products_dataframe(init_dir)
        print(df_products.to_string(index=False))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
