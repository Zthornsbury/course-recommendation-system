import MySQLdb

try:
    conn = MySQLdb.connect(host='localhost', user='root', passwd='')
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS course_recommendation")
    cursor.close()
    conn.close()
    print("Database created successfully!")
except Exception as e:
    print(f"Error: {e}")
