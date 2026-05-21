import sqlite3
import random

db_path = 'd:/ccf/ccf_v2.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing
cursor.execute("SELECT COUNT(*) FROM testimonials")
count = cursor.fetchone()[0]
print(f"Current testimonials count: {count}")

# Generate 10 testimonials
emotions = ["Gratitud", "Gozo", "Paz", "Esperanza", "Fe", "Amor"]
contents = [
    "Desde que llegué a esta iglesia, mi vida cambió por completo. Encontré una familia espiritual que me apoya.",
    "Dios restauró mi matrimonio cuando pensaba que todo estaba perdido. ¡Gloria a Dios!",
    "La enseñanza aquí es tan profunda y aplicable a la vida diaria. He crecido muchísimo espiritualmente.",
    "Fui sanado de una enfermedad grave. Sé que las oraciones de la congregación fueron clave.",
    "Mis hijos aman ir a la escuela dominical. Es increíble verlos crecer en su fe.",
    "El ministerio de alabanza me conecta directamente con el cielo cada domingo.",
    "Participar en los grupos pequeños me ha dado amigos genuinos y un sentido de pertenencia.",
    "Llegué con depresión y ansiedad, pero el amor de Dios que se refleja en esta casa me sanó.",
    "Servir en el ministerio ha sido la mejor decisión. Siento que mi vida tiene propósito.",
    "Las misiones y el trabajo social de la iglesia me inspiran a ser mejor cristiano cada día."
]

testimonials_to_insert = []
for i in range(10):
    content = contents[i]
    emotion = random.choice(emotions)
    testimonials_to_insert.append((1, content, emotion, 1))

cursor.executemany("INSERT INTO testimonials (author_id, content, emotion, is_approved) VALUES (?, ?, ?, ?)", testimonials_to_insert)
conn.commit()

cursor.execute("SELECT COUNT(*) FROM testimonials")
new_count = cursor.fetchone()[0]
print(f"New testimonials count: {new_count}")

conn.close()
print("Successfully inserted 10 testimonials.")
