import sqlite3

conn = sqlite3.connect('mentorconnect_v3.db')
c = conn.cursor()
c.execute("""
    UPDATE bookings
    SET scheduled_at = datetime('now', '-10 minutes')
    WHERE status = 'confirmed'
      AND mentor_id = (SELECT id FROM mentors WHERE name = 'Vinita Bhandiwad')
      AND student_id = (SELECT id FROM users WHERE full_name = 'Swapnil Bhabal')
""")
conn.commit()
print('updated', c.rowcount, 'row(s)')