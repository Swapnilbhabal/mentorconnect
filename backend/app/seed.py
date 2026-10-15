"""Demo data: real VIT Information Technology department faculty, one demo student, and one admin.

Idempotent: everything is matched by e-mail, so running it again only adds what is missing.

NOTE on honesty: these are real, named people (provided by the project owner from the college's
own faculty pages). Nothing about them is fabricated here -- no invented ratings, no invented
meeting links, no invented "Platform Verified" status, and no invented office-hours slots. Every
one of them starts as a completely clean mentor profile (unverified, zero reviews, no configured
meeting links, no structured availability) exactly as if they had just registered themselves.
They (or an admin on their behalf) fill in the rest for real through the app.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models.availability import AvailabilitySlot
from .models.mentor import Mentor
from .models.user import User
from .security import hash_password
from .services.avatars import avatar_for

# Weekday availability, explicitly confirmed by the project owner: "almost all faculty are free
# 4-6 PM on weekdays." Stored as UTC (10:30-12:30), since that's the whole app's storage
# convention -- 4-6 PM IST converts to exactly this. Saturday is deliberately left OUT: the
# owner said they don't know the exact Saturday hours, so nothing is guessed for it. Every
# mentor (or an admin) can add/correct their own real hours later via the app.
DEFAULT_WEEKDAY_SLOTS = [(w, "10:30", "12:30") for w in range(5)]  # Mon-Fri

MENTOR_PASSWORD = "VitMentor@123"
STUDENT_EMAIL = "student@mentorconnect.edu"
STUDENT_PASSWORD = "Student@123"
ADMIN_EMAIL = "admin@mentorconnect.edu"
ADMIN_PASSWORD = "Admin@123"

INSTITUTE_TYPE = "college"  # "Autonomous College Affiliated to University of Mumbai" per VIT's own letterhead
INSTITUTE_NAME = "Vidyalankar Institute of Technology (VIT)"

# Real faculty, Department of Information Technology, VIT -- provided by the project owner.
# "bio" is the short line shown on the mentor card list; "long_bio" is the fuller professional
# write-up (qualifications, experience, publications) shown only on that mentor's own detail
# page. Deliberately NOT included here: institute_unique_id (no staff ID was provided -- nothing
# fabricated), meet_link/teams_link/campus_location (nobody supplied their real personal room
# or office number), availability slots beyond the confirmed weekday default, and verification
# status (no actual ID/document was reviewed). All of that is left for each mentor -- or an
# admin -- to fill in for real via the app.
PROFESSORS = [
    {
        "email": "vinita.bhandiwad@vit.edu.in",
        "name": "Vinita Bhandiwad",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Cyber Security, IoT, Computer Networks",
        "bio": "Star Certified IoT Trainer and Expert; teaches computer networks and security with a focus on IoT systems.",
        "long_bio": "Holds an M.E. in Electronics & Telecommunication, a B.E. in Telecommunication Engineering and a Diploma in Electronics & Telecommunication. Over 5 years of teaching experience, with 12 technical papers published and 12 undergraduate project groups guided. A Star Certified Expert and Trainer for the Internet of Things (IoT) and a member of ISTE, with teaching interests spanning computer networks, security and IoT systems.",
        "years": 5,
    },
    {
        "email": "ajitkumar.khachane@vit.edu.in",
        "name": "Ajitkumar Khachane",
        "department": "Associate Professor \u00b7 Information Technology, VIT",
        "expertise": "Computer Organization & Architecture, Operating Systems, IoT, Embedded Systems",
        "bio": "Former Head of Department with over two decades of experience; guides student projects in embedded systems, IoT and image processing.",
        "long_bio": "Holds an M.E. and B.E. in Electronics, with 25+ years of teaching experience and over 10 years of administrative and managerial experience, including 13 years as Head of Department. Has published 27 technical papers and founded the department's Greek Olympiad event under the Information Technology Student Association. A life member of ISTE, with a strong focus on guiding student projects in embedded systems, IoT and image processing.",
        "years": 25,
    },
    {
        "email": "akshay.loke@vit.edu.in",
        "name": "Akshay Loke",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Data Structures & Algorithms, C Programming, Computer Engineering",
        "bio": "Member of the Career Counselling Committee; focuses on foundational programming and data structures education.",
        "long_bio": "Holds an M.E. and B.E. in Computer Engineering, with 10+ years of teaching experience and 4 technical papers published. A member of the Career Counselling Committee and the Staff Development Committee, with a teaching focus on data structures, algorithms and foundational programming.",
        "years": 10,
    },
    {
        "email": "dhanashree1.tamhane@vit.edu.in",
        "name": "Dhanashree Tamhane",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Data Analytics, Business Intelligence, SQL, Python, Power BI",
        "bio": "Brings industry experience in data migration, financial compliance and analytics; bridges business and data analysis for students.",
        "long_bio": "Holds a B.E. in Electronics & Telecommunication and an M.E. in Engineering Management from the Stevens Institute of Technology, USA. Brings 3+ years of industry experience in data migration, financial compliance and analytics using SQL, Python, Power BI and Excel, with 1 technical paper published. Focuses on connecting business and data analysis for students through case studies and project-based learning.",
        "years": 3,
    },
    {
        "email": "bhanu.tekwani@vit.edu.in",
        "name": "Bhanu Tekwani",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Java, Python, Software Testing, E-Commerce",
        "bio": "Certified Star Python Instructor with experience in corporate technical training across Java, .NET and software testing.",
        "long_bio": "Holds an M.E. in Computer Engineering, a B.E. and a Diploma in Information Technology, with 5+ years of teaching experience and 16 technical papers published. A certified Star Python Instructor and recipient of the Teacher of Developing Era award at an international conference, with corporate training experience across C, Java, .NET and software testing.",
        "years": 5,
    },
    {
        "email": "debarati.ghosal@vit.edu.in",
        "name": "Debarati Ghosal",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Databases, Algorithms, Cloud Computing, Web Development",
        "bio": "Guides students publishing in IEEE conferences; holds Google Cloud and AWS certifications in cloud development.",
        "long_bio": "Holds an M.E. in Computer Science and a B.E. in Information Technology, with 10+ years of teaching experience and 12 technical papers published. An active lifetime member of ISTE and a Google Certified Professional Cloud Developer and AWS educator, who has guided students publishing research in IEEE conferences across web programming, cloud computing and Android development.",
        "years": 10,
    },
    {
        "email": "deepali.shrikhande@vit.edu.in",
        "name": "Deepali Shrikhande",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Cyber Security, Software Testing, Project Management",
        "bio": "VIT alumna focused on security, software testing and software engineering project management.",
        "long_bio": "Holds an M.E. in Information Technology and a B.E. in Computer Science from VIT, with 5+ years of teaching experience and 10 technical papers published. Focuses on cyber security, software testing and software engineering project management, with a teaching style centred on real-world case studies and interactive classroom techniques.",
        "years": 5,
    },
    {
        "email": "digambar.puri@vit.edu.in",
        "name": "Dr. Digambar Puri",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Machine Learning, Signal Processing, Computer Networks, Python",
        "bio": "PhD in EEG-based Alzheimer's detection; researches machine learning and biomedical signal processing.",
        "long_bio": "Holds a Ph.D., M.Tech. and B.Tech. in Electronics & Telecommunication, with 11+ years of teaching experience, 5+ years of administrative experience and 20 technical papers published. Doctoral research focused on detecting Alzheimer's disease using EEG signals, with work published in Elsevier, Springer, IEEE and PLOS ONE; research interests include machine learning, biomedical signal processing and data science.",
        "years": 11,
    },
    {
        "email": "dilip.motwani@vit.edu.in",
        "name": "Dr. Dilip Motwani",
        "department": "Professor \u00b7 Information Technology, VIT",
        "expertise": "Information Security, Blockchain, E-Commerce, Algorithms",
        "bio": "Examinations In-charge at VIT with two decades of experience in networking, security and blockchain.",
        "long_bio": "Holds a Ph.D. in Technology, an M.E. and a B.E. in Computer Engineering, with 20+ years of teaching experience and 15+ years of administrative experience. Has authored 1 book, published 30 technical papers and guided 15 doctoral and masters students. Currently serves as Examinations In-charge at VIT, with teaching and research interests in information security, blockchain and algorithms.",
        "years": 20,
    },
    {
        "email": "kanchan.dhuri@vit.edu.in",
        "name": "Dr. Kanchan Dhuri",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "IoT, Embedded Systems, Computer Organization & Architecture",
        "bio": "Leads the student project committee; guides teams for hackathons and technical paper presentations.",
        "long_bio": "Holds an M.E. and B.E. in Electronics & Telecommunication, with 5+ years of teaching experience, 15 technical papers published and 12 undergraduate project groups guided. A member of ISTE and recipient of the Best NSS Student award, who leads the student project committee and guides teams for hackathons and technical paper presentations.",
        "years": 5,
    },
    {
        "email": "neha.kudu@vit.edu.in",
        "name": "Dr. Neha Kudu",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Image Processing, Digital Signal Processing, Computer Networks",
        "bio": "Departmental placement coordinator; mentors UG projects in sensor networks, IoT and network security.",
        "long_bio": "Holds an M.E. and B.E. in Electronics & Telecommunication along with a Ph.D., bringing 5+ years of teaching experience and up to 5 years of research and industrial experience, with 8 technical papers published. Serves as departmental placement coordinator and mentors undergraduate projects in sensor networks, IoT and network security.",
        "years": 5,
    },
    {
        "email": "rasika.ransing@vit.edu.in",
        "name": "Dr. Rasika Ransing",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Machine Learning, Deep Learning, NLP",
        "bio": "Research interests in AI, NLP and deep learning; active member of the Career Counseling and Placement Committee.",
        "long_bio": "Holds an M.E. and B.E. in Electronics & Telecommunication, with up to 5 years of teaching experience and 2 technical papers published. Research interests include artificial intelligence, natural language processing and deep learning, with past project work in question-answering systems and claim-detection using NLP; an active member of the Career Counseling and Placement Committee.",
        "years": 5,
    },
    {
        "email": "rugved.deolekar@vit.edu.in",
        "name": "Dr. Rugved Deolekar",
        "department": "Associate Professor \u00b7 Information Technology, VIT",
        "expertise": "Data Structures & Algorithms, Machine Learning, Java, Deep Learning",
        "bio": "UG Program Coordinator with industry HR/L&D experience; PhD in machine learning and deep learning.",
        "long_bio": "Holds a Ph.D., M.E. and B.E. in Computer Engineering, with 17 years of teaching experience and 5+ years of industry experience, including a prior role as Manager, HR and Learning & Development. Has published 25 technical papers and holds 2 patents, with doctoral research in machine learning and deep learning; has served as UG Program Coordinator for the Computer Engineering department.",
        "years": 17,
    },
    {
        "email": "santosh.tamboli@vit.edu.in",
        "name": "Dr. Santosh Tamboli",
        "department": "Associate Professor \u00b7 Information Technology, VIT",
        "expertise": "Machine Learning, Deep Learning, Data Structures, Computer Graphics",
        "bio": "NBA Coordinator; guides final-year projects in machine learning applications like fraud and malware detection.",
        "long_bio": "Holds an M.E. in Computer Engineering and a B.E. in Information Technology, with 15+ years of teaching experience and 12 technical papers published. Formerly a corporate trainer in Oracle SQL and PL/SQL for Siemens; serves as NBA Coordinator and guides final-year machine learning projects, including indoor navigation for the visually impaired, malware detection and ATM fraud detection.",
        "years": 15,
    },
    {
        "email": "shashikant.mahajan@vit.edu.in",
        "name": "Dr. Shashikant Mahajan",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Computer Networks, Network Security, Operating Systems",
        "bio": "PhD in covert communication over TCP/IP; co-inventor on a published Indian patent application.",
        "long_bio": "Holds a Ph.D. and M.E. in Computer Engineering and a B.E. in Computer Engineering, with 15+ years of teaching experience, 5+ years of administrative experience and 13+ technical papers published. Doctoral research (2025) developed a covert-communication paradigm over IPv4 using TCP/IP header fields, resulting in two Scopus-indexed journal papers and co-inventorship on a published Indian patent application; began at VIT as a Laboratory Assistant before moving through Network Engineer and faculty roles.",
        "years": 15,
    },
    {
        "email": "sushopti.gawade@vit.edu.in",
        "name": "Dr. Sushopti Gawade",
        "department": "Professor \u00b7 Information Technology, VIT",
        "expertise": "UI/UX, AI/ML, Data Science",
        "bio": "25+ years of teaching; supervises PhD and postgraduate research in AI, decision support systems and UI/UX.",
        "long_bio": "Holds a Ph.D., M.E. and B.E. in Computer Science & Engineering, with 25+ years of teaching experience, 5+ years of administrative experience, 88 technical papers published and 16 doctoral/masters projects guided. Supervises PhD and postgraduate research in AI/ML, data science, UI/UX and decision support systems, currently guiding scholars across healthcare, agriculture and education applications.",
        "years": 25,
    },
    {
        "email": "varsha.bhosale@vit.edu.in",
        "name": "Dr. Varsha Bhosale",
        "department": "Professor & Vice Principal \u00b7 Information Technology, VIT",
        "expertise": "Database Systems, Data Science, Machine Learning, Image Processing",
        "bio": "Vice Principal of VIT; Chartered Engineer and Fellow of the Institution of Engineers, India.",
        "long_bio": "Holds a Ph.D. in Technology, an M.E. in Information Technology and a B.E. in Computer Engineering, with 20+ years of teaching experience, 15+ years of administrative and managerial experience and 17 technical papers published, including 2 authored books and 11 masters students guided. A Chartered Engineer (IEI), Fellow of the Institution of Engineers India and recipient of the Lions Club International Teaching Students Excellence Award (2015); currently serves as Vice Principal of VIT, with research interests in databases, data science and machine learning.",
        "years": 20,
    },
    {
        "email": "pallavi.kharat@vit.edu.in",
        "name": "Pallavi Kharat",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Data Science, Machine Learning, Wireless Communication",
        "bio": "Focuses on bridging theory with practical data visualization and analytical tools.",
        "long_bio": "Holds a B.E. and M.E. in Electronics & Telecommunication, with 16+ years of teaching experience and over 20 technical papers published. Focuses on bridging theoretical concepts with practical data visualization and analytical tools, with teaching interests spanning data science, machine learning and wireless communication.",
        "years": 16,
    },
    {
        "email": "swapnil.gite@vit.edu.in",
        "name": "Swapnil Gite",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "IoT, Embedded Systems, Biomedical Instrumentation",
        "bio": "Former Research Engineer at an IIT Bombay-incubated medtech startup; focuses on IoT-based smart healthcare systems.",
        "long_bio": "Holds a B.E. in Electronics & Telecommunication and an M.Tech. from VJTI, Mumbai, with 3+ years of industry experience and 2 technical papers published. Previously a Research Engineer at Acuradyne Medical Systems, an IIT Bombay (SINE)-incubated healthtech startup, working on embedded hardware and IoT-enabled healthcare devices; focuses on IoT, embedded systems and biomedical instrumentation.",
        "years": 3,
    },
    {
        "email": "shruti.agrawal@vit.edu.in",
        "name": "Shruti Agrawal",
        "department": "Assistant Professor \u00b7 Information Technology, VIT",
        "expertise": "Java, Python, Data Science, Machine Learning",
        "bio": "Departmental placement coordinator; teaches programming with a project-based learning approach.",
        "long_bio": "Holds an M.E. in Computer Engineering and a B.Tech. in Computer Science & Engineering, with 5+ years of teaching experience and 6 technical papers published. Joined VIT in 2018 and serves as a departmental placement coordinator, teaching Java and Python with a hands-on, project-based learning approach.",
        "years": 5,
    },
]


def seed_database(db: Session) -> dict:
    added_mentors = 0
    for p in PROFESSORS:
        if db.scalar(select(User).where(User.email == p["email"])):
            continue
        avatar = avatar_for(p["name"])
        user = User(
            email=p["email"],
            full_name=p["name"],
            hashed_password=hash_password(MENTOR_PASSWORD),
            role="mentor",
            avatar_url=avatar,
        )
        db.add(user)
        db.flush()
        mentor = Mentor(
            user_id=user.id,
            name=p["name"],
            department=p["department"],
            expertise=p["expertise"],
            bio=p["bio"],
            long_bio=p.get("long_bio"),
            avatar_url=avatar,
            years_experience=p["years"],
            institute_type=INSTITUTE_TYPE,
            institute_name=INSTITUTE_NAME,
            campus_location=p.get("campus_location"),
            # base_rating_* intentionally left at their zero defaults -- no invented reviews.
        )
        db.add(mentor)
        db.flush()
        for weekday, start_time, end_time in DEFAULT_WEEKDAY_SLOTS:
            db.add(AvailabilitySlot(mentor_id=mentor.id, weekday=weekday, start_time=start_time, end_time=end_time))
        added_mentors += 1

    added_student = False
    if not db.scalar(select(User).where(User.email == STUDENT_EMAIL)):
        db.add(
            User(
                email=STUDENT_EMAIL,
                full_name="Demo Student",
                hashed_password=hash_password(STUDENT_PASSWORD),
                role="student",
                avatar_url=avatar_for("Demo Student"),
            )
        )
        added_student = True

    added_admin = False
    if not db.scalar(select(User).where(User.email == ADMIN_EMAIL)):
        db.add(
            User(
                email=ADMIN_EMAIL,
                full_name="Platform Admin",
                hashed_password=hash_password(ADMIN_PASSWORD),
                role="admin",
                avatar_url=avatar_for("Platform Admin"),
            )
        )
        added_admin = True

    db.commit()
    return {"mentors_added": added_mentors, "student_added": added_student, "admin_added": added_admin}