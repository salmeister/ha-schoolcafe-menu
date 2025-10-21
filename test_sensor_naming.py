#!/usr/bin/env python3
"""
Test script for the improved SchoolCafe integration sensor naming.

This script demonstrates the new sensor naming scheme and how to use
the is_weekday attribute for filtering.
"""

from datetime import datetime, timedelta


def simulate_sensor_names(days=7):
    """Simulate the new sensor naming scheme."""
    print("🔄 New SchoolCafe Sensor Naming Scheme")
    print("=" * 50)
    
    for day_offset in range(days):
        target_date = datetime.now().date() + timedelta(days=day_offset)
        is_weekday = target_date.weekday() < 5  # Monday(0) through Friday(4)
        
        # Generate sensor name
        if day_offset == 0:
            day_suffix = "today"
            friendly_name = "Today"
        elif day_offset == 1:
            day_suffix = "tomorrow"
            friendly_name = "Tomorrow"
        else:
            day_suffix = f"today_plus{day_offset}"
            friendly_name = f"Today +{day_offset} ({target_date.strftime('%A')})"
        
        # Blue Line sensor
        blue_sensor = f"sensor.schoolcafe_blue_line_{day_suffix}"
        gold_sensor = f"sensor.schoolcafe_gold_line_{day_suffix}"
        
        weekday_icon = "📚" if is_weekday else "🏖️"
        status = "School Day" if is_weekday else "Weekend"
        
        print(f"Day {day_offset}: {target_date.strftime('%A %m/%d')} {weekday_icon}")
        print(f"  Friendly Name: SchoolCafe Blue Line {friendly_name}")
        print(f"  Blue Sensor:   {blue_sensor}")
        print(f"  Gold Sensor:   {gold_sensor}")
        print(f"  is_weekday:    {is_weekday} ({status})")
        print()


def show_lovelace_benefits():
    """Show how this improves Lovelace card configuration."""
    print("✨ Lovelace Benefits")
    print("=" * 50)
    print("OLD naming (difficult to use in order):")
    print("  - sensor.schoolcafe_blue_line_day_0")
    print("  - sensor.schoolcafe_blue_line_day_1")
    print("  - sensor.schoolcafe_blue_line_day_2")
    print("  - etc...")
    print()
    
    print("NEW naming (intuitive and sequential):")
    print("  - sensor.schoolcafe_blue_line_today")
    print("  - sensor.schoolcafe_blue_line_tomorrow")
    print("  - sensor.schoolcafe_blue_line_today_plus2")
    print("  - sensor.schoolcafe_blue_line_today_plus3")
    print("  - etc...")
    print()
    
    print("🎯 Key Improvements:")
    print("  ✅ Predictable naming pattern")
    print("  ✅ Easy to understand in Lovelace")
    print("  ✅ Sequential numbering for automation")
    print("  ✅ is_weekday attribute for filtering")
    print("  ✅ No need to calculate day offsets in templates")
    print()


def show_filter_example():
    """Show example of weekend filtering using is_weekday."""
    print("🔍 Weekend Filtering Example")
    print("=" * 50)
    print("Lovelace template to show only school days:")
    print()
    print("```yaml")
    print("- type: conditional")
    print("  conditions:")
    print("    - condition: template")
    print("      value_template: >")
    print("        {{ state_attr('sensor.schoolcafe_blue_line_tomorrow', 'is_weekday') == true }}")
    print("  card:")
    print("    entity: sensor.schoolcafe_blue_line_tomorrow")
    print("    name: 'Tomorrow's Menu'")
    print("```")
    print()
    print("This will automatically hide weekend days!")


if __name__ == "__main__":
    print("🍽️ SchoolCafe Integration - Sensor Naming Improvements")
    print("=" * 60)
    print()
    
    simulate_sensor_names(7)
    show_lovelace_benefits()
    show_filter_example()
    
    print("📝 Summary:")
    print("The new naming scheme makes it much easier to create")
    print("Lovelace cards that display menus in chronological order")
    print("and automatically filter out weekends using the is_weekday attribute.")