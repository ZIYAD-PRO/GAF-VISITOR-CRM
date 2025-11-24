# ----------------------------------------------
# GAF Communication App v7
# - Remembers previous work (auto-load autosave)
# - Auto-saves to visitors_autosave_gaf.xlsx
# - Tabs + Progress dashboard + Templates
# ----------------------------------------------

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date, timedelta
import os

st.set_page_config(page_title="GAF Communication App v7", layout="wide")

st.title("🛫 Global Airports Forum – Visitor Communication & CRM")
st.caption("Made for: *Muhammed Ziyaad – Business Engagement Team*")

AUTOSAVE_VISITORS = "visitors_autosave_gaf.xlsx"
AUTOSAVE_EXHIBITORS = "exhibitors_autosave_gaf.xlsx"

# ==============================================
# Helpers: Loaders & Column Detection
# ==============================================
def ensure_crm_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make sure all CRM columns exist."""
    if "Call Status" not in df.columns:
        df["Call Status"] = ""
    if "Call Notes" not in df.columns:
        df["Call Notes"] = ""
    if "Priority" not in df.columns:
        df["Priority"] = 3
    if "Updated By" not in df.columns:
        df["Updated By"] = ""
    if "Email Sent" not in df.columns:
        df["Email Sent"] = "No"
    if "WhatsApp Sent" not in df.columns:
        df["WhatsApp Sent"] = "No"
    if "Logged In" not in df.columns:
        df["Logged In"] = "No"
    if "Last Updated" not in df.columns:
        df["Last Updated"] = ""
    return df


def load_visitors_uploaded(file):
    """Load visitor Excel where row 3 is header (original ZIYAAD.xlsx)."""
    df = pd.read_excel(file, header=2)  # 0-based, so row3 = 2
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    df = df.dropna(how="all")
    df = ensure_crm_columns(df)
    return df


def load_visitors_autosave(path: str):
    """Load visitors from autosave file (standard Excel header at row 1)."""
    df = pd.read_excel(path)
    df = df.dropna(how="all")
    df = ensure_crm_columns(df)
    return df


def load_exhibitors_any(source):
    """Load exhibitors from uploaded file or autosave path."""
    df = pd.read_excel(source)
    df = df.dropna(how="all")
    return df


def detect_columns(df):
    """Detect important columns from ZIYAAD.xlsx."""
    col_map = {
        "first_name": None,
        "last_name": None,
        "email": None,
        "phone": None,
        "nationality": None,
        "country": None,
        "primary_interest": None,
        "secondary_interest": None,
        "company": None,
        "job_title": None,
        "logged_in": None,
    }

    for col in df.columns:
        name = str(col).strip().lower()

        if name == "first name":
            col_map["first_name"] = col
        elif name == "last name":
            col_map["last_name"] = col
        elif name == "email":
            col_map["email"] = col
        elif name in ["phone", "mobile", "telephone"]:
            col_map["phone"] = col
        elif name == "nationality":
            col_map["nationality"] = col
        elif name == "country":
            col_map["country"] = col
        elif name == "primary interest":
            col_map["primary_interest"] = col
        elif name == "secondary interest":
            col_map["secondary_interest"] = col
        elif name == "company":
            col_map["company"] = col
        elif name == "job title":
            col_map["job_title"] = col
        elif "logged" in name:
            col_map["logged_in"] = col

    return col_map


# ==============================================
# Small helper functions
# ==============================================
def normalize(text):
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def search_results(df, query):
    if not query:
        return df
    q = normalize(query)
    mask = df.apply(lambda row: q in normalize(str(row)), axis=1)
    return df[mask]


def safe(visitor_row, col_key, col_map):
    col = col_map.get(col_key)
    if col is None:
        return "—"
    return visitor_row.get(col, "—")


def parse_interests(value):
    if pd.isna(value):
        return []
    text = str(value)
    text = text.replace("،", ",")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    unique = []
    for p in parts:
        if p not in unique:
            unique.append(p)
    return unique


def match_exhibitors(df_exhibitors, interests):
    if df_exhibitors is None:
        return {}
    matches = {}
    for intr in interests:
        if intr in df_exhibitors.columns:
            companies = df_exhibitors[intr].dropna().astype(str).tolist()
            if companies:
                matches[intr] = companies
    return matches


def autosave_visitors(df, filename=AUTOSAVE_VISITORS):
    """Auto-save current visitor data to an Excel file on disk."""
    try:
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        st.sidebar.success(f"🔄 Autosaved visitors to: {filename}")
    except Exception as e:
        st.sidebar.error(f"Autosave failed: {e}")


def autosave_exhibitors(df, filename=AUTOSAVE_EXHIBITORS):
    """Save exhibitors so app remembers list next time."""
    try:
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        st.sidebar.success(f"💾 Saved exhibitors to: {filename}")
    except Exception as e:
        st.sidebar.error(f"Exhibitors autosave failed: {e}")


# ==============================================
# Upload / Auto-load Section
# ==============================================
st.header("📂 Upload Files (or Use Last Saved)")

col_up1, col_up2 = st.columns(2)

with col_up1:
    visitor_file = st.file_uploader("Visitor Excel (ZIYAAD.xlsx OR autosave)", type=["xlsx"])

with col_up2:
    exhibitor_file = st.file_uploader("Exhibitor Excel (list of exhibitors.xlsx OR autosave)", type=["xlsx"])

df_visitors = None
df_exhibitors = None
visitor_source = ""
exhibitor_source = ""

# --- Visitors load logic ---
if visitor_file is not None:
    df_visitors = load_visitors_uploaded(visitor_file)
    visitor_source = "upload"
    st.success(f"Loaded {len(df_visitors)} visitor records from uploaded file.")
elif os.path.exists(AUTOSAVE_VISITORS):
    df_visitors = load_visitors_autosave(AUTOSAVE_VISITORS)
    visitor_source = "autosave"
    st.info(f"Loaded {len(df_visitors)} visitor records from previous autosave ({AUTOSAVE_VISITORS}).")

if df_visitors is None:
    st.error("No visitor data available. Please upload ZIYAAD.xlsx at least once.")
    st.stop()

# --- Exhibitors load logic ---
if exhibitor_file is not None:
    df_exhibitors = load_exhibitors_any(exhibitor_file)
    exhibitor_source = "upload"
    st.success(f"Loaded {len(df_exhibitors)} exhibitor rows from uploaded file.")
    autosave_exhibitors(df_exhibitors)  # remember this list
elif os.path.exists(AUTOSAVE_EXHIBITORS):
    df_exhibitors = load_exhibitors_any(AUTOSAVE_EXHIBITORS)
    exhibitor_source = "autosave"
    st.info(f"Loaded {len(df_exhibitors)} exhibitor rows from previous save ({AUTOSAVE_EXHIBITORS}).")
else:
    df_exhibitors = None
    st.warning("No exhibitor list loaded yet. You can still work on calls, but exhibitor matching will be empty.")

# Sidebar info
if visitor_source == "upload":
    st.sidebar.info("📁 Using *uploaded* visitor file this session.")
elif visitor_source == "autosave":
    st.sidebar.info("📁 Using *previous autosave* visitor file.")

if exhibitor_source == "upload":
    st.sidebar.info("🏢 Using *uploaded* exhibitor list.")
elif exhibitor_source == "autosave":
    st.sidebar.info("🏢 Using *saved* exhibitor list from last session.")

detected_cols = detect_columns(df_visitors)

with st.expander("🔍 Show Auto-Detected Column Mapping", expanded=False):
    st.json(detected_cols)

# ==============================================
# Search & Select Visitor
# ==============================================
st.markdown("---")
st.header("🔍 1. Search & Select Visitor")

search_term = st.text_input("Search by name, company, email, or phone")

results = search_results(df_visitors, search_term)
st.write(f"Found *{len(results)}* visitor(s).")

if len(results) == 0:
    st.stop()

selected_row = st.selectbox(
    "Select Visitor",
    results.index,
    format_func=lambda i: f"{results.loc[i, detected_cols.get('first_name', '')]} {results.loc[i, detected_cols.get('last_name', '')]}"
)

visitor = df_visitors.loc[selected_row]

# Pre-calc values used everywhere
first_name = safe(visitor, "first_name", detected_cols)
last_name = safe(visitor, "last_name", detected_cols)
visitor_full_name = f"{first_name} {last_name}".strip()
job_title = safe(visitor, "job_title", detected_cols)
company = safe(visitor, "company", detected_cols)
email = safe(visitor, "email", detected_cols)
phone = safe(visitor, "phone", detected_cols)
country = safe(visitor, "country", detected_cols)
primary_interest_val = safe(visitor, "primary_interest", detected_cols)
secondary_interest_val = safe(visitor, "secondary_interest", detected_cols)

primary_interests = parse_interests(primary_interest_val)
secondary_interests = parse_interests(secondary_interest_val)

logged_status = str(safe(visitor, "logged_in", detected_cols)).strip().lower()
is_logged_in = (logged_status == "yes")

# Exhibitor matches
primary_matches = match_exhibitors(df_exhibitors, primary_interests)
secondary_matches = match_exhibitors(df_exhibitors, secondary_interests)

# ==============================================
# TABS LAYOUT
# ==============================================
st.markdown("---")
tabs = st.tabs([
    "👤 2. Profile & Call",
    "📊 3. Progress",
    "🏢 4. Exhibitor Matching",
    "🌐 5. Language & Templates",
    "📥 6. Export",
])

# ==============================================
# TAB 1 — Profile & Call Panel
# ==============================================
with tabs[0]:
    st.subheader("👤 Profile Overview")

    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
        st.markdown("*Name*")
        st.write(visitor_full_name or "—")
        st.markdown("*Job Title*")
        st.write(job_title or "—")
        st.markdown("*Company*")
        st.write(company or "—")

    with col_p2:
        st.markdown("*Email*")
        st.write(email or "—")
        st.markdown("*Phone*")
        st.write(phone or "—")
        st.markdown("*Country*")
        st.write(country or "—")

    with col_p3:
        st.markdown("*Primary Interest*")
        st.write(primary_interest_val or "—")
        st.markdown("*Secondary Interest*")
        st.write(secondary_interest_val or "—")
        st.markdown("*Account Logged In?*")
        st.write("✅ Yes" if is_logged_in else "❌ Not yet / Unknown")

    st.markdown("---")
    st.subheader("⭐ Priority & Follow-Up")

    col_call_left, col_call_right = st.columns(2)

    # LEFT: Call status + communication checkboxes
    with col_call_left:
        st.markdown("### 📌 Call Status")

        status_options = [
            "",
            "Not Contacted",
            "No Answer / Busy",
            "Spoken – Interested",
            "Spoken – Not Interested",
            "Follow-up Required",
            "Meeting Requested",
            "Meeting Confirmed",
        ]

        current_status = df_visitors.at[selected_row, "Call Status"]
        new_status = st.selectbox(
            "Call Status",
            status_options,
            index=status_options.index(current_status) if current_status in status_options else 0,
        )
        df_visitors.at[selected_row, "Call Status"] = new_status

        st.markdown("### 📨 Communication Status")

        current_email_sent = df_visitors.at[selected_row, "Email Sent"]
        current_whatsapp_sent = df_visitors.at[selected_row, "WhatsApp Sent"]
        current_logged_in_flag = df_visitors.at[selected_row, "Logged In"]

        email_sent_checkbox = st.checkbox(
            "Email Sent ✔",
            value=(current_email_sent == "Yes"),
        )
        whatsapp_sent_checkbox = st.checkbox(
            "WhatsApp Sent ✔",
            value=(current_whatsapp_sent == "Yes"),
        )
        login_checkbox = st.checkbox(
            "Visitor Logged In (Platform)",
            value=(current_logged_in_flag == "Yes"),
        )

        df_visitors.at[selected_row, "Email Sent"] = "Yes" if email_sent_checkbox else "No"
        df_visitors.at[selected_row, "WhatsApp Sent"] = "Yes" if whatsapp_sent_checkbox else "No"
        df_visitors.at[selected_row, "Logged In"] = "Yes" if login_checkbox else "No"

    # RIGHT: Notes + priority
    with col_call_right:
        st.markdown("### 📝 Notes")
        current_notes = df_visitors.at[selected_row, "Call Notes"]
        new_notes = st.text_area(
            "Write Notes Here:",
            value=current_notes,
            height=180,
        )
        df_visitors.at[selected_row, "Call Notes"] = new_notes

        st.markdown("### ⭐ Priority Slider")

        priority_value = int(df_visitors.at[selected_row, "Priority"])
        new_priority = st.slider("Set Priority (1 Low → 5 High)", 1, 5, priority_value)
        df_visitors.at[selected_row, "Priority"] = new_priority

        priority_display = {
            1: ("🟢 LOW", "Low priority – not urgent"),
            2: ("🟡 MEDIUM-LOW", "Moderate follow-up"),
            3: ("🟠 MEDIUM", "Standard follow-up"),
            4: ("🟠 HIGH-MEDIUM", "Important – follow soon"),
            5: ("🔴 HIGH", "Urgent – contact immediately"),
        }
        color_label, desc = priority_display.get(new_priority, ("⚪ Unknown", ""))
        st.markdown(f"*Priority Level:* {color_label}")
        st.caption(desc)

    # Stamp updater & date for progress tracking
    df_visitors.at[selected_row, "Updated By"] = "Muhammed Ziyaad"
    df_visitors.at[selected_row, "Last Updated"] = date.today().isoformat()

    st.success("✔ Call details updated (autosave active).")

# ==============================================
# TAB 2 — Progress (Daily / Weekly / Monthly)
# ==============================================
with tabs[1]:
    st.subheader("📊 Progress Overview")

    # Prepare date column
    last_updated_series = pd.to_datetime(df_visitors["Last Updated"], errors="coerce").dt.date
    today = date.today()
    start_week = today - timedelta(days=today.weekday())  # Monday
    start_month = today.replace(day=1)

    def get_stats(start_d, end_d):
        mask = (last_updated_series >= start_d) & (last_updated_series <= end_d)
        subset = df_visitors[mask]

        total_updated = len(subset)

        # Calls attempted = any status other than blank / Not Contacted
        calls_attempted = subset["Call Status"].apply(
            lambda s: isinstance(s, str) and s.strip() not in ["", "Not Contacted"]
        ).sum()

        contacted_statuses = [
            "Spoken – Interested",
            "Spoken – Not Interested",
            "Follow-up Required",
            "Meeting Requested",
            "Meeting Confirmed",
        ]
        contacted = subset["Call Status"].isin(contacted_statuses).sum()

        emails_sent = (subset["Email Sent"] == "Yes").sum()
        whatsapp_sent = (subset["WhatsApp Sent"] == "Yes").sum()
        followups = (subset["Call Status"] == "Follow-up Required").sum()

        return {
            "total_updated": total_updated,
            "calls_attempted": calls_attempted,
            "contacted": contacted,
            "emails_sent": emails_sent,
            "whatsapp_sent": whatsapp_sent,
            "followups": followups,
            "subset": subset,
        }

    stats_today = get_stats(today, today)
    stats_week = get_stats(start_week, today)
    stats_month = get_stats(start_month, today)

    total_visitors = len(df_visitors)
    daily_target_calls = 100  # your daily target

    # Today summary
    st.markdown("### 📅 Today")

    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.metric("Updated Today", stats_today["total_updated"])
    with col_t2:
        st.metric("Calls Attempted", stats_today["calls_attempted"])
    with col_t3:
        st.metric("Contacted (Spoken)", stats_today["contacted"])
    with col_t4:
        st.metric("Follow-ups Marked", stats_today["followups"])

    if daily_target_calls > 0:
        st.write("*Daily Call Target Progress*")
        st.progress(min(1.0, stats_today["calls_attempted"] / daily_target_calls))
        st.caption(f"Calls today: {stats_today['calls_attempted']} / {daily_target_calls} target")

    st.markdown("---")
    st.markdown("### 📆 This Week")

    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    with col_w1:
        st.metric("Updated This Week", stats_week["total_updated"])
    with col_w2:
        st.metric("Calls Attempted", stats_week["calls_attempted"])
    with col_w3:
        st.metric("Emails Sent", stats_week["emails_sent"])
    with col_w4:
        st.metric("WhatsApps Sent", stats_week["whatsapp_sent"])

    if total_visitors > 0:
        st.write("*Visitor Coverage (Week)*")
        st.progress(min(1.0, stats_week["total_updated"] / total_visitors))

    st.markdown("---")
    st.markdown("### 🗓 This Month")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Updated This Month", stats_month["total_updated"])
    with col_m2:
        st.metric("Calls Attempted", stats_month["calls_attempted"])
    with col_m3:
        st.metric("Emails Sent", stats_month["emails_sent"])
    with col_m4:
        st.metric("Follow-ups", stats_month["followups"])

    if total_visitors > 0:
        st.write("*Visitor Coverage (Month)*")
        st.progress(min(1.0, stats_month["total_updated"] / total_visitors))

    st.markdown("---")
    st.markdown("### 📊 Visual Summary (Today / Week / Month)")

    progress_df = pd.DataFrame({
        "Period": ["Today", "This Week", "This Month"],
        "Updated Records": [
            stats_today["total_updated"],
            stats_week["total_updated"],
            stats_month["total_updated"],
        ],
        "Calls Attempted": [
            stats_today["calls_attempted"],
            stats_week["calls_attempted"],
            stats_month["calls_attempted"],
        ],
        "Contacted (Spoken)": [
            stats_today["contacted"],
            stats_week["contacted"],
            stats_month["contacted"],
        ],
        "Emails Sent": [
            stats_today["emails_sent"],
            stats_week["emails_sent"],
            stats_month["emails_sent"],
        ],
        "WhatsApps Sent": [
            stats_today["whatsapp_sent"],
            stats_week["whatsapp_sent"],
            stats_month["whatsapp_sent"],
        ],
        "Follow-ups": [
            stats_today["followups"],
            stats_week["followups"],
            stats_month["followups"],
        ],
    }).set_index("Period")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### 🔵 Updated Records & Calls")
        st.bar_chart(progress_df[["Updated Records", "Calls Attempted"]])

    with col_g2:
        st.markdown("#### 🟣 Contact, Email, WhatsApp, Follow-ups")
        st.bar_chart(progress_df[["Contacted (Spoken)", "Emails Sent", "WhatsApps Sent", "Follow-ups"]])

    st.markdown("---")
    st.markdown("### ☎ Today’s Call Status Breakdown")

    subset_today = stats_today["subset"]
    if len(subset_today) == 0:
        st.caption("No visitors updated today yet.")
    else:
        status_counts = (
            subset_today["Call Status"]
            .fillna("")
            .replace("", "No Status")
            .value_counts()
            .sort_values(ascending=False)
        )
        status_df = status_counts.to_frame(name="Count")
        st.bar_chart(status_df)
        st.caption("Shows how many visitors are in each call status for *today*.")

# ==============================================
# TAB 3 — Exhibitor Matching
# ==============================================
with tabs[2]:
    st.subheader("🏢 Exhibitor Matching")

    col_int1, col_int2 = st.columns(2)
    with col_int1:
        st.markdown("### 🟦 Primary Interests")
        if primary_interests:
            for p in primary_interests:
                st.write(f"- {p}")
        else:
            st.write("No primary interests.")

    with col_int2:
        st.markdown("### 🟩 Secondary Interests")
        if secondary_interests:
            for s in secondary_interests:
                st.write(f"- {s}")
        else:
            st.write("No secondary interests.")

    st.markdown("---")
    st.markdown("### 🏭 Matched Exhibitors")

    if df_exhibitors is None:
        st.info("Upload the exhibitor Excel file to see matches.")
    elif not primary_matches and not secondary_matches:
        st.warning("No matching exhibitor categories found for this visitor.")
    else:
        if primary_matches:
            st.markdown("#### 🔵 Primary Interest Matches")
            for intr, companies in primary_matches.items():
                st.markdown(f"{intr}")
                for c in companies:
                    st.write(f"- {c}")
        if secondary_matches:
            st.markdown("#### 🟢 Secondary Interest Matches")
            for intr, companies in secondary_matches.items():
                st.markdown(f"{intr}")
                for c in companies:
                    st.write(f"- {c}")

# ==============================================
# TAB 4 — Language & Templates (Email + WhatsApp)
# ==============================================
with tabs[3]:
    st.subheader("🌐 Language & Communication Templates")

    language_options = [
        "English",
        "Arabic",
        "Hindi",
        "Urdu",
        "Filipino",
        "French",
        "Italian",
        "Chinese",
        "Russian",
        "Turkish",
    ]

    selected_language = st.selectbox("Choose additional language", language_options, index=1)

    st.markdown("---")
    st.subheader("📧 Email Templates")

    def build_exhibitor_block(pm, sm):
        lines = []
        if pm:
            lines.append("YOUR PRIMARY INTEREST(S):")
            for intr, companies in pm.items():
                lines.append(f"\n{intr}:")
                for i, c in enumerate(companies, start=1):
                    lines.append(f"{i}. {c}")
        if sm:
            lines.append("\nYOUR SECONDARY INTEREST(S):")
            for intr, companies in sm.items():
                lines.append(f"\n{intr}:")
                for i, c in enumerate(companies, start=1):
                    lines.append(f"{i}. {c}")
        if not lines:
            return "(No exhibitor list available yet.)"
        return "\n".join(lines)

    exhibitor_block = build_exhibitor_block(primary_matches, secondary_matches)

    if is_logged_in:
        email_subject_en = "Connect with Exhibitors That Match Your Business Interests at Global Airports Forum"
        email_intro_en = f"""Dear {visitor_full_name},

We’ve identified several exhibiting companies whose business sectors align with the areas of interest you selected during registration. Please review the list below and highlight which companies you’d like to meet during Global Airports Forum 2025. I’ll assist in arranging these meetings through the Business Engagement platform."""
        email_closing_en = """
Once you’ve reviewed the list, please reply with your preferred companies so I can help schedule your meetings in advance.

Best regards,
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""
    else:
        email_subject_en = "Activate Your Account — Connect with Exhibitors Matching Your Interests at Global Airports Forum"
        email_intro_en = f"""Dear {visitor_full_name},

Based on the areas of interest you selected during registration, we’ve identified several exhibiting companies whose business sectors align with what you’re looking for. Once you log in to your Business Engagement account, you’ll be able to view exhibitor profiles, send and receive meeting requests, and plan your schedule ahead of the show. Please review the list below and log in using the link provided to select which companies you’d like to meet."""
        email_closing_en = """
Login here:
https://globalairportsforum.com/event-tools/

Download the mobile app:
iOS (iPhone): https://apps.apple.com/id/app/gaf-2025/id6752826285
Android: https://play.google.com/store/apps/details?id=com.jublia.gaf2025

Once you’ve activated your account, reply to this email with your preferred companies and I’ll help schedule your meetings.

Best regards,
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""

    email_body_en = (
        email_intro_en
        + "\n\nExhibiting Companies Matching Your Interest Areas:\n\n"
        + exhibitor_block
        + email_closing_en
    )

    col_email_left, col_email_right = st.columns(2)

    with col_email_left:
        st.markdown("#### 🇬🇧 English Email — Subject")
        st.code(email_subject_en, language="text")
        st.markdown("#### 🇬🇧 English Email — Body")
        st.code(email_body_en, language="text")

    with col_email_right:
        st.markdown(f"#### 🌐 {selected_language} Email")

        primary_text = primary_interest_val or "Not available"
        secondary_text = secondary_interest_val or "Not available"

        if selected_language == "English":
            email_body_lang = email_body_en

        elif selected_language == "Arabic":
            email_body_lang = f"""سعادة {visitor_full_name} المحترم،

استنادًا إلى مجالات الاهتمام التي اخترتموها أثناء التسجيل، قمنا بتحديد عدد من الشركات العارضة التي تتوافق قطاعات أعمالها مع ما تبحثون عنه۔

الاهتمام الأساسي: {primary_text}
الاهتمام الثانوي: {secondary_text}

يرجى تسجيل الدخول إلى حسابكم في منصة Business Engagement للاطلاع على ملفات العارضين وإرسال واستقبال طلبات الاجتماعات، وترتيب جدولكم قبل انطلاق المعرض:
https://globalairportsforum.com/event-tools/

كما يمكنكم تحميل تطبيق GAF 2025 على أجهزة iOS وأندرويد لإدارة اجتماعاتكم بسهولة أثناء الفعالية۔

بعد الاطلاع على قائمة الشركات، نرجو تزويدنا بأولوية الشركات التي تودون الاجتماع بها، وسأقوم بمساعدتكم في جدولة الاجتماعات مسبقًا۔

مع خالص التحية،
محمد زياد
فريق Business Engagement
Global Airports Forum
"""

        elif selected_language == "Hindi":
            email_body_lang = f"""प्रिय {visitor_full_name},

आपकी पंजीकरण के समय चुनी गई रुचियों के आधार पर, हमने ऐसे कई प्रदर्शकों की पहचान की है जिनके व्यवसाय आपके आवश्यकताओं से मेल खाते हैं।

मुख्य रुचि: {primary_text}
द्वितीयक रुचि: {secondary_text}

कृपया अपने Business Engagement खाते में लॉग इन करके प्रदर्शकों की प्रोफाइल देखें, मीटिंग रिक्वेस्ट भेजें और शो से पहले ही अपना शेड्यूल प्लान करें:
https://globalairportsforum.com/event-tools/

आप ऐप GAF 2025 को iOS और Android पर भी उपयोग कर सकते हैं।

कृपया सूची की समीक्षा करने के बाद हमें बताएं कि आप किन कंपनियों से मिलना चाहते हैं, ताकि मैं आपकी मीटिंग्स शेड्यूल करने में मदद कर सकूँ।

सादर,
मुहम्मद ज़ियाद
Business Engagement टीम
Global Airports Forum
"""

        elif selected_language == "Urdu":
            email_body_lang = f"""محترم {visitor_full_name}،

رجسٹریشن کے دوران آپ کی منتخب کردہ دلچسپیوں کی بنیاد پر ہم نے ایسی نمائش کنندہ کمپنیوں की فہرست تیار کی ہے جو آپ کی کاروباری ضروریات سے مطابقت رکھتی हैं۔

بنیادی دلچسپی: {primary_text}
ثانوی دلچسپی: {secondary_text}

براہِ کرم अपने Business Engagement اکاؤنٹ में لاگ اِن ہو कर عارضین کے پروفائل ملاحظہ کریں، میٹنگ की درخواستیں بھیجیں और ایونٹ سے پہلے اپنا شیڈول منظم کریں:
https://globalairportsforum.com/event-tools/

آپ iOS और Android के لئے GAF 2025 موبائل ایپ بھی استعمال कर سکتے हैं।

فہرست کا جائزہ لینے کے بعد براہِ کرم ہمیں ان کمپنیوں کے نام ارسال کریں جن سے آپ ملاقات کرنا چاہتے हैं، تاکہ میں آپ की ملاقاتوں کو پہلے سے شیڈول کر سکوں۔

نیک تمنائیں،
محمد زیاد
بزنس انگیجمنٹ ٹیم
Global Airports Forum
"""

        elif selected_language == "Filipino":
            email_body_lang = f"""Mahal na {visitor_full_name},

Batay sa mga interest na pinili mo noong rehistrasyon, nakapili kami ng ilang exhibitors na tumutugma sa pangangailangan ng iyong negosyo۔

Pangunahing interest: {primary_text}
Pangalawang interest: {secondary_text}

Mangyaring mag-log in sa iyong Business Engagement account upang makita ang mga profile ng exhibitors, magpadala at tumanggap ng meeting requests, at maayos ang iyong schedule bago magsimula ang forum:
https://globalairportsforum.com/event-tools/

Available din ang GAF 2025 mobile app sa iOS at Android para mas madali mong ma-manage ang iyong mga meeting۔

Pagkatapos mong tingnan ang listahan، paki-ibahagi kung aling mga kompanya ang nais mong makausap upang matulungan kitang i-schedule ang mga meeting nang maaga۔

Lubos na gumagalang،
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""

        elif selected_language == "French":
            email_body_lang = f"""Cher/Chère {visitor_full_name},

Sur la base des centres d’intérêt que vous avez indiqués lors de votre inscription, nous avons identifié plusieurs exposants dont les activités correspondent à vos besoins۔

Intérêt principal : {primary_text}
Intérêt secondaire : {secondary_text}

Nous vous invitons à vous connecter à votre compte Business Engagement afin de consulter les profils des exposants, d’envoyer et de recevoir des demandes de rendez-vous et de planifier votre agenda avant le salon :
https://globalairportsforum.com/event-tools/

Vous pouvez également utiliser l’application mobile GAF 2025 (iOS et Android) pour gérer vos rendez-vous pendant l’événement۔

Après avoir consulté la liste، merci de nous indiquer les entreprises que vous souhaitez rencontrer afin que je puisse vous aider à organiser vos rendez-vous à l’avance۔

Cordialement،
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""

        elif selected_language == "Italian":
            email_body_lang = f"""Gentile {visitor_full_name},

In base agli interessi indicati in fase di registrazione, abbiamo individuato diversi espositori i cui settori di attività corrispondono alle esigenze del suo business۔

Interesse principale: {primary_text}
Interesse secondario: {secondary_text}

La invitiamo ad accedere al suo account Business Engagement per consultare i profili degli espositori, inviare e ricevere richieste di incontro e pianificare l’agenda prima dell’evento:
https://globalairportsforum.com/event-tools/

Può inoltre utilizzare l’app mobile GAF 2025 (iOS e Android) per gestire comodamente i suoi meeting durante il forum۔

Dopo aver visionato l’elenco، la preghiamo di indicarci le aziende che desidera incontrare، così potrò aiutarla a fissare gli appuntamenti in anticipo۔

Cordiali saluti،
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""

        elif selected_language == "Chinese":
            email_body_lang = f"""尊敬的 {visitor_full_name}，

根据您在注册时选择的兴趣领域，我们为您筛选出多家与您业务需求高度匹配的参展企业。

主要兴趣：{primary_text}
次要兴趣：{secondary_text}

请登录您的 Business Engagement 账户，查看参展商资料、发送和接收会议预约，并在展会开始前合理安排您的行程：
https://globalairportsforum.com/event-tools/

您还可以在 iOS 和 Android 设备上使用 GAF 2025 手机应用，方便地管理现场会面。

在浏览完名单后，请告知您希望重点会面的企业，我将协助您提前安排会议时间。

此致敬礼，
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""

        elif selected_language == "Russian":
            email_body_lang = f"""Уважаемый(ая) {visitor_full_name},

На основе интересов, которые вы указали при регистрации, мы отобрали несколько компаний-экспонентов, чья деятельность соответствует потребностям вашего бизнеса۔

Основной интерес: {primary_text}
Второстепенный интерес: {secondary_text}

Пожалуйста, войдите в свой аккаунт Business Engagement, чтобы просмотреть профили экспонентов, отправить и получить запросы на встречи и спланировать свой график до начала форума:
https://globalairportsforum.com/event-tools/

Также вы можете использовать мобильное приложение GAF 2025 (iOS и Android) для удобного управления встречами во время мероприятия۔

После ознакомления со списком، сообщите, с какими компаниями вы хотели бы встретиться، и я помогу заранее организовать эти встречи۔

С уважением،
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""

        elif selected_language == "Turkish":
            email_body_lang = f"""Sayın {visitor_full_name},

Kayıt sırasında seçtiğiniz ilgi alanlarına göre, iş ihtiyaçlarınıza uygun çeşitli katılımcı firmaları belirledik۔

Ana ilgi alanı: {primary_text}
İkincil ilgi alanı: {secondary_text}

Lütfen Business Engagement hesabınıza giriş yaparak katılımcı profillerini inceleyin, toplantı talepleri gönderip alın ve etkinlik başlamadan önce programınızı planlayın:
https://globalairportsforum.com/event-tools/

Ayrıca GAF 2025 mobil uygulamasını (iOS ve Android) kullanarak forum süresince toplantılarınızı kolayca yönetebilirsiniz۔

Listeyi inceledikten sonra, görüşmek istediğiniz firmaları bizimle paylaşmanız halinde, toplantılarınızın önceden планlanmasına yardımcı olabilirim۔

Saygılarımla،
Muhammed Ziyaad
Business Engagement Team
Global Airports Forum
"""

        else:
            email_body_lang = email_body_en

        st.code(email_body_lang, language="text")

    st.markdown("---")
    st.subheader("📲 WhatsApp Templates")

    primary_text = primary_interest_val or "Not available"
    secondary_text = secondary_interest_val or "Not available"

    wa_english = f"""Hello {visitor_full_name},

This is Muhammed Ziyaad from the Global Airports Forum Business Engagement Team.

Based on the areas of interest you selected during registration (Primary: {primary_text}, Secondary: {secondary_text}), we’ve identified several exhibitors that match your business needs.

Please log in to your Business Engagement account to review them and select which companies you’d like to meet:
https://globalairportsforum.com/event-tools/

Once you’ve chosen, I’ll help schedule your meetings in advance.
"""

    col_wa_left, col_wa_right = st.columns(2)

    with col_wa_left:
        st.markdown("#### 🇬🇧 WhatsApp (English)")
        st.code(wa_english, language="text")

    with col_wa_right:
        st.markdown(f"#### 🌐 WhatsApp ({selected_language})")

        if selected_language == "English":
            wa_lang = wa_english

        elif selected_language == "Arabic":
            wa_lang = f"""مرحبًا {visitor_full_name}،

معك محمد زياد من فريق Business Engagement في Global Airports Forum۔

استنادًا إلى مجالات الاهتمام التي اخترتموها أثناء التسجيل (الاهتمام الأساسي: {primary_text}، الاهتمام الثانوي: {secondary_text})، قمنا بتحديد عدد من العارضين المناسبين لكم۔

يمكنكم تسجيل الدخول إلى حسابكم عبر الرابط التالي للاطلاع على الشركات واختيار من تودون مقابلته:
https://globalairportsforum.com/event-tools/

بعد اختياركم للشركات المفضلة، يسعدني أن أساعدكم في جدولة الاجتماعات مسبقًا۔
"""

        elif selected_language == "Hindi":
            wa_lang = f"""नमस्ते {visitor_full_name},

मैं मुहम्मद ज़ियाद, Global Airports Forum की Business Engagement टीम से बोल रहा हूँ।

आपकी पंजीकरण रुचियों (मुख्य: {primary_text}, द्वितीयक: {secondary_text}) के आधार पर हमने आपके लिए उपयुक्त प्रदर्शकों की सूची तैयार की है।

कृपया नीचे दिए गए लिंक से अपने खाते में लॉग इन करके कंपनियों की सूची देखें और जिनसे मिलना चाहें उन्हें चुनें:
https://globalairportsforum.com/event-tools/

आपके चयन के बाद, मैं आपकी मीटिंग्स शेड्यूल करने में मदद करूँगा।
"""

        elif selected_language == "Urdu":
            wa_lang = f"""السلام علیکم {visitor_full_name}،

میں محمد زیاد، Global Airports Forum کی بزنس انگیجمنٹ टीम سے ہوں۔

آپ کی رجسٹریشن کے دوران منتخب کردہ دلچسپیوں (بنیادی: {primary_text}، ثانوی: {secondary_text}) کی بنیاد پر ہم نے آپ کے لیے مناسب نمائش کنندگان کی فہرست تیار کی है۔

براہِ کرم اس لنک کے ذریعے لاگ اِن ہوں اور کمپنیوں کی تفصیل دیکھ کر اُن کا انتخاب کریں جن سے آپ ملنا چاہتے हैं:
https://globalairportsforum.com/event-tools/

آپ کے انتخاب کے بعد، میں آپ کی ملاقاتوں کو شیڈول کرنے میں مدد کروں گا۔
"""

        elif selected_language == "Filipino":
            wa_lang = f"""Hello {visitor_full_name},

Ito si Muhammed Ziyaad mula sa Business Engagement Team ng Global Airports Forum۔

Batay sa mga interest na pinili mo (Primary: {primary_text}, Secondary: {secondary_text}), nakapili kami ng ilang exhibitors na akma sa iyong pangangailangan۔

Paki-log in dito upang makita ang listahan at pumili ng mga kumpanyang gusto mong makausap:
https://globalairportsforum.com/event-tools/

Pagkatapos mong pumili, tutulungan kitang i-schedule ang mga meeting۔
"""

        elif selected_language == "French":
            wa_lang = f"""Bonjour {visitor_full_name},

Ici Muhammed Ziyaad de l’équipe Business Engagement du Global Airports Forum۔

En fonction des centres d’intérêt indiqués lors de votre inscription (principal : {primary_text}, secondaire : {secondary_text}), nous avons identifié plusieurs exposants pertinents pour votre activité۔

Merci de vous connecter à votre compte pour consulter la liste et choisir les entreprises que vous souhaitez rencontrer :
https://globalairportsforum.com/event-tools/

Je pourrai ensuite vous aider à organiser les rendez-vous à l’avance۔
"""

        elif selected_language == "Italian":
            wa_lang = f"""Buongiorno {visitor_full_name},

sono Muhammed Ziyaad del Business Engagement Team del Global Airports Forum۔

In base agli interessi indicati in fase di registrazione (principale: {primary_text}, secondario: {secondary_text}), abbiamo selezionato alcuni espositori adatti al suo business۔

La invito ad accedere al suo account per consultare l’elenco e scegliere le aziende con cui desidera incontrarsi:
https://globalairportsforum.com/event-tools/

Successivamente potrò aiutarla a fissare gli appuntamenti۔
"""

        elif selected_language == "Chinese":
            wa_lang = f"""您好 {visitor_full_name}，

我是 Global Airports Forum 业务联络团队的 Muhammed Ziyaad۔

根据您在注册时选择的兴趣（主要：{primary_text}，次要：{secondary_text}），我们为您筛选了一些匹配的参展企业۔

请通过以下链接登录您的账户，查看企业名单并选择希望会面的公司：
https://globalairportsforum.com/event-tools/

确定意向后，我可以协助您提前安排会议时间۔
"""

        elif selected_language == "Russian":
            wa_lang = f"""Здравствуйте, {visitor_full_name},

это Muhammed Ziyaad из команды Business Engagement форума Global Airports Forum۔

С учётом ваших интересов при регистрации (основной: {primary_text}, второстепенный: {secondary_text}) мы подобрали для вас список подходящих экспонентов۔

Пожалуйста, войдите в свой аккаунт по ссылке ниже, просмотрите список компаний и выберите тех, с кем вы хотели бы встретиться:
https://globalairportsforum.com/event-tools/

После вашего выбора я помогу заранее согласовать время встреч۔
"""

        elif selected_language == "Turkish":
            wa_lang = f"""Merhaba {visitor_full_name},

Ben Global Airports Forum Business Engagement ekibinden Muhammed Ziyaad۔

Kayıt sırasında seçtiğiniz ilgi alanlarına (Ana: {primary_text}, İkincil: {secondary_text}) göre, işinize uygun bazı katılımcı firmaları belirledik۔

Lütfen aşağıdaki bağlantı üzerinden hesabınıza giriş yaparak firma listesini inceleyin ve görüşmek istediğiniz şirketleri seçin:
https://globalairportsforum.com/event-tools/

Seçiminizin ardından toplantılarınızı önceden planlamanıza memnuniyetle yardımcı olurum۔
"""

        else:
            wa_lang = wa_english

        st.code(wa_lang, language="text")

# ==============================================
# TAB 5 — Export (optional manual download)
# ==============================================
with tabs[4]:
    st.subheader("📥 Export Updated Visitor List (Optional)")

    def visitors_to_excel_bytes(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output

    excel_bytes = visitors_to_excel_bytes(df_visitors)

    st.download_button(
        label="⬇ Download Updated Excel File",
        data=excel_bytes,
        file_name="visitors_updated_gaf.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.info(
        "You *do not* need to click this to save your work. "
        "Autosave is already writing to visitors_autosave_gaf.xlsx. "
        "This download is just if you want a copy / backup."
    )

# ==============================================
# GLOBAL AUTOSAVE (end of script)
# ==============================================
autosave_visitors(df_visitors)