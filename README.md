# SchoolCafe Menu Integration for Home Assistant

A custom Home Assistant integration that connects to the SchoolCafe API to retrieve and display school lunch menus as sensor entities.

## Features

- ✅ Retrieves daily menu information from SchoolCafe API
- ✅ Configurable menu lines (e.g., "BLUE LINE", "GOLD LINE")
- ✅ Support for multiple days ahead (configurable 1-30 days)
- ✅ Rich attributes including nutrition info, allergens, ratings
- ✅ Configurable polling intervals
- ✅ Easy setup through Home Assistant UI

## Installation

### Method 1: Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/schoolcafe` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "SchoolCafe Menu" and click to add it

### Method 2: HACS (if/when published)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Search for "SchoolCafe Menu"
4. Click Install

## Configuration

### Required Settings

- **School ID**: Your school's unique identifier (e.g., `ef44acd3-63cb-6c9e-840a-80ed1ef89779`)

### Optional Settings

- **Grade**: Student grade level (default: `09`)
- **Meal Type**: Type of meal (default: `Lunch`)
- **Serving Line**: Which serving line (default: `Main Lines`)
- **Person ID**: Optional person identifier (default: `null`)

### Advanced Settings

- **Menu Lines**: Comma-separated list of menu lines to track (default: `BLUE LINE, GOLD LINE`)
- **Days to Fetch**: Number of days ahead to retrieve (1-30, default: `7`)
- **Poll Interval**: How often to update data in minutes (15-1440, default: `60`)

## Finding Your School ID

To find your School ID:

1. Go to your school's SchoolCafe website
2. Open browser developer tools (F12)
3. Go to the Network tab
4. Navigate to the menu page
5. Look for API calls to `webapis.schoolcafe.com`
6. Find the `SchoolId` parameter in the URL

Example API URL:
```
https://webapis.schoolcafe.com/api/CalendarView/GetDailyMenuitemsByGrade?SchoolId=ef44acd3-63cb-6c9e-840a-80ed1ef89779&...
```

## Sensor Entities

The integration creates sensor entities for each combination of:
- Menu line (e.g., "BLUE LINE", "GOLD LINE")  
- Day offset (Today, Tomorrow, Wednesday, etc.)

### Entity Names
- `sensor.schoolcafe_blue_line_today`
- `sensor.schoolcafe_blue_line_tomorrow`
- `sensor.schoolcafe_gold_line_today`
- etc.

### Entity State
The sensor state contains a comma-separated list of menu item descriptions for that line and day.

### Entity Attributes
Each sensor includes rich attributes:

- `serving_date`: Date of the menu (YYYY-MM-DD)
- `category`: Menu line name
- `serving_line`: Serving line configuration
- `school_id`: Your school ID
- `grade`: Grade level
- `meal_type`: Meal type
- `item_count`: Number of menu items
- `items`: Detailed array of menu items with:
  - `description`: Item name/description
  - `calories`: Calorie count
  - `allergens`: List of allergens
  - `nutrition`: Nutrition facts (fat, carbs, protein)
  - `rating`: Average rating
  - `likes_percentage`: Percentage of students who like it
  - `serving_size`: Serving size information
  - `ingredients`: Ingredient list
  - `thumbnail_url`: Image URL if available

## Example Usage

### Displaying Today's Menu

```yaml
# In your dashboard
- type: entity
  entity: sensor.schoolcafe_blue_line_today
  name: "Blue Line Today"
  
- type: entity  
  entity: sensor.schoolcafe_gold_line_today
  name: "Gold Line Today"
```

### Creating Menu Cards

```yaml
# Lovelace card showing detailed menu
- type: markdown
  content: |
    ## Today's Blue Line Menu
    **{{ states('sensor.schoolcafe_blue_line_today') }}**
    
    {% for item in state_attr('sensor.schoolcafe_blue_line_today', 'items') %}
    - **{{ item.description }}** ({{ item.calories }} cal)
      - Rating: {{ item.rating }}/5 ⭐
      - Allergens: {{ item.allergens | join(', ') if item.allergens else 'None' }}
    {% endfor %}
```

### Automations

```yaml
# Notify when pizza is on the menu
- alias: "Pizza Day Notification"
  trigger:
    - platform: state
      entity_id: sensor.schoolcafe_blue_line_today
  condition:
    - condition: template
      value_template: "{{ 'pizza' in states('sensor.schoolcafe_blue_line_today') | lower }}"
  action:
    - service: notify.mobile_app_your_phone
      data:
        message: "🍕 Pizza is on the menu today!"
```

## Testing

Before installing, you can test the integration using the provided test script:

```bash
cd ha-schoolcafe-menu
python test_integration.py
```

Make sure to update the `school_id` in the test script with your actual School ID.

## Troubleshooting

### Connection Issues
- Verify your School ID is correct
- Check that your school uses the SchoolCafe system
- Ensure Home Assistant can reach the internet

### No Data
- Some schools may not have menus available for certain dates
- Check the Home Assistant logs for API errors
- Verify your grade and meal type settings

### Sensor Not Updating
- Check the poll interval setting
- Look for errors in Home Assistant logs
- Try reloading the integration

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/salmeister/ha-schoolcafe-menu/issues) page.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is unofficial and not affiliated with SchoolCafe or Primero Edge. Use at your own risk.