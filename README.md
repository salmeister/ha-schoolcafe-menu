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

- **School ID or public menu URL**: The guest menu link from SchoolCafe (it contains `viewID`), or a school id. Example: `https://www.schoolcafe.com/PriorLake/menus?viewID=e73b1a29-a925-4fce-879b-0747773b891d`

### Optional Settings

- **Grade**: Student grade level (default: `09`)
- **Meal Type**: Type of meal (default: `Lunch`)
- **Serving Line**: Which serving line (default: `Main Line`). Several lines can be joined with `~`.
- **Person ID**: Optional person identifier (default: `null`)

### Advanced Settings

- **Menu Lines**: Comma-separated list of menu lines to track (default: `BLUE LINE, GOLD LINE`)
- **Days to Fetch**: Number of days ahead to retrieve (1-30, default: `7`)
- **Poll Interval**: How often to update data in minutes (15-1440, default: `60`)

## Finding Your School

SchoolCafe now publishes a public guest link for each school. Paste that whole URL into the School ID field.

1. Open your school's menu as a guest
2. Copy the address bar URL. It looks like `https://www.schoolcafe.com/YourDistrict/menus?viewID=...`
3. Paste that URL into the integration

The integration reads `viewID` and asks SchoolCafe which school, grade, meal, and serving lines that link uses. School ids can change; the guest link keeps working.

Prior Lake High School:

```
https://www.schoolcafe.com/PriorLake/menus?viewID=e73b1a29-a925-4fce-879b-0747773b891d
```

That link currently resolves to school id `ef44acd3-63cb-4d3b-828e-80ed1ef89779`. The older id `ef44acd3-63cb-6c9e-840a-80ed1ef89779` no longer returns a menu. Serving line `Main Lines` is also empty; the published name is `Main Line`.

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

### No Data / "No School"
- An empty menu is what the dashboard calls "No School". Weekends are empty on purpose.
- On a weekday, paste the public guest menu URL into the integration options. A saved school id can stop matching after SchoolCafe changes it.
- Serving line `Main Lines` no longer matches. Use `Main Line`, or leave the default and the integration will switch to the lines the school publishes.
- The sample dashboard must use `sensor.schoolcafe_blue_line_today` and `sensor.schoolcafe_gold_line_today`. Older `schoolcafe_fixed_` entities are not created anymore.

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