import streamlit as st
import google.generativeai as genai
import io
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Configure Google Gemini API
GOOGLE_API_KEY = "AIzaSyDwOJg_uEVcDCN5oM2mA64QBaGYR8gWcK0"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)

# Function to call Google Gemini API
def call_gemini_api(prompt, max_tokens=500):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens))
        return response.text
    except Exception as e:
        st.error(f"Failed to call Gemini API: {str(e)}")
        return None

# Function to generate a structured study plan
def generate_study_plan(subjects, mode, daily_hours):
    prompt = f"""
    Generate a {mode} level study plan for the following subjects: {', '.join(subjects)}. 
    The user has {daily_hours} hours per day. 
    Provide the study plan in plain text format, organized by days of the week.
    Example:
    Monday:
    - Study Python basics for 2 hours
    - Solve Java problems for 1 hour

    Tuesday:
    - Learn Data Science concepts for 3 hours
    """
    response = call_gemini_api(prompt)
    return response if response else "Failed to generate study plan."

# Function to generate notes
def generate_notes(subject, mode):
    prompt = f"Generate {mode} level notes for {subject}. Include key concepts and examples."
    response = call_gemini_api(prompt)
    return response if response else f"No notes available for {subject}."

# Function to generate questions
def generate_questions(subject, mode):
    prompt = f"Generate {mode} level questions for {subject}. Include both theoretical and practical questions. Output questions in a numbered list format."
    response = call_gemini_api(prompt)
    if response:
        return [line.strip() for line in response.split('\n') if line.strip()]
    return ["No questions available."]

# Function to create a PDF
def create_pdf(subject, notes, questions):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Notes for {subject}", styles['Heading1']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(notes.replace('\n', '<br/>'), styles['BodyText']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Predicted Questions:", styles['Heading2']))
        for q in questions:
            story.append(Paragraph(f"- {q}", styles['BodyText']))

        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Failed to create PDF for {subject}: {str(e)}")
        return None

# Function to parse hours from task string
def parse_hours(task):
    try:
        return float(task.split("for")[-1].split("hour")[0].strip())
    except:
        return 0.0

# Function to generate performance report
def generate_performance_report(scheduled_plan, completed_tasks):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    scheduled_hours = {day: 0.0 for day in days}
    actual_hours = {day: 0.0 for day in days}

    if not isinstance(scheduled_plan, str):
        st.error("Study plan format is incorrect. Unable to generate report.")
        return

    # Parse scheduled hours
    current_day = None
    for line in scheduled_plan.split('\n'):
        if line.strip() in days:
            current_day = line.strip()
        elif '-' in line and current_day:
            scheduled_hours[current_day] += parse_hours(line)

    # Calculate completed hours
    for day, tasks in completed_tasks.items():
        if isinstance(tasks, list):
            actual_hours[day] = sum(parse_hours(task) for task in tasks)

    total_scheduled_hours = sum(scheduled_hours.values())
    total_actual_hours = sum(actual_hours.values())

    df = pd.DataFrame({
        "Metric": ["Total Scheduled Hours", "Total Completed Hours"],
        "Value": [total_scheduled_hours, total_actual_hours]
    })

    fig, ax = plt.subplots()
    ax.bar(df["Metric"], df["Value"])
    ax.set_ylabel("Hours")
    ax.set_title("Scheduled vs Completed Study Hours")
    st.pyplot(fig)
    st.write("### Performance Report")
    st.dataframe(df)

# Function to generate quiz
def generate_quiz(study_plan, completed_tasks):
    quiz_questions = []
    if not completed_tasks:
        st.write("No tasks completed yet. Complete tasks to generate a quiz.")
        return

    for day, tasks in completed_tasks.items():
        if isinstance(tasks, list):
            for task in tasks:
                prompt = f"Generate a multiple-choice quiz question related to: '{task}'. Include 4 options and the correct answer."
                response = call_gemini_api(prompt)
                if response:
                    quiz_questions.append(response)
    if quiz_questions:
        st.subheader("📝 Quiz Time!")
        for i, question in enumerate(quiz_questions, 1):
            st.write(f"Question {i}:")
            st.write(question)
            st.write("---")
    else:
        st.write("No quiz questions available. Complete some tasks to generate a quiz.")

# Streamlit App
st.title("📚 AI-Powered Study Planner Bot")

# Initialize session state
if "weekly_plan" not in st.session_state:
    st.session_state.weekly_plan = ""
if "completed_tasks" not in st.session_state:
    st.session_state.completed_tasks = {}

# User input
name = st.text_input("Enter your name:")
subjects_list = ["Python", "Java", "Data Science", "C", "C++", "HTML", "CSS", "JavaScript"]
selected_subjects = st.multiselect("Select subjects you want to study:", subjects_list)
mode = st.selectbox("Choose Study Mode:", ["Easy", "Moderate", "Advanced"])
daily_hours = st.number_input("Enter total available study hours per day (max 12):", min_value=1.0, max_value=12.0, step=0.5, value=1.0)

# Generate Study Plan
if st.button("Generate Study Plan"):
    if not name:
        st.error("Please enter your name.")
    elif not selected_subjects:
        st.error("Please select at least one subject.")
    else:
        study_plan = generate_study_plan(selected_subjects, mode, daily_hours)
        st.session_state.weekly_plan = study_plan
        st.subheader(f"✅ {mode} Study Plan")
        st.write(st.session_state.weekly_plan)

# Notes and PDFs
if selected_subjects:
    st.subheader("📝 Notes and PDFs")
    for subject in selected_subjects:
        notes = generate_notes(subject, mode)
        questions = generate_questions(subject, mode)
        st.markdown(f"### {subject} Notes")
        st.write(notes)
        st.markdown("Predicted Questions:")
        st.write("\n".join(questions))

        pdf_buffer = create_pdf(subject, notes, questions)
        if pdf_buffer:
            st.download_button(
                label=f"Download {subject} Notes PDF",
                data=pdf_buffer,
                file_name=f"{subject}notes{mode.lower()}.pdf",
                mime="application/pdf"
            )

# Study Plan & Progress Tracking
if st.session_state.weekly_plan:
    st.subheader("📅 Track Your Study Progress")
    completed_tasks = st.session_state.completed_tasks

    task_list = st.session_state.weekly_plan.split('\n')
    for task in task_list:
        if '-' in task:
            if st.checkbox(task, key=task):
                day = task_list[task_list.index(task) - 1].replace(':', '')
                if day not in completed_tasks:
                    completed_tasks[day] = []
                if task not in completed_tasks[day]:
                    completed_tasks[day].append(task)
    st.session_state.completed_tasks = completed_tasks

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate Performance Report"):
            generate_performance_report(st.session_state.weekly_plan, st.session_state.completed_tasks)
    with col2:
        if st.button("Generate Quiz"):
            generate_quiz(st.session_state.weekly_plan, st.session_state.completed_tasks)