"""
Generate all report images (cards, charts, diagrams).

This module orchestrates all image generation for reports,
keeping the main pipeline clean.
"""

from generate_production_cards import generate_all_cards


def generate_images(output_dir: str):
    """
    Generate all report images.
    
    Args:
        output_dir: Simulation output directory
    
    Generates:
        - Production status cards
        - (Future: other charts, diagrams, etc.)
    """
    print("🖼️  Generating report images...")
    
    # Generate production status cards
    try:
        generate_all_cards(output_dir)
        print("✅ Production cards generated")
    except Exception as e:
        print(f"⚠️  Warning: Production cards generation failed: {e}")
    
    # Future: add other image generation here
    # generate_station_utilization_chart(output_dir)
    # generate_transporter_timeline(output_dir)
    # etc.
    
    print("🖼️  Report images generation completed")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        generate_images(output_dir)
    else:
        print("Usage: python generate_images.py <output_dir>")
