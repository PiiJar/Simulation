"""
Generate production status cards as images.

Cards are sized to fit 3 across an A4 page with margins.
Card format: square (width = height)
"""

import os
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import timedelta

from load_customer_json import load_customer_json


def calculate_card_dimensions():
    """
    Calculate card dimensions for 3 cards across A4 with margins.
    A4 width: 210mm
    Margins: 10mm left + 10mm right = 20mm total
    Available width: 190mm
    3 cards with 2 gaps: (190mm - 2*gap) / 3
    Use 5mm gap between cards
    Card width: (190 - 10) / 3 = 60mm
    Convert to pixels at 300 DPI: 60mm * (300/25.4) ≈ 709 pixels
    """
    mm_to_pixels = 300 / 25.4  # 300 DPI conversion
    card_width_mm = 60
    card_width_px = int(card_width_mm * mm_to_pixels)
    card_height_px = card_width_px  # Square card
    
    return card_width_px, card_height_px


def get_status_color(actual, target):
    """
    Determine card status color based on actual vs target.
    Returns: (header_color, text_color)
    """
    if actual is None or target is None:
        return ('#4a4a4a', '#ffffff')  # Dark gray, white text
    
    if actual >= target:
        return ('#28a745', '#ffffff')  # Green, white text
    else:
        return ('#dc3545', '#ffffff')  # Red, white text


def create_annual_production_card(output_dir: str, report_data: dict):
    """
    Create Annual Production card showing product targets vs actual.
    
    Args:
        output_dir: Simulation output directory
        report_data: Report data from report_data.json
    """
    card_width, card_height = calculate_card_dimensions()
    
    # Create image
    img = Image.new('RGB', (card_width, card_height), color='#f5f5f5')  # Light gray background
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    try:
        header_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        body_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    except Exception:
        # Fallback to default font
        header_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Get production data
    scaled_production = report_data.get('simulation_info', {}).get('scaled_production_estimates', {})
    year_data = scaled_production.get('year', {})
    by_product = year_data.get('by_product', {})
    
    # Determine status (compare total actual vs total target)
    total_actual = 0
    total_target = 0
    
    # Get targets from customer data (this would need to be loaded from customer.json)
    # For now, use a simple check based on whether we have data
    has_data = len(by_product) > 0
    
    # Calculate status based on actual production
    for product_id, product_data in by_product.items():
        actual_pieces = product_data.get('pieces', 0)
        total_actual += actual_pieces
    
    # Get target from customer.json if available
    init_dir = os.path.join(output_dir, 'initialization')
    customer_json_path = os.path.join(init_dir, 'customer.json')
    
    if os.path.exists(customer_json_path):
        try:
            with open(customer_json_path, 'r') as f:
                customer_data = json.load(f)
                plant = customer_data.get('plant', {})
                targets = plant.get('production_targets', {}).get('annual', [])
                for target in targets:
                    total_target += target.get('target_quantity', 0)
        except Exception:
            total_target = None
    else:
        total_target = None
    
    # Determine header color
    header_color, header_text_color = get_status_color(total_actual, total_target)
    
    # Draw header (20% of card height)
    header_height = int(card_height * 0.20)
    draw.rectangle([(0, 0), (card_width, header_height)], fill=header_color)
    
    # Draw header text
    header_text = "Annual Production"
    # Center text in header
    bbox = draw.textbbox((0, 0), header_text, font=header_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    header_x = (card_width - text_width) // 2
    header_y = (header_height - text_height) // 2
    draw.text((header_x, header_y), header_text, fill=header_text_color, font=header_font)
    
    # Content area starts after header
    content_y = header_height + 20
    margin_x = 20
    
    # Draw product rows (max 5 products)
    row_height = (card_height - header_height - 40) // 5  # Space for 5 rows
    
    products_list = list(by_product.items())[:5]  # Max 5 products

    if len(products_list) == 0:
        # No data message
        no_data_text = "No production data"
        bbox = draw.textbbox((0, 0), no_data_text, font=body_font)
        text_width = bbox[2] - bbox[0]
        text_x = (card_width - text_width) // 2
        text_y = content_y + 100
        draw.text((text_x, text_y), no_data_text, fill='#666666', font=body_font)
    else:
        for idx, (product_id, product_data) in enumerate(products_list):
            y_pos = content_y + (idx * row_height)

            product_name = product_data.get('name', product_id)
            if len(product_name) > 20:
                product_name = product_name[:17] + '...'

            draw.text((margin_x, y_pos), product_name, fill='#888888', font=small_font)

            actual_pieces = product_data.get('pieces', 0)

            target_pieces = None
            if os.path.exists(customer_json_path):
                try:
                    with open(customer_json_path, 'r') as f:
                        customer_data = json.load(f)
                        plant = customer_data.get('plant', {})
                        targets = plant.get('production_targets', {}).get('annual', [])
                        for target in targets:
                            if target.get('product_id') == product_id:
                                target_pieces = target.get('target_quantity', 0)
                                break
                except Exception:
                    pass

            detail_y = y_pos + 22
            action_text = f"Simulated: {actual_pieces:,}"
            target_text = f"Target: {target_pieces:,}" if target_pieces is not None else "Target: —"
            draw.text((margin_x, detail_y), action_text, fill='#111111', font=body_font)
            draw.text((margin_x + card_width // 2, detail_y), target_text, fill='#111111', font=body_font)
    
    # Save card
    images_dir = os.path.join(output_dir, 'reports', 'images')
    os.makedirs(images_dir, exist_ok=True)
    card_path = os.path.join(images_dir, 'card_annual_production.png')
    img.save(card_path, format='PNG', quality=95)
    
    print(f"✅ Created card: {card_path}")
    return card_path


def format_seconds(seconds):
    """Format seconds as HH:MM:SS."""
    try:
        secs = int(seconds)
    except (TypeError, ValueError):
        return "00:00:00"

    hours = secs // 3600
    minutes = (secs % 3600) // 60
    remaining_seconds = secs % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def get_production_schedule(output_dir: str):
    """Load production schedule (shifts, hours, etc.) from customer.json."""
    init_dir = os.path.join(output_dir, 'initialization')
    try:
        _, plant, _ = load_customer_json(init_dir)
        return plant.get('production_schedule', {})
    except Exception:
        return {}


def get_annual_target_batches(output_dir: str):
    """Calculate annual target batch count based on customer.json data."""
    init_dir = os.path.join(output_dir, 'initialization')
    try:
        _, plant, products = load_customer_json(init_dir)
        targets = plant.get('production_targets', {}).get('annual', [])
        product_map = {prod.get('id'): prod for prod in products}
        total_batches = 0.0
        for target in targets:
            product_id = target.get('product_id')
            target_qty = target.get('target_quantity', 0)
            product = product_map.get(product_id, {})
            pieces_per_batch = product.get('properties', {}).get('pieces_per_batch', 1)
            if pieces_per_batch:
                total_batches += target_qty / pieces_per_batch
        return total_batches
    except Exception:
        return 0


def calculate_period_targets(annual_batches: float, schedule: dict):
    """Estimate target batch counts for shift/day/week/year using production schedule."""
    shifts_per_day = schedule.get('shifts_per_day', 2) or 2
    days_per_week = schedule.get('days_per_week', 5) or 5
    weeks_per_year = schedule.get('weeks_per_year', 48) or 48

    denominator = shifts_per_day * days_per_week * weeks_per_year
    shift_target = annual_batches / denominator if denominator > 0 else 0

    day_target = shift_target * shifts_per_day
    week_target = day_target * days_per_week
    year_target = annual_batches

    return {
        'shift': shift_target,
        'day': day_target,
        'week': week_target,
        'year': year_target
    }


def create_performance_card(output_dir: str, report_data: dict):
    """Create a Performance card summarizing line performance."""
    card_width, card_height = calculate_card_dimensions()

    img = Image.new('RGB', (card_width, card_height), color='#f5f5f5')
    draw = ImageDraw.Draw(img)

    try:
        header_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        body_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    except Exception:
        header_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    sim_info = report_data.get('simulation_info', {})
    scaled = sim_info.get('scaled_production_estimates', {})
    ramp_up_seconds = sim_info.get('ramp_up_time_seconds')
    ramp_down_seconds = sim_info.get('ramp_down_time_seconds')
    ramp_up_time = sim_info.get('ramp_up_time') or format_seconds(ramp_up_seconds)
    ramp_down_time = sim_info.get('ramp_down_time') or format_seconds(ramp_down_seconds)

    schedule = get_production_schedule(output_dir)
    shifts_per_day = schedule.get('shifts_per_day', 2)
    hours_per_shift = schedule.get('hours_per_shift', 8.0)
    day_duration = shifts_per_day * hours_per_shift
    annual_batches = get_annual_target_batches(output_dir)
    target_counts = calculate_period_targets(annual_batches, schedule)
    header_detail = f"Shift duration: {timedelta(hours=hours_per_shift)}" \
                    f" | Day duration: {timedelta(hours=day_duration)}"

    actual_counts = {}
    for period_key in ['shift', 'day', 'week', 'year']:
        period_data = scaled.get(period_key, {})
        by_product = period_data.get('by_product', {})
        total_batches = sum(prod.get('batches', 0) for prod in by_product.values())
        actual_counts[period_key] = total_batches

    header_color, header_text_color = get_status_color(actual_counts['year'], target_counts['year'] if target_counts['year'] > 0 else None)

    header_height = int(card_height * 0.20)
    draw.rectangle([(0, 0), (card_width, header_height)], fill=header_color)
    header_text = "Performance"
    bbox = draw.textbbox((0, 0), header_text, font=header_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    header_x = (card_width - text_width) // 2
    header_y = (header_height - text_height) // 2
    draw.text((header_x, header_y), header_text, fill=header_text_color, font=header_font)

    content_y = header_height + 20
    margin_x = 20

    draw.text((margin_x, content_y), f"Ramp up: {ramp_up_time}", fill='#333333', font=body_font)
    draw.text((margin_x, content_y + 28), f"Ramp down: {ramp_down_time}", fill='#333333', font=body_font)

    table_start_y = content_y + 70
    row_height = 60
    shifts_per_day = schedule.get('shifts_per_day', 2)
    hours_per_shift = schedule.get('hours_per_shift', 8.0)
    days_per_week = schedule.get('days_per_week', 5)
    weeks_per_year = schedule.get('weeks_per_year', 48)

    period_info = [
        ('Shift', shifts_per_day, hours_per_shift),
        ('Day', 1, shifts_per_day * hours_per_shift),
        ('Week', days_per_week, shifts_per_day * days_per_week * hours_per_shift),
        ('Year', weeks_per_year, shifts_per_day * days_per_week * weeks_per_year * hours_per_shift)
    ]

    for idx, (period, multiplier, duration_hours) in enumerate(period_info):
        y_pos = table_start_y + idx * row_height
        period_key = period.lower()
        target_value = target_counts.get(period_key, 0)
        actual_value = actual_counts.get(period_key, 0)

        label = f"{period} ({duration_hours:.1f}h)"
        draw.text((margin_x, y_pos), label, fill='#888888', font=small_font)

        detail_y = y_pos + 22
        actual_text = f"Simulated: {actual_value:,}"
        title_target = f"Target: {int(target_value):,}" if target_value > 0 else "Target: —"
        draw.text((margin_x, detail_y), actual_text, fill='#111111', font=body_font)
        draw.text((margin_x + card_width // 2, detail_y), title_target, fill='#111111', font=body_font)

        divider_y = y_pos + row_height - 10
        draw.line([(margin_x, divider_y), (card_width - margin_x, divider_y)], fill='#dddddd', width=1)

    images_dir = os.path.join(output_dir, 'reports', 'images')
    os.makedirs(images_dir, exist_ok=True)
    card_path = os.path.join(images_dir, 'card_performance.png')
    img.save(card_path, format='PNG', quality=95)

    print(f"✅ Created card: {card_path}")
    return card_path


def generate_all_cards(output_dir: str):
    """
    Generate all production status cards.
    
    Args:
        output_dir: Simulation output directory
    """
    # Load report data
    reports_dir = os.path.join(output_dir, 'reports')
    report_data_path = os.path.join(reports_dir, 'report_data.json')
    
    if not os.path.exists(report_data_path):
        print(f"⚠️  Warning: report_data.json not found at {report_data_path}")
        return
    
    with open(report_data_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Generate cards
    cards = []
    cards.append(create_annual_production_card(output_dir, report_data))
    cards.append(create_performance_card(output_dir, report_data))
    
    return cards


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        generate_all_cards(output_dir)
    else:
        print("Usage: python generate_production_cards.py <output_dir>")
