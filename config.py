from pathlib import Path
APP_NAME = "HE-DSS 4.5"
APP_SUBTITLE = "Prototyp analizy CALL–OBJECTIVE i oceny 12 determinant MDSM"
VERSION = '4.2'
ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "database" / "he_dss.db"
DATA_DIR = ROOT_DIR / "data"
UPLOADS_DIR = ROOT_DIR / "uploads"
ASSETS_DIR = ROOT_DIR / "assets"
