import codecs

with codecs.open('frontend/src/app/crm/events/[id]/page.tsx', 'r', 'utf-8') as f:
    c = f.read()

bad_export = """            const res = await apiFetch<Blob>(`/crm/events/${event.id}/sessions/${sessionDate}/export`, {
                token,
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(res);"""

good_export = """            const res = await apiFetch<string>(`/crm/events/${event.id}/sessions/${sessionDate}/export`, { token });
            const blob = new Blob([res], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);"""

c = c.replace(bad_export, good_export)

with codecs.open('frontend/src/app/crm/events/[id]/page.tsx', 'w', 'utf-8') as f:
    f.write(c)

print("Export blob logic fixed")
