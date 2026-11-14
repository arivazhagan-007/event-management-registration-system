import os
import sqlite3
from datetime import date, datetime
import pandas as pd
import streamlit as st

DB_PATH = "events.db"

st.set_page_config(page_title="Event Management & Registration", page_icon="🎟️", layout="wide")

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_conn() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, category TEXT, description TEXT,
            event_date TEXT, location TEXT, capacity INTEGER,
            skills TEXT, status TEXT DEFAULT 'Open'
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE,
            interests TEXT, skills TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER, participant_id INTEGER,
            registered_at TEXT, status TEXT DEFAULT 'Registered',
            UNIQUE(event_id, participant_id),
            FOREIGN KEY(event_id) REFERENCES events(id),
            FOREIGN KEY(participant_id) REFERENCES participants(id)
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER, participant_id INTEGER,
            rating INTEGER, comments TEXT
        )""")

def read_df(query, params=()):
    with get_conn() as con:
        return pd.read_sql_query(query, con, params=params)

def seed_demo():
    with get_conn() as con:
        count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count == 0:
            events = [
                ("AI & Data Science Summit", "Technology", "Explore practical AI, ML and analytics applications.", "2026-12-05", "Chennai", 120, "AI, machine learning, python, data"),
                ("Startup Networking Meetup", "Business", "Connect with founders, students and early-stage teams.", "2026-12-12", "Coimbatore", 80, "startup, business, networking"),
                ("Python Web Development Workshop", "Workshop", "Hands-on introduction to Python web applications.", "2026-12-18", "Online", 50, "python, web development, programming"),
                ("Creative Design Fest", "Design", "A showcase of UI, graphic and product design.", "2026-12-22", "Chennai", 100, "design, creativity, ui, ux")
            ]
            con.executemany("""INSERT INTO events
                (title,category,description,event_date,location,capacity,skills)
                VALUES (?,?,?,?,?,?,?)""", events)
            people = [
                ("Arun Kumar", "arun@example.com", "AI, data science, python", "python, machine learning"),
                ("Priya S", "priya@example.com", "design, ui, creativity", "figma, ui, ux"),
                ("Karthik R", "karthik@example.com", "startup, networking, business", "communication, marketing")
            ]
            con.executemany("INSERT INTO participants (name,email,interests,skills) VALUES (?,?,?,?)", people)

def tokens(value):
    return {x.strip().lower() for x in (value or "").replace(";", ",").split(",") if x.strip()}

def match_score(person, event):
    interests = tokens(person.get("interests", "")) | tokens(person.get("skills", ""))
    tags = tokens(event.get("skills", "")) | tokens(event.get("category", ""))
    if not interests or not tags:
        return 0
    overlap = len(interests & tags)
    return round(100 * overlap / max(1, len(tags)), 1)

def ai_generate(prompt, system_prompt="You are a helpful event planning assistant."):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "AI assistant is not configured yet. Add OPENAI_API_KEY to your environment or .env file to enable LLM responses. The event matching feature works without an API key."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"AI request could not be completed: {exc}"

init_db()
seed_demo()

st.title("🎟️ Event Management & Registration System")
st.caption("Discover events, manage registrations, and use AI-powered matching to improve event participation.")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Go to", ["Dashboard", "Browse & Register", "Manage Events", "Participants", "AI Event Assistant", "Feedback"])
    st.divider()
    st.caption("Demo data is included on first launch. Data is stored locally in events.db.")

events_df = read_df("SELECT * FROM events ORDER BY event_date")
regs_df = read_df("""SELECT r.id, e.title AS event, p.name AS participant, p.email,
    r.registered_at, r.status FROM registrations r
    JOIN events e ON e.id=r.event_id JOIN participants p ON p.id=r.participant_id""")
people_df = read_df("SELECT * FROM participants")

if page == "Dashboard":
    st.subheader("Overview")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total events", len(events_df))
    c2.metric("Participants", len(people_df))
    c3.metric("Registrations", len(regs_df))
    c4.metric("Open events", int((events_df["status"] == "Open").sum()) if not events_df.empty else 0)
    left,right = st.columns(2)
    with left:
        st.markdown("#### Registrations by event")
        if not regs_df.empty:
            st.bar_chart(regs_df.groupby("event").size().rename("Registrations"))
        else:
            st.info("No registrations yet.")
    with right:
        st.markdown("#### Upcoming events")
        if not events_df.empty:
            st.dataframe(events_df[["title","event_date","location","category","status"]], use_container_width=True, hide_index=True)
        else:
            st.info("Add an event to get started.")
    st.markdown("#### Recent registrations")
    st.dataframe(regs_df.tail(8), use_container_width=True, hide_index=True)

elif page == "Browse & Register":
    st.subheader("Find an event that matches your interests")
    with st.expander("Create or update your participant profile", expanded=True):
        with st.form("participant_form"):
            name = st.text_input("Full name")
            email = st.text_input("Email")
            interests = st.text_input("Interests (comma-separated)", placeholder="AI, Python, networking")
            skills = st.text_input("Skills (comma-separated)", placeholder="Python, communication")
            submitted = st.form_submit_button("Save participant profile")
        if submitted:
            if not name.strip() or "@" not in email:
                st.error("Enter a name and a valid email address.")
            else:
                try:
                    with get_conn() as con:
                        con.execute("""INSERT INTO participants(name,email,interests,skills) VALUES(?,?,?,?)
                            ON CONFLICT(email) DO UPDATE SET name=excluded.name, interests=excluded.interests, skills=excluded.skills""",
                            (name.strip(), email.strip().lower(), interests, skills))
                    st.success("Participant profile saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    people_df = read_df("SELECT * FROM participants")
    events_df = read_df("SELECT * FROM events WHERE status='Open' ORDER BY event_date")
    if not people_df.empty and not events_df.empty:
        chosen_email = st.selectbox("Select your participant profile", people_df["email"].tolist())
        person_row = people_df[people_df.email == chosen_email].iloc[0].to_dict()
        scored = []
        for _, ev in events_df.iterrows():
            row = ev.to_dict()
            row["Match score"] = match_score(person_row, row)
            scored.append(row)
        scored_df = pd.DataFrame(scored).sort_values("Match score", ascending=False)
        st.markdown("#### Recommended events")
        for _, ev in scored_df.iterrows():
            with st.container(border=True):
                a,b = st.columns([4,1])
                with a:
                    st.markdown(f"**{ev['title']}**  ·  {ev['category']}")
                    st.write(ev["description"])
                    st.caption(f"{ev['event_date']}  |  {ev['location']}  |  Tags: {ev['skills']}")
                with b:
                    st.metric("Match", f"{ev['Match score']}%")
                    if st.button("Register", key=f"reg_{int(ev['id'])}"):
                        try:
                            with get_conn() as con:
                                registered = con.execute("SELECT COUNT(*) FROM registrations WHERE event_id=? AND status='Registered'", (int(ev["id"]),)).fetchone()[0]
                                if registered >= int(ev["capacity"]):
                                    st.error("This event has reached its capacity.")
                                else:
                                    con.execute("INSERT INTO registrations(event_id,participant_id,registered_at) VALUES(?,?,?)",
                                        (int(ev["id"]), int(person_row["id"]), datetime.now().isoformat(timespec="minutes")))
                                    st.success("Registration successful!")
                                    st.rerun()
                        except sqlite3.IntegrityError:
                            st.warning("You are already registered for this event.")
    else:
        st.info("Add at least one participant and one open event to use recommendations.")

elif page == "Manage Events":
    st.subheader("Create and manage events")
    with st.form("event_form"):
        title = st.text_input("Event title")
        category = st.selectbox("Category", ["Technology","Workshop","Business","Design","Education","Other"])
        description = st.text_area("Description")
        event_date = st.date_input("Event date", value=date.today())
        location = st.text_input("Location", value="Online")
        capacity = st.number_input("Capacity", min_value=1, max_value=100000, value=50)
        skills = st.text_input("Matching tags / skills", placeholder="AI, Python, data science")
        add = st.form_submit_button("Add event")
    if add:
        if not title.strip():
            st.error("Event title is required.")
        else:
            with get_conn() as con:
                con.execute("""INSERT INTO events(title,category,description,event_date,location,capacity,skills)
                    VALUES(?,?,?,?,?,?,?)""", (title,category,description,str(event_date),location,int(capacity),skills))
            st.success("Event added.")
            st.rerun()
    st.markdown("#### Existing events")
    st.dataframe(events_df, use_container_width=True, hide_index=True)
    if not events_df.empty:
        selected = st.selectbox("Change event status", events_df["id"].tolist(), format_func=lambda x: f"#{x} — {events_df[events_df.id==x].iloc[0]['title']}")
        status = st.selectbox("Status", ["Open","Closed","Completed"])
        if st.button("Update status"):
            with get_conn() as con:
                con.execute("UPDATE events SET status=? WHERE id=?", (status,int(selected)))
            st.success("Event status updated.")
            st.rerun()

elif page == "Participants":
    st.subheader("Participants and registrations")
    st.dataframe(people_df, use_container_width=True, hide_index=True)
    st.markdown("#### Registration list")
    st.dataframe(regs_df, use_container_width=True, hide_index=True)
    if not regs_df.empty:
        reg_id = st.selectbox("Select registration to cancel", regs_df["id"].tolist())
        if st.button("Cancel selected registration"):
            with get_conn() as con:
                con.execute("UPDATE registrations SET status='Cancelled' WHERE id=?", (int(reg_id),))
            st.success("Registration cancelled.")
            st.rerun()

elif page == "AI Event Assistant":
    st.subheader("AI assistant for event organisers")
    st.write("Generate event descriptions, promotion ideas, schedules, and practical ways to improve attendance.")
    goal = st.selectbox("What do you need help with?", ["Write an event description","Suggest a promotion plan","Create an event agenda","Improve event attendance","Analyse event feedback"])
    details = st.text_area("Describe your event and requirements", placeholder="Example: A one-day Python workshop for college students in Chennai...")
    if st.button("Generate with AI"):
        if not details.strip():
            st.warning("Enter a few details about your event.")
        else:
            prompt = f"Task: {goal}\nEvent details: {details}\nGive a clear, practical answer with headings and actionable suggestions."
            st.markdown(ai_generate(prompt))

elif page == "Feedback":
    st.subheader("Collect participant feedback")
    all_events = read_df("SELECT id,title FROM events ORDER BY event_date")
    all_people = read_df("SELECT id,name,email FROM participants ORDER BY name")
    if not all_events.empty and not all_people.empty:
        with st.form("feedback_form"):
            ev_id = st.selectbox("Event", all_events["id"].tolist(), format_func=lambda x: all_events[all_events.id==x].iloc[0]["title"])
            p_id = st.selectbox("Participant", all_people["id"].tolist(), format_func=lambda x: all_people[all_people.id==x].iloc[0]["name"])
            rating = st.slider("Rating", 1, 5, 4)
            comments = st.text_area("Comments")
            save = st.form_submit_button("Submit feedback")
        if save:
            with get_conn() as con:
                con.execute("INSERT INTO feedback(event_id,participant_id,rating,comments) VALUES(?,?,?,?)",
                    (int(ev_id),int(p_id),int(rating),comments))
            st.success("Feedback submitted.")
    feedback_df = read_df("""SELECT e.title AS event,p.name AS participant,f.rating,f.comments
        FROM feedback f JOIN events e ON e.id=f.event_id JOIN participants p ON p.id=f.participant_id""")
    st.markdown("#### Feedback summary")
    if not feedback_df.empty:
        st.dataframe(feedback_df, use_container_width=True, hide_index=True)
        st.metric("Average rating", f"{feedback_df.rating.mean():.1f}/5")
    else:
        st.info("No feedback has been submitted yet.")

st.divider()
st.caption("Academic prototype · Matching uses keyword overlap as a simple baseline. Configure an LLM API key to enable the generative AI assistant.")
