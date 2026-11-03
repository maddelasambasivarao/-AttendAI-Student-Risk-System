import sqlite3
conn = sqlite3.connect('attendai.db')
c = conn.cursor()
c.execute('DELETE FROM users WHERE username != "admin"')
conn.commit()
conn.close()
print("CLEANED!")