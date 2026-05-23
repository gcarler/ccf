f = open('frontend/src/app/crm/events/[id]/page.tsx', encoding='utf-8')
c = f.read()
f.close()

# Fix 1: Update SessionData type
old_type = """type SessionData = {
    event_id: number;
    session_date: string;
    assignments: Assignment[];
    metrics: Record<string, number>;"""

new_type = """type SessionData = {
    event_id: number;
    session_date: string;
    assignments: Assignment[];
    metrics: Record<string, number>;
    attendees: { member_id: number; name: string; role: string; scanned_at: string | null }[];
    absentees: { member_id: number; name: string; role: string; phone: string }[];
    total_absentees: number;
    absentees_truncated: boolean;
    total_attendance: number;
    total_expected: number;
    attendance_rate: number;"""

if 'total_absentees' not in c:
    c = c.replace(old_type, new_type)

# Fix 2: Add Download import
if 'Download' not in c:
    c = c.replace("import { ArrowLeft, MapPin, Calendar, Users, Save, Mic, UserPlus, X, Check, TrendingUp, QrCode }", 
                  "import { ArrowLeft, MapPin, Calendar, Users, Save, Mic, UserPlus, X, Check, TrendingUp, QrCode, Download }")

f = open('frontend/src/app/crm/events/[id]/page.tsx', 'w', encoding='utf-8')
f.write(c)
f.close()

# Fix 3: events/page.tsx - add missing imports
f2 = open('frontend/src/app/crm/events/page.tsx', encoding='utf-8')
c2 = f2.read()
f2.close()

# Add toast import
if "from 'react-toastify'" not in c2:
    c2 = c2.replace("import { apiFetch } from '@/lib/http';", "import { apiFetch } from '@/lib/http';\nimport { toast } from 'react-toastify';")

# Fix icon imports - find the lucide import line and add missing icons
import re
# Find existing import block
if 'Pencil' not in c2:
    c2 = c2.replace('ChevronRight\n} from \'lucide-react\';', 'ChevronRight,\n    Pencil,\n    Trash2,\n    MoreVertical\n} from \'lucide-react\';')

f2 = open('frontend/src/app/crm/events/page.tsx', 'w', encoding='utf-8')
f2.write(c2)
f2.close()
print("All TS import fixes applied")
