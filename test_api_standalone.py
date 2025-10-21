#!/usr/bin/env python3
"""
Standalone test script for SchoolCafe API.

This script tests the SchoolCafe API independently without Home Assistant dependencies.
"""
import asyncio
import json
import aiohttp
from datetime import datetime
from urllib.parse import quote


async def test_schoolcafe_api_standalone():
    """Test the SchoolCafe API directly."""
    
    # Use your school ID here
    school_id = "ef44acd3-63cb-6c9e-840a-80ed1ef89779"
    grade = "09"
    meal_type = "Lunch"
    serving_line = "Main Lines"
    person_id = "null"
    
    print("=" * 60)
    print("SchoolCafe API Standalone Test")
    print("=" * 60)
    print(f"School ID: {school_id}")
    print(f"Grade: {grade}")
    print(f"Meal Type: {meal_type}")
    print(f"Serving Line: {serving_line}")
    print()
    
    # Build API URL for today
    today = datetime.now()
    date_str = quote(today.strftime("%m/%d/%Y"))
    serving_line_encoded = quote(serving_line)
    meal_type_encoded = quote(meal_type)
    
    url = (
        f"https://webapis.schoolcafe.com/api/CalendarView/GetDailyMenuitemsByGrade"
        f"?SchoolId={school_id}"
        f"&ServingDate={date_str}"
        f"&ServingLine={serving_line_encoded}"
        f"&MealType={meal_type_encoded}"
        f"&Grade={grade}"
        f"&PersonId={person_id}"
    )
    
    print(f"🔗 API URL: {url}")
    print()
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print("🔍 Making API request...")
            async with session.get(url) as response:
                print(f"📊 Response Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API request successful!")
                    print(f"📋 Found {len(data)} menu categories")
                    print()
                    
                    # Display menu categories
                    for category, items in data.items():
                        print(f"🍽️  {category}:")
                        if items:
                            for item in items:
                                desc = item.get("MenuItemDescription", "Unknown Item")
                                calories = item.get("Calories", "N/A")
                                rating = item.get("MyRating", "N/A")
                                print(f"   📝 {desc} ({calories} cal, {rating}★)")
                        else:
                            print("   ❌ No items")
                        print()
                    
                    # Test specific lines
                    blue_line = data.get("BLUE LINE", [])
                    gold_line = data.get("GOLD LINE", [])
                    
                    print(f"🔵 BLUE LINE: {len(blue_line)} items")
                    print(f"🟡 GOLD LINE: {len(gold_line)} items")
                    
                    if blue_line:
                        descriptions = [item.get("MenuItemDescription", "Unknown") for item in blue_line]
                        print(f"   Blue Line Menu: {', '.join(descriptions)}")
                    
                    if gold_line:
                        descriptions = [item.get("MenuItemDescription", "Unknown") for item in gold_line]
                        print(f"   Gold Line Menu: {', '.join(descriptions)}")
                    
                    print()
                    print("🎉 Test completed successfully!")
                    return True
                    
                else:
                    error_text = await response.text()
                    print(f"❌ API request failed with status {response.status}")
                    print(f"📄 Response: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the standalone test."""
    print("Testing SchoolCafe API connection...")
    print("This test will verify that the API is accessible and returns data.")
    print()
    
    success = asyncio.run(test_schoolcafe_api_standalone())
    
    if success:
        print()
        print("✅ API test passed! The SchoolCafe integration should work correctly.")
        print()
        print("Next steps:")
        print("1. Copy the custom_components/schoolcafe folder to your Home Assistant")
        print("   config/custom_components/ directory")
        print("2. Restart Home Assistant")
        print("3. Go to Settings -> Devices & Services -> Add Integration")
        print("4. Search for 'SchoolCafe Menu' and follow the setup wizard")
    else:
        print()
        print("❌ API test failed. Please check:")
        print("- Your internet connection")
        print("- The School ID is correct")
        print("- The school uses SchoolCafe system")


if __name__ == "__main__":
    main()