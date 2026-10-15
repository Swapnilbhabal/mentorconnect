"""One-time, safe content update: sets the `long_bio` field (the full professional write-up,
shown only on each mentor's detail page) for the 20 real VIT faculty, from seed.py -- WITHOUT
touching anything else. The short `bio` field used on the card list, every account, booking,
rating, availability slot, and any other profile edit is completely unaffected.

Run once from the backend folder (with the venv active):
    python backfill_bios.py

Safe to run more than once -- it always just sets long_bio to the current seed.py value for
each matched email, so running it twice produces the same end state as running it once.
"""
from app.database import SessionLocal
from app.models.mentor import Mentor
from app.models.user import User
from app.seed import PROFESSORS

with SessionLocal() as db:
    updated = 0
    skipped = []
    for p in PROFESSORS:
        user = db.query(User).filter(User.email == p["email"]).first()
        if not user or not user.mentor_profile:
            skipped.append(p["email"])
            continue
        user.mentor_profile.long_bio = p.get("long_bio")
        updated += 1
    db.commit()

print(f"Updated long_bio for {updated} mentor(s).")
if skipped:
    print(f"Skipped {len(skipped)} (not found in this database yet): {', '.join(skipped)}")