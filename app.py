import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Google Sheets setup
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Replace with your Google Sheet ID (the long string in your Google Sheet URL)
SHEET_ID = "17xK1VRZKPPO8YjoG7s7DvD9aE8FdDEG1_3ArUqBgy9M"


def get_gsheet():
    # Load credentials from Streamlit secrets (nested TOML table)
    creds_dict = st.secrets["gcp_service_account"]

    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

def load_data():
    sheet = get_gsheet()
    df = get_as_dataframe(sheet, parse_dates=True)
    df.dropna(how="all", inplace=True)  # Remove empty rows
    return df

def save_data(df):
    sheet = get_gsheet()
    sheet.clear()
    set_with_dataframe(sheet, df)

def get_kid_options(df):
    return sorted(df["Kid"].dropna().unique())

# Load existing data from Google Sheets
df = load_data()

st.title("🏀 Basketball Lesson Tracker")

# --- Form: Add New Lesson ---
st.subheader("➕ Log a New Lesson")

with st.form("lesson_form"):
    date = st.date_input("Lesson Date", value=datetime.today())
    kid_options = get_kid_options(df)
    kid = st.selectbox("Kid's Name", options=[""] + kid_options) if kid_options else st.text_input("Kid's Name")
    if kid == "":
        kid = st.text_input("New Kid's Name")

    amount = st.number_input("Amount Paid ($)", value=40.0, step=5.0)
    notes = st.text_area("Notes", placeholder="Any special feedback or drills?")

    submitted = st.form_submit_button("Save Lesson")

    if submitted:
        new_row = {"Date": date, "Kid": kid.strip(), "Amount": amount, "Notes": notes}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success(f"Saved lesson for {kid} on {date.strftime('%b %d')}")

# --- Dashboard ---
st.subheader("📊 Dashboard")

if df.empty:
    st.info("No lessons yet! Add one above.")
else:
    df["Date"] = pd.to_datetime(df["Date"])

    with st.expander("🔍 Filter Options"):
        selected_kid = st.selectbox("Filter by Kid", options=["All"] + get_kid_options(df))
        start_date = st.date_input("Start Date", value=df["Date"].min().date())
        end_date = st.date_input("End Date", value=df["Date"].max().date())

        filtered = df.copy()
        if selected_kid != "All":
            filtered = filtered[filtered["Kid"] == selected_kid]
        filtered = filtered[(filtered["Date"] >= pd.to_datetime(start_date)) & (filtered["Date"] <= pd.to_datetime(end_date))]

    # Metrics horizontally
    col1, col2, col3 = st.columns(3)
    total_earned = filtered["Amount"].sum()
    total_lessons = len(filtered)
    top_kid = filtered["Kid"].value_counts().idxmax() if not filtered.empty else "N/A"

    col1.metric("💵 Total Earned", f"${total_earned:.2f}")
    col2.metric("📚 Lessons Given", total_lessons)
    col3.metric("🏅 Most Active Kid", top_kid)

    st.write("📄 Lesson Log", filtered.sort_values("Date", ascending=False))

    # Table: total amount by kid
    summary_table = filtered.groupby("Kid")["Amount"].sum().reset_index().rename(columns={"Amount": "Total Amount"})
    st.markdown("### 💰 Total Amount by Kid")
    st.table(summary_table)

    # Daily summary
    daily_summary = (
        filtered.groupby("Date")
        .agg(lesson_count=("Kid", "count"), total_amount=("Amount", "sum"))
        .reset_index()
        .sort_values("Date")
    )

    st.markdown("### 📅 Lessons Per Day Summary")
    for _, row in daily_summary.iterrows():
        st.write(f"{row['Date'].date()} — {row['lesson_count']} lessons (${row['total_amount']:.2f})")
