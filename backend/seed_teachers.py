"""Register the demo professors (with profile pictures) and a demo student.

    python seed_teachers.py            # add anything missing
    python seed_teachers.py --reset    # wipe the database first
"""
import sys

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401 - registers the tables
from app.seed import MENTOR_PASSWORD, PROFESSORS, STUDENT_EMAIL, STUDENT_PASSWORD, seed_database

if "--reset" in sys.argv:
    Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    result = seed_database(db)

print(f"Seeded: {result['mentors_added']} professor(s) added, student added: {result['student_added']}\n")
print("Professor logins (password for all: %s)" % MENTOR_PASSWORD)
for p in PROFESSORS:
    print(f"  {p['name']:<20} {p['email']}")
print(f"\nDemo student login: {STUDENT_EMAIL} / {STUDENT_PASSWORD}")
