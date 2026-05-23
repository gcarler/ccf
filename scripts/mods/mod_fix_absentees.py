f = open("backend/api/crm.py", encoding="utf-8")
c = f.read()
f.close()

old = '    attended_ids = {a["member_id"] for a in attendee_list}\r\n    absentees = []\r\n    \r\n    for m in expected_members:\r\n        if m.id not in attended_ids:\r\n            absentees.append({\r\n                "member_id": m.id,\r\n                "name": f"{m.first_name} {m.last_name}",\r\n                "role": m.church_role,\r\n                "phone": m.phone\r\n            })\r\n\r\n    return {\r\n        "event_id": event.id,\r\n        "session_date": session_date.isoformat(),\r\n        "assignments": assignments,\r\n        "metrics": metrics,\r\n        "attendees": attendee_list,\r\n        "absentees": absentees,\r\n        "total_attendance": len(attendee_list),\r\n        "total_expected": len(expected_members),\r\n        "attendance_rate": round(len(attendee_list) / len(expected_members) * 100, 1) if len(expected_members) > 0 else 0\r\n    }'

new = '    attended_ids = {a["member_id"] for a in attendee_list}\r\n    absentees_full = []\r\n    ABSENTEES_PREVIEW_LIMIT = 50\r\n    \r\n    for m in expected_members:\r\n        if m.id not in attended_ids:\r\n            absentees_full.append({\r\n                "member_id": m.id,\r\n                "name": f"{m.first_name} {m.last_name}",\r\n                "role": m.church_role,\r\n                "phone": m.phone\r\n            })\r\n\r\n    total_absentees = len(absentees_full)\r\n    absentees_preview = absentees_full[:ABSENTEES_PREVIEW_LIMIT]\r\n\r\n    return {\r\n        "event_id": event.id,\r\n        "session_date": session_date.isoformat(),\r\n        "assignments": assignments,\r\n        "metrics": metrics,\r\n        "attendees": attendee_list,\r\n        "absentees": absentees_preview,\r\n        "total_absentees": total_absentees,\r\n        "absentees_truncated": total_absentees > ABSENTEES_PREVIEW_LIMIT,\r\n        "total_attendance": len(attendee_list),\r\n        "total_expected": len(expected_members),\r\n        "attendance_rate": round(len(attendee_list) / len(expected_members) * 100, 1) if len(expected_members) > 0 else 0\r\n    }'

if old in c:
    c = c.replace(old, new)
    open("backend/api/crm.py", "w", encoding="utf-8").write(c)
    print("Fix 1 APPLIED: absentees limiter")
else:
    print("Pattern not found with CRLF - trying LF...")
    old_lf = old.replace("\r\n", "\n")
    new_lf = new.replace("\r\n", "\n")
    if old_lf in c:
        c = c.replace(old_lf, new_lf)
        open("backend/api/crm.py", "w", encoding="utf-8").write(c)
        print("Fix 1 APPLIED with LF")
    else:
        # Last resort: line-by-line replacement
        lines = c.split("\n")
        for i, line in enumerate(lines):
            if (
                "absentees = []" in line
                and i < len(lines) - 3
                and "for m in expected_members" in lines[i + 2]
            ):
                idx = i
                # Find the return block
                for j in range(i, len(lines)):
                    if '"attendance_rate"' in lines[j]:
                        end_idx = j
                        break
                replacement = [
                    "    absentees_full = []",
                    "    ABSENTEES_PREVIEW_LIMIT = 50",
                    "    ",
                    "    for m in expected_members:",
                    "        if m.id not in attended_ids:",
                    "            absentees_full.append({",
                    '                "member_id": m.id,',
                    '                "name": f"{m.first_name} {m.last_name}",',
                    '                "role": m.church_role,',
                    '                "phone": m.phone',
                    "            })",
                    "",
                    "    total_absentees = len(absentees_full)",
                    "    absentees_preview = absentees_full[:ABSENTEES_PREVIEW_LIMIT]",
                    "",
                    "    return {",
                    '        "event_id": event.id,',
                    '        "session_date": session_date.isoformat(),',
                    '        "assignments": assignments,',
                    '        "metrics": metrics,',
                    '        "attendees": attendee_list,',
                    '        "absentees": absentees_preview,',
                    '        "total_absentees": total_absentees,',
                    '        "absentees_truncated": total_absentees > ABSENTEES_PREVIEW_LIMIT,',
                    '        "total_attendance": len(attendee_list),',
                    '        "total_expected": len(expected_members),',
                    '        "attendance_rate": round(len(attendee_list) / len(expected_members) * 100, 1) if len(expected_members) > 0 else 0',
                    "    }",
                ]
                lines[idx : end_idx + 1] = replacement
                open("backend/api/crm.py", "w", encoding="utf-8").write(
                    "\n".join(lines)
                )
                print("Fix 1 APPLIED via line manipulation")
                break
        else:
            print("Fix 1 FAILED - requires manual edit")
