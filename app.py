
import os
import csv
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

import gradio as gr
import requests
from dotenv import load_dotenv

# --------------------------------------------------
# 1. LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

load_dotenv()

APP_TITLE = "My Next 4 Years | AI Growth Engine"

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"

LEADS_FILE = DATA_DIR / "leads.csv"
EVENTS_FILE = DATA_DIR / "events.csv"
CATALOG_FILE = DATA_DIR / "college_catalog.csv"

DATA_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# 2. CSV DATABASE CONFIGURATION
# --------------------------------------------------

LEAD_FIELDS = [
    "lead_id",
    "created_at",
    "name",
    "email",
    "phone",
    "exam",
    "rank_score",
    "state",
    "branch",
    "budget",
    "interests",
    "intent_score",
    "lead_status",
    "consent",
    "source"
]

EVENT_FIELDS = [
    "event_id",
    "created_at",
    "event_type",
    "lead_id",
    "details"
]


def ensure_csv(path, fields):

    if not path.exists():

        with path.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()


ensure_csv(LEADS_FILE, LEAD_FIELDS)
ensure_csv(EVENTS_FILE, EVENT_FIELDS)


# --------------------------------------------------
# 3. EVENT TRACKING
# --------------------------------------------------

def log_event(event_type, lead_id="", details=""):

    row = {
        "event_id": str(uuid.uuid4()),

        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "event_type": event_type,

        "lead_id": lead_id,

        "details": details[:1000]
    }

    with EVENTS_FILE.open(
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=EVENT_FIELDS
        )

        writer.writerow(row)


def read_rows(path):

    if not path.exists():
        return []

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        return list(csv.DictReader(file))


# --------------------------------------------------
# 4. COLLEGE CATALOGUE
# --------------------------------------------------

def get_catalog():

    if not CATALOG_FILE.exists():
        return []

    with CATALOG_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        rows = list(csv.DictReader(file))

    # Only show verified catalogue entries.

    return [
        row for row in rows
        if row.get(
            "verified",
            ""
        ).strip().lower() == "yes"
    ]


def catalog_matches(state, branch):

    matches = []

    for row in get_catalog():

        states = [
            x.strip().lower()
            for x in row.get(
                "state",
                ""
            ).split("|")
        ]

        branches = [
            x.strip().lower()
            for x in row.get(
                "branches",
                ""
            ).split("|")
        ]

        state_ok = (
            "all" in states
            or state.lower() in states
        )

        branch_ok = (
            "all" in branches
            or branch.lower() in branches
        )

        if state_ok and branch_ok:
            matches.append(row)

    return matches[:12]


# --------------------------------------------------
# 5. STUDENT PROFILE
# --------------------------------------------------

def make_profile(
    name,
    exam,
    rank_score,
    state,
    branch,
    budget,
    interests,
    preferences
):

    return {

        "name": (
            name or "Student"
        ).strip(),

        "exam": exam,

        "rank_score": (
            rank_score or "Not provided"
        ).strip(),

        "state": state,

        "branch": branch,

        "budget": budget,

        "interests": interests or [],

        "preferences": (
            preferences or ""
        ).strip()
    }


# --------------------------------------------------
# 6. STUDENT INTENT CLASSIFICATION
# --------------------------------------------------

def estimate_intent(profile):

    # This is a transparent engagement heuristic.
    # It is NOT an admission prediction.

    score = 20

    if profile["rank_score"] != "Not provided":
        score += 15

    if profile["state"]:
        score += 10

    if (
        profile["branch"]
        and profile["branch"] != "Not decided"
    ):
        score += 15

    if (
        profile["budget"]
        and profile["budget"] != "Not sure yet"
    ):
        score += 10

    if profile["interests"]:
        score += 15

    if profile["preferences"]:
        score += 5

    score = min(score, 90)

    if score >= 70:
        status = "High intent"

    elif score >= 45:
        status = "Medium intent"

    else:
        status = "Early exploration"

    return score, status


# --------------------------------------------------
# 7. GOOGLE GEMINI AI INTEGRATION
# --------------------------------------------------

def call_gemini(prompt):

    api_key = os.getenv(
        "GEMINI_API_KEY",
        ""
    ).strip()

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Add your Gemini API key to the .env file."
        )

    from google import genai

    client = genai.Client(
        api_key=api_key
    )

    model_name = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    response = client.models.generate_content(

        model=model_name,

        contents=prompt
    )

    if not getattr(response, "text", None):

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return response.text


# --------------------------------------------------
# 8. FALLBACK DISCOVERY REPORT
# --------------------------------------------------

def fallback_report(
    profile,
    catalog,
    intent_score,
    status
):

    interest = ", ".join(
        profile["interests"]
    ) if profile["interests"] else "Not specified"

    lines = [

        "# Your College & Career Discovery Snapshot",

        f"Hello **{profile['name']}** — here is a starting point for your research.",

        "## Your profile",

        f"- Exam: {profile['exam']}",

        f"- Rank/score: {profile['rank_score']}",

        f"- Preferred state: {profile['state']}",

        f"- Preferred branch: {profile['branch']}",

        f"- Annual tuition budget: {profile['budget']}",

        f"- Interests: {interest}",

        f"- Exploration readiness: **{status} ({intent_score}/100)**",

        "",

        "## What to investigate",

        "1. Check current eligibility and counselling rules with the official exam/counselling authority.",

        "2. Compare total cost, including tuition, hostel, transport and other fees.",

        "3. Review curriculum, labs, faculty, internships and placement reports from primary sources.",

        "4. Speak with current students and ask about day-to-day academic experience.",

        "",

        "## Verified catalogue matches"
    ]

    if catalog:

        for college in catalog:

            lines.append(

                f"- **{college.get('college_name', 'College')}** "
                f"— {college.get('state', '')}; "
                f"branches: {college.get('branches', '')}; "
                f"source: {college.get('source_url', '')}"

            )

    else:

        lines.append(

            "No matching entries marked verified are present in the sample catalogue. "
            "The app will not invent college names, cut-offs or fees."

        )

    lines += [

        "",

        "## NIAT information to verify",

        "If you are considering NIAT, independently check the current partner university, "
        "degree-awarding institution, curriculum, fees, campus, admission process and student support. "
        "Do not assume details are identical across partners.",

        "",

        "**Note:** This is an exploration aid, not an admission prediction or guarantee."

    ]

    return "\n".join(lines)


# --------------------------------------------------
# 9. GENERATE AI DISCOVERY REPORT
# --------------------------------------------------

def generate_discovery(

    name,
    exam,
    rank_score,
    state,
    branch,
    budget,
    interests,
    preferences

):

    profile = make_profile(

        name,
        exam,
        rank_score,
        state,
        branch,
        budget,
        interests,
        preferences

    )

    intent_score, status = estimate_intent(
        profile
    )

    matches = catalog_matches(
        state,
        branch
    )

    log_event(

        "profile_created",

        details=json.dumps({

            "exam": exam,

            "state": state,

            "branch": branch

        })

    )

    prompt = f"""

You are My Next 4 Years, an Indian college and career discovery assistant.

Your task is to generate a personalised college and career discovery report.

STUDENT PROFILE:

{json.dumps(profile, ensure_ascii=False)}

STUDENT INTEREST CLASSIFICATION:

{status} ({intent_score}/100)

VERIFIED COLLEGE CATALOGUE:

{json.dumps(matches, ensure_ascii=False)}

INSTRUCTIONS:

1. Welcome the student by name.

2. Summarise their academic profile.

3. Explain possible career paths based on their interests.

4. Explain what they should investigate before selecting a college.

5. Provide a college comparison checklist.

6. Suggest practical next steps.

7. Explain how to verify information using official counselling authorities and college websites.

8. Never invent college names, admission cut-offs, fees, placements, eligibility or institutional facts.

9. Only mention catalogue records included above, and label them as entries to independently verify.

10. Explain that the intent score is a simple engagement heuristic, not an admission score.

11. If NIAT is mentioned, advise the student to independently verify the current partner university, degree-awarding institution, curriculum, fees and admission process.

12. Use simple English that an Indian Class 12 student can understand.

13. Format the answer using Markdown headings, numbered lists and bullet points.

14. End with a short disclaimer that this is not an admission prediction or guarantee.

"""

    try:

        report = call_gemini(prompt)

        mode = (
            "AI report successfully generated using Google Gemini."
        )

    except Exception as exc:

        report = fallback_report(

            profile,
            matches,
            intent_score,
            status

        )

        mode = (
            "Demo/fallback report shown. "
            f"Gemini unavailable: {str(exc)[:220]}"
        )

    return (

        report,

        f"**{mode}**  \n"
        f"Lead interest: **{status} ({intent_score}/100)**",

        profile,

        intent_score,

        status

    )


# --------------------------------------------------
# 10. GOOGLE SHEETS INTEGRATION
# --------------------------------------------------

def save_to_google_sheets(row):

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()

    credentials_file = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "google_credentials.json"
    )

    credentials_path = ROOT / credentials_file

    if not sheet_id:
        return "Google Sheet ID not configured."

    if not credentials_path.exists():
        return "Google credentials JSON file not found."

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(
        str(credentials_path),
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    sheet = client.open_by_key(sheet_id).sheet1

    if not sheet.get_all_values():
        sheet.append_row(LEAD_FIELDS)

    sheet.append_row([
        str(row.get(field, ""))
        for field in LEAD_FIELDS
    ])

    return "Lead successfully synced to Google Sheets."


# --------------------------------------------------
# 11. N8N WEBHOOK INTEGRATION
# --------------------------------------------------

def send_to_n8n(row):

    webhook = os.getenv(
        "N8N_WEBHOOK_URL",
        ""
    ).strip()

    if not webhook:

        return "n8n webhook not configured."

    response = requests.post(

        webhook,

        json=row,

        timeout=15

    )

    response.raise_for_status()

    return "Lead successfully sent to n8n workflow."


# --------------------------------------------------
# 12. STUDENT LEAD CAPTURE
# --------------------------------------------------

def submit_lead(

    profile,
    email,
    phone,
    consent,
    intent_score,
    lead_status

):

    if not profile:

        raise gr.Error(

            "Generate a discovery report before submitting an enquiry."

        )

    if not consent:

        raise gr.Error(

            "Consent is required before submitting contact details."

        )

    email = (email or "").strip()

    phone = (phone or "").strip()

    if not email and not phone:

        raise gr.Error(

            "Please provide an email address or phone number."

        )

    if email and (

        "@" not in email

        or "." not in email.split("@")[-1]

    ):

        raise gr.Error(

            "Please enter a valid email address."

        )

    lead_id = str(uuid.uuid4())

    row = {

        "lead_id": lead_id,

        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "name": profile.get(
            "name",
            ""
        ),

        "email": email,

        "phone": phone,

        "exam": profile.get(
            "exam",
            ""
        ),

        "rank_score": profile.get(
            "rank_score",
            ""
        ),

        "state": profile.get(
            "state",
            ""
        ),

        "branch": profile.get(
            "branch",
            ""
        ),

        "budget": profile.get(
            "budget",
            ""
        ),

        "interests": ", ".join(
            profile.get(
                "interests",
                []
            )
        ),

        "intent_score": intent_score or 0,

        "lead_status": lead_status or "Unclassified",

        "consent": "yes",

        "source": "My Next 4 Years discovery page"

    }

    # Save locally.

    with LEADS_FILE.open(

        "a",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=LEAD_FIELDS

        )

        writer.writerow(row)

    log_event(

        "consented_enquiry_submitted",

        lead_id,

        row["lead_status"]

    )

    integrations = []

    # Optional integrations.

    for label, function in [

        ("Google Sheets", save_to_google_sheets),

        ("n8n", send_to_n8n)

    ]:

        try:

            integrations.append(
                function(row)
            )

        except Exception as exc:

            integrations.append(

                f"{label} error: {str(exc)[:180]}"

            )

    return (

        "Enquiry successfully saved. "

        + " ".join(integrations)

    )


# --------------------------------------------------
# 13. GEMINI AI CHAT ASSISTANT
# --------------------------------------------------

def ask_assistant(question, profile):

    if not question or not question.strip():

        raise gr.Error(
            "Please enter a question."
        )

    student_profile = profile or {}

    prompt = f"""

You are My Next 4 Years, an Indian college and career discovery assistant.

STUDENT PROFILE:

{json.dumps(student_profile, ensure_ascii=False)}

STUDENT QUESTION:

{question}

INSTRUCTIONS:

1. Answer in simple and clear English.

2. Give practical suggestions.

3. Explain concepts step by step when required.

4. Personalise your answer using the student profile.

5. Never fabricate current college cut-offs, fees, placement figures, eligibility or institutional facts.

6. Direct students to official sources for information that changes over time.

7. Use headings and bullet points where helpful.

8. Do not guarantee admission or employment.

"""

    try:

        answer = call_gemini(
            prompt
        )

        return answer

    except Exception as exc:

        return (

            f"Gemini AI is unavailable: {str(exc)[:220]}\n\n"

            "Please check your GEMINI_API_KEY in the .env file, "
            "verify your internet connection and restart the application.\n\n"

            "For now, compare official eligibility, fees, curriculum, "
            "location, facilities and student outcomes."

        )


# --------------------------------------------------
# 14. GROWTH ANALYTICS DASHBOARD
# --------------------------------------------------

def analytics():

    leads = read_rows(
        LEADS_FILE
    )

    events = read_rows(
        EVENTS_FILE
    )

    total_profiles = sum(

        1 for event in events

        if event.get("event_type") == "profile_created"

    )

    enquiries = len(leads)

    high = sum(

        1 for lead in leads

        if lead.get("lead_status") == "High intent"

    )

    medium = sum(

        1 for lead in leads

        if lead.get("lead_status") == "Medium intent"

    )

    conversion = (

        enquiries / total_profiles * 100

        if total_profiles

        else 0

    )

    summary = (

        "### Growth metrics\n\n"

        f"- Discovery profiles created: **{total_profiles}**\n\n"

        f"- Consented enquiries: **{enquiries}**\n\n"

        f"- High-intent enquiries: **{high}**\n\n"

        f"- Medium-intent enquiries: **{medium}**\n\n"

        f"- Profile-to-enquiry rate: **{conversion:.1f}%**\n\n"

        "These are local prototype counts from this app instance. "
        "They are not NIAT's actual metrics."

    )

    recent = leads[-10:][::-1]

    if recent:

        table = [

            [

                "Name",

                "Exam",

                "State",

                "Branch",

                "Intent",

                "Created (UTC)"

            ]

        ]

        for lead in recent:

            table.append([

                lead.get("name", ""),

                lead.get("exam", ""),

                lead.get("state", ""),

                lead.get("branch", ""),

                lead.get("lead_status", ""),

                lead.get("created_at", "")[:19]

            ])

    else:

        table = [

            [

                "No enquiries yet",

                "",

                "",

                "",

                "",

                ""

            ]

        ]

    return summary, table


def refresh_analytics():

    return analytics()


# --------------------------------------------------
# 15. GRADIO USER INTERFACE
# --------------------------------------------------

with gr.Blocks(

    title=APP_TITLE,

    theme=gr.themes.Soft()

) as app:

    # Application states.

    profile_state = gr.State({})

    score_state = gr.State(0)

    status_state = gr.State("Unclassified")

    # Main heading.

    gr.Markdown(

        "# 🎓 My Next 4 Years\n"

        "### AI-powered college & career discovery for students\n\n"

        "Explore options, get personalised guidance and request a follow-up. "

        "This is an independent prototype, not an official admissions service."

    )

    # --------------------------------------------------
    # TAB 1: DISCOVER
    # --------------------------------------------------

    with gr.Tab("1 · Discover"):

        gr.Markdown(
            "### Tell us what matters to you"
        )

        with gr.Row():

            name = gr.Textbox(
                label="Student name"
            )

            exam = gr.Dropdown(

                [

                    "AP EAPCET",

                    "TG EAPCET",

                    "JEE Main",

                    "Other / Not decided"

                ],

                value="AP EAPCET",

                label="Entrance exam"

            )

        with gr.Row():

            rank = gr.Textbox(

                label="Rank / score (optional)"

            )

            state = gr.Dropdown(

                [

                    "Andhra Pradesh",

                    "Telangana",

                    "Karnataka",

                    "Tamil Nadu",

                    "Other"

                ],

                value="Andhra Pradesh",

                label="Preferred state"

            )

        with gr.Row():

            branch = gr.Dropdown(

                [

                    "Computer Science / AI",

                    "CSE",

                    "AI & Data Science",

                    "ECE",

                    "Electrical / EEE",

                    "Mechanical",

                    "Not decided"

                ],

                value="Computer Science / AI",

                label="Preferred branch"

            )

            budget = gr.Dropdown(

                [

                    "Below ₹1 lakh/year",

                    "₹1–2 lakh/year",

                    "₹2–4 lakh/year",

                    "Above ₹4 lakh/year",

                    "Not sure yet"

                ],

                value="Not sure yet",

                label="Annual tuition budget"

            )

        interests = gr.CheckboxGroup(

            [

                "AI / Machine Learning",

                "Data Science",

                "Software Development",

                "Robotics / Embedded",

                "Electronics / VLSI",

                "Not sure yet"

            ],

            label="Career interests"

        )

        preferences = gr.Textbox(

            label="Other preferences (optional)",

            placeholder="For example: hostel, city, commute, language..."

        )

        discover_btn = gr.Button(

            "Generate my discovery report",

            variant="primary"

        )

        report = gr.Markdown()

        report_status = gr.Markdown()

        discover_btn.click(

            generate_discovery,

            [

                name,

                exam,

                rank,

                state,

                branch,

                budget,

                interests,

                preferences

            ],

            [

                report,

                report_status,

                profile_state,

                score_state,

                status_state

            ]

        )

    # --------------------------------------------------
    # TAB 2: ASK AI
    # --------------------------------------------------

    with gr.Tab("2 · Ask AI"):

        gr.Markdown(
            "### Ask a follow-up question"
        )

        question = gr.Textbox(

            label="Your question",

            lines=3,

            placeholder="What should I compare before choosing a college?"

        )

        ask_btn = gr.Button(

            "Ask the AI assistant",

            variant="primary"

        )

        answer = gr.Markdown()

        ask_btn.click(

            ask_assistant,

            [

                question,

                profile_state

            ],

            answer

        )

    # --------------------------------------------------
    # TAB 3: REQUEST FOLLOW-UP
    # --------------------------------------------------

    with gr.Tab("3 · Request follow-up"):

        gr.Markdown(

            "### Contact request\n\n"

            "Your details are collected only when you submit this form and give consent. "

            "The prototype stores submissions in a local CSV file and can optionally sync to Google Sheets/n8n."

        )

        email = gr.Textbox(

            label="Email address (optional)"

        )

        phone = gr.Textbox(

            label="Phone number (optional)"

        )

        consent = gr.Checkbox(

            label="I consent to being contacted about my education enquiry."

        )

        submit_btn = gr.Button(

            "Submit consent-based enquiry",

            variant="primary"

        )

        submit_status = gr.Markdown()

        submit_btn.click(

            submit_lead,

            [

                profile_state,

                email,

                phone,

                consent,

                score_state,

                status_state

            ],

            submit_status

        )

    # --------------------------------------------------
    # TAB 4: GROWTH DASHBOARD
    # --------------------------------------------------

    with gr.Tab("4 · Growth dashboard"):

        gr.Markdown(
            "### Funnel performance"
        )

        refresh_btn = gr.Button(
            "Refresh dashboard"
        )

        metrics = gr.Markdown()

        leads_table = gr.Dataframe(

            headers=[

                "Name",

                "Exam",

                "State",

                "Branch",

                "Intent",

                "Created (UTC)"

            ],

            interactive=False,

            label="Latest enquiries"

        )

        refresh_btn.click(

            refresh_analytics,

            outputs=[

                metrics,

                leads_table

            ]

        )

        app.load(

            refresh_analytics,

            outputs=[

                metrics,

                leads_table

            ]

        )

    # --------------------------------------------------
    # TAB 5: ABOUT & SAFEGUARDS
    # --------------------------------------------------

    with gr.Tab("About & safeguards"):

        gr.Markdown(

            "### Connected system components\n\n"

            "1. Gradio student acquisition interface.\n\n"

            "2. Google Gemini API for personalised report generation and AI question answering.\n\n"

            "3. Local CSV lead and event storage.\n\n"

            "4. Optional Google Sheets integration.\n\n"

            "5. Optional n8n webhook for downstream automation.\n\n"

            "6. Built-in growth funnel dashboard.\n\n"

            "### Important safeguards\n\n"

            "- Intent score is a transparent engagement heuristic, not an admission score.\n\n"

            "- The app does not invent cut-offs, fees, placement figures or college recommendations.\n\n"

            "- Only catalogue rows explicitly marked `yes` in the `verified` column are shown.\n\n"

            "- Contact details are saved only after explicit consent.\n\n"

            "- Do not enter sensitive personal information.\n\n"

            "- Verify current admission information with official sources."

        )


# --------------------------------------------------
# 16. LAUNCH APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.launch(

        server_name="127.0.0.1",

        server_port=int(
            os.getenv("PORT", "7860")
        ),

        show_error=True,

        inbrowser=True

    )
