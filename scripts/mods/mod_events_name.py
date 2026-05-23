import codecs

with codecs.open('frontend/src/app/crm/events/[id]/page.tsx', 'r', 'utf-8') as f:
    c = f.read()

c = c.replace('event.name', 'event.title')

with codecs.open('frontend/src/app/crm/events/[id]/page.tsx', 'w', 'utf-8') as f:
    f.write(c)

print("Fixed event.title TS error")
