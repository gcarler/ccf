import re

f = open("frontend/src/app/evangelism/events/page.tsx", encoding="utf-8").read()
f = f.replace(
    '<option value="PERMANENT">📅 Semanal / Rutinario</option>',
    '<option value="PERMANENT">Semanal / Rutinario</option>',
)
f = f.replace(
    '<option value="MONTHLY">🗓️ Mensual</option>',
    '<option value="MONTHLY">Mensual</option>',
)
f = f.replace(
    '<option value="ANNUAL">🎉 Anual</option>', '<option value="ANNUAL">Anual</option>'
)
f = f.replace(
    '<option value="ONCE">📌 Única Vez / Fecha Fija</option>',
    '<option value="ONCE">Única Vez / Fecha Fija</option>',
)
f = f.replace(
    '<option value="SPECIAL">⭐ Especial / Campaña</option>',
    '<option value="SPECIAL">Especial / Campaña</option>',
)
f = f.replace(
    '<option value="FARO">🏠 Faro en Casa / Célula</option>',
    '<option value="FARO">Faro en Casa / Célula</option>',
)
f = f.replace(
    '<option value="ONLINE">💻 En Línea / Transmisión</option>',
    '<option value="ONLINE">En Línea / Transmisión</option>',
)
open("frontend/src/app/evangelism/events/page.tsx", "w", encoding="utf-8").write(f)
print("Emojis removed")
