import codecs
import re

# Fix 1: events/[id]/page.tsx
with codecs.open("frontend/src/app/crm/events/[id]/page.tsx", "r", "utf-8") as f:
    c1 = f.read()

s1_old = "    const [visitorForm, setVisitorForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });"
s1_new = "    const [visitorForm, setVisitorForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });\n    const [refreshKey, setRefreshKey] = useState(0);"
c1 = c1.replace(s1_old, s1_new)

s2_old = "    }, [activeTab, sessionDate, token, id]);"
s2_new = "    }, [activeTab, sessionDate, token, id, refreshKey]);"
c1 = c1.replace(s2_old, s2_new)

s3_old = "            loadSessionData(sessionDate); // Reload the session to see the new attendance"
s3_new = "            setRefreshKey(k => k + 1);"
c1 = c1.replace(s3_old, s3_new)

with codecs.open("frontend/src/app/crm/events/[id]/page.tsx", "w", "utf-8") as f:
    f.write(c1)

# Fix 2: events/page.tsx
with codecs.open("frontend/src/app/crm/events/page.tsx", "r", "utf-8") as f:
    c2 = f.read()

# Update initial state typing if needed, actually it is automatically inferred.
# The issue is we pass `target_audience: 'ALL'` on line 168. Let's find it.
c2 = c2.replace(
    "setNewEvent({ name: '', description: '', event_type: 'PERMANENT', day_of_week: '0', month_day: '', fixed_date: '' });",
    "setNewEvent({ name: '', description: '', event_type: 'PERMANENT', target_audience: 'ALL', target_role_id: '', day_of_week: '0', month_day: '', fixed_date: '' });",
)
# We already did the above replace. Let's check where the TS error actually is.
# "target_audience does not exist in type SetStateAction..."
# It means the initial state did NOT have target_audience when it was inferred!
s4_old = """    const [newEvent, setNewEvent] = useState({
        name: '',
        description: '',
        event_type: 'PERMANENT',
        day_of_week: '0',
        month_day: '',
        fixed_date: ''
    });"""

# Since I modified this file with string replace before, maybe the old replace failed and it still doesn't have target_audience at the top!
s4_new = """    const [newEvent, setNewEvent] = useState({
        name: '',
        description: '',
        event_type: 'PERMANENT',
        target_audience: 'ALL',
        target_role_id: '',
        day_of_week: '0',
        month_day: '',
        fixed_date: ''
    });"""

c2 = c2.replace(s4_old, s4_new)  # In case it didn't replace before

with codecs.open("frontend/src/app/crm/events/page.tsx", "w", "utf-8") as f:
    f.write(c2)

print("TS errors fixed")
