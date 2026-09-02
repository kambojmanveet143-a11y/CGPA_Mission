import sqlite3
import hashlib
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="CGPA Mission",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# DATABASE
# =========================================================

DB_NAME = "cgpa_mission_final.db"


def get_db():
    return sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )


def init_database():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            goal TEXT NOT NULL,
            gate_enabled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            subject TEXT NOT NULL,
            UNIQUE(username, subject)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS study_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            study_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            hours REAL NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            study_type TEXT NOT NULL,
            UNIQUE(username, study_date, subject)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS center_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            study_date TEXT NOT NULL,
            activity TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# CONSTANTS
# =========================================================

DEFAULT_SUBJECTS = [
    "Data Structures",
    "Operating Systems",
    "Computer Architecture",
    "Cybersecurity",
    "Information Systems",
]

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
    "☕ Break / Refresh",
]

STUDY_TYPES = [
    "📖 Concept Study",
    "📝 Practice Questions",
    "🔁 Revision",
    "🧠 Active Recall",
    "💻 Coding / Practical",
    "🧪 Test / Mock",
]


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def make_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


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
                password,
                goal,
                gate_enabled,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                make_password(password),
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
                    (username, subject)
                    VALUES (?, ?)
                    """,
                    (
                        username,
                        subject
                    )
                )

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        conn.rollback()

        return False

    finally:

        conn.close()


def login_user(username, password):

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
        AND password = ?
        """,
        (
            username.strip(),
            make_password(password)
        )
    )

    result = cur.fetchone()

    conn.close()

    return result


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

    return [row[0] for row in rows]


def add_subject(username, subject):

    subject = subject.strip()

    if not subject:
        return False

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO subjects
        (username, subject)
        VALUES (?, ?)
        """,
        (
            username,
            subject
        )
    )

    changed = cur.rowcount > 0

    conn.commit()
    conn.close()

    return changed


def delete_subject(username, subject):

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

    cur.execute(
        """
        INSERT OR REPLACE INTO study_records
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


def get_records(username):

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


# =========================================================
# DATE FUNCTIONS
# =========================================================

def get_monday(day):

    return day - timedelta(
        days=day.weekday()
    )


def get_sunday(day):

    return get_monday(day) + timedelta(
        days=6
    )


def get_exam_date():

    today = date.today()

    exam_date = date(
        today.year,
        11,
        1
    )

    if today > exam_date:

        exam_date = date(
            today.year + 1,
            11,
            1
        )

    return exam_date


def days_left_for_exam():

    return max(
        0,
        (
            get_exam_date() -
            date.today()
        ).days
    )


# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


# =========================================================
# LOGIN PAGE
# =========================================================

if not st.session_state.logged_in:

    st.title("🎓 CGPA MISSION")

    st.subheader(
        "Personal Academic Planner"
    )

    st.info(
        "🏆 Target: Highest CGPA  |  "
        "🔥 DS + OS Priority  |  "
        "📊 Progress Analysis  |  "
        "🎯 GATE Optional"
    )

    login_tab, signup_tab = st.tabs(
        [
            "🔐 Login",
            "✨ Create Account"
        ]
    )

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    with login_tab:

        st.write("### Welcome Back 👋")

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
                    "Username and password enter karo."
                )

            else:

                user = login_user(
                    login_username,
                    login_password
                )

                if user is None:

                    st.error(
                        "❌ Username ya password incorrect hai."
                    )

                else:

                    st.session_state.logged_in = True
                    st.session_state.username = user[0]

                    st.rerun()

    # -----------------------------------------------------
    # CREATE ACCOUNT
    # -----------------------------------------------------

    with signup_tab:

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

        new_goal = st.selectbox(
            "🎯 Main Goal",
            [
                "🏆 Highest CGPA",
                "📚 Strong Concepts",
                "🎯 CGPA + GATE",
                "💻 Skills + CGPA"
            ]
        )

        gate_enabled = st.checkbox(
            "🎯 Include GATE Preparation"
        )

        selected_subjects = st.multiselect(
            "📚 Select Semester Subjects",
            DEFAULT_SUBJECTS,
            default=DEFAULT_SUBJECTS
        )

        extra_subjects = st.text_input(
            "Other subjects",
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
                        x.strip()
                        for x in extra_subjects.split(",")
                        if x.strip()
                    ]
                )

            # Remove duplicates
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

            elif not final_subjects:

                st.warning(
                    "At least one subject select karo."
                )

            else:

                created = create_account(
                    new_username,
                    new_password,
                    new_goal,
                    gate_enabled,
                    final_subjects
                )

                if created:

                    st.success(
                        "✅ Account created! "
                        "Ab Login tab se login karo."
                    )

                else:

                    st.error(
                        "❌ Ye username already exists."
                    )

    st.stop()


# =========================================================
# LOAD CURRENT USER
# =========================================================

username = st.session_state.username

student = get_student(username)

# Safe check — no NoneType error.
if student is None:

    st.session_state.logged_in = False
    st.session_state.username = ""

    st.error(
        "Student profile nahi mila. Please login again."
    )

    st.stop()


goal = student[1]
gate_enabled = bool(student[2])

subjects = get_subjects(username)

# Safety: if an account somehow has no subjects.
if not subjects:

    for item in DEFAULT_SUBJECTS:
        add_subject(username, item)

    subjects = get_subjects(username)


records = get_records(username)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("🎓 CGPA Mission")

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

    st.write("🎯 **Goal**")
    st.info(goal)

    st.write(
        f"📚 **Subjects:** {len(subjects)}"
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

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.session_state.username = ""

        st.rerun()


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.title("🏠 Student Dashboard")

    st.caption(
        f"Welcome {username} 👋 | "
        "Your mission: Highest CGPA 🏆"
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
                str(get_monday(today)),
                str(get_sunday(today))
            )
        ]

    today_hours = (
        float(today_df["Hours"].sum())
        if not today_df.empty
        else 0
    )

    week_hours = (
        float(week_df["Hours"].sum())
        if not week_df.empty
        else 0
    )

    total_hours = (
        float(records["Hours"].sum())
        if not records.empty
        else 0
    )

    active_days = (
        records["Date"].nunique()
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
        days_left_for_exam()
    )

    st.divider()

    st.subheader(
        "🔥 Today's Progress"
    )

    target_hours = max(
        len(subjects) * 0.75,
        1
    )

    progress = min(
        today_hours / target_hours,
        1
    )

    st.progress(
        progress,
        text=(
            f"{today_hours:.1f} / "
            f"{target_hours:.1f} planned hours"
        )
    )

    if progress >= 1:

        st.success(
            "🏆 Today's planned target completed!"
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
        "📚 Subject-wise Study"
    )

    subject_rows = []

    for subject in subjects:

        if records.empty:

            sdf = records

        else:

            sdf = records[
                records["Subject"] == subject
            ]

        hours = (
            float(sdf["Hours"].sum())
            if not sdf.empty
            else 0
        )

        sessions = (
            len(sdf)
            if not sdf.empty
            else 0
        )

        subject_rows.append(
            {
                "Subject": subject,
                "Hours": round(hours, 1),
                "Sessions": sessions
            }
        )

    subject_table = pd.DataFrame(
        subject_rows
    )

    st.dataframe(
        subject_table,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "🏆 Mission Rules"
    )

    rules = [
        "🔥 DS + OS ko extra time do because they are priority subjects.",
        "📚 Har semester subject ko weekly cover karo.",
        "💻 5–6 PM ko coding, project, revision, assignment ya break choose kar sakte ho.",
        "🎯 GATE optional hai; semester syllabus ko priority do.",
        "📊 Sunday ko apni weekly progress check karo.",
        "🌙 12 AM planning cutoff hai — sleep sacrifice karna target nahi hai."
    ]

    for rule in rules:
        st.write(rule)


# =========================================================
# DAILY PLANNER
# =========================================================

elif page == "📅 Daily Planner":

    st.title(
        "📅 Daily Study Planner"
    )

    st.caption(
        "3 PM ke baad structured study plan."
    )

    selected_date = st.date_input(
        "📅 Select Date",
        value=date.today()
    )

    st.subheader(
        "🕒 Evening Schedule"
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
            "Threats + security + revision."
        ),

        (
            "10:15–10:45 PM",
            "📊 Information Systems",
            "MIS / DSS / KM concepts."
        ),
    ]

    if gate_enabled:

        schedule.append(
            (
                "10:45–11:30 PM",
                "🎯 Optional GATE",
                "GATE topic revision + PYQs."
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
                "Time": x[0],
                "Activity": x[1],
                "Purpose": x[2]
            }
            for x in schedule
        ]
    )

    st.divider()

    st.subheader(
        "📚 Record Today's Study"
    )

    for index, subject in enumerate(subjects):

        with st.container(border=True):

            st.write(
                f"### 📘 {subject}"
            )

            a, b, c = st.columns(3)

            with a:

                hours = st.number_input(
                    "Study Hours",
                    min_value=0.0,
                    max_value=10.0,
                    value=0.75,
                    step=0.25,
                    key=f"hours_{selected_date}_{index}"
                )

            with b:

                completed = st.checkbox(
                    "✅ Completed",
                    value=True,
                    key=f"complete_{selected_date}_{index}"
                )

            with c:

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
        "🕔 5–6 PM Computer Center Choice"
    )

    center_choice = st.selectbox(
        "Choose your activity",
        CENTER_OPTIONS
    )

    st.info(
        f"Recommended activity: **{center_choice}**"
    )

    if st.button(
        "💾 Save 5–6 PM Choice",
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


# =========================================================
# WEEKLY PLAN
# =========================================================

elif page == "🗓️ Weekly Plan":

    st.title(
        "🗓️ Weekly Study Plan"
    )

    st.caption(
        "DS + OS extra focus, while every other subject gets regular attention."
    )

    selected_day = st.date_input(
        "Select any day",
        value=date.today()
    )

    monday = get_monday(
        selected_day
    )

    sunday = get_sunday(
        selected_day
    )

    st.info(
        f"Week: {monday.strftime('%d %b')} "
        f"→ {sunday.strftime('%d %b %Y')}"
    )

    focus = [
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

        current_day = monday + timedelta(
            days=i
        )

        if i in [0, 3]:

            main_subject = "Data Structures"

        elif i in [1, 4]:

            main_subject = "Operating Systems"

        else:

            main_subject = subjects[
                i % len(subjects)
            ]

        second_subject = subjects[
            (i + 1) % len(subjects)
        ]

        weekly_rows.append(
            {
                "Day": current_day.strftime("%A"),
                "Date": current_day.strftime("%d %b"),
                "Main Focus": main_subject,
                "Second Focus": second_subject,
                "5–6 PM": CENTER_OPTIONS[i],
                "Night Focus": focus[i]
            }
        )

    st.dataframe(
        pd.DataFrame(weekly_rows),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "🎯 Weekly Targets"
    )

    target_table = pd.DataFrame(
        [
            {
                "Area": "Data Structures",
                "Target": "3 focused sessions + coding"
            },
            {
                "Area": "Operating Systems",
                "Target": "3 focused sessions + problems"
            },
            {
                "Area": "Other Subjects",
                "Target": "At least 1 session each"
            },
            {
                "Area": "Revision",
                "Target": "Sunday revision"
            },
            {
                "Area": "Progress",
                "Target": "Record study daily"
            },
        ]
    )

    st.table(
        target_table
    )


# =========================================================
# PROGRESS ANALYSIS
# =========================================================

elif page == "📊 Progress Analysis":

    st.title(
        "📊 Progress Analysis"
    )

    st.caption(
        "See how consistently you are studying."
    )

    if records.empty:

        st.info(
            "Abhi koi study record nahi hai. "
            "Daily Planner se pehla record add karo."
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
            "⏱️ Total Study",
            f"{total_hours:.1f} h"
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
            "🗓️ Weekly Study Trend"
        )

        temp = records.copy()

        temp["DateObj"] = pd.to_datetime(
            temp["Date"]
        )

        temp["Week"] = (
            temp["DateObj"]
            - pd.to_timedelta(
                temp["DateObj"].dt.weekday,
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
            "📚 Subject-wise Analysis"
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
                "🏆 Excellent! Tum apne planned tasks consistently complete kar rahe ho."
            )

        elif completion_rate >= 60:

            st.info(
                "🔥 Good progress! Ab consistency aur improve karo."
            )

        else:

            st.warning(
                "💪 Targets thode realistic rakho aur jo plan karo use complete karo."
            )


# =========================================================
# SUBJECT MANAGER
# =========================================================

elif page == "📚 Subject Manager":

    st.title(
        "📚 Subject Manager"
    )

    st.write(
        "Your current subjects:"
    )

    for index, subject in enumerate(subjects):

        a, b = st.columns(
            [5, 1]
        )

        with a:

            st.write(
                f"📘 **{subject}**"
            )

        with b:

            if st.button(
                "Delete",
                key=f"del_{index}"
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
                "Subject empty hai ya already exists."
            )


# =========================================================
# EXAM MISSION
# =========================================================

elif page == "🎯 Exam Mission":

    st.title(
        "🎯 November Exam Mission"
    )

    days = days_left_for_exam()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "📅 Exam Month",
        "November"
    )

    c2.metric(
        "⏳ Days Left",
        days
    )

    c3.metric(
        "🏆 Target",
        "Highest CGPA"
    )

    st.divider()

    st.subheader(
        "🗓️ Preparation Roadmap"
    )

    roadmap = pd.DataFrame(
        [
            {
                "Phase": "September",
                "Focus": "📖 Concept Building",
                "Goal": "Complete fundamentals"
            },
            {
                "Phase": "Late September",
                "Focus": "🔥 DS + OS",
                "Goal": "Extra practice + problems"
            },
            {
                "Phase": "Early October",
                "Focus": "📝 Practice",
                "Goal": "Questions + weak topics"
            },
            {
                "Phase": "Late October",
                "Focus": "🧪 Revision + Mock",
                "Goal": "Full revision + tests"
            },
            {
                "Phase": "November",
                "Focus": "🏆 Exam Mode",
                "Goal": "Final revision + exams"
            },
        ]
    )

    st.table(
        roadmap
    )

    st.divider()

    st.subheader(
        "🔥 Priority Order"
    )

    st.write(
        "1. 🔥 Data Structures"
    )

    st.write(
        "2. 🔥 Operating Systems"
    )

    st.write(
        "3. 💻 Computer Architecture"
    )

    st.write(
        "4. 🛡️ Cybersecurity"
    )

    st.write(
        "5. 📊 Information Systems"
    )

    if gate_enabled:

        st.warning(
            "🎯 GATE ON hai, but it is optional. "
            "November exams close aane par semester subjects ko priority do."
        )

    else:

        st.info(
            "🎯 GATE currently OFF hai. "
            "Tum college preparation par full focus kar sakte ho."
        )


# =========================================================
# PROFILE
# =========================================================

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
        + (
            "Enabled 🎯"
            if gate_enabled
            else
            "Optional / Off"
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
        "🌙 Study Rule"
    )

    st.info(
        "12:00 AM ko planning cutoff rakho. "
        "Sleep sacrifice karke timetable complete karna required nahi hai."
    )

    st.subheader(
        "🏆 Mission"
    )

    st.write(
        "Concepts strong karo → practice karo → "
        "weekly revision karo → progress analyse karo → "
        "November exams ke liye ready ho jao."
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🎓 CGPA Mission | Multi-user | SQLite | "
    "Daily Planner | Weekly Analysis | November Exam Roadmap"
)
