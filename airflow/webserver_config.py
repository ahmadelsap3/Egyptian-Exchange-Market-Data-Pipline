
import os
from airflow.www.fab_security.manager import AUTH_DB

basedir = os.path.abspath(os.path.dirname(__file__))

# Flask-WTF flag for CSRF
WTF_CSRF_ENABLED = True

# ----------------------------------------------------
# AUTHENTICATION CONFIG
# ----------------------------------------------------
# For read-only, remove the following line
# AUTH_TYPE = AUTH_DB

# ----------------------------------------------------
# THEME CONFIGURATION
# ----------------------------------------------------
# POWERED BY BOOTSWATCH
# ----------------------------------------------------
# valid themes: "amelia", "cerulean", "cosmo", "cyborg", "darkly", "flatly", "journal",
# "lumen", "paper", "readable", "sandstone", "simplex", "slate", "solar", "spacelab",
# "superhero", "united", "yeti"
APP_THEME = "darkly.css"
