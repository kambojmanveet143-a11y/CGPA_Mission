import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta

# ============================================================
# CGPA MISSION - MULTI USER STUDY PLANNER
# No Plotly / no custom HTML required
# ============================================================

DB_NAME = "student_progress.db"

DEFAULT_SUBJECTS = [
    "Data Structures",
    "Operating Systems",
    "DBMS",
    "Computer Networks",
    "Python",
    "Mathematics"
]

ACTIVITIES_5_6 = [
    "☕ Break + refresh",
    "📖 Light revision",
    "🧠 Practice questions",
    "💻 Coding practice",
    "📝 Assignment / notes",
    "🎯 GATE practice",
    "🚶 Walk / exercise",
    "🎨 Hobby / personal time"
]


# ---------------- DATABASE ----------------

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            goal TEXT NOT NULL,
            gate_enabled INTEGER DEFAULT 0,
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
            hours REAL NOT NULL,
            completed INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            activity_date TEXT NOT NULL,
            activity TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_student(username, password, goal, gate_enabled, subjects):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO students
            (username, password_hash, goal, gate_enabled, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username.strip(),
                hash_password(password),
                goal,
                int(gate_enabled),
                datetime.now().isoformat(timespec="seconds")
            )
        )

        for subject in subjects:
            subject = subject.strip()
            if subject:
                cur.execute(
                    "INSERT OR IGNORE INTO subjects(username, subject) VALUES (?, ?)",
                    (username.strip(), subject)
                )

        conn.commit()
        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "This username already exists."

    finally:
        conn.close()


def authenticate(username, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT username, goal, gate_enabled FROM students "
        "WHERE username = ? AND password_hash = ?",
        (username.strip(), hash_password(password))
    )

    result = cur.fetchone()
    conn.close()
    return result


def get_student(username):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT username, goal, gate_enabled FROM students WHERE username = ?",
        (username,)
    )

    result = cur.fetchone()
    conn.close()
    return result


def get_subjects(username):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT subject FROM subjects WHERE username = ? ORDER BY id",
        (username,)
    )

    rows = cur.fetchall()
    conn.close()

    return [row[0] for row in rows]


def add_subject(username, subject):
    subject = subject.strip()

    if not subject:
        return False

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO subjects(username, subject) VALUES (?, ?)",
        (username, subject)
    )

    conn.commit()
    changed = cur.rowcount > 0
    conn.close()

    return changed


def save_study_record(username, study_date, subject, hours, completed=True):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO study_records
        (username, study_date, subject, hours, completed)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            username,
            str(study_date),
            subject,
            float(hours),
            int(completed)
        )
    )

    conn.commit()
    conn.close()


def save_activity(username, activity_date, activity):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO daily_activities(username, activity_date, activity) "
        "VALUES (?, ?, ?)",
        (username, str(activity_date), activity)
    )

    conn.commit()
    conn.close()


def get_records(username):
    conn = get_connection()

    try:
        import pandas as pd

        df = pd.read_sql_query(
            """
            SELECT study_date AS Date,
                   subject AS Subject,
                   hours AS Hours,
                   completed AS Completed
            FROM study_records
            WHERE username = ?
            ORDER BY study_date DESC, id DESC
            """,
            conn,
            params=(username,)
        )
    finally:
        conn.close()

    return df


# ---------------- HELPERS ----------------

def week_start(day):
    return day - timedelta(days=day.weekday())


def week_end(day):
    return week_start(day) + timedelta(days=6)


def get_week_records(username, start_day):
    import pandas as pd

    conn = get_connection()

    try:
        df = pd.read_sql_query(
            """
            SELECT study_date AS Date,
                   subject AS Subject,
                   hours AS Hours,
                   completed AS Completed
            FROM study_records
            WHERE username = ?
              AND study_date BETWEEN ? AND ?
            ORDER BY study_date
            """,
            conn,
            params=(username, str(start_day), str(week_end(start_day)))
        )
    finally:
        conn.close()

    return df


def total_hours(df):
    if df.empty:
        return 0.0
    return float(df["Hours"].sum())


def show_metric_cards(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.metric(label, value)


# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="CGPA Mission",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# Native Streamlit CSS only. No custom HTML blocks.
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f7f4ff 0%, #eef6ff 50%, #f8fbff 100%);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #17152e 0%, #29245a 100%);
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.85);
        border: 1px solid rgba(100,80,180,0.15);
        padding: 15px;
        border-radius: 18px;
        box-shadow: 0 8px 24px rgba(50,40,100,0.08);
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
    }

    .study-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #29245a;
    }

    .study-subtitle {
        color: #66677a;
        font-size: 1.05rem;
    }

    .notice {
        padding: 14px 18px;
        border-radius: 14px;
        background: rgba(255,255,255,0.85);
        border: 1px solid rgba(100,80,180,0.12);
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ---------------- SESSION ----------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


# ============================================================
# LOGIN / REGISTER
# ============================================================

if not st.session_state.logged_in:

    st.markdown(
        """
        <div class="study-title">🎓 CGPA MISSION</div>
        <div class="study-subtitle">
        Personal Academic Planner • Progress Tracker • Weekly Planner • November Exam Mission
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")
    st.info(
        "🏆 Mission: Highest CGPA. "
        "Har din sabhi important subjects ko touch karo, progress record karo "
        "aur November exams ke liye consistently prepare karo."
    )

    login_tab, signup_tab = st.tabs(["🔐 Login", "✨ Create Account"])

    with login_tab:
        st.subheader("Welcome back")

        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")

        if st.button("🚀 Login", use_container_width=True):
            if not login_user.strip() or not login_pass:
                st.warning("Username aur password dono enter karo.")
            else:
                student = authenticate(login_user, login_pass)

                if student:
                    st.session_state.logged_in = True
                    st.session_state.username = student[0]
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")

    with signup_tab:
        st.subheader("Create your personal study profile")

        new_user = st.text_input("Choose username", key="new_user")
        new_pass = st.text_input(
            "Create password",
            type="password",
            key="new_pass"
        )

        goal = st.selectbox(
            "🎯 Main Goal",
            [
                "🏆 Highest CGPA",
                "📚 Strong Concepts",
                "🎯 CGPA + GATE",
                "💻 Skills + CGPA"
            ]
        )

        gate = st.toggle(
            "🎯 Include optional GATE Preparation",
            value=False
        )

        st.write("📚 Select / enter your subjects")

        selected_defaults = st.multiselect(
            "Default subjects",
            DEFAULT_SUBJECTS,
            default=DEFAULT_SUBJECTS
        )

        extra_subjects = st.text_input(
            "Other subjects (comma separated)",
            placeholder="e.g. Java, Statistics"
        )

        if st.button("✨ Create My Study Dashboard", use_container_width=True):
            subjects = list(selected_defaults)

            if extra_subjects.strip():
                subjects.extend(
                    [x.strip() for x in extra_subjects.split(",") if x.strip()]
                )

            if not new_user.strip() or not new_pass:
                st.warning("Username aur password enter karo.")
            elif len(new_pass) < 4:
                st.warning("Password kam se kam 4 characters ka rakho.")
            elif not subjects:
                st.warning("At least one subject select karo.")
            else:
                ok, message = create_student(
                    new_user,
                    new_pass,
                    goal,
                    gate,
                    subjects
                )

                if ok:
                    st.success(message + " Ab Login tab se login karo.")
                else:
                    st.error(message)

    st.stop()


# ============================================================
# CURRENT USER - SAFE DATABASE CHECK
# ============================================================

username = st.session_state.username
student = get_student(username)

# This prevents the previous NoneType error:
# goal = student[1] when student was None.
if student is None:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.error("Student profile not found. Please login again.")
    st.stop()

goal = student[1]
gate_enabled = bool(student[2])

subjects = get_subjects(username)

if not subjects:
    for subject in DEFAULT_SUBJECTS:
        add_subject(username, subject)
    subjects = get_subjects(username)

records = get_records(username)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🎓 CGPA MISSION")
    st.caption(f"Student: {username}")

    st.divider()

    page = st.radio(
        "📌 Dashboard",
        [
            "🏠 Home",
            "📅 Today's Plan",
            "📊 Progress Analysis",
            "🗓️ Weekly Plan",
            "📝 Study Record",
            "📚 Subjects",
            "⚙️ Profile"
        ]
    )

    st.divider()

    st.write("🎯 **Goal**")
    st.write(goal)

    if gate_enabled:
        st.success("GATE: ON")
    else:
        st.info("GATE: Optional / OFF")

    st.divider()

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()


# ============================================================
# HOME
# ============================================================

if page == "🏠 Home":

    st.markdown(
        '<div class="study-title">🎓 Your CGPA Mission Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="study-subtitle">'
        'Consistency → Revision → Practice → Better CGPA'
        '</div>',
        unsafe_allow_html=True
    )

    st.write("")

    today = date.today()
    this_week = get_week_records(username, week_start(today))

    today_df = records[records["Date"] == str(today)] if not records.empty else records

    today_hours = total_hours(today_df)
    week_hours = total_hours(this_week)

    unique_days = records["Date"].nunique() if not records.empty else 0

    show_metric_cards(
        [
            ("📚 Subjects", len(subjects)),
            ("⏱️ Today", f"{today_hours:.1f} h"),
            ("📈 This Week", f"{week_hours:.1f} h"),
            ("🔥 Study Days", unique_days)
        ]
    )

    st.write("")

    left, right = st.columns([1.4, 1])

    with left:
        st.subheader("🏆 Mission Status")

        st.success(
            "Your target is the **highest CGPA**. "
            "Small daily progress matters more than last-minute studying."
        )

        st.progress(
            min(today_hours / max(len(subjects) * 0.75, 1), 1.0),
            text="Today's study completion"
        )

        st.write(
            "🌙 **Study window:** plan your work through the evening, "
            "with breaks and enough sleep. The app can organize tasks up to "
            "the 12 AM target without requiring you to skip sleep."
        )

    with right:
        st.subheader("📅 November Exam Mission")

        days_to_november = max(
            (date(date.today().year, 11, 1) - date.today()).days,
            0
        )

        st.metric("Days until November", days_to_november)

        st.write(
            "Recommended strategy:"
        )
        st.write("1. 📖 Complete concepts")
        st.write("2. 📝 Practice questions")
        st.write("3. 🔁 Weekly revision")
        st.write("4. 🧪 Mock / previous-paper practice")
        st.write("5. 🎯 Final revision before exams")

    st.divider()

    st.subheader("📌 Quick Actions")

    q1, q2, q3 = st.columns(3)

    with q1:
        if st.button("➕ Add Study Record", use_container_width=True):
            st.session_state.quick_page = "📝 Study Record"
            st.rerun()

    with q2:
        if st.button("📊 View Progress", use_container_width=True):
            st.session_state.quick_page = "📊 Progress Analysis"
            st.rerun()

    with q3:
        if st.button("🗓️ Open Weekly Plan", use_container_width=True):
            st.session_state.quick_page = "🗓️ Weekly Plan"
            st.rerun()


# ============================================================
# TODAY'S PLAN
# ============================================================

elif page == "📅 Today's Plan":

    st.title("📅 Today's Smart Study Plan")
    st.caption("Har subject ko daily touch karne ka simple plan.")

    today = date.today()

    st.info(
        "🎯 Rule: Aaj har subject mein kuch na kuch productive work karo. "
        "Hours subject difficulty ke according adjust ho sakte hain."
    )

    st.subheader("📚 Subject-wise plan")

    for i, subject in enumerate(subjects):
        cols = st.columns([2.5, 1.2, 2.5])

        with cols[0]:
            st.write(f"**{i + 1}. {subject}**")

        with cols[1]:
            hours = st.number_input(
                "Hours",
                min_value=0.0,
                max_value=6.0,
                value=0.75,
                step=0.25,
                key=f"today_hours_{i}"
            )

        with cols[2]:
            task = st.selectbox(
                "Task",
                [
                    "📖 Learn concept",
                    "📝 Revise notes",
                    "🧠 Practice questions",
                    "🔁 Revision",
                    "🧪 Mock / test"
                ],
                key=f"today_task_{i}"
            )

        if st.button(
            f"Save {subject}",
            key=f"save_today_{i}",
            use_container_width=True
        ):
            save_study_record(
                username,
                today,
                subject,
                hours,
                True
            )
            st.success(f"Saved: {subject} — {hours:.2f} hours.")

    st.divider()

    st.subheader("🕔 5 PM – 6 PM: You decide")

    activity = st.selectbox(
        "Choose what you want to do",
        ACTIVITIES_5_6
    )

    if st.button("💾 Save 5–6 PM Activity", use_container_width=True):
        save_activity(username, today, activity)
        st.success(f"Saved activity: {activity}")

    st.divider()

    st.subheader("🌙 Evening → 12 AM Mission")

    evening_plan = {
        "7:00 – 8:00": "📖 Difficult subject / core concept",
        "8:00 – 8:30": "🍽️ Dinner + break",
        "8:30 – 9:30": "🧠 Questions / coding practice",
        "9:30 – 10:30": "📚 Second subject revision",
        "10:30 – 11:15": "🔁 Quick revision",
        "11:15 – 12:00": "📝 Tomorrow planning + light revision"
    }

    st.table(
        [{"Time": time_slot, "Suggested Work": task}
         for time_slot, task in evening_plan.items()]
    )

    st.warning(
        "💡 Midnight is the planner's upper target, not a requirement to "
        "sacrifice sleep. If you're tired, stop earlier and continue tomorrow."
    )


# ============================================================
# PROGRESS ANALYSIS
# ============================================================

elif page == "📊 Progress Analysis":

    st.title("📊 Student Progress Analysis")

    if records.empty:
        st.info(
            "Abhi progress data nahi hai. Today's Plan ya Study Record se "
            "pehla record add karo."
        )
        st.stop()

    records["Date"] = records["Date"].astype(str)

    total = float(records["Hours"].sum())
    days = records["Date"].nunique()
    avg = total / max(days, 1)

    show_metric_cards(
        [
            ("⏱️ Total Hours", f"{total:.1f}"),
            ("📅 Active Days", days),
            ("📈 Avg / Study Day", f"{avg:.1f} h"),
            ("📚 Subjects Covered", records["Subject"].nunique())
        ]
    )

    st.write("")

    st.subheader("📈 Daily Study Trend")

    daily = records.groupby("Date")["Hours"].sum()

    st.line_chart(daily)

    st.subheader("📚 Subject-wise Progress")

    subject_hours = records.groupby("Subject")["Hours"].sum().sort_values(
        ascending=False
    )

    st.bar_chart(subject_hours)

    st.subheader("🗓️ Weekly Progress")

    temp = records.copy()
    temp["Date"] = temp["Date"].apply(date.fromisoformat)
    temp["Week"] = temp["Date"].apply(week_start)

    weekly = temp.groupby("Week")["Hours"].sum()

    st.line_chart(weekly)

    st.subheader("🎯 Subject Balance")

    balance = (
        records.groupby("Subject")["Hours"]
        .sum()
        .reindex(subjects, fill_value=0)
    )

    st.dataframe(
        balance.rename("Total Hours").reset_index(),
        use_container_width=True,
        hide_index=True
    )

    max_hours = max(float(balance.max()), 1)

    st.write("### Coverage")

    for subject in subjects:
        value = float(balance.get(subject, 0))
        st.write(f"**{subject}** — {value:.1f} hours")
        st.progress(min(value / max_hours, 1.0))

    st.divider()

    st.subheader("🧠 Weekly Review")

    current_week = get_week_records(username, week_start(date.today()))

    if current_week.empty:
        st.info("Is week ke records add karo, phir analysis yahan dikhega.")
    else:
        current_hours = total_hours(current_week)

        if current_hours >= 20:
            st.success(
                "🔥 Excellent consistency! Keep maintaining the routine."
            )
        elif current_hours >= 10:
            st.info(
                "👍 Good progress. Next week thoda aur consistency improve karo."
            )
        else:
            st.warning(
                "💪 Start small. Daily subject coverage ko consistent banao."
            )


# ============================================================
# WEEKLY PLAN
# ============================================================

elif page == "🗓️ Weekly Plan":

    st.title("🗓️ Weekly Study Plan")

    selected_monday = st.date_input(
        "Select week",
        value=week_start(date.today())
    )

    selected_monday = week_start(selected_monday)
    selected_sunday = week_end(selected_monday)

    st.info(
        f"Week: {selected_monday.strftime('%d %b')} – "
        f"{selected_sunday.strftime('%d %b %Y')}"
    )

    st.subheader("🎯 Weekly Strategy")

    plan = [
        ("Monday", "📖 Concepts + difficult topic"),
        ("Tuesday", "🧠 Practice questions"),
        ("Wednesday", "📚 Second-round revision"),
        ("Thursday", "💻 Coding / practical work"),
        ("Friday", "📝 Assignments + weak topics"),
        ("Saturday", "🧪 Mock / previous-paper practice"),
        ("Sunday", "🔁 Weekly revision + progress analysis")
    ]

    st.table(
        [{"Day": day, "Focus": focus} for day, focus in plan]
    )

    st.subheader("📚 Every Subject Rule")

    st.write(
        "Har week **all subjects** ko at least ek baar revise/practice karo. "
        "Weak subjects ko extra time do."
    )

    week_df = get_week_records(username, selected_monday)

    if not week_df.empty:
        st.subheader("📊 Selected Week Record")

        weekly_subjects = (
            week_df.groupby("Subject")["Hours"]
            .sum()
            .reindex(subjects, fill_value=0)
        )

        st.bar_chart(weekly_subjects)

        st.metric(
            "Total weekly study",
            f"{float(week_df['Hours'].sum()):.1f} hours"
        )

    else:
        st.info("Is week ke liye abhi koi study record saved nahi hai.")

    st.divider()

    st.subheader("🎓 November Exam Roadmap")

    roadmap = [
        ("September", "📖 Concepts + syllabus coverage"),
        ("Early October", "🧠 Practice + weak topics"),
        ("Late October", "🧪 Mocks + previous questions"),
        ("November", "🔁 Final revision + exam mode")
    ]

    st.table(
        [{"Phase": phase, "Focus": focus} for phase, focus in roadmap]
    )

    if gate_enabled:
        st.success(
            "🎯 GATE is enabled. Keep it secondary to your college/exam "
            "priorities when your November exams are close."
        )
    else:
        st.info("GATE preparation is optional and currently OFF.")


# ============================================================
# STUDY RECORD
# ============================================================

elif page == "📝 Study Record":

    st.title("📝 Add Study Record")

    study_date = st.date_input(
        "Study date",
        value=date.today()
    )

    subject = st.selectbox(
        "Subject",
        subjects
    )

    hours = st.number_input(
        "Study hours",
        min_value=0.0,
        max_value=12.0,
        value=1.0,
        step=0.25
    )

    completed = st.checkbox(
        "✅ Mark task as completed",
        value=True
    )

    if st.button(
        "💾 Save Study Record",
        use_container_width=True
    ):
        save_study_record(
            username,
            study_date,
            subject,
            hours,
            completed
        )
        st.success("Study record saved successfully.")

    st.divider()

    st.subheader("📋 Your Recent Records")

    fresh_records = get_records(username)

    if fresh_records.empty:
        st.info("No records yet.")
    else:
        st.dataframe(
            fresh_records.head(30),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# SUBJECTS
# ============================================================

elif page == "📚 Subjects":

    st.title("📚 Manage Subjects")

    st.write("Current subjects:")

    for subject in subjects:
        st.write(f"• {subject}")

    st.divider()

    new_subject = st.text_input(
        "Add new subject",
        placeholder="e.g. Software Engineering"
    )

    if st.button("➕ Add Subject", use_container_width=True):
        if add_subject(username, new_subject):
            st.success(f"{new_subject} added.")
            st.rerun()
        else:
            st.warning("Subject empty hai ya already exists.")


# ============================================================
# PROFILE
# ============================================================

elif page == "⚙️ Profile":

    st.title("⚙️ Student Profile")

    st.write(f"**Username:** {username}")
    st.write(f"**Goal:** {goal}")
    st.write(
        f"**GATE Preparation:** "
        f"{'Enabled 🎯' if gate_enabled else 'Optional / Disabled'}"
    )

    st.divider()

    st.subheader("🎯 Mission Rules")

    st.write("1. 📚 Har subject ko weekly cover karo.")
    st.write("2. 📈 Har study session ka record save karo.")
    st.write("3. 🧠 Weak topics ko extra time do.")
    st.write("4. 🔁 Sunday ko weekly progress check karo.")
    st.write("5. 🎓 November exams ke liye October tak major syllabus complete karne ki koshish karo.")
    st.write("6. 🌙 Midnight target ko flexible rakho; sleep aur breaks important hain.")

    st.divider()

    st.subheader("📊 Overall Statistics")

    if records.empty:
        st.info("Statistics ke liye study records add karo.")
    else:
        show_metric_cards(
            [
                ("Total Study", f"{records['Hours'].sum():.1f} h"),
                ("Study Sessions", len(records)),
                ("Subjects", records["Subject"].nunique()),
                ("Best Day", str(records.groupby("Date")["Hours"].sum().max()) + " h")
            ]
        )

st.divider()

st.caption(
    "🎓 CGPA Mission • Personal Study Planner • Multi-user SQLite • "
    "Weekly Progress • November Exam Roadmap"
)
