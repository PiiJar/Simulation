"""
Convert simulation output from CSV format to JSON format.

This tool allows gradual migration from CSV-based data storage
to JSON-based storage for better structure and type safety.

Usage:
    python convert_to_json.py <output_dir>
    
Example:
    python convert_to_json.py output/900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-13_07-29-28
"""

import sys
import os
from data_loader import SimulationDataLoader


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_to_json.py <output_dir>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    
    if not os.path.exists(output_dir):
        print(f"❌ Error: Directory not found: {output_dir}")
        sys.exit(1)
    
    print(f"🔄 Converting simulation data to JSON...")
    print(f"   Source: {output_dir}")
    
    # Load from CSV
    loader = SimulationDataLoader(output_dir, source_format="csv")
    
    # Export to JSON
    json_file = loader.export_to_json()
    
    print(f"✅ Conversion complete!")
    print(f"   Output: {json_file}")
    print()
    print("Next steps:")
    print("  1. Review the generated JSON file")
    print("  2. Update code to use: data_loader.get_data_loader(output_dir, prefer_json=True)")
    print("  3. Test that reports still generate correctly")


if __name__ == "__main__":
    main()
