#!/usr/bin/env python3
"""
Test script for SchoolCafe integration.

This script tests the SchoolCafe API client independently to verify
it can connect and retrieve menu data correctly.
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta

# Add the custom_components path to sys.path for imports
sys.path.insert(0, '.')

from custom_components.schoolcafe.api import SchoolCafeAPI, SchoolCafeAPIError


async def test_schoolcafe_api():
    """Test the SchoolCafe API with sample data."""
    
    # Use your school ID here - replace with actual value
    school_id = "ef44acd3-63cb-6c9e-840a-80ed1ef89779"  # Replace with your school ID
    
    print("=" * 60)
    print("SchoolCafe Integration Test")
    print("=" * 60)
    
    # Initialize the API client
    api = SchoolCafeAPI(
        school_id=school_id,
        grade="09",
        meal_type="Lunch",
        serving_line="Main Lines",
        person_id=None,
        menu_lines=["BLUE LINE", "GOLD LINE"],
        days_to_fetch=3,  # Test with 3 days
    )
    
    try:
        print(f"Testing connection to SchoolCafe API...")
        print(f"School ID: {school_id}")
        print(f"Grade: {api.grade}")
        print(f"Meal Type: {api.meal_type}")
        print(f"Menu Lines: {api.menu_lines}")
        print()
        
        # Test connection
        print("🔍 Testing connection...")
        await api.test_connection()
        print("✅ Connection successful!")
        print()
        
        # Get menu data for today
        today = datetime.now().date()
        print(f"📅 Fetching menu for today ({today})...")
        menu_data = await api.get_menu_for_date(today)
        
        if menu_data:
            print(f"✅ Retrieved menu data with {len(menu_data)} categories")
            
            # Display menu for each configured line
            for line in api.menu_lines:
                print(f"\n🍽️  {line}:")
                items = api.extract_menu_items_for_line(menu_data, line)
                
                if items:
                    description = api.format_menu_description(items)
                    print(f"   📝 Description: {description}")
                    
                    # Show detailed info for first item
                    if items:
                        first_item = items[0]
                        print(f"   🥘 First item details:")
                        print(f"      - Calories: {first_item.get('Calories', 'N/A')}")
                        print(f"      - Rating: {first_item.get('MyRating', 'N/A')}")
                        print(f"      - Likes: {first_item.get('LikesPercentage', 'N/A')}%")
                        
                        allergens = api.get_allergen_info(first_item)
                        if allergens:
                            print(f"      - Allergens: {', '.join(allergens)}")
                        
                        nutrition = api.get_nutrition_info(first_item)
                        print(f"      - Nutrition: {nutrition}")
                else:
                    print(f"   ❌ No items found for {line}")
        else:
            print("❌ No menu data found for today")
        
        print()
        
        # Test multi-day fetch
        print("📅 Testing multi-day menu fetch...")
        all_menu_data = await api.get_menu_data()
        
        print(f"✅ Retrieved menu data for {len(all_menu_data)} days:")
        for date_key, day_data in all_menu_data.items():
            categories = len(day_data) if day_data else 0
            print(f"   - {date_key}: {categories} categories")
        
        print()
        print("🎉 All tests completed successfully!")
        
    except SchoolCafeAPIError as e:
        print(f"❌ SchoolCafe API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await api.close()
    
    return True


def main():
    """Run the test script."""
    success = asyncio.run(test_schoolcafe_api())
    
    if success:
        print("\n✅ Integration test passed! The SchoolCafe integration should work correctly.")
        print("\nNext steps:")
        print("1. Copy the custom_components/schoolcafe folder to your Home Assistant config/custom_components/ directory")
        print("2. Restart Home Assistant")
        print("3. Go to Settings -> Devices & Services -> Add Integration")
        print("4. Search for 'SchoolCafe Menu' and follow the setup wizard")
    else:
        print("\n❌ Integration test failed. Please check the errors above and fix any issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()