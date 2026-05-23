f = open("frontend/src/app/crm/events/[id]/page.tsx", encoding="utf-8")
c = f.read()
f.close()

# Fix the import to add Download and TrendingUp and UserPlus (used in component)
c = c.replace(
    'import { Calendar, MapPin, Users, Clock, CheckCircle2, LayoutDashboard, ArrowLeft, Share2, QrCode, Mic, BookOpen, HandHeart, Save, Plus, X, Search } from "lucide-react";',
    'import { Calendar, MapPin, Users, Clock, CheckCircle2, LayoutDashboard, ArrowLeft, Share2, QrCode, Mic, BookOpen, HandHeart, Save, Plus, X, Search, Download, TrendingUp, UserPlus } from "lucide-react";',
)

# Fix SessionData type - find where it is
old_type = "type SessionData = {"
idx = c.find(old_type)
if idx > -1:
    # Find the closing }
    end_idx = c.find("\n};", idx)
    if end_idx > -1:
        old_block = c[idx : end_idx + 3]
        new_block = """type SessionData = {
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
    attendance_rate: number;
};"""
        c = c.replace(old_block, new_block)
        print("SessionData type updated")

f = open("frontend/src/app/crm/events/[id]/page.tsx", "w", encoding="utf-8")
f.write(c)
f.close()
print("Done")
