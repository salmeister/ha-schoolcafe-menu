# SchoolCafe Home Assistant Integration - Installation Guide

## ✅ Integration Complete!

Your SchoolCafe Home Assistant integration has been successfully created and tested. The API test confirms it can connect to SchoolCafe and retrieve menu data correctly.

## 📁 What Was Created

```
custom_components/schoolcafe/
├── __init__.py          # Integration setup and coordination
├── api.py              # SchoolCafe API client
├── config_flow.py      # User configuration interface
├── const.py            # Constants and default values
├── manifest.json       # Integration metadata
├── sensor.py           # Sensor entities for menu data
└── strings/
    └── en.json         # UI text and translations
```

## 🚀 Installation Steps

### 1. Copy Integration Files
Copy the entire `custom_components/schoolcafe` folder to your Home Assistant `config/custom_components/` directory:

```
config/
├── custom_components/
│   └── schoolcafe/        # ← Copy this entire folder here
└── configuration.yaml
```

### 2. Restart Home Assistant
Restart Home Assistant to load the new integration.

### 3. Add Integration
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "SchoolCafe Menu"
4. Click to add it

### 4. Configure Integration
Fill in the configuration form:

**Required:**
- **School ID**: paste the public guest menu URL, `https://www.schoolcafe.com/PriorLake/menus?viewID=e73b1a29-a925-4fce-879b-0747773b891d`

**Optional (with your current defaults):**
- **Grade**: `09`
- **Meal Type**: `Lunch`
- **Serving Line**: `Main Line`
- **Person ID**: (leave empty)

**Advanced Options:**
- **Menu Lines**: `BLUE LINE, GOLD LINE` (your requested lines)
- **Days to Fetch**: `7` (7 days ahead)
- **Poll Interval**: `60` (update every hour)

## 🔍 What You'll Get

### Sensor Entities
The integration will create sensors like:
- `sensor.schoolcafe_blue_line_today`
- `sensor.schoolcafe_blue_line_tomorrow`
- `sensor.schoolcafe_gold_line_today`
- `sensor.schoolcafe_gold_line_tomorrow`
- etc. (for each day up to your configured limit)

### Rich Attributes
Each sensor includes detailed attributes:
- Menu descriptions, calories, ratings
- Allergen information
- Nutrition facts (fat, carbs, protein)
- Serving sizes and ingredients
- Student ratings and like percentages

## 📱 Example Usage

### Dashboard Cards
```yaml
# Simple entity cards
- type: entity
  entity: sensor.schoolcafe_blue_line_today
  name: "Blue Line Today"

- type: entity
  entity: sensor.schoolcafe_gold_line_today
  name: "Gold Line Today"
```

### Detailed Menu Card
```yaml
# Markdown card with full details
- type: markdown
  content: |
    ## Today's Menu
    
    **Blue Line:** {{ states('sensor.schoolcafe_blue_line_today') }}
    **Gold Line:** {{ states('sensor.schoolcafe_gold_line_today') }}
    
    {% set blue_items = state_attr('sensor.schoolcafe_blue_line_today', 'items') %}
    {% if blue_items %}
    ### Blue Line Details:
    {% for item in blue_items %}
    - **{{ item.description }}** ({{ item.calories }} cal) ⭐{{ item.rating }}
    {% endfor %}
    {% endif %}
```

### Automation Example
```yaml
# Notify when favorite food is available
- alias: "Pizza Day Alert"
  trigger:
    - platform: state
      entity_id: 
        - sensor.schoolcafe_blue_line_today
        - sensor.schoolcafe_gold_line_today
  condition:
    - condition: template
      value_template: >
        {{ 'pizza' in trigger.to_state.state | lower }}
  action:
    - service: notify.mobile_app_your_phone
      data:
        message: "🍕 Pizza is on the menu today!"
```

## 🎯 Benefits Over Command Line Sensors

✅ **Native Integration** - Proper Home Assistant integration with device registry
✅ **Rich Attributes** - Full menu details, nutrition, allergens, ratings
✅ **Multiple Days** - Not just today, but week ahead
✅ **Configurable** - Easy to modify lines, days, polling via UI
✅ **Error Handling** - Robust API error handling and retries
✅ **User Friendly** - No need to maintain YAML configuration

## 🔧 Customization

You can easily customize the integration by:
- Adding more menu lines (e.g., "VEGETABLE VARIETY", "FRUIT VARIETY")
- Changing the number of days to fetch (1-30 days)
- Adjusting polling frequency (15 minutes to 24 hours)
- Modifying grade level or meal type

## 📞 Support

- Test successful: ✅ API connection verified  
- All files created: ✅ Integration complete
- Ready for installation: ✅ Copy to Home Assistant

The integration is ready to use! The API test confirmed it works correctly with your School ID and returns the same data format as your existing curl command.