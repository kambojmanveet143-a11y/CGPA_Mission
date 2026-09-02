import sqlite3
import hashlib
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CGPA Mission",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# DATABASE LOCATION
# ============================================================

# Database ALWAYS stays beside TimeTable.py.
# This prevents the password/data disappearing problem.

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cgpa_mission.db"


# ============================================================
# DEFAULT SUBJECTS
# ============================================================

DEFAULT_SUBJECTS = [
    "Data Structures",
    "Operating Systems",
    "Computer Architecture",
    "Cybersecurity",
    "Information Systems"
]


# ============================================================
# 5-6 PM COMPUTER CENTER OPTIONS
# ============================================================

CENTER_OPTIONS = [
    "💻 Coding Practice",
    "🔥 Data Structures Practice",
    "🔥 Operating Systems Practice",
    "🐍 Python Practice",
    "📊 Pandas / NumPy Practice",
    "🎓 College Project",
    "📝 Assignment / Notes",
    "🧠 Practice Questions",
    "🔁 Revision",
    "☕ Break / Refresh"
]


# ============================================================
# STUDY TYPES
# ============================================================

STUDY_TYPES = [
    "📖 Concept Study",
    "📝 Practice Questions",
    "🔁 Revision",
    "🧠 Active Recall",
    "💻 Coding / Practical",
    "🧪 Test / Mock"
]


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    return sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_database():

    conn = get_db()
    cur = conn.cursor()

    # ---------------- STUDENTS ----------------

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            goal TEXT NOT NULL,
            gate_enabled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    # ---------------- SUBJECTS ----------------

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            subject TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(username, subject)
        )
        """
    )

    # ---------------- STUDY RECORDS ----------------

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS study_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            study_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            hours REAL NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            study_type TEXT NOT NULL
        )
        """
    )

    # ---------------- COMPUTER CENTER ----------------

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS center_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            study_date TEXT NOT NULL,
            activity TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


init_database()


# ============================================================
# PASSWORD HASH
# ============================================================

def hash_password(password):

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# ============================================================
# CREATE ACCOUNT
# ============================================================

def create_account(
    username,
    password,
    goal,
    gate_enabled,
    subject_list
):

    username = username.strip()

    conn = get_db()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            INSERT INTO students
            (
                username,
                password_hash,
                goal,
                gate_enabled,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                hash_password(password),
                goal,
                int(gate_enabled),
                datetime.now().isoformat()
            )
        )

        for subject in subject_list:

            subject = subject.strip()

            if subject:

                cur.execute(
                    """
                    INSERT OR IGNORE INTO subjects
                    (
                        username,
                        subject,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        username,
                        subject,
                        datetime.now().isoformat()
                    )
                )

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        conn.rollback()

        return False

    finally:

        conn.close()


# ============================================================
# LOGIN
# ============================================================

def login_user(
    username,
    password
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            username,
            goal,
            gate_enabled
        FROM students
        WHERE username = ?
        AND password_hash = ?
        """,
        (
            username.strip(),
            hash_password(password)
        )
    )

    result = cur.fetchone()

    conn.close()

    return result


# ============================================================
# GET STUDENT
# ============================================================

def get_student(username):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            username,
            goal,
            gate_enabled
        FROM students
        WHERE username = ?
        """,
        (username,)
    )

    result = cur.fetchone()

    conn.close()

    return result


# ============================================================
# GET SUBJECTS
# ============================================================

def get_subjects(username):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT subject
        FROM subjects
        WHERE username = ?
        ORDER BY id
        """,
        (username,)
    )

    rows = cur.fetchall()

    conn.close()

    return [
        row[0]
        for row in rows
    ]


# ============================================================
# ADD SUBJECT
# ============================================================

def add_subject(
    username,
    subject
):

    subject = subject.strip()

    if not subject:
        return False

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO subjects
        (
            username,
            subject,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            username,
            subject,
            datetime.now().isoformat()
        )
    )

    changed = cur.rowcount > 0

    conn.commit()
    conn.close()

    return changed


# ============================================================
# DELETE SUBJECT
# ============================================================

def delete_subject(
    username,
    subject
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM subjects
        WHERE username = ?
        AND subject = ?
        """,
        (
            username,
            subject
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# SAVE STUDY RECORD
# ============================================================

def save_study_record(
    username,
    study_date,
    subject,
    hours,
    completed,
    study_type
):

    conn = get_db()
    cur = conn.cursor()

    # Remove old record for the same date and subject.
    cur.execute(
        """
        DELETE FROM study_records
        WHERE username = ?
        AND study_date = ?
        AND subject = ?
        """,
        (
            username,
            str(study_date),
            subject
        )
    )

    # Insert latest record.
    cur.execute(
        """
        INSERT INTO study_records
        (
            username,
            study_date,
            subject,
            hours,
            completed,
            study_type
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            str(study_date),
            subject,
            float(hours),
            int(completed),
            study_type
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# SAVE COMPUTER CENTER ACTIVITY
# ============================================================

def save_center_activity(
    username,
    study_date,
    activity
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO center_records
        (
            username,
            study_date,
            activity
        )
        VALUES (?, ?, ?)
        """,
        (
            username,
            str(study_date),
            activity
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# LOAD STUDY RECORDS
# ============================================================

def load_records(username):

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            study_date AS Date,
            subject AS Subject,
            hours AS Hours,
            completed AS Completed,
            study_type AS StudyType
        FROM study_records
        WHERE username = ?
        ORDER BY study_date DESC
        """,
        conn,
        params=(username,)
    )

    conn.close()

    return df


# ============================================================
# DATE HELPERS
# ============================================================

def monday_of(day):

    return day - timedelta(
        days=day.weekday()
    )


def sunday_of(day):

    return monday_of(day) + timedelta(
        days=6
    )


def days_until_november():

    today = date.today()

    november = date(
        today.year,
        11,
        1
    )

    if today > november:

        november = date(
            today.year + 1,
            11,
            1
        )

    return (
        november - today
    ).days


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:

    st.session_state.logged_in = False


if "username" not in st.session_state:

    st.session_state.username = ""


# ============================================================
# SIMPLE PROFESSIONAL THEME
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F7F5FF;
    }

    [data-testid="stSidebar"] {
        background-color: #29234F;
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #E5DFFF;
        border-radius: 15px;
        padding: 12px;
    }

    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# LOGIN SCREEN
# ============================================================

if not st.session_state.logged_in:

    st.title("🎓 CGPA MISSION")

    st.subheader(
        "Personal Academic Planner"
    )

    st.info(
        "🏆 Highest CGPA   •   "
        "🔥 DS + OS Priority   •   "
        "📊 Progress Analysis   •   "
        "🎯 Optional GATE"
    )

    login_tab, create_tab = st.tabs(
        [
            "🔐 Login",
            "✨ Create Account"
        ]
    )

    # --------------------------------------------------------
    # LOGIN TAB
    # --------------------------------------------------------

    with login_tab:

        st.write(
            "### Welcome Back 👋"
        )

        login_username = st.text_input(
            "Username",
            key="login_username"
        )

        login_password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "🚀 Login",
            use_container_width=True,
            type="primary"
        ):

            if (
                not login_username.strip()
                or not login_password
            ):

                st.warning(
                    "Username aur password dono enter karo."
                )

            else:

                student = login_user(
                    login_username,
                    login_password
                )

                if student is None:

                    st.error(
                        "❌ Username ya password incorrect hai."
                    )

                else:

                    st.session_state.logged_in = True
                    st.session_state.username = student[0]

                    st.rerun()

    # --------------------------------------------------------
    # CREATE ACCOUNT TAB
    # --------------------------------------------------------

    with create_tab:

        st.write(
            "### ✨ Create Your Study Profile"
        )

        new_username = st.text_input(
            "Choose Username",
            key="new_username"
        )

        new_password = st.text_input(
            "Create Password",
            type="password",
            key="new_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="confirm_password"
        )

        new_goal = st.selectbox(
            "🎯 Main Goal",
            [
                "🏆 Highest CGPA",
                "📚 Strong Concepts",
                "🎯 CGPA + GATE",
                "💻 Skills + CGPA"
            ]
        )

        gate = st.checkbox(
            "🎯 Include optional GATE preparation"
        )

        selected_subjects = st.multiselect(
            "📚 Semester Subjects",
            DEFAULT_SUBJECTS,
            default=DEFAULT_SUBJECTS
        )

        extra_subjects = st.text_input(
            "Other subjects (comma separated)",
            placeholder="Example: DBMS, Mathematics"
        )

        if st.button(
            "✨ Create Account",
            use_container_width=True
        ):

            final_subjects = list(
                selected_subjects
            )

            if extra_subjects.strip():

                final_subjects.extend(
                    [
                        item.strip()
                        for item in extra_subjects.split(",")
                        if item.strip()
                    ]
                )

            # Remove duplicate subjects
            final_subjects = list(
                dict.fromkeys(
                    final_subjects
                )
            )

            if not new_username.strip():

                st.warning(
                    "Username enter karo."
                )

            elif len(new_password) < 4:

                st.warning(
                    "Password minimum 4 characters ka hona chahiye."
                )

            elif new_password != confirm_password:

                st.error(
                    "Passwords match nahi kar rahe."
                )

            elif not final_subjects:

                st.warning(
                    "At least one subject select karo."
                )

            else:

                created = create_account(
                    new_username,
                    new_password,
                    new_goal,
                    gate,
                    final_subjects
                )

                if created:

                    st.success(
                        "✅ Account created successfully! "
                        "Ab Login tab se login karo."
                    )

                else:

                    st.error(
                        "❌ Ye username already exists."
                    )

    st.stop()


# ============================================================
# LOAD CURRENT USER
# ============================================================

username = st.session_state.username

student = get_student(username)

# Important safety check.
# Prevents the old NoneType error.

if student is None:

    st.session_state.logged_in = False
    st.session_state.username = ""

    st.error(
        "Student profile nahi mila. Please login again."
    )

    st.stop()


goal = student[1]

gate_enabled = bool(
    student[2]
)


# ============================================================
# LOAD SUBJECTS
# ============================================================

subjects = get_subjects(
    username
)

# Safety for empty old profiles.

if not subjects:

    for subject in DEFAULT_SUBJECTS:

        add_subject(
            username,
            subject
        )

    subjects = get_subjects(
        username
    )


# ============================================================
# LOAD RECORDS
# ============================================================

records = load_records(
    username
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "🎓 CGPA Mission"
    )

    st.success(
        f"👤 {username}"
    )

    st.divider()

    page = st.radio(
        "📌 MENU",
        [
            "🏠 Dashboard",
            "📅 Daily Planner",
            "🗓️ Weekly Plan",
            "📊 Progress Analysis",
            "📚 Subject Manager",
            "🎯 Exam Mission",
            "⚙️ Profile"
        ]
    )

    st.divider()

    st.write(
        "### 🎯 Goal"
    )

    st.info(
        goal
    )

    st.write(
        f"📚 Subjects: {len(subjects)}"
    )

    if gate_enabled:

        st.success(
            "🎯 GATE: ON"
        )

    else:

        st.info(
            "🎯 GATE: OPTIONAL"
        )

    st.divider()

    st.caption(
        "Study Smart • Revise • Track • Improve"
    )

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.session_state.username = ""

        st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title(
        "🏠 Student Dashboard"
    )

    st.caption(
        f"Welcome {username} 👋 | "
        "Mission: Highest CGPA 🏆"
    )

    today = date.today()

    if records.empty:

        today_df = records
        week_df = records

    else:

        today_df = records[
            records["Date"] == str(today)
        ]

        week_df = records[
            records["Date"].between(
                str(monday_of(today)),
                str(sunday_of(today))
            )
        ]

    today_hours = (
        float(
            today_df["Hours"].sum()
        )
        if not today_df.empty
        else 0
    )

    week_hours = (
        float(
            week_df["Hours"].sum()
        )
        if not week_df.empty
        else 0
    )

    total_hours = (
        float(
            records["Hours"].sum()
        )
        if not records.empty
        else 0
    )

    active_days = (
        int(
            records["Date"].nunique()
        )
        if not records.empty
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "📚 Subjects",
        len(subjects)
    )

    c2.metric(
        "⏱️ Today",
        f"{today_hours:.1f} h"
    )

    c3.metric(
        "🗓️ This Week",
        f"{week_hours:.1f} h"
    )

    c4.metric(
        "📅 Days to November",
        days_until_november()
    )

    st.divider()

    st.subheader(
        "🔥 Today's Progress"
    )

    planned_hours = max(
        len(subjects) * 0.75,
        1
    )

    progress = min(
        today_hours / planned_hours,
        1
    )

    st.progress(
        progress,
        text=(
            f"{today_hours:.1f} / "
            f"{planned_hours:.1f} planned hours"
        )
    )

    if progress >= 1:

        st.success(
            "🏆 Today's study target complete!"
        )

    elif progress >= 0.5:

        st.info(
            "🔥 Good progress! Keep going."
        )

    else:

        st.warning(
            "💪 Start with one subject and build momentum."
        )

    st.divider()

    st.subheader(
        "📚 Subject Coverage"
    )

    rows = []

    for subject in subjects:

        if records.empty:

            sdf = records

        else:

            sdf = records[
                records["Subject"] == subject
            ]

        hours = (
            float(
                sdf["Hours"].sum()
            )
            if not sdf.empty
            else 0
        )

        sessions = (
            len(sdf)
            if not sdf.empty
            else 0
        )

        rows.append(
            {
                "Subject": subject,
                "Study Hours": round(
                    hours,
                    1
                ),
                "Sessions": sessions
            }
        )

    summary = pd.DataFrame(
        rows
    )

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )

    if summary["Study Hours"].sum() > 0:

        st.subheader(
            "📊 Hours by Subject"
        )

        st.bar_chart(
            summary.set_index(
                "Subject"
            )["Study Hours"]
        )

    st.divider()

    st.subheader(
        "🏆 Mission Rules"
    )

    st.write(
        "🔥 DS + OS ko extra priority do."
    )

    st.write(
        "📚 Har semester subject ko weekly cover karo."
    )

    st.write(
        "💻 5–6 PM mein coding, project, assignment, revision ya break choose karo."
    )

    st.write(
        "🎯 GATE optional hai."
    )

    st.write(
        "📈 Har Sunday weekly progress check karo."
    )

    st.write(
        "🌙 12 AM planning cutoff hai; sleep sacrifice mat karo."
    )


# ============================================================
# DAILY PLANNER
# ============================================================

elif page == "📅 Daily Planner":

    st.title(
        "📅 Daily Study Planner"
    )

    st.caption(
        "3 PM ke baad structured evening plan."
    )

    selected_date = st.date_input(
        "📅 Select Date",
        value=date.today()
    )

    st.subheader(
        "🕒 Suggested Schedule"
    )

    schedule = [
        (
            "3:00–3:30 PM",
            "🏠 Home + Refresh",
            "College ke baad fresh ho jao."
        ),

        (
            "3:30–4:30 PM",
            "🔥 Data Structures",
            "Concept + coding + practice."
        ),

        (
            "4:30–4:50 PM",
            "☕ Break",
            "Short refresh."
        ),

        (
            "4:50–5:00 PM",
            "🎒 Preparation",
            "Computer Center ke liye ready ho."
        ),

        (
            "5:00–6:00 PM",
            "💻 Computer Center",
            "Apni activity choose karo."
        ),

        (
            "6:00–6:30 PM",
            "☕ Break",
            "Snack / refresh."
        ),

        (
            "6:30–7:45 PM",
            "🔥 Operating Systems",
            "Concept + problems + revision."
        ),

        (
            "7:45–8:15 PM",
            "🍽️ Dinner",
            "Proper break."
        ),

        (
            "8:15–9:15 PM",
            "💻 Computer Architecture",
            "Theory + diagrams + questions."
        ),

        (
            "9:15–9:30 PM",
            "☕ Break",
            "Refresh."
        ),

        (
            "9:30–10:15 PM",
            "🛡️ Cybersecurity",
            "Security concepts + revision."
        ),

        (
            "10:15–10:45 PM",
            "📊 Information Systems",
            "MIS + DSS + important concepts."
        )
    ]

    if gate_enabled:

        schedule.append(
            (
                "10:45–11:30 PM",
                "🎯 Optional GATE",
                "GATE revision + PYQs."
            )
        )

    else:

        schedule.append(
            (
                "10:45–11:30 PM",
                "🧠 Mixed Revision",
                "Today's important topics revise karo."
            )
        )

    schedule.append(
        (
            "11:30–12:00 AM",
            "📝 Daily Review",
            "Progress check + tomorrow planning."
        )
    )

    st.table(
        [
            {
                "Time": item[0],
                "Activity": item[1],
                "Purpose": item[2]
            }
            for item in schedule
        ]
    )

    st.divider()

    st.subheader(
        "📚 Record Your Study"
    )

    for index, subject in enumerate(subjects):

        with st.container(border=True):

            st.write(
                f"### 📘 {subject}"
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                hours = st.number_input(
                    "Study Hours",
                    min_value=0.0,
                    max_value=12.0,
                    value=0.75,
                    step=0.25,
                    key=f"hours_{selected_date}_{index}"
                )

            with col2:

                completed = st.checkbox(
                    "✅ Completed",
                    value=True,
                    key=f"completed_{selected_date}_{index}"
                )

            with col3:

                study_type = st.selectbox(
                    "Study Type",
                    STUDY_TYPES,
                    key=f"type_{selected_date}_{index}"
                )

            if st.button(
                f"💾 Save {subject}",
                key=f"save_{selected_date}_{index}",
                use_container_width=True
            ):

                save_study_record(
                    username,
                    selected_date,
                    subject,
                    hours,
                    completed,
                    study_type
                )

                st.success(
                    f"✅ {subject} saved."
                )

    st.divider()

    st.subheader(
        "🕔 5–6 PM Computer Center"
    )

    center_choice = st.selectbox(
        "What do you want to do?",
        CENTER_OPTIONS
    )

    st.info(
        f"Today's selected activity: **{center_choice}**"
    )

    if st.button(
        "💾 Save 5–6 PM Activity",
        use_container_width=True
    ):

        save_center_activity(
            username,
            selected_date,
            center_choice
        )

        st.success(
            "✅ 5–6 PM activity saved."
        )


# ============================================================
# WEEKLY PLAN
# ============================================================

elif page == "🗓️ Weekly Plan":

    st.title(
        "🗓️ Weekly Study Plan"
    )

    st.caption(
        "DS + OS extra focus, while every subject gets regular attention."
    )

    selected_day = st.date_input(
        "Select any day of the week",
        value=date.today()
    )

    monday = monday_of(
        selected_day
    )

    sunday = sunday_of(
        selected_day
    )

    st.info(
        f"Week: {monday.strftime('%d %b')} → "
        f"{sunday.strftime('%d %b %Y')}"
    )

    weekly_focus = [
        "🔥 DS Concepts",
        "🔥 OS Concepts",
        "📚 Other Subjects",
        "💻 Coding / Practical",
        "📝 Questions",
        "🧪 Test / Mock",
        "🔁 Weekly Revision"
    ]

    weekly_rows = []

    for i in range(7):

        current_day = (
            monday +
            timedelta(days=i)
        )

        if i in [0, 3]:

            main_subject = (
                "Data Structures"
            )

        elif i in [1, 4]:

            main_subject = (
                "Operating Systems"
            )

        else:

            main_subject = subjects[
                i % len(subjects)
            ]

        second_subject = subjects[
            (i + 1) % len(subjects)
        ]

        weekly_rows.append(
            {
                "Day":
                    current_day.strftime(
                        "%A"
                    ),

                "Date":
                    current_day.strftime(
                        "%d %b"
                    ),

                "Main Focus":
                    main_subject,

                "Second Focus":
                    second_subject,

                "5–6 PM":
                    CENTER_OPTIONS[i],

                "Night Focus":
                    weekly_focus[i],

                "Cutoff":
                    "12:00 AM"
            }
        )

    st.dataframe(
        pd.DataFrame(
            weekly_rows
        ),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "🎯 Weekly Targets"
    )

    target_rows = [
        {
            "Area": "Data Structures",
            "Target":
                "3 focused sessions + coding"
        },

        {
            "Area": "Operating Systems",
            "Target":
                "3 focused sessions + problems"
        },

        {
            "Area": "Other Subjects",
            "Target":
                "At least 1 focused session each"
        },

        {
            "Area": "Revision",
            "Target":
                "Sunday revision"
        },

        {
            "Area": "Progress",
            "Target":
                "Record study daily"
        }
    ]

    st.table(
        target_rows
    )


# ============================================================
# PROGRESS ANALYSIS
# ============================================================

elif page == "📊 Progress Analysis":

    st.title(
        "📊 Progress Analysis"
    )

    st.caption(
        "Your study records become your weekly performance report."
    )

    if records.empty:

        st.info(
            "No records yet. Daily Planner se study record add karo."
        )

    else:

        total_hours = float(
            records["Hours"].sum()
        )

        total_sessions = len(
            records
        )

        completed_sessions = int(
            records["Completed"].sum()
        )

        active_days = records[
            "Date"
        ].nunique()

        completion_rate = (
            completed_sessions /
            total_sessions *
            100
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "⏱️ Total Hours",
            f"{total_hours:.1f}"
        )

        c2.metric(
            "📝 Sessions",
            total_sessions
        )

        c3.metric(
            "✅ Completion",
            f"{completion_rate:.0f}%"
        )

        c4.metric(
            "🔥 Active Days",
            active_days
        )

        st.divider()

        st.subheader(
            "📈 Daily Study Trend"
        )

        daily_hours = (
            records
            .groupby("Date")["Hours"]
            .sum()
            .sort_index()
        )

        st.line_chart(
            daily_hours
        )

        st.divider()

        st.subheader(
            "🗓️ Weekly Study Hours"
        )

        temp = records.copy()

        temp["DateObject"] = pd.to_datetime(
            temp["Date"]
        )

        temp["Week"] = (
            temp["DateObject"]
            -
            pd.to_timedelta(
                temp["DateObject"].dt.weekday,
                unit="D"
            )
        ).dt.date

        weekly_hours = (
            temp
            .groupby("Week")["Hours"]
            .sum()
            .sort_index()
        )

        st.bar_chart(
            weekly_hours
        )

        st.divider()

        st.subheader(
            "📚 Subject-wise Study"
        )

        subject_hours = (
            records
            .groupby("Subject")["Hours"]
            .sum()
            .reindex(
                subjects,
                fill_value=0
            )
        )

        st.bar_chart(
            subject_hours
        )

        st.dataframe(
            subject_hours
            .round(1)
            .rename("Total Hours")
            .reset_index(),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.subheader(
            "🧠 Performance Feedback"
        )

        if completion_rate >= 80:

            st.success(
                "🏆 Excellent consistency! Keep it up."
            )

        elif completion_rate >= 60:

            st.info(
                "🔥 Good progress. Next week consistency improve karo."
            )

        else:

            st.warning(
                "💪 Smaller targets rakho aur unhe complete karo."
            )


# ============================================================
# SUBJECT MANAGER
# ============================================================

elif page == "📚 Subject Manager":

    st.title(
        "📚 Subject Manager"
    )

    st.write(
        "Current subjects:"
    )

    for index, subject in enumerate(
        subjects
    ):

        col1, col2 = st.columns(
            [5, 1]
        )

        with col1:

            st.write(
                f"📘 **{subject}**"
            )

        with col2:

            if st.button(
                "Delete",
                key=f"delete_{index}"
            ):

                if len(subjects) <= 1:

                    st.warning(
                        "At least one subject must remain."
                    )

                else:

                    delete_subject(
                        username,
                        subject
                    )

                    st.rerun()

    st.divider()

    new_subject = st.text_input(
        "➕ Add New Subject",
        placeholder="Example: DBMS"
    )

    if st.button(
        "Add Subject",
        use_container_width=True
    ):

        if add_subject(
            username,
            new_subject
        ):

            st.success(
                "✅ Subject added."
            )

            st.rerun()

        else:

            st.warning(
                "Enter a new subject name."
            )


# ============================================================
# EXAM MISSION
# ============================================================

elif page == "🎯 Exam Mission":

    st.title(
        "🎯 November Exam Mission"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "📅 Exam Month",
        "November"
    )

    c2.metric(
        "⏳ Days Left",
        days_until_november()
    )

    c3.metric(
        "🏆 Target",
        "Highest CGPA"
    )

    st.divider()

    st.subheader(
        "🗓️ Preparation Roadmap"
    )

    roadmap = [
        {
            "Phase": "September",
            "Focus": "📖 Concept Building",
            "Target": "Complete core concepts"
        },

        {
            "Phase": "Late September",
            "Focus": "🔥 DS + OS",
            "Target": "Extra practice + problems"
        },

        {
            "Phase": "Early October",
            "Focus": "📝 Practice",
            "Target": "Questions + weak topics"
        },

        {
            "Phase": "Late October",
            "Focus": "🧪 Revision + Mock",
            "Target": "Full revision + tests"
        },

        {
            "Phase": "November",
            "Focus": "🏆 EXAM MODE",
            "Target": "Final revision + exams"
        }
    ]

    st.table(
        roadmap
    )

    st.divider()

    st.subheader(
        "🔥 Priority Order"
    )

    priorities = [
        "1. Data Structures",
        "2. Operating Systems",
        "3. Computer Architecture",
        "4. Cybersecurity",
        "5. Information Systems"
    ]

    for item in priorities:

        st.write(item)

    if gate_enabled:

        st.warning(
            "🎯 GATE ON hai, but optional hai. "
            "November exams close aane par Semester subjects priority rahenge."
        )

    else:

        st.info(
            "🎯 GATE OFF hai. College preparation par focus kar sakte ho."
        )


# ============================================================
# PROFILE
# ============================================================

elif page == "⚙️ Profile":

    st.title(
        "⚙️ My Profile"
    )

    st.write(
        f"**Username:** {username}"
    )

    st.write(
        f"**Goal:** {goal}"
    )

    st.write(
        "**GATE:** "
        +
        (
            "Enabled 🎯"
            if gate_enabled
            else "Optional / Off"
        )
    )

    st.divider()

    st.subheader(
        "📚 My Subjects"
    )

    for subject in subjects:

        st.write(
            f"• {subject}"
        )

    st.divider()

    st.subheader(
        "🔐 Password & Database"
    )

    st.info(
        "Password plain text mein store nahi hota. "
        "Uska SHA-256 hash local database mein save hota hai. "
        "Database file TimeTable.py ke same folder mein rahegi."
    )

    st.subheader(
        "🌙 Study Rule"
    )

    st.write(
        "12:00 AM planning cutoff hai. "
        "Sleep sacrifice karke padhna required nahi hai."
    )

    st.divider()

    st.subheader(
        "🏆 Mission"
    )

    st.write(
        "Understand → Practice → Revise → Analyse → Improve → "
        "Highest CGPA."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🎓 CGPA Mission | Multi-user | SQLite | "
    "Daily Planner | Weekly Progress | November Exam Roadmap"
)
