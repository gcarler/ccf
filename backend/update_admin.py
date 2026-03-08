from sqlalchemy import create_engine, text
# The actual DB path from .env is sqlite:///../ccf_v2.db
engine = create_engine('sqlite:///d:/ccf/ccf_v2.db')
with engine.connect() as conn:
    # Use 'role' column instead of is_admin/is_staff
    conn.execute(text("UPDATE users SET role = 'admin' WHERE email = 'admin@ccf.com'"))
    conn.commit()
    print('User role updated to admin for admin@ccf.com')
