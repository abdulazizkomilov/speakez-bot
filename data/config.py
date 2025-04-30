import yaml
from pathlib import Path
from decouple import Config, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent

config = Config(RepositoryEnv(BASE_DIR / '.env'))
config_dir = BASE_DIR / "config"

with open(config_dir / "config.yml", 'r') as f:
    config_yaml = yaml.safe_load(f)

with open(config_dir / "chat_modes.yml", 'r') as f:
    chat_modes = yaml.safe_load(f)

with open(config_dir / "models.yml", 'r') as f:
    models = yaml.safe_load(f)

telegram_token = config("TELEGRAM_TOKEN")

openai_api_key_1 = config("KEY_1")
openai_api_key_2 = config("KEY_2")
openai_api_key_3 = config("KEY_3")
openai_api_key_4 = config("KEY_4")
openai_api_key_5 = config("KEY_5")

GOOGLE_API_KEY = config("GOOGLE_API_KEY")
TENOR_API_KEY = config("TENOR_API_KEY")

KAFKA_SERVER = config("KAFKA_SERVER")
KAFKA_PORT = config("KAFKA_PORT")
KAFKA_TOPIC = "telegram-messages"

REDIS_SERVER = config("REDIS_SERVER")
REDIS_PORT = config("REDIS_PORT")

mongodb_uri = config("MONGODB_URI")

API_URL_SPEECH = config("API_URL_SPEECH")
PAYMENT_URL = config("PAYMENT_URL")

SENTRY_URL = config("SENTRY_URL")

openai_api_keys = [
    openai_api_key_1,
    openai_api_key_2,
    openai_api_key_3,
    openai_api_key_4,
    openai_api_key_5
]

openai_api_base = config_yaml.get("openai_api_base", None)
allowed_telegram_usernames = config_yaml["allowed_telegram_usernames"]
new_dialog_timeout = config_yaml["new_dialog_timeout"]
enable_message_streaming = config_yaml.get("enable_message_streaming", True)
return_n_generated_images = config_yaml.get("return_n_generated_images", 1)
image_size = config_yaml.get("image_size", "512x512")
n_chat_modes_per_page = config_yaml.get("n_chat_modes_per_page", 5)
admins = config_yaml["admins_list"]

celery_broker_url = f"redis://{REDIS_SERVER}:{REDIS_PORT}"
celery_result_backend = f"redis://{REDIS_SERVER}:{REDIS_PORT}"

REQUIRED_CHANNELS = [
    {
        "channel_id": config("channel_id"),
        "link": config("link")
    }
]
