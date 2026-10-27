from olahrasa.settings import *

# URL khusus untuk pengujian Tracker
ROOT_URLCONF = "tracker.test_urls"

# Izinkan akses lokal
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]

# Khusus development lokal
DEBUG = True
