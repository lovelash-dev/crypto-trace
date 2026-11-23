import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
ETHERSCAN_API_URL = os.getenv("ETHERSCAN_API_URL", "https://api.etherscan.io/v2/api")
DEFAULT_CHAIN_ID = 1
DEFAULT_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
DEFAULT_MAX_TRANSACTIONS = 100
DEFAULT_MAX_DEPTH = 7
ATTRIBUTION_DB_PATH = DATA_DIR / "exchanges.json"
REQUEST_HEADERS = {"User-Agent": "CryptoTrace-Web/1.0", "Accept": "application/json"}
