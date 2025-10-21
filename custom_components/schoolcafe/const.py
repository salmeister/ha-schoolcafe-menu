"""Constants for the SchoolCafe integration."""

DOMAIN = "schoolcafe"

# Configuration keys
CONF_SCHOOL_ID = "school_id"
CONF_GRADE = "grade"
CONF_MEAL_TYPE = "meal_type"
CONF_SERVING_LINE = "serving_line"
CONF_PERSON_ID = "person_id"
CONF_MENU_LINES = "menu_lines"
CONF_DAYS_TO_FETCH = "days_to_fetch"
CONF_POLL_INTERVAL = "poll_interval"

# Default values
DEFAULT_GRADE = "09"
DEFAULT_MEAL_TYPE = "Lunch"
DEFAULT_SERVING_LINE = "Main Lines"
DEFAULT_PERSON_ID = None
DEFAULT_MENU_LINES = ["BLUE LINE", "GOLD LINE"]
DEFAULT_DAYS_TO_FETCH = 7
DEFAULT_POLL_INTERVAL = 60  # 1 hour in minutes
MIN_POLL_INTERVAL = 15  # Minimum 15 minutes
MAX_POLL_INTERVAL = 1440  # Maximum 24 hours

# API constants
SCHOOLCAFE_API_BASE = "https://webapis.schoolcafe.com/api"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Sensor constants
ATTR_SERVING_DATE = "serving_date"
ATTR_CATEGORY = "category"
ATTR_SERVING_LINE = "serving_line"
ATTR_CALORIES = "calories"
ATTR_ALLERGENS = "allergens"
ATTR_RATING = "rating"
ATTR_LIKES_PERCENTAGE = "likes_percentage"
ATTR_THUMBNAIL_URL = "thumbnail_url"
ATTR_SERVING_SIZE = "serving_size"
ATTR_INGREDIENTS = "ingredients"
ATTR_NUTRITION = "nutrition"
