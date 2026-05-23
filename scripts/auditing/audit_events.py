import re

f = open("backend/api/crm.py", encoding="utf-8").read()

# 1. Inventory all event/faro routes
routes = re.findall(r'@router\.(get|post|put|patch|delete)\("(/[^"]+)"', f)
event_routes = [
    (m, r)
    for m, r in routes
    if any(k in r.lower() for k in ["event", "faro", "session", "visitor", "scanner"])
]
print("=== EVENT API ROUTES ===")
for m, r in event_routes:
    print(f"  {m.upper():8} /crm{r}")

# 2. Check for missing UniqueConstraints in EventAttendance
models_f = open("backend/models.py", encoding="utf-8").read()
print("\n=== DB MODEL CHECKS ===")

# Check EventAttendance for unique constraint
ea_idx = models_f.find("class EventAttendance")
ea_block = models_f[ea_idx : ea_idx + 600]
print("UniqueConstraint in EventAttendance:", "UniqueConstraint" in ea_block)
print("attended field in EventAttendance:", "attended" in ea_block)
print("ondelete CASCADE in EventAttendance:", "ondelete" in ea_block)

# Check FaroSeason exists in models
print("\nFaroSeason in models.py:", "class FaroSeason" in models_f)
print("GloryHouseSession in models.py:", "class GloryHouseSession" in models_f)
print("GloryHouseAttendance in models.py:", "class GloryHouseAttendance" in models_f)
print(
    "day_of_week in GloryHouse:",
    "day_of_week"
    in models_f[
        models_f.find("class GloryHouse") : models_f.find("class GloryHouse") + 500
    ],
)

# Check for crm.py issues
print("\n=== BACKEND LOGIC CHECKS ===")
print("Duplicate attendance guard in fast_checkin:", "already_exists" in f)
print("Absentees limit (ABSENTEES_PREVIEW_LIMIT):", "ABSENTEES_PREVIEW_LIMIT" in f)
print("update_event endpoint:", "def update_event" in f)
print("delete_event endpoint:", "def delete_event" in f)
print("get_global_event_analytics:", "def get_global_event_analytics" in f)
print("list_faro_seasons:", "def list_faro_seasons" in f)
print("create_faro_session:", "def create_faro_session" in f)
print("add_faro_attendance:", "def add_faro_attendance" in f)
print("get_faro_analytics:", "def get_faro_analytics" in f)

# Check for potential N+1 queries
print("\n=== PERFORMANCE CHECKS ===")
n_plus_one = [
    line.strip()
    for line in f.split("\n")
    if "db.query" in line and "for " in f[max(0, f.find(line) - 200) : f.find(line)]
]
print(f"Potential N+1 patterns found: {len(n_plus_one)}")
for n in n_plus_one[:5]:
    print(f"  > {n[:80]}")
