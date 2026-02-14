SITES = ["mefi", "askme", "meta", "fanfare", "music"]

INFODUMP_HOMEPAGE = "https://stuff.metafilter.com/infodump/"
INFODUMP_BASE_URL = "https://mefi.us/infodump/"

INFODUMP_FILENAMES = (
    ["usernames"]
    + [f"postdata_{site}" for site in SITES]
    + [f"commentdata_{site}" for site in SITES]
)

KEY_TIMESTAMP = "_published"

# need to keep js consistent with these
ACTIVITY_LEVELS = [1, 5, 10, 25, 50]
AGE_THRESHOLDS = [
    0,
    365,
    365 * 5,
    365 * 10,
    365 * 15,
    365 * 100,
]
TOP_N = [0.01, 0.05, 0.1]
