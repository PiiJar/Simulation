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


def format_time(seconds):
    """
    Format seconds to HH:MM:SS.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def draw_card_row(draw, y_pos, label, left_value, right_value, card_width, margin_x, 
                  body_font, small_font, draw_divider=True):
    """
    Draw a standardized card row with label and two values.
    
    Args:
        draw: ImageDraw object
        y_pos: Y position for the row
        label: Label text (gray, small font)
        left_value: Left value text (black, body font)
        right_value: Right value text (black, body font)
        card_width: Width of the card
        margin_x: Left/right margin
        body_font: Font for values
        small_font: Font for label
        draw_divider: Whether to draw divider line below (ignored - no dividers)
    
    Returns:
        Next available y position
    """
    # Draw label (gray, small font)
    draw.text((margin_x, y_pos), label, fill='#888888', font=small_font)
    
    # Draw values (black, body font) - more space between label and data
    detail_y = y_pos + 32  # Increased from 22 to 32
    draw.text((margin_x, detail_y), left_value, fill='#111111', font=body_font)
    draw.text((margin_x + card_width // 2, detail_y), right_value, fill='#111111', font=body_font)
    
    # No divider lines for better readability
    # Balanced row height for good spacing between rows
    row_height = 100  # Reduced from 120 to 100
    
    return y_pos + row_height


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
    
    # Try to load fonts (larger sizes for better readability in PDF)
    try:
        # Use same sizing/style as Performance card info area for consistency
        header_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 56)
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 38)
        body_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 38)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 34)
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

    # Draw header text (centered both horizontally and vertically)
    header_text = "Production"
    header_x = card_width // 2
    header_y = header_height // 2
    draw.text((header_x, header_y), header_text, fill=header_text_color, font=header_font, anchor='mm')

    # Content area starts after header
    content_y = header_height + 20
    margin_x = 30  # Increased left margin for better readability

    # Move 'Annual:' into the info area with same alignment/spacing as Performance card
    top_margin_extra = 24
    y_pos = content_y + top_margin_extra
    draw.text((margin_x, y_pos), "Annual:", fill='#000000', font=title_font)
    y_pos += 72

    # Draw up to 5 product rows as: ProductName S/T: simulated/target
    products_list = list(by_product.items())[:5]
    if len(products_list) == 0:
        no_data_text = "No production data"
        bbox = draw.textbbox((0, 0), no_data_text, font=body_font)
        text_width = bbox[2] - bbox[0]
        text_x = (card_width - text_width) // 2
        text_y = y_pos + 20
        draw.text((text_x, text_y), no_data_text, fill='#666666', font=body_font)
    else:
        for idx, (product_id, product_data) in enumerate(products_list):
            product_name = product_data.get('name', product_id)
            # Always truncate product name to max 10 chars (add ellipsis if longer)
            if len(product_name) > 10:
                product_name = product_name[:10] + '...'

            actual_pieces = int(product_data.get('pieces', 0))

            target_pieces = None
            if os.path.exists(customer_json_path):
                try:
                    with open(customer_json_path, 'r') as f:
                        customer_data = json.load(f)
                        plant = customer_data.get('plant', {})
                        targets = plant.get('production_targets', {}).get('annual', [])
                        for target in targets:
                            if target.get('product_id') == product_id:
                                target_pieces = int(target.get('target_quantity', 0))
                                break
                except Exception:
                    pass

            # Compose S/T text
            if target_pieces is not None and target_pieces > 0:
                st_text = f"{actual_pieces:,}/{target_pieces:,}"
            else:
                st_text = f"{actual_pieces:,}/—"

            # Draw product label and S/T using black text and larger fonts
            draw.text((margin_x, y_pos), f"{product_name} S/T:", fill='#000000', font=small_font)
            draw.text((margin_x + card_width // 2, y_pos), st_text, fill='#000000', font=body_font)
            y_pos += 72
    
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
        header_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 56)
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 38)
        # Further increase sizes for info area per user's follow-up
        body_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 38)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 34)
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
    header_x = card_width // 2
    header_y = header_height // 2
    draw.text((header_x, header_y), header_text, fill=header_text_color, font=header_font, anchor='mm')

    content_y = header_height + 20
    margin_x = 30  # Increased left margin for better readability

    # Per-user request: remove ramp times row entirely.
    # Draw 'Batches:' title at top of info area, adding a small top margin
    top_margin_extra = 24
    y_pos = content_y + top_margin_extra
    draw.text((margin_x, y_pos), "Batches:", fill='#000000', font=title_font)
    # Add extra spacing under the 'Batches:' title as requested
    y_pos += 72
    
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

    # Draw four rows with format: "<Period> (<duration>h) S/T: <simulated>/<target>"
    for idx, (period, multiplier, duration_hours) in enumerate(period_info):
        period_key = period.lower()
        target_value = int(target_counts.get(period_key, 0)) if target_counts.get(period_key, 0) else None
        actual_value = int(actual_counts.get(period_key, 0)) if actual_counts.get(period_key, 0) else 0

        # Compose label and S/T text
        label_text = f"{period} ({duration_hours:.0f}h) S/T:"
        if target_value is not None and target_value > 0:
            st_text = f"{actual_value:,}/{target_value:,}"
        else:
            st_text = f"{actual_value:,}/—"

        # Draw label (black) and S/T (black) using larger fonts
        draw.text((margin_x, y_pos), label_text, fill='#000000', font=small_font)
        draw.text((margin_x + card_width // 2, y_pos), st_text, fill='#000000', font=body_font)

        # Move down for next row
        y_pos += 72

    images_dir = os.path.join(output_dir, 'reports', 'images')
    os.makedirs(images_dir, exist_ok=True)
    card_path = os.path.join(images_dir, 'card_performance.png')
    img.save(card_path, format='PNG', quality=95)

    print(f"✅ Created card: {card_path}")
    return card_path


def create_workload_balance_card(output_dir: str, report_data: dict):
    """
    Create Workload Balance card showing transporter utilization balance.
    Header color depends on the variance in workload:
    - Green: differences < 3%
    - Yellow: differences 3-7%
    - Red: differences > 7%
    
    Args:
        output_dir: Simulation output directory
        report_data: Report data from report_data.json
    """
    card_width, card_height = calculate_card_dimensions()
    
    # Get transporter statistics
    transporter_stats = report_data.get('transporter_statistics', [])
    
    if not transporter_stats:
        # Create empty card
        img = Image.new('RGB', (card_width, card_height), color='#f5f5f5')
        draw = ImageDraw.Draw(img)
        try:
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        except:
            title_font = ImageFont.load_default()
        draw.text((card_width // 2, card_height // 2), "No Data", fill='#666666', font=title_font, anchor='mm')
        return img
    
    # Calculate utilization percentages and avg batch times, find min/max
    utilizations = []
    avg_batch_times = []
    for stat in transporter_stats:
        utilization = stat.get('utilization_percent', 0)
        avg_batch = stat.get('avg_time_per_batch_minutes', 0)
        utilizations.append(utilization)
        avg_batch_times.append(avg_batch)
    
    if not utilizations:
        # Create empty card
        img = Image.new('RGB', (card_width, card_height), color='#f5f5f5')
        return img
    
    # Calculate utilization difference
    min_util = min(utilizations)
    max_util = max(utilizations)
    util_diff_percent = max_util - min_util
    avg_util = sum(utilizations) / len(utilizations)
    
    # Calculate avg/batch difference (as percentage of average)
    min_batch = min(avg_batch_times)
    max_batch = max(avg_batch_times)
    avg_batch = sum(avg_batch_times) / len(avg_batch_times)
    if avg_batch > 0:
        batch_diff_percent = ((max_batch - min_batch) / avg_batch) * 100
    else:
        batch_diff_percent = 0
    
    # Determine header color based on BOTH differences (worst case wins)
    max_diff = max(util_diff_percent, batch_diff_percent)
    if max_diff < 3:
        header_color = '#28a745'  # Green - both good
    elif max_diff <= 7:
        header_color = '#ffc107'  # Yellow - at least one in warning range
    else:
        header_color = '#dc3545'  # Red - at least one critical
    
    header_text_color = '#ffffff'  # White text for all header colors
    
    # Create image
    img = Image.new('RGB', (card_width, card_height), color='#f5f5f5')
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts (larger sizes for better readability)
    try:
        header_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 56)
        body_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
    except Exception:
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw header (20% of card height, same as other cards)
    header_height = int(card_height * 0.20)
    draw.rectangle([(0, 0), (card_width, header_height)], fill=header_color)
    
    # Draw header text (centered both horizontally and vertically)
    header_text = "Workload Balance"
    header_x = card_width // 2
    header_y = header_height // 2
    draw.text((header_x, header_y), header_text, fill=header_text_color, font=header_font, anchor='mm')
    
    # Content area starts after header
    content_y = header_height + 20
    margin_x = 30  # Increased left margin for better readability
    
    # Draw transporter rows (same style as other cards)
    num_transporters = len(transporter_stats)
    y_pos = content_y
    
    for idx, stat in enumerate(sorted(transporter_stats, key=lambda x: x.get('transporter_id', 0))):
        t_id = stat.get('transporter_id', 0)
        utilization = stat.get('utilization_percent', 0)
        avg_time_per_batch = stat.get('avg_time_per_batch_minutes', 0)
        
        # Transporter row with utilization and avg time per batch
        label = f"Transporter {t_id}"
        utilization_text = f"Utilization: {utilization:.1f}%"
        time_text = f"Avg/batch: {avg_time_per_batch:.1f} min"
        
        # Use standardized row drawing
        draw_divider = (idx < num_transporters - 1)  # Divider for all except last row
        y_pos = draw_card_row(draw, y_pos, label, utilization_text, time_text,
                             card_width, margin_x, body_font, small_font, draw_divider)
    
    # Add summary rows at bottom (y_pos is now after last transporter row)
    
    # Row 1: Balance Variance header
    draw.text((margin_x, y_pos), "Balance Variance", fill='#888888', font=small_font)
    y_pos += 32  # More space between label and data (was 22)
    
    # Row 2: Values with color coding
    util_color = '#28a745' if util_diff_percent < 3 else '#ffc107' if util_diff_percent <= 7 else '#dc3545'
    batch_color = '#28a745' if batch_diff_percent < 3 else '#ffc107' if batch_diff_percent <= 7 else '#dc3545'
    
    left_text = f"Utilization: {util_diff_percent:.1f}%"
    right_text = f"Avg/batch: {batch_diff_percent:.1f}%"
    
    draw.text((margin_x, y_pos), left_text, fill=util_color, font=body_font)
    draw.text((margin_x + card_width // 2, y_pos), right_text, fill=batch_color, font=body_font)
    
    # No divider line - removed for better readability
    
    # Save card
    reports_dir = os.path.join(output_dir, 'reports', 'images')
    os.makedirs(reports_dir, exist_ok=True)
    card_path = os.path.join(reports_dir, 'card_workload_balance.png')
    img.save(card_path)
    print(f"✅ Created Workload Balance card: {card_path}")
    
    return img


def create_slowest_phases_card(output_dir: str, report_data: dict):
    """
    Create Slowest Phases card showing the 3 phases with longest cycle times.
    Color-coded based on comparison with target takt time.
    
    Args:
        output_dir: Simulation output directory
        report_data: Report data from report_data.json
    """
    card_width, card_height = calculate_card_dimensions()
    
    # Get all phases with cycle times from all treatment programs
    all_phases = []
    treatment_programs = report_data.get('treatment_programs', {}).get('programs', {})
    
    for prog_num, prog_data in treatment_programs.items():
        steps = prog_data.get('steps', [])
        for step in steps:
            cycle_time = step.get('minimum_cycle_time_seconds', 0)
            if cycle_time > 0:  # Only include phases with valid cycle time
                all_phases.append({
                    'treatment_program': int(prog_num),
                    'stage': step.get('stage'),
                    'min_station': step.get('min_station'),
                    'max_station': step.get('max_station'),
                    'cycle_time_seconds': cycle_time
                })
    
    # Sort by cycle time (longest first) and take top 3
    all_phases.sort(key=lambda x: x['cycle_time_seconds'], reverse=True)
    top_3_phases = all_phases[:3]
    
    # Calculate target takt time from batches_per_hour
    scaled_production = report_data.get('simulation_info', {}).get('scaled_production_estimates', {})
    batches_per_hour = scaled_production.get('batches_per_hour', 0)
    target_takt_time_seconds = (3600 / batches_per_hour) if batches_per_hour > 0 else 0
    
    # Determine header color based on worst phase
    if len(top_3_phases) > 0 and target_takt_time_seconds > 0:
        worst_cycle_time = top_3_phases[0]['cycle_time_seconds']
        diff = target_takt_time_seconds - worst_cycle_time
        
        if diff < 15:  # Cycle time within 15 seconds of target (critical bottleneck)
            header_color = '#dc3545'  # Red
        elif diff < 60:  # Difference < 1 minute (warning)
            header_color = '#fd7e14'  # Orange
        else:  # Good margin
            header_color = '#28a745'  # Green
        header_text_color = '#ffffff'
    else:
        header_color = '#4a4a4a'  # Gray
        header_text_color = '#ffffff'
    
    # Create image
    img = Image.new('RGB', (card_width, card_height), color='#f5f5f5')
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        header_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 56)
        body_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
    except Exception:
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw header
    header_height = int(card_height * 0.20)
    draw.rectangle([(0, 0), (card_width, header_height)], fill=header_color)
    header_text = "Slowest Phases"
    draw.text((card_width // 2, header_height // 2), header_text, 
              fill=header_text_color, font=header_font, anchor='mm')
    
    # Content area
    content_y = header_height + 20
    margin_x = 30
    
    if len(top_3_phases) == 0:
        no_data_text = "No cycle time data"
        bbox = draw.textbbox((0, 0), no_data_text, font=body_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((card_width - text_width) // 2, content_y + 100), 
                  no_data_text, fill='#666666', font=body_font)
    else:
        y_pos = content_y
        for phase in top_3_phases:
            prog = phase['treatment_program']
            stage = phase['stage']
            min_st = phase['min_station']
            max_st = phase['max_station']
            cycle_seconds = phase['cycle_time_seconds']
            
            # Determine color for this row
            if target_takt_time_seconds > 0:
                diff = target_takt_time_seconds - cycle_seconds
                if diff < 15:  # Cycle time within 15 seconds of target (critical bottleneck)
                    value_color = '#dc3545'  # Red
                elif diff < 60:  # Difference < 1 minute (warning)
                    value_color = '#fd7e14'  # Orange
                else:  # Good margin
                    value_color = '#28a745'  # Green
            else:
                value_color = '#111111'  # Black (default)
            
            # Row label: "Program: X, Phase: Y"
            label = f"Program: {prog}, Phase: {stage}"
            
            # Draw label (gray, small font)
            draw.text((margin_x, y_pos), label, fill='#888888', font=small_font)
            
            # Draw values with color-coded cycle time
            detail_y = y_pos + 32
            stations_text = f"Stations: {min_st}-{max_st}"
            cycle_text = f"Cycle: {format_time(cycle_seconds)}"
            
            draw.text((margin_x, detail_y), stations_text, fill='#111111', font=body_font)
            draw.text((margin_x + card_width // 2, detail_y), cycle_text, fill=value_color, font=body_font)
            
            y_pos += 100
    
    # Save card
    reports_dir = os.path.join(output_dir, 'reports')
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    card_path = os.path.join(images_dir, 'card_slowest_phases.png')
    img.save(card_path, 'PNG', dpi=(300, 300))
    print(f"✅ Created Slowest Phases card: {card_path}")
    return card_path


def create_simple_metric_card(output_dir, report_data, metric_type):
    """
    Create a simple metric card with dark blue header and large value.
    
    metric_type can be:
    - 'total_simulation_time': Total simulation time in HH:MM:SS
    - 'batches_processed': Total number of batches
    - 'avg_cycle_time': Average cycle time in HH:MM:SS
    """
    # Card configuration
    mm_to_px = 300 / 25.4  # 300 DPI
    card_size_mm = 60
    card_size_px = int(card_size_mm * mm_to_px)
    
    # Create card
    card = Image.new('RGB', (card_size_px, card_size_px), color='white')
    draw = ImageDraw.Draw(card)
    
    # Load fonts
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        large_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 84)
    except:
        header_font = ImageFont.load_default()
        large_font = ImageFont.load_default()
    
    # Define metric-specific content
    if metric_type == 'total_simulation_time':
        header_text = "Total Simulation Time"
        # Get simulation duration from report_data
        sim_duration = report_data.get('simulation', {}).get('duration_seconds', 0)
        value_text = format_time(sim_duration)
        filename = "card_total_simulation_time.png"
        
    elif metric_type == 'batches_processed':
        header_text = "Batches Processed"
        # Get total batches from report_data
        batches = report_data.get('simulation', {}).get('total_batches', 0)
        value_text = str(batches)
        filename = "card_batches_processed.png"
        
    elif metric_type == 'avg_cycle_time':
        header_text = "Avg. Cycle Time"
        # Get steady-state average cycle time from report_data (pre-calculated)
        avg_seconds = report_data.get('simulation', {}).get('steady_state_avg_cycle_time_seconds', 0)
        
        # Fallback if not available
        if avg_seconds == 0:
            scaled_estimates = report_data.get('simulation_info', {}).get('scaled_production_estimates', {})
            batches_per_hour = scaled_estimates.get('batches_per_hour', 0)
            
            if batches_per_hour > 0:
                avg_seconds = 3600 / batches_per_hour
            else:
                # Final fallback: exclude ramp-up time
                total_batches = report_data.get('simulation', {}).get('total_batches', 1)
                sim_duration = report_data.get('simulation', {}).get('duration_seconds', 0)
                ramp_up_time = report_data.get('simulation_info', {}).get('ramp_up_time_seconds', 0)
                
                if total_batches > 1:
                    avg_seconds = (sim_duration - ramp_up_time) / (total_batches - 1)
                else:
                    avg_seconds = sim_duration
        
        value_text = format_time(avg_seconds)
        filename = "card_avg_cycle_time.png"
    else:
        raise ValueError(f"Unknown metric_type: {metric_type}")
    
    # Dark blue header
    header_height = 200
    header_color = (25, 55, 95)  # Dark blue
    draw.rectangle([(0, 0), (card_size_px, header_height)], fill=header_color)
    
    # Header text (white)
    bbox = draw.textbbox((0, 0), header_text, font=header_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (card_size_px - text_width) // 2
    text_y = (header_height - text_height) // 2
    draw.text((text_x, text_y), header_text, fill='white', font=header_font)
    
    # Large value centered in remaining space
    bbox = draw.textbbox((0, 0), value_text, font=large_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    remaining_height = card_size_px - header_height
    text_x = (card_size_px - text_width) // 2
    text_y = header_height + (remaining_height - text_height) // 2
    
    draw.text((text_x, text_y), value_text, fill='black', font=large_font)
    
    # Save card
    images_dir = os.path.join(output_dir, "reports", "images")
    os.makedirs(images_dir, exist_ok=True)
    output_path = os.path.join(images_dir, filename)
    card.save(output_path)
    print(f"✅ Created {metric_type} card: {output_path}")
    
    return output_path


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
    cards.append(create_workload_balance_card(output_dir, report_data))
    cards.append(create_slowest_phases_card(output_dir, report_data))
    cards.append(create_simple_metric_card(output_dir, report_data, 'total_simulation_time'))
    cards.append(create_simple_metric_card(output_dir, report_data, 'batches_processed'))
    cards.append(create_simple_metric_card(output_dir, report_data, 'avg_cycle_time'))
    
    return cards


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        generate_all_cards(output_dir)
    else:
        print("Usage: python generate_production_cards.py <output_dir>")
