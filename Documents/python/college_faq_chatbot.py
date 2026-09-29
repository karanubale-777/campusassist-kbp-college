# ============================================================
# KBP COLLEGE VASHI - CAMPUSASSIST
# Improved Goal-Based College FAQ Chatbot
# ------------------------------------------------------------
# Install:
#     pip install customtkinter
#
# Run:
#     python college_faq_chatbot.py
#
# Main improvements:
# 1. KBP College Vashi is the fixed college.
# 2. Official KBP website is the primary information source.
# 3. Live pages are fetched when the student asks a question.
# 4. No generic/fake college data or invented fees/dates.
# 5. Goal-Based Agent is still the ONLY agent.
# 6. SQLite stores users and chat history.
# 7. Current information can be refreshed from the website.
# ============================================================

import os
import re
import sqlite3
import hashlib
import secrets
import threading
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
from datetime import datetime

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk


# ============================================================
# APP SETTINGS
# ============================================================

APP_NAME = "CampusAssist"
COLLEGE_NAME = "Karmaveer Bhaurao Patil College, Vashi"
COLLEGE_SHORT = "KBP College Vashi"
COLLEGE_LOCATION = "Vashi, Navi Mumbai, Maharashtra 400703"
COLLEGE_PHONE = "+91-022-27661210"
OFFICIAL_HOME = "https://www.kbpcollegevashi.edu.in/"

DB_NAME = "kbp_campusassist.db"
WEB_TIMEOUT = 12

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")  # base theme; all visible controls are overridden below

BG = "#F4EFE7"
CARD = "#FFFDF8"
CARD2 = "#E9DED0"
BORDER = "#CDBBA7"
BROWN = "#6F4E37"
BROWN_DARK = "#4B3324"
BROWN_LIGHT = "#8A684F"
WHITE = "#FFFFFF"
TEXT = "#3E3027"
MUTED = "#78695D"
GREEN = "#7C8A70"
RED = "#A64B3C"
GOLD = BROWN
GOLD2 = "#9A7253"
PINK = BROWN
PINK2 = BROWN_LIGHT
TEXTURE = "#EDE3D7"
TEXTURE_LIGHT = "#E1D3C3"
SIDEBAR = "#E6D8C8"
SIDEBAR_CARD = "#F1E8DD"
INPUT = "#FFFDF9"

# ============================================================
# TYPOGRAPHY
# ============================================================
# Larger, more expressive fonts so the interface is comfortable
# to read on a full-size desktop screen.
FONT_DISPLAY = "Georgia"
FONT_BODY = "Trebuchet MS"
FONT_UI = "Century Gothic"
FONT_MONO = "Consolas"

# IMPORTANT: Do not create CTkFont objects here.
# CustomTkinter creates CTkFont objects through Tkinter, and Tkinter needs
# a root window first. Tuple fonts are safe to define before the app starts.
FONT_DISPLAY_XL = (FONT_DISPLAY, 36, "bold")
FONT_DISPLAY_L = (FONT_DISPLAY, 28, "bold")
FONT_DISPLAY_M = (FONT_DISPLAY, 24, "bold")
FONT_UI_L = (FONT_UI, 15, "bold")
FONT_UI = (FONT_UI, 13)
FONT_BODY = (FONT_BODY, 14)
FONT_BODY_BOLD = (FONT_BODY, 14, "bold")
FONT_SMALL = (FONT_UI, 11)
FONT_MONO = (FONT_MONO, 10, "bold")



# ============================================================
# OFFICIAL KBP WEBSITE SOURCES
# ============================================================
# These URLs were selected from the official KBP College website.
# The chatbot fetches the page when that category is requested.

OFFICIAL_SOURCES = {
    "home": OFFICIAL_HOME,

    "courses":
        "https://www.kbpcollegevashi.edu.in/userPanel/"
        "DisplayPage.aspx?ItemID=ce&page=kq",

    "admission":
        "https://www.kbpcollegevashi.edu.in/Department/"
        "DisplayDeptPage.aspx?ItemID=eem&nDeptID=qi&page=cos",

    "examination":
        "https://www.kbpcollegevashi.edu.in/UserPanel/"
        "DisplayPage.aspx?ItemID=eg&page=gg",

    "scholarship":
        "https://www.kbpcollegevashi.edu.in/Department/"
        "DisplayDeptPage.aspx?ItemID=gkk&nDeptID=caa&page=eme",

    "library":
        "https://www.kbpcollegevashi.edu.in/Department/"
        "DisplayDeptPage.aspx?ItemID=ecs&nDeptID=ma&page=eq",

    "library_services":
        "https://www.kbpcollegevashi.edu.in/Department/"
        "DisplayDeptPage.aspx?ItemID=eee&nDeptID=ma&page=cok",

    "facilities":
        "https://www.kbpcollegevashi.edu.in/UserPanel/SSR.aspx",

    "notices": OFFICIAL_HOME,
    "contact": OFFICIAL_HOME,
}


# ============================================================
# DATABASE
# ============================================================

class Database:
    def __init__(self, db_name=DB_NAME):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.create_tables()
        self.ensure_default_admin()

    def create_tables(self):
        with self.lock:
            cur = self.conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    full_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_message TEXT NOT NULL,
                    detected_goal TEXT,
                    bot_response TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            self.conn.commit()

    @staticmethod
    def hash_password(password, salt):
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            120000
        ).hex()

    def ensure_default_admin(self):
        with self.lock:
            exists = self.conn.execute(
                "SELECT 1 FROM users WHERE username='admin'"
            ).fetchone()

            if exists:
                return

            salt = secrets.token_hex(16)
            password_hash = self.hash_password("admin123", salt)

            self.conn.execute("""
                INSERT INTO users
                (username, password_hash, salt, role, full_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "admin",
                password_hash,
                salt,
                "admin",
                "CampusAssist Administrator",
                self.now()
            ))
            self.conn.commit()

    @staticmethod
    def now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def create_user(self, username, password, full_name):
        username = username.strip().lower()
        full_name = full_name.strip()

        if not username or not password or not full_name:
            return False, "All fields are required."

        if len(password) < 6:
            return False, "Password must contain at least 6 characters."

        salt = secrets.token_hex(16)
        password_hash = self.hash_password(password, salt)

        try:
            with self.lock:
                self.conn.execute("""
                    INSERT INTO users
                    (username, password_hash, salt, role, full_name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    username,
                    password_hash,
                    salt,
                    "user",
                    full_name,
                    self.now()
                ))
                self.conn.commit()

            return True, "Account created successfully."

        except sqlite3.IntegrityError:
            return False, "Username already exists."

    def authenticate(self, username, password):
        row = self.conn.execute("""
            SELECT * FROM users
            WHERE lower(username)=lower(?)
        """, (username.strip(),)).fetchone()

        if not row:
            return None

        expected = self.hash_password(password, row["salt"])

        if expected == row["password_hash"]:
            return row

        return None

    def log_chat(self, user_id, message, goal, response):
        with self.lock:
            self.conn.execute("""
                INSERT INTO chat_logs
                (user_id, user_message, detected_goal, bot_response, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                message,
                goal,
                response,
                self.now()
            ))
            self.conn.commit()

    def get_chat_count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM chat_logs"
        ).fetchone()[0]


# ============================================================
# WEBSITE RETRIEVER
# ============================================================

class KBPWebsite:
    """
    Official-source retrieval tool.

    It does NOT decide what the user wants.
    The GoalBasedAgent decides the goal and then calls this class.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 CampusAssist-KBP/3.0"
    )

    def __init__(self):
        self.cache = {}
        self.cache_time = {}

    @staticmethod
    def clean_html(html):
        html = re.sub(
            r"<script[\s\S]*?</script>",
            " ",
            html,
            flags=re.I
        )

        html = re.sub(
            r"<style[\s\S]*?</style>",
            " ",
            html,
            flags=re.I
        )

        html = re.sub(
            r"<noscript[\s\S]*?</noscript>",
            " ",
            html,
            flags=re.I
        )

        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
        html = re.sub(r"</p\s*>", "\n", html, flags=re.I)
        html = re.sub(r"</li\s*>", "\n", html, flags=re.I)
        html = re.sub(r"</tr\s*>", "\n", html, flags=re.I)
        html = re.sub(r"<[^>]+>", " ", html)

        # The official website often places "Click Here" next to
        # document links. CampusAssist is a chatbot and these are not
        # interactive links, so do not show misleading "Click Here" text.
        html = re.sub(r"\bclick\s+here\b", " ", html, flags=re.I)

        replacements = {
            "&nbsp;": " ",
            "&amp;": "&",
            "&quot;": '"',
            "&#39;": "'",
            "&ndash;": "–",
            "&mdash;": "—",
            "&bull;": "•",
        }

        for old, new in replacements.items():
            html = html.replace(old, new)

        html = re.sub(r"[ \t]+", " ", html)
        html = re.sub(r"\n\s*\n+", "\n", html)

        return html.strip()

    def fetch(self, key, force=False):
        url = OFFICIAL_SOURCES.get(key, OFFICIAL_HOME)

        if not force and key in self.cache:
            return self.cache[key]

        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept-Language": "en-IN,en;q=0.9"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=WEB_TIMEOUT
            ) as response:

                raw = response.read(
                    1200000
                ).decode(
                    "utf-8",
                    errors="ignore"
                )

            text = self.clean_html(raw)

            # Remove repeated website navigation where possible.
            text = self.remove_noise(text)

            self.cache[key] = {
                "url": url,
                "text": text,
                "ok": True,
                "error": ""
            }

            return self.cache[key]

        except Exception as exc:
            result = {
                "url": url,
                "text": "",
                "ok": False,
                "error": str(exc)
            }

            self.cache[key] = result
            return result

    @staticmethod
    def remove_noise(text):
        lines = []

        for line in text.splitlines():
            line = re.sub(r"\s+", " ", line).strip()

            if not line:
                continue

            # Skip obvious repeated menu/footer fragments.
            if line.lower() in {
                "skip navigation links",
                "image image image image",
                "click here",
            }:
                continue

            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def terms(question):
        stop = {
            "what", "is", "are", "the", "a", "an", "of", "for",
            "to", "in", "at", "on", "and", "or", "can", "i",
            "me", "tell", "about", "please", "give", "show",
            "does", "do", "how", "where", "when", "which",
            "college", "kbp", "vashi", "please"
        }

        words = re.findall(
            r"[a-z0-9&+.-]+",
            question.lower()
        )

        return [
            w for w in words
            if len(w) > 2 and w not in stop
        ]

    def find_excerpts(self, text, question, limit=6):
        if not text:
            return []

        terms = self.terms(question)

        # Split around line breaks and sentence boundaries.
        chunks = re.split(
            r"\n+|(?<=[.!?])\s+",
            text
        )

        scored = []

        for chunk in chunks:
            chunk = chunk.strip()

            if len(chunk) < 30:
                continue

            low = chunk.lower()

            score = 0

            for term in terms:
                if term in low:
                    score += 1

            # Strong category-specific terms.
            if any(x in low for x in [
                "programme", "programmes", "course", "degree"
            ]):
                if any(x in terms for x in [
                    "course", "courses", "program", "programmes",
                    "degree", "bsc", "msc", "bcom", "bms", "bba"
                ]):
                    score += 3

            if any(x in low for x in [
                "admission", "pre-admission", "eligibility"
            ]):
                if "admission" in terms or "eligibility" in terms:
                    score += 3

            if "scholarship" in low:
                if "scholarship" in terms:
                    score += 3

            if "exam" in low or "time table" in low:
                if "exam" in terms or "examination" in terms:
                    score += 3

            if "library" in low:
                if "library" in terms or "book" in terms:
                    score += 3

            if score:
                scored.append((score, chunk))

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        result = []
        seen = set()

        for _, chunk in scored:
            key = chunk.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(chunk)

            if len(result) >= limit:
                break

        return result

    def get_answer_data(self, key, question):
        page = self.fetch(key)

        if not page["ok"]:
            return {
                "ok": False,
                "url": page["url"],
                "excerpts": [],
                "error": page["error"]
            }

        excerpts = self.find_excerpts(
            page["text"],
            question,
            limit=7
        )

        return {
            "ok": True,
            "url": page["url"],
            "excerpts": excerpts,
            "error": ""
        }


# ============================================================
# OFFICIAL COLLEGE PROFILE + COURSE CATALOG
# ============================================================
# The following descriptive information is based on the current
# official KBP College Vashi website and is used for direct answers
# inside CampusAssist.

COLLEGE_PROFILE = {
    "name": "Karmaveer Bhaurao Patil College, Vashi",
    "established": "1979",
    "campus": "5 acres in Vashi, Navi Mumbai",
    "status": "Empowered Autonomous College",
    "affiliation": "University of Mumbai",
    "recognition": "Recognized by the University Grants Commission (UGC)",
    "naac": "NAAC A++ (CGPA 3.51)",
    "iso": "ISO 9001:2015 certified",
    "star": "Star College Status from the Department of Biotechnology, Government of India",
    "award": "Best College Award by the University of Mumbai",
    "streams": ["Arts", "Commerce", "Science", "Management"],
    "address": "Vashi, Thane, Navi Mumbai, Maharashtra 400703",
    "phone": "+91-022-27661210",
    "email": "enquiry@kbpcollegevashi.edu.in",
}

COURSE_CATALOG = {
    "Arts": {
        "UG": ["B.A. (English)", "B.A. (Economics)", "B.A. (Geography)", "B.A. (Psychology)"],
        "PG": ["M.A. (Business Economics)", "M.A. (English)", "M.A. (Geography)", "M.A. (Psychology)"],
        "Research": ["Ph.D. (Humanities) / English", "Ph.D. (Humanities) / Economics"],
    },
    "Science": {
        "UG": [
            "B.Sc. (Microbiology)",
            "B.Sc. (Physics)",
            "B.Sc. (Chemistry)",
            "B.Sc. (Mathematics)",
            "B.Sc. (Biotechnology)",
            "B.Sc. (Information Technology)",
            "B.Sc. (Computer Science)",
            "B.Voc. (Food Technology)",
            "B.Sc. in Medical Lab Technology",
            "B.Sc. in Medical Imaging Technology",
        ],
        "PG": [
            "M.Sc. (Physics)",
            "M.Sc. (Organic Chemistry)",
            "M.Sc. (Inorganic Chemistry)",
            "M.Sc. (Analytical Chemistry)",
            "M.Sc. (Mathematics)",
            "M.Sc. (Microbiology)",
            "M.Sc. (Bioanalytical Science)",
            "M.Sc. (Information Technology)",
            "M.Sc. (Computer Science)",
            "M.Sc. (Data Science)",
            "M.Sc. (AI & ML)",
            "M.Sc. (Geoinformatics)",
        ],
        "Research": [
            "Ph.D. (Science) / Chemistry",
            "Ph.D. (Science) / Microbiology",
            "Ph.D. (Science) / Physics",
        ],
    },
    "Commerce": {
        "UG": [
            "B.Com. (Bachelor of Commerce)",
            "B.M.S. (Bachelor of Management Studies)",
            "B.Com. (Banking & Insurance)",
            "B.Com. (Accounting & Finance)",
            "B.Com. (Capital Market)",
            "BBA (Logistics & Supply Chain Management)",
        ],
        "PG": ["M.Com. (Accountancy)"],
        "Research": ["Ph.D. (Commerce) / Business Policy & Administration"],
    },
}


# ============================================================
# GOAL-BASED AGENT
# ============================================================

class GoalBasedAgent:
    """
    ONE intelligent agent:
        Perceive
        -> identify goal
        -> identify course/context
        -> select official source
        -> retrieve information
        -> respond
        -> update state

    The website retriever is only a tool.
    It is NOT another agent.
    """

    GOALS = {
        "Admission": {
            "admission", "apply", "application", "enroll",
            "enrollment", "eligibility", "pre admission",
            "pre-admission", "documents", "registration"
        },

        "Courses": {
            "course", "courses", "program", "programmes",
            "programme", "degree", "bsc", "msc", "bcom",
            "bms", "bba", "ba", "phd", "ph.d", "biotechnology",
            "microbiology", "physics", "chemistry", "mathematics",
            "computer", "information", "data", "aiml", "ai",
            "food", "medical", "imaging", "commerce", "psychology"
        },

        "Examination": {
            "exam", "examination", "exams", "result", "results",
            "marks", "atkt", "paper", "semester", "timetable",
            "time-table", "schedule"
        },

        "Scholarship": {
            "scholarship", "scholarships", "freeship",
            "financial", "aid", "minority", "merit",
            "divyang", "disability", "ebc", "obc", "vjnt",
            "sbc", "tribal"
        },

        "Library": {
            "library", "book", "books", "journal", "journals",
            "opac", "reading", "knowledge resource", "study"
        },

        "Facilities": {
            "facility", "facilities", "laboratory", "lab",
            "classroom", "computer", "sports", "gym",
            "gymkhana", "campus", "infrastructure", "canteen"
        },

        "Contact": {
            "contact", "phone", "telephone", "email",
            "address", "location", "office", "helpdesk"
        },

        "Notices": {
            "notice", "notices", "announcement", "announcements",
            "latest", "current", "today", "new", "update"
        },

        "Fees": {
            "fee", "fees", "cost", "payment", "tuition",
            "charges", "amount"
        },

        "Hostel": {
            "hostel", "accommodation", "stay", "residence"
        },

        "About College": {
            "about", "college", "campus", "history", "profile",
            "overview", "established", "autonomous", "accreditation",
            "accredited", "recognition", "affiliation", "background"
        }
    }

    COURSE_ALIASES = {
        "computer science": "B.Sc. Computer Science",
        "bsc cs": "B.Sc. Computer Science",
        "b.sc cs": "B.Sc. Computer Science",
        "information technology": "B.Sc. Information Technology",
        "bsc it": "B.Sc. Information Technology",
        "biotechnology": "B.Sc. Biotechnology",
        "microbiology": "B.Sc. Microbiology",
        "physics": "B.Sc. Physics",
        "chemistry": "B.Sc. Chemistry",
        "mathematics": "B.Sc. Mathematics",
        "food technology": "B.Voc. Food Technology",
        "medical lab": "B.Sc. Medical Lab Technology",
        "medical laboratory": "B.Sc. Medical Lab Technology",
        "medical imaging": "B.Sc. Medical Imaging Technology",
        "data science": "M.Sc. Data Science",
        "ai ml": "M.Sc. AI & ML",
        "aiml": "M.Sc. AI & ML",
        "m.sc ai": "M.Sc. AI & ML",
        "msc ai": "M.Sc. AI & ML",
        "bcom": "B.Com.",
        "b.com": "B.Com.",
        "bms": "B.M.S.",
        "banking insurance": "B.Com. Banking & Insurance",
        "accounting finance": "B.Com. Accounting & Finance",
        "capital market": "B.Com. Capital Market",
        "logistics": "BBA / B.Com. Logistics & Supply Chain Management",
        "psychology": "B.A. Psychology",
        "english": "B.A. English",
        "economics": "B.A. Economics",
        "geography": "B.A. Geography",
        "msc computer science": "M.Sc. Computer Science",
        "msc information technology": "M.Sc. Information Technology",
        "msc microbiology": "M.Sc. Microbiology",
        "msc mathematics": "M.Sc. Mathematics",
        "msc physics": "M.Sc. Physics",
        "msc chemistry": "M.Sc. Organic / Inorganic / Analytical Chemistry",
        "bioanalytical": "M.Sc. Bioanalytical Science",
        "geoinformatics": "M.Sc. Geoinformatics",
    }

    SOURCE_FOR_GOAL = {
        "Admission": "admission",
        "Courses": "courses",
        "Examination": "examination",
        "Scholarship": "scholarship",
        "Library": "library",
        "Facilities": "facilities",
        "Contact": "contact",
        "Notices": "notices",
        "Fees": "admission",
        "Hostel": "home",
        "About College": "home",
    }

    def __init__(self):
        self.web = KBPWebsite()
        self.current_goal = None
        self.selected_course = None
        self.state = "Waiting for user goal"
        self.next_action = "Listen to user"

    @staticmethod
    def clean(text):
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s&+.-]", " ", text)
        return set(text.split())

    def detect_goal(self, question):
        q = question.lower()
        words = self.clean(question)

        # Direct phrase checks first.
        if "time table" in q or "timetable" in q:
            return "Examination"

        if "admission" in q or "pre admission" in q:
            return "Admission"

        if "scholarship" in q or "freeship" in q:
            return "Scholarship"

        scores = {}

        for goal, keywords in self.GOALS.items():
            score = len(words.intersection(keywords))

            if score:
                scores[goal] = score

        if not scores:
            return "Unknown"

        return max(
            scores,
            key=scores.get
        )

    def detect_course(self, question):
        q = question.lower()

        # Longest aliases first.
        for alias, course in sorted(
            self.COURSE_ALIASES.items(),
            key=lambda x: len(x[0]),
            reverse=True
        ):
            if alias in q:
                return course

        return None

    def source_key(self, goal):
        return self.SOURCE_FOR_GOAL.get(
            goal,
            "home"
        )

    def build_about_answer(self):
        return (
            "🏛️ **About Karmaveer Bhaurao Patil College, Vashi**\n\n"
            f"**Established:** {COLLEGE_PROFILE['established']}\n"
            f"**Status:** {COLLEGE_PROFILE['status']}\n"
            f"**Affiliation:** {COLLEGE_PROFILE['affiliation']}\n"
            f"**Recognition:** {COLLEGE_PROFILE['recognition']}\n"
            f"**Accreditation:** {COLLEGE_PROFILE['naac']}\n"
            f"**Quality certification:** {COLLEGE_PROFILE['iso']}\n\n"
            "**College overview**\n"
            "Karmaveer Bhaurao Patil College, Vashi is a branch of Rayat Shikshan Sanstha. "
            "The college was established in 1979 and has a 5-acre campus in Vashi, Navi Mumbai. "
            "It offers education across Arts, Commerce, Science and Management, with undergraduate, "
            "postgraduate and research programmes listed on its official website.\n\n"
            "**Academic profile**\n"
            "Arts and Commerce programmes are offered at UG and PG levels. The Science stream includes "
            "UG and PG programmes, including areas such as Computer Science, Information Technology, "
            "Biotechnology, Microbiology, Bioanalytical Science, Data Science and AI & ML. The college "
            "also lists doctoral programmes in selected subjects.\n\n"
            "**Campus and student development**\n"
            "The official college site highlights academic and infrastructural development, skill building, "
            "innovation and entrepreneurship, social responsibility, scientific temperament, communication, "
            "human values and employability. The site also lists facilities and support areas such as the "
            "library, sports/gymkhana, laboratories, competitive-exam guidance, innovation activities and "
            "student-support cells.\n\n"
            "**Library**\n"
            "The Prof. Dr. N. D. Patil Knowledge Resource Center is described by the college as an 8,000 sq. ft. "
            "central library with more than 94,430 books, 24,043 unique titles, 89 journals/periodicals, "
            "Web OPAC, more than 195,809 e-books and 6,293 e-journals, along with access through N-LIST and DELNET.\n\n"
            "**Recognition and achievements**\n"
            f"The official site currently lists {COLLEGE_PROFILE['star']} and the {COLLEGE_PROFILE['award']}.\n\n"
            "📍 **Location:** " + COLLEGE_PROFILE["address"] + "\n"
            "☎️ **Phone:** " + COLLEGE_PROFILE["phone"] + "\n"
            "📧 **Email:** " + COLLEGE_PROFILE["email"] + "\n\n"
            "Ask me something more specific, such as **courses, admission, scholarships, exams, library, "
            "facilities or contact details**, and I’ll give you the relevant information in the chat."
        )

    def build_courses_answer(self):
        lines = [
            "📚 **Courses & Programmes at KBP College Vashi**",
            "",
            "The current official KBP College programme list includes Arts, Science and Commerce programmes at UG, PG and research levels.",
            "",
        ]

        for faculty, levels in COURSE_CATALOG.items():
            lines.append(f"🏷️ **Faculty of {faculty}**")
            for level, courses in levels.items():
                label = {"UG": "Undergraduate (UG)", "PG": "Postgraduate (PG)", "Research": "Research / Ph.D."}[level]
                lines.append(f"**{label}:**")
                for course in courses:
                    lines.append(f"• {course}")
                lines.append("")

        lines.extend([
            "💡 **Course selection:** Tell me the course name and I can continue with available admission, eligibility or related information.",
            "",
            "The programme list can change with the academic year, so the chatbot will use the latest official KBP information when you ask about current admissions."
        ])
        return "\n".join(lines)

    def build_response(self, goal, question, data):
        """Turn retrieved KBP content into a natural chatbot answer.

        The website is used as the information source, but the student
        receives the answer inside CampusAssist. A source URL is shown
        only when the student explicitly asks for the source/link.
        """
        q = question.lower()
        wants_source = any(term in q for term in (
            "source", "official website", "website link", "link", "url",
            "where did you get", "reference"
        ))

        if not data["ok"]:
            return (
                f"I couldn't reach the KBP College website right now. "
                f"Please try the same question again in a moment."
            )

        # Detailed, structured answers for the two core informational areas.
        if goal == "About College":
            answer = self.build_about_answer()
            if wants_source:
                answer += f"\n\n🔗 **Official source:** {data['url']}"
            return answer

        if goal == "Courses" and any(term in q for term in (
            "what courses", "courses available", "course available",
            "programmes offered", "programs offered", "courses offered",
            "all courses", "list courses", "list of courses",
            "what programs", "what programmes"
        )):
            answer = self.build_courses_answer()
            if wants_source:
                answer += f"\n\n🔗 **Official source:** {data['url']}"
            return answer

        excerpts = data["excerpts"]

        # Give a direct answer for common contact questions instead of
        # forcing the student to read a website page.
        if goal == "Contact" and any(x in q for x in (
            "phone", "telephone", "number", "contact", "address", "where"
        )):
            answer = (
                "📞 **KBP College Vashi Contact Details**\n\n"
                f"• College: {COLLEGE_NAME}\n"
                f"• Location: {COLLEGE_LOCATION}\n"
                f"• Phone: {COLLEGE_PHONE}\n\n"
                "If you need a particular office or department contact, "
                "tell me which one and I’ll look for it."
            )
            if wants_source:
                answer += f"\n\n🔗 Official source: {data['url']}"
            return answer

        if not excerpts:
            answer = (
                f"I couldn't find an exact answer for that in the current "
                f"KBP information I retrieved. Try asking it a little more "
                f"specifically — for example, mention the course, semester, "
                f"or admission/exam topic."
            )
            if wants_source:
                answer += f"\n\n🔗 Official source: {data['url']}"
            return answer

        heading = {
            "Admission": "🎓 **Admission Information**",
            "Courses": "📚 **Courses & Programmes**",
            "Examination": "📝 **Examination Information**",
            "Scholarship": "🎓 **Scholarships & Freeships**",
            "Library": "📖 **Library Information**",
            "Facilities": "🏫 **Campus & Facilities**",
            "Contact": "📞 **Contact Information**",
            "Notices": "📢 **Latest College Information**",
            "Fees": "💰 **Fee Information**",
            "Hostel": "🏠 **Hostel Information**",
            "About College": "🏛️ **About KBP College Vashi**",
        }.get(goal, "ℹ️ **KBP College Information**")

        # Remove raw website URLs from retrieved text. The chatbot should
        # answer the student, not repeatedly paste links.
        cleaned = []
        for excerpt in excerpts[:6]:
            excerpt = re.sub(r"https?://\S+", "", excerpt).strip()
            excerpt = re.sub(r"\s{2,}", " ", excerpt)
            if not excerpt:
                continue
            if len(excerpt) > 520:
                excerpt = excerpt[:520].rstrip() + "…"
            cleaned.append(excerpt)

        lines = [heading, ""]

        if self.selected_course:
            lines.append(f"🎯 Course context: **{self.selected_course}**")
            lines.append("")

        # Present the retrieved information as readable chat points.
        for excerpt in cleaned[:5]:
            lines.append(f"• {excerpt}")

        lines.append("")

        if goal in {"Admission", "Examination", "Scholarship", "Fees", "Notices"}:
            lines.append(
                "ℹ️ These details can change, so I’ll use the latest "
                "information available from KBP when you ask again."
            )
        else:
            lines.append(
                "If you want more detail, ask me a follow-up question "
                "and I’ll continue from here."
            )

        if wants_source:
            lines.extend([
                "",
                f"🔗 **Official source:** {data['url']}"
            ])

        return "\n".join(lines)

    def respond(self, question):
        question = question.strip()

        if not question:
            return "Unknown", "Please type your question."

        detected_goal = self.detect_goal(question)
        course = self.detect_course(question)

        if course:
            self.selected_course = course

        # A course-only follow-up should preserve the previous goal.
        course_only = (
            course is not None
            and detected_goal == "Courses"
            and len(question.split()) <= 6
        )

        if detected_goal != "Unknown" and not course_only:
            self.current_goal = detected_goal

        goal = self.current_goal or detected_goal

        # Friendly reset.
        if question.lower() in {
            "reset",
            "start over",
            "new question",
            "clear context"
        }:
            self.current_goal = None
            self.selected_course = None
            self.state = "Waiting for user goal"
            self.next_action = "Listen to user"
            return (
                "Reset",
                "Context cleared. What would you like to know "
                "about KBP College Vashi?"
            )

        if goal == "Unknown":
            self.state = "No clear goal detected"
            self.next_action = "Ask for clarification"

            return (
                "Unknown",
                "I can help with KBP College Vashi.\n\n"
                "Try asking about:\n"
                "• Courses and programmes\n"
                "• Admission\n"
                "• Examinations / ATKT timetable\n"
                "• Scholarships and freeships\n"
                "• Library\n"
                "• Facilities\n"
                "• Notices\n"
                "• Fees\n"
                "• Hostel / accommodation\n"
                "• Contact details"
            )

        self.state = f"Goal identified: {goal}"
        self.next_action = (
            f"Retrieve official KBP information for {goal}"
        )

        # Course-only question.
        if course_only and self.current_goal in {
            "Admission",
            "Fees",
            "Examination",
            "Scholarship"
        }:
            goal = self.current_goal

        # Make the retrieval question more precise.
        search_question = question

        if self.selected_course:
            if self.selected_course.lower() not in search_question.lower():
                search_question += (
                    " " + self.selected_course
                )

        key = self.source_key(goal)

        # Fees are especially time-sensitive. The official admission/
        # course pages may link to current fee information, but the
        # chatbot will never fabricate a number.
        data = self.web.get_answer_data(
            key,
            search_question
        )

        response = self.build_response(
            goal,
            search_question,
            data
        )

        self.state = "Official information retrieved"
        self.next_action = "Return answer inside chatbot"

        return goal, response

    def refresh(self):
        self.web.cache.clear()
        self.web.cache_time.clear()


# ============================================================
# UI HELPERS
# ============================================================

class RoundedCard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("corner_radius", 18)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", BORDER)
        kwargs.setdefault("fg_color", CARD)
        super().__init__(master, **kwargs)


class ScrollableChat(ctk.CTkScrollableFrame):
    pass


# ============================================================
# MAIN APPLICATION
# ============================================================

class CollegeChatbotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(
            "CampusAssist | KBP College Vashi"
        )

        self.geometry("1250x780")
        self.minsize(1000, 650)
        self.configure(fg_color=BG)

        self.db = Database()
        self.agent = GoalBasedAgent()

        self.current_user = None
        self.chat_messages = []
        self.login_mode = "login"

        self.protocol(
            "WM_DELETE_WINDOW",
            self.destroy
        )

        self.show_login()

    # ========================================================
    # COMMON
    # ========================================================

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def make_button(
        self,
        master,
        text,
        command,
        width=160,
        fg=GOLD,
        hover=GOLD2
    ):
        return ctk.CTkButton(
            master,
            text=text,
            command=command,
            width=width,
            height=42,
            corner_radius=12,
            fg_color=fg,
            hover_color=hover,
            text_color=WHITE if fg in (BROWN, BROWN_DARK, BROWN_LIGHT) else TEXT,
            border_width=1,
            border_color=BROWN_LIGHT if fg in (BROWN, BROWN_DARK, BROWN_LIGHT) else BORDER,
            font=ctk.CTkFont(
                family="Century Gothic",
                size=13,
                weight="bold"
            )
        )

    def add_texture(self, parent, accent=False):
        """Draw a subtle premium pattern behind the interface."""
        canvas = tk.Canvas(
            parent,
            bg=parent.cget("fg_color"),
            highlightthickness=0,
            bd=0
        )
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        def draw():
            canvas.delete("all")
            try:
                w = max(canvas.winfo_width(), 900)
                h = max(canvas.winfo_height(), 650)
            except Exception:
                w, h = 1200, 700

            # Fine dot matrix
            for x in range(24, w, 38):
                for y in range(22, h, 38):
                    canvas.create_oval(
                        x, y, x + 2, y + 2,
                        fill=TEXTURE_LIGHT if (x // 38 + y // 38) % 3 == 0 else TEXTURE,
                        outline=""
                    )

            # Large soft geometric rings
            canvas.create_oval(
                w - 360, -180, w + 100, 280,
                outline="#D6C7B7", width=2
            )
            canvas.create_oval(
                w - 290, -110, w + 30, 210,
                outline="#E0D4C6", width=1
            )
            canvas.create_line(
                0, h - 150, w * 0.42, h - 430,
                fill="#D9CBBB", width=1
            )
            canvas.create_line(
                0, h - 148, w * 0.42, h - 428,
                fill="#E5D9CC", width=1
            )

            if accent:
                canvas.create_arc(
                    -130, h - 270, 260, h + 120,
                    start=200, extent=95,
                    style="arc", outline="#B89A7A", width=2
                )

            return canvas

        parent.after(40, draw)
        return canvas

    # ========================================================
    # LOGIN / REGISTER
    # ========================================================

    def show_login(self):
        self.clear()

        self.configure(fg_color=SIDEBAR)
        container = ctk.CTkFrame(self, fg_color=BG)
        container.pack(expand=True, fill="both")
        self.add_texture(container, accent=True)

        # Decorative left brand panel
        brand = ctk.CTkFrame(
            container,
            fg_color=SIDEBAR,
            corner_radius=0,
            width=430
        )
        brand.place(relx=0, rely=0, relwidth=0.36, relheight=1)
        brand.pack_propagate(False)
        self.add_texture(brand, accent=True)

        ctk.CTkLabel(
            brand,
            text="CAMPUS",
            text_color=WHITE,
            font=ctk.CTkFont(family="Georgia", size=38, weight="bold")
        ).place(relx=0.12, rely=0.27, anchor="w")
        ctk.CTkLabel(
            brand,
            text="ASSIST",
            text_color=GOLD2,
            font=ctk.CTkFont(family="Georgia", size=38, weight="bold")
        ).place(relx=0.12, rely=0.34, anchor="w")
        ctk.CTkLabel(
            brand,
            text="KBP COLLEGE VASHI",
            text_color=MUTED,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold")
        ).place(relx=0.125, rely=0.43, anchor="w")
        ctk.CTkFrame(brand, width=92, height=3, fg_color=GOLD).place(relx=0.125, rely=0.47, anchor="w")
        ctk.CTkLabel(
            brand,
            text="Official-source information assistant\nfor students, applicants and visitors.",
            text_color=MUTED,
            justify="left",
            font=ctk.CTkFont(family="Trebuchet MS", size=14)
        ).place(relx=0.125, rely=0.53, anchor="w")

        # Login card
        card = RoundedCard(
            container,
            width=430,
            height=510,
            fg_color=WHITE,
            border_color=BORDER
        )
        card.place(relx=0.68, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card,
            text="WELCOME BACK",
            text_color=GOLD2,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold")
        ).pack(pady=(45, 4))

        ctk.CTkLabel(
            card,
            text="College Information Assistant",
            text_color=WHITE,
            font=ctk.CTkFont(family="Georgia", size=26, weight="bold")
        ).pack()

        ctk.CTkLabel(
            card,
            text="Sign in to access CampusAssist",
            text_color=MUTED,
            font=ctk.CTkFont(family="Century Gothic", size=12)
        ).pack(pady=(7, 28))

        self.login_user = ctk.CTkEntry(
            card, placeholder_text="Username", width=330, height=46,
            corner_radius=11, border_width=1, border_color=BROWN_LIGHT,
            fg_color=INPUT,
            text_color=TEXT,
            placeholder_text_color=BROWN_LIGHT,
            font=ctk.CTkFont(family="Trebuchet MS", size=14)
        )
        self.login_user.pack(pady=7)

        self.login_pass = ctk.CTkEntry(
            card, placeholder_text="Password", show="•", width=330, height=46,
            corner_radius=11, border_width=1, border_color=BROWN_LIGHT,
            fg_color=INPUT,
            text_color=TEXT,
            placeholder_text_color=BROWN_LIGHT,
            font=ctk.CTkFont(family="Trebuchet MS", size=14)
        )
        self.login_pass.pack(pady=7)

        self.full_name_entry = ctk.CTkEntry(
            card, placeholder_text="Full name", width=330, height=46,
            corner_radius=11, border_width=1, border_color=BROWN_LIGHT,
            fg_color=INPUT,
            text_color=TEXT,
            placeholder_text_color=BROWN_LIGHT,
            font=ctk.CTkFont(family="Trebuchet MS", size=14)
        )

        self.auth_button = self.make_button(card, "LOGIN  →", self.login, width=330)
        self.auth_button.pack(pady=(18, 8))

        self.switch_button = ctk.CTkButton(
            card, text="Create a new account", command=self.switch_auth_mode,
            fg_color="transparent", hover_color=CARD2, text_color=BROWN,
            width=300, height=34, font=ctk.CTkFont(family="Century Gothic", size=13, weight="bold")
        )
        self.switch_button.pack()

        ctk.CTkLabel(
            card, text="DEMO ADMIN  •  admin / admin123", text_color=MUTED,
            font=ctk.CTkFont(family="Consolas", size=10)
        ).pack(pady=(25, 0))

    def switch_auth_mode(self):
        if self.login_mode == "login":
            self.login_mode = "register"

            self.full_name_entry.pack(
                before=self.auth_button,
                pady=8
            )

            self.auth_button.configure(
                text="CREATE ACCOUNT",
                command=self.register
            )

            self.switch_button.configure(
                text="Already have an account? Login"
            )

        else:
            self.login_mode = "login"

            self.full_name_entry.pack_forget()

            self.auth_button.configure(
                text="LOGIN",
                command=self.login
            )

            self.switch_button.configure(
                text="Create a new account"
            )

    def login(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get()

        user = self.db.authenticate(
            username,
            password
        )

        if not user:
            messagebox.showerror(
                "Login Failed",
                "Invalid username or password."
            )
            return

        self.current_user = user
        self.agent = GoalBasedAgent()
        self.chat_messages = []

        self.show_chat()

    def register(self):
        full_name = self.full_name_entry.get().strip()
        username = self.login_user.get().strip()
        password = self.login_pass.get()

        ok, message = self.db.create_user(
            username,
            password,
            full_name
        )

        if ok:
            messagebox.showinfo(
                "Account Created",
                message
            )
            self.login_mode = "login"
            self.switch_auth_mode()

        else:
            messagebox.showerror(
                "Registration",
                message
            )

    # ========================================================
    # CHAT LAYOUT
    # ========================================================

    def show_chat(self):
        self.clear()

        # Main grid.
        self.grid_columnconfigure(
            1,
            weight=1
        )
        self.grid_rowconfigure(
            0,
            weight=1
        )

        self.build_sidebar()
        self.build_chat_area()

        self.add_bot_message(
            "Welcome to CampusAssist.\n\n"
            "I’m your Goal-Based FAQ Assistant "
            "for Karmaveer Bhaurao Patil College, Vashi.\n\n"
            "I use the official KBP College website as my primary "
            "source for current college information.\n\n"
            "What would you like to know?"
        )

    def build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, width=290, corner_radius=0, fg_color=SIDEBAR
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self.add_texture(sidebar, accent=True)

        # Brand header
        ctk.CTkLabel(
            sidebar, text="CAMPUSASSIST", text_color=GOLD2,
            font=ctk.CTkFont(family="Georgia", size=29, weight="bold")
        ).pack(anchor="w", padx=25, pady=(27, 2))
        ctk.CTkLabel(
            sidebar, text="KBP COLLEGE VASHI", text_color=BROWN_LIGHT,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold")
        ).pack(anchor="w", padx=27, pady=(0, 20))
        ctk.CTkFrame(sidebar, width=68, height=2, fg_color=GOLD).pack(anchor="w", padx=27, pady=(0, 20))

        self.make_button(sidebar, "＋  NEW CHAT", self.new_chat, width=240).pack(
            padx=25, pady=(0, 20)
        )

        ctk.CTkLabel(
            sidebar, text="QUICK ACCESS", text_color=BROWN_LIGHT,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold")
        ).pack(anchor="w", padx=29, pady=(4, 8))

        quick_questions = [
            "Tell me about the college",
            "What courses are offered?",
            "How can I apply for admission?",
            "What scholarships are available?",
            "Tell me about the library",
            "What facilities are available?",
            "Give me the college contact details",
        ]

        for i, question in enumerate(quick_questions, 1):
            btn = ctk.CTkButton(
                sidebar,
                text=f"{i:02d}   {question}",
                command=lambda q=question: self.use_quick_question(q),
                width=240, height=40, anchor="w",
                fg_color="transparent", hover_color=SIDEBAR_CARD,
                text_color=TEXT, corner_radius=9,
                font=ctk.CTkFont(family="Century Gothic", size=12)
            )
            btn.pack(padx=25, pady=1)

        ctk.CTkFrame(
            sidebar,
            height=1,
            fg_color=BORDER
        ).pack(
            fill="x",
            padx=22,
            pady=22
        )

        self.make_button(
            sidebar,
            "◉  Official KBP Website",
            lambda: webbrowser.open(OFFICIAL_HOME),
            width=225,
            fg=BROWN_DARK,
            hover=BROWN
        ).pack(
            padx=22,
            pady=5
        )

        self.make_button(
            sidebar,
            "↻  Refresh Website Data",
            self.refresh_data,
            width=225,
            fg=BROWN_DARK,
            hover=BROWN
        ).pack(
            padx=22,
            pady=5
        )

        bottom = ctk.CTkFrame(
            sidebar,
            fg_color="transparent"
        )
        bottom.pack(
            side="bottom",
            fill="x",
            padx=22,
            pady=22
        )

        name = self.current_user["full_name"]

        ctk.CTkLabel(
            bottom,
            text=f"◉  {name}",
            text_color=WHITE,
            anchor="w",
            font=ctk.CTkFont(family="Century Gothic", size=13, weight="bold")
        ).pack(
            fill="x",
            pady=(0, 8)
        )

        # Admin panel is intentionally placed at the bottom-left.
        # It is visible only for authenticated administrators.
        if self.current_user and self.current_user["role"] == "admin":
            self.make_button(
                bottom,
                "⚙  ADMIN PANEL",
                self.show_admin_stats,
                width=225,
                fg=BROWN_DARK,
                hover=BROWN
            ).pack(
                pady=(0, 7)
            )

        self.make_button(
            bottom,
            "Logout",
            self.logout,
            width=225,
            fg=BROWN_DARK,
            hover=BROWN
        ).pack()

    def show_about_college(self):
        self.clear()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        page = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        page.grid(row=0, column=0, sticky="nsew")
        self.add_texture(page, accent=True)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(page, fg_color=WHITE, height=92, corner_radius=0, border_width=1, border_color=BORDER)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        ctk.CTkFrame(header, height=3, fg_color=BROWN).pack(side="bottom", fill="x")

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=30, pady=14)
        ctk.CTkLabel(left, text="ABOUT THE COLLEGE", text_color=BROWN_DARK, font=ctk.CTkFont(family="Georgia", size=26, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text="KARMAVEER BHAURAO PATIL COLLEGE • VASHI", text_color=BROWN, font=ctk.CTkFont(family="Consolas", size=10, weight="bold")).pack(anchor="w")

        self.make_button(header, "← Back to Chat", self.show_chat, width=150, fg=BROWN_DARK, hover=BROWN).pack(side="right", padx=25)

        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", scrollbar_button_color=BROWN_LIGHT)
        scroll.grid(row=1, column=0, sticky="nsew", padx=35, pady=28)

        ctk.CTkLabel(scroll, text=COLLEGE_PROFILE["name"], text_color=BROWN_DARK, font=ctk.CTkFont(family="Georgia", size=30, weight="bold")).pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(scroll, text="Established in 1979 • Empowered Autonomous • University of Mumbai", text_color=BROWN, font=ctk.CTkFont(family="Century Gothic", size=13, weight="bold")).pack(anchor="w", pady=(0, 20))

        intro = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER)
        intro.pack(fill="x", pady=(0, 16))
        intro_text = (
            "Karmaveer Bhaurao Patil College, Vashi is a branch of Rayat Shikshan Sanstha. "
            "According to the official college website, it was established in 1979 and has a 5-acre campus in Vashi, Navi Mumbai. "
            "The college currently describes itself as an Empowered Autonomous College and lists programmes across Arts, Commerce, Science and Management, "
            "including undergraduate, postgraduate and research programmes. The college also highlights quality education, skills, innovation, research, "
            "social responsibility and holistic student development."
        )
        ctk.CTkLabel(intro, text=intro_text, text_color=TEXT, justify="left", anchor="w", wraplength=1020, font=ctk.CTkFont(family="Trebuchet MS", size=15)).pack(fill="x", padx=22, pady=20)

        stats = ctk.CTkFrame(scroll, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 16))
        facts = [
            ("1979", "Established"),
            ("5 Acres", "Campus"),
            ("A++", "NAAC Grade"),
            ("4", "Academic Streams"),
        ]
        for value, label in facts:
            card = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER, width=220, height=100)
            card.pack(side="left", fill="both", expand=True, padx=5)
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=value, text_color=BROWN, font=ctk.CTkFont(family="Georgia", size=24, weight="bold")).pack(pady=(15, 2))
            ctk.CTkLabel(card, text=label, text_color=MUTED, font=ctk.CTkFont(family="Century Gothic", size=11, weight="bold")).pack()

        details = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER)
        details.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(details, text="RECOGNITION & IDENTITY", text_color=BROWN, font=ctk.CTkFont(family="Consolas", size=11, weight="bold")).pack(anchor="w", padx=22, pady=(18, 8))
        recognition = (
            f"• {COLLEGE_PROFILE['naac']}\n"
            f"• {COLLEGE_PROFILE['iso']}\n"
            f"• {COLLEGE_PROFILE['star']}\n"
            f"• {COLLEGE_PROFILE['award']}\n"
            f"• {COLLEGE_PROFILE['recognition']}\n"
            f"• Affiliated with {COLLEGE_PROFILE['affiliation']}"
        )
        ctk.CTkLabel(details, text=recognition, text_color=TEXT, justify="left", anchor="w", wraplength=1020, font=ctk.CTkFont(family="Trebuchet MS", size=14)).pack(fill="x", padx=22, pady=(0, 20))

        contact = ctk.CTkFrame(scroll, fg_color=SIDEBAR, corner_radius=18, border_width=1, border_color=BORDER)
        contact.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(contact, text="CONTACT", text_color=BROWN_DARK, font=ctk.CTkFont(family="Georgia", size=19, weight="bold")).pack(anchor="w", padx=22, pady=(16, 7))
        ctk.CTkLabel(contact, text=f"📍 {COLLEGE_PROFILE['address']}\n☎️ {COLLEGE_PROFILE['phone']}\n📧 {COLLEGE_PROFILE['email']}", text_color=TEXT, justify="left", anchor="w", font=ctk.CTkFont(family="Trebuchet MS", size=14)).pack(anchor="w", padx=22, pady=(0, 18))

    def build_chat_area(self):
        area = ctk.CTkFrame(
            self,
            fg_color=BG,
            corner_radius=0
        )
        self.add_texture(area, accent=False)
        area.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=0,
            pady=0
        )

        area.grid_columnconfigure(
            0,
            weight=1
        )
        area.grid_rowconfigure(
            1,
            weight=1
        )

        header = ctk.CTkFrame(
            area,
            fg_color=WHITE,
            height=88,
            border_width=1,
            border_color=BORDER
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew"
        )
        header.grid_propagate(False)

        ctk.CTkFrame(header, height=2, fg_color=GOLD).pack(side="bottom", fill="x")

        title_box = ctk.CTkFrame(
            header,
            fg_color="transparent"
        )
        title_box.pack(
            side="left",
            padx=28,
            pady=16
        )

        ctk.CTkLabel(
            title_box,
            text="KBP COLLEGE  /  FAQ DESK",
            text_color=WHITE,
            font=ctk.CTkFont(
                family="Georgia",
                size=27,
                weight="bold"
            )
        ).pack(
            anchor="w"
        )

        ctk.CTkLabel(
            title_box,
            text="OFFICIAL-SOURCE GOAL-BASED AGENT   •   KBP VASHI",
            text_color=BROWN_LIGHT,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold")
        ).pack(
            anchor="w"
        )

        self.state_label = ctk.CTkLabel(
            header,
            text="GOAL: WAITING",
            text_color=GOLD2,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold")
        )
        self.state_label.pack(
            side="right",
            padx=28
        )

        self.chat = ScrollableChat(
            area,
            fg_color=BG
        )
        self.chat.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=25,
            pady=20
        )

        composer = ctk.CTkFrame(
            area,
            fg_color="transparent",
            height=112
        )
        composer.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 18)
        )

        composer.grid_columnconfigure(
            0,
            weight=1
        )

        self.input_box = ctk.CTkTextbox(
            composer,
            height=64,
            corner_radius=15,
            border_width=1,
            border_color=BROWN_LIGHT,
            fg_color=INPUT,
            text_color=BROWN_DARK,
            font=ctk.CTkFont(family="Trebuchet MS", size=15)
        )
        self.input_box.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10)
        )

        self.input_box.bind(
            "<Control-Return>",
            lambda event: self.send_message()
        )

        self.send_btn = self.make_button(
            composer,
            "Send  ➤",
            self.send_message,
            width=120
        )
        self.send_btn.grid(
            row=0,
            column=1
        )

        ctk.CTkLabel(
            composer,
            text="Ctrl + Enter to send • Information is retrieved from official KBP pages",
            text_color=MUTED,
            font=ctk.CTkFont(family="Century Gothic", size=10)
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            pady=(5, 0)
        )

    # ========================================================
    # CHAT MESSAGES
    # ========================================================

    def add_user_message(self, text):
        row = ctk.CTkFrame(
            self.chat,
            fg_color="transparent"
        )
        row.pack(
            fill="x",
            padx=8,
            pady=7
        )

        bubble = ctk.CTkFrame(
            row,
            fg_color="#E7D8C8",
            border_width=1,
            border_color="#B99E84",
            corner_radius=15
        )
        bubble.pack(
            anchor="e",
            padx=(100, 0)
        )

        ctk.CTkLabel(
            bubble,
            text=text,
            text_color=TEXT,
            justify="left",
            wraplength=700,
            font=ctk.CTkFont(family="Trebuchet MS", size=14)
        ).pack(
            padx=16,
            pady=11
        )

        self.chat._parent_canvas.yview_moveto(1)

    def add_bot_message(self, text):
        row = ctk.CTkFrame(
            self.chat,
            fg_color="transparent"
        )
        row.pack(
            fill="x",
            padx=8,
            pady=7
        )

        bubble = ctk.CTkFrame(
            row,
            fg_color=CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=15
        )
        bubble.pack(
            anchor="w",
            padx=(0, 100)
        )

        ctk.CTkLabel(
            bubble,
            text="✦  CAMPUSASSIST",
            text_color=GOLD2,
            font=ctk.CTkFont(
                family="Consolas",
                size=11,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=15,
            pady=(10, 2)
        )

        ctk.CTkLabel(
            bubble,
            text=text,
            text_color=TEXT,
            justify="left",
            anchor="w",
            wraplength=850,
            font=ctk.CTkFont(family="Trebuchet MS", size=14)
        ).pack(
            anchor="w",
            padx=16,
            pady=(2, 13)
        )

        self.chat._parent_canvas.yview_moveto(1)

    def send_message(self):
        message = self.input_box.get(
            "1.0",
            "end"
        ).strip()

        if not message:
            return

        self.input_box.delete(
            "1.0",
            "end"
        )

        self.add_user_message(message)

        self.send_btn.configure(
            state="disabled",
            text="Checking..."
        )

        self.state_label.configure(
            text="GOAL: ANALYSING..."
        )

        # Web requests run in a worker thread so the UI does not freeze.
        thread = threading.Thread(
            target=self.process_message,
            args=(message,),
            daemon=True
        )
        thread.start()

    def process_message(self, message):
        try:
            goal, response = self.agent.respond(
                message
            )

            self.db.log_chat(
                self.current_user["id"],
                message,
                goal,
                response
            )

            self.after(
                0,
                lambda: self.finish_message(
                    goal,
                    response
                )
            )

        except Exception as exc:
            response = (
                "Something went wrong while processing the question.\n\n"
                f"Error: {exc}"
            )

            self.after(
                0,
                lambda: self.finish_message(
                    "Error",
                    response
                )
            )

    def finish_message(self, goal, response):
        self.add_bot_message(
            response
        )

        self.state_label.configure(
            text=f"GOAL: {goal.upper()}"
        )

        self.send_btn.configure(
            state="normal",
            text="Send  ➤"
        )

    def use_quick_question(self, question):
        self.input_box.delete(
            "1.0",
            "end"
        )

        self.input_box.insert(
            "1.0",
            question
        )

        self.send_message()

    # ========================================================
    # CHAT CONTROLS
    # ========================================================

    def new_chat(self):
        self.agent = GoalBasedAgent()
        self.chat_messages = []

        for widget in self.chat.winfo_children():
            widget.destroy()

        self.state_label.configure(
            text="Goal: Waiting"
        )

        self.add_bot_message(
            "New conversation started.\n\n"
            "Ask me anything about KBP College Vashi."
        )

    def refresh_data(self):
        self.agent.refresh()

        messagebox.showinfo(
            "Website Data Refreshed",
            "Cached KBP website information has been cleared.\n\n"
            "The next question will retrieve fresh information "
            "from the official KBP website."
        )

    def logout(self):
        self.current_user = None
        self.agent = GoalBasedAgent()
        self.show_login()

    # ========================================================
    # ADMIN PANEL
    # ========================================================

    def show_admin_stats(self):
        self.clear()

        wrapper = ctk.CTkFrame(
            self,
            fg_color=BG
        )
        wrapper.pack(
            expand=True,
            fill="both",
            padx=40,
            pady=40
        )

        ctk.CTkLabel(
            wrapper,
            text="⚙  ADMIN PANEL",
            text_color=GOLD2,
            font=ctk.CTkFont(
                family="Georgia",
                size=30,
                weight="bold"
            )
        ).pack(
            anchor="w",
            pady=(10, 5)
        )

        ctk.CTkLabel(
            wrapper,
            text="CampusAssist administration overview",
            text_color=MUTED
        ).pack(
            anchor="w",
            pady=(0, 30)
        )

        card = RoundedCard(
            wrapper,
            width=450,
            height=180
        )
        card.pack(
            anchor="w"
        )

        count = self.db.get_chat_count()

        ctk.CTkLabel(
            card,
            text="TOTAL QUESTIONS",
            text_color=MUTED,
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        ).pack(
            pady=(35, 5)
        )

        ctk.CTkLabel(
            card,
            text=str(count),
            text_color=PINK,
            font=ctk.CTkFont(
                size=40,
                weight="bold"
            )
        ).pack()

        self.make_button(
            wrapper,
            "← Back to Chat",
            self.show_chat,
            width=180
        ).pack(
            anchor="w",
            pady=25
        )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":
    app = CollegeChatbotApp()
    app.mainloop()


