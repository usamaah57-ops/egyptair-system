import streamlit as st
import sqlite3
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

DB_FILE = "flight_data.db"

# --- Initialize Database ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Current services table
    c.execute("""
        CREATE TABLE IF NOT EXISTS services (
            key TEXT PRIMARY KEY,
            time TEXT,
            staff TEXT
        )
    """)

    # Archive table
    c.execute("""
        CREATE TABLE IF NOT EXISTS archive (
            flight TEXT,
            reg TEXT,
            date TEXT,
            key TEXT,
            time TEXT,
            staff TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_service(key, time, staff):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO services (key, time, staff) VALUES (?, ?, ?)", (key, time, staff))
    conn.commit()
    conn.close()


def load_services():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key, time, staff FROM services")
    rows = c.fetchall()
    conn.close()
    return {r[0]: {"time": r[1], "staff": r[2]} for r in rows}


def clear_services():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM services")
    conn.commit()
    conn.close()


# --- Archive with duplicate prevention ---
def archive_services(flight, reg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date = datetime.now().strftime("%d/%m/%Y")

    # Check if flight already archived with same number, reg, and date
    c.execute("SELECT COUNT(*) FROM archive WHERE flight=? AND reg=? AND date=?", (flight, reg, date))
    exists = c.fetchone()[0]

    if exists > 0:
        st.warning(f"⚠️ Flight {flight} ({reg}) already archived for {date}.")
        conn.close()
        return False

    services = load_services()
    for k, v in services.items():
        c.execute("INSERT INTO archive (flight, reg, date, key, time, staff) VALUES (?, ?, ?, ?, ?, ?)",
                  (flight, reg, date, k, v['time'], v['staff']))

    conn.commit()
    conn.close()
    return True


def load_archive():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT flight, reg, date, key, time, staff FROM archive ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return rows


# --- FIXED PDF Generator ---
def generate_pdf(flight, reg, date, records):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Baghdad Station Operations Report", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.ln(5)
    pdf.cell(0, 8, f"Flight: {flight}", ln=True)
    pdf.cell(0, 8, f"Registration: {reg}", ln=True)
    pdf.cell(0, 8, f"Date: {date}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 8, "Service", border=1)
    pdf.cell(40, 8, "Time", border=1)
    pdf.cell(80, 8, "Staff", border=1, ln=True)

    pdf.set_font("Arial", "", 11)
    for r in records:
        pdf.cell(60, 8, r[3], border=1)
        pdf.cell(40, 8, r[4], border=1)
        pdf.cell(80, 8, r[5], border=1, ln=True)

    # --- FIX: Correct PDF output for Streamlit ---
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer


# --- Initialize DB ---
init_db()

# --- Page Settings ---
st.set_page_config(page_title="Baghdad Station Operations", page_icon="✈️", layout="centered")

# --- Header Image ---
st.image("egyptair_plane.jpg.webp", use_column_width=True)

st.title("✈️ Baghdad Station Operations")

# --- Staff Login ---
if 'staff_confirmed' not in st.session_state:
    st.session_state.staff_confirmed = False

if 'current_staff' not in st.session_state:
    st.session_state.current_staff = ""

if not st.session_state.staff_confirmed:
    name_input = st.text_input("Enter your full name:")
    if st.button("Confirm and Enter"):
        if name_input.strip():
            st.session_state.current_staff = name_input.strip()
            st.session_state.staff_confirmed = True
            st.rerun()
        else:
            st.error("Please enter your name to continue.")
    st.stop()

st.write(f"👷 Current Staff: **{st.session_state.current_staff}**")

# --- Flight Inputs ---
flight = st.text_input("Flight Number", value="MS616").upper()
reg = st.text_input("Registration (Reg)", value="SU-").upper()

st.divider()

# --- Add New Flight Button ---
if st.button("➕ Add New Flight", use_container_width=True):
    clear_services()
    st.rerun()

# --- Services ---
services_labels = [
    ("⏱ Chocks ON", "CHOCKS_ON"), ("⚡ GPU Arrival", "GPU_ARRIVAL"),
    ("🔌 APU Start", "APU_START"), ("🛠 Air Starter", "AIR_STARTER"),
    ("📦 FWD Open", "FWD_OPEN"), ("📦 FWD Close", "FWD_CLOSE"),
    ("📦 AFT Open", "AFT_OPEN"), ("📦 AFT Close", "AFT_CLOSE"),
    ("🚛 Fuel Arrival", "FUEL_ARRIVAL"), ("⛽ Fuel End", "FUEL_END"),
    ("🧹 Cleaning START", "CLEANING_START"), ("✨ Cleaning END", "CLEANING_END"),
    ("🚶 First Pax", "FIRST_PAX"), ("🏁 Last Pax", "LAST_PAX"),
    ("📑 Loadsheet", "LOADSHEET"), ("🚪 Close Door", "CLOSE_DOOR"),
    ("🚜 Pushback Truck", "PUSHBACK_TRUCK"), ("🚀 Push Back", "PUSH_BACK")
]

current_shared_times = load_services()
cols = st.columns(2)

for i, (label, key) in enumerate(services_labels):
    if key in current_shared_times:
        recorded = current_shared_times[key]
        cols[i % 2].success(f"{label}\n{recorded['time']} ({recorded['staff']})")
    else:
        if cols[i % 2].button(label, key=key, use_container_width=True):
            now_t = datetime.now().strftime("%H:%M")
            save_service(key, now_t, st.session_state.current_staff)
            st.rerun()

st.divider()

# --- Final Report Button ---
if st.button("📧 Send Final Report and Archive Data", type="primary", use_container_width=True):
    if not current_shared_times:
        st.warning("⚠️ No data available!")
    else:
        ok = archive_services(flight, reg)
        if ok:
            clear_services()
            st.success("✅ Report archived successfully.")
            st.balloons()
            st.rerun()

# --- Archive Viewer ---
st.divider()
st.subheader("📂 Archived Reports")

archive = load_archive()

if archive:

    # Group by flight/reg/date
    grouped = {}
    for row in archive:
        key = (row[0], row[1], row[2])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(row)

    for (flight, reg, date), records in grouped.items():

        st.write(f"✈️ Flight {flight} | Reg {reg} | Date {date}")

        # PDF button
        pdf_buffer = generate_pdf(flight, reg, date, records)

        st.download_button(
            label="📄 Download PDF",
            data=pdf_buffer,
            file_name=f"{flight}_{reg}_{date}.pdf",
            mime="application/pdf"
        )

        # Show records
        for r in records:
            st.write(f"- {r[3]} at {r[4]} by {r[5]}")

        st.markdown("---")

else:
    st.info("No archived reports yet.")
