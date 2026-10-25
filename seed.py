"""Load DUMMY sample data (safe to publish). Usage: python seed.py"""
from app.crud import create_student, count_students
from app.database import get_connection, init_db

SAMPLE = [
    ("Aarav Sharma", "2004-05-17", "aarav.sharma@example.com", "+91 98100 00001", "Python Backend", "Ludhiana", "2024-07-01"),
    ("Diya Verma", "2006-02-11", "diya.verma@example.com", None, "Data Science", "Chandigarh", "2024-07-01"),
    ("Kabir Singh", "2003-11-30", "kabir.singh@example.com", "+91 98100 00003", "Python Backend", "Amritsar", "2024-08-12"),
    ("Meera Iyer", "2005-08-23", None, "+91 98100 00004", "Web Development", "Jalandhar", "2024-08-12"),
    ("Rohan Gupta", "2007-01-09", "rohan.gupta@example.com", "+91 98100 00005", "Data Science", "Patiala", "2025-01-06"),
    ("Sana Khan", "2005-12-02", "sana.khan@example.com", None, "Web Development", "Ludhiana", "2025-01-06"),
    ("Vikram Patel", "2002-06-19", "vikram.patel@example.com", "+91 98100 00007", "Python Backend", "Mohali", "2023-07-03"),
    ("Ananya Das", "2006-09-14", "ananya.das@example.com", "+91 98100 00008", "Data Science", "Bathinda", "2025-01-06"),
]

if __name__ == "__main__":
    init_db()
    conn = get_connection()
    if count_students(conn):
        print("Database already has students; skipping seed.")
    else:
        for n, dob, email, phone, course, addr, enr in SAMPLE:
            create_student(conn, dict(name=n, date_of_birth=dob, email=email, phone=phone,
                                      course=course, address=addr, enrollment_date=enr))
        print(f"Seeded {len(SAMPLE)} dummy students.")
    conn.close()
