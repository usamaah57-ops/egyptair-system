import streamlit as st
import sqlite3
from datetime import datetime
import pytz
from fpdf import FPDF
from io import BytesIO

# --- الإعدادات الثابتة ---
DB_FILE = "flight_data.db"
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# --- وظائف قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS services (key TEXT PRIMARY KEY, time TEXT, staff TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS archive (flight TEXT, reg TEXT, date TEXT, key TEXT, time TEXT, staff TEXT)")
    conn.commit()
    conn.close()

def save_service(key, time, staff):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO services (key, time, staff) VALUES (?, ?, ?)", (key, time, staff))
    conn.commit()
    conn.close()

def delete_service(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM services WHERE key=?", (key,))
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

def archive_services(flight, reg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date = datetime.now(BAGHDAD_TZ).strftime("%d/%m/%Y")
    services = load_services()
    if not services: return False
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

# --- وظيفة إنشاء الـ PDF ---
def generate_pdf(flight, reg, date, records):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Baghdad Station Operations Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(5)
    pdf.cell(0, 8, f"Flight: {flight} | Reg: {reg} | Date: {date}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 8, "Service", border=1)
    pdf.cell(40, 8, "Time", border=1)
    pdf.cell(80, 8, "Staff", border=1, ln=True)
    pdf.set_font("Arial", "", 11)
    for r in records:
        # r[3] هو اسم الخدمة، r[4] الوقت، r[5] الموظف
        pdf.cell(60, 8, str(r[3]), border=1)
        pdf.cell(40, 8, str(r[4]), border=1)
        pdf.cell(80, 8, str(r[5]), border=1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- واجهة Streamlit ---
init_db()
st.set_page_config(page_title="عمليات محطة بغداد", page_icon="✈️", layout="wide")

if 'staff_confirmed' not in st.session_state:
    st.session_state.staff_confirmed = False

if not st.session_state.staff_confirmed:
    st.title("🔐 تسجيل الدخول")
    name_input = st.text_input("الرجاء إدخال اسم الموظف المسؤول:")
    if st.button("دخول"):
        if name_input.strip():
            st.session_state.current_staff = name_input.strip()
            st.session_state.staff_confirmed = True
            st.rerun()
    st.stop()

# --- القائمة الجانبية ---
with st.sidebar:
    st.title("📊 التحكم")
    app_mode = st.radio("انتقل إلى:", ["تسجيل الرحلة الحالية", "سجل الرحلات المنفذة"])
    st.divider()
    manual_mode = st.toggle("تفعيل التعديل اليدوي ✍️")
    st.write(f"الموظف: {st.session_state.current_staff}")

# --- الصفحة الأولى: التسجيل ---
if app_mode == "تسجيل الرحلة الحالية":
    st.title("✈️ لوحة تسجيل العمليات")
    col1, col2 = st.columns(2)
    flight = col1.text_input("رقم الرحلة", value="MS616")
    reg = col2.text_input("التسجيل (Reg)", value="SU-")

    st.divider()

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

    current_data = load_services()
    cols = st.columns(2)

    for i, (label, key) in enumerate(services_labels):
        with cols[i % 2]:
            if key in current_data:
                rec = current_data[key]
                st.success(f"✅ {label}: {rec['time']}")
                if manual_mode:
                    new_t = st.text_input(f"تعديل {label}", value=rec['time'], key=f"ed_{key}")
                    c1, c2 = st.columns(2)
                    if c1.button("حفظ", key=f"sv_{key}"):
                        save_service(key, new_t, st.session_state.current_staff)
                        st.rerun()
                    if c2.button("حذف", key=f"dl_{key}"):
                        delete_service(key)
                        st.rerun()
            else:
                if manual_mode:
                    m_t = st.text_input(f"وقت {label}", placeholder="HH:MM", key=f"in_{key}")
                    if st.button(f"تسجيل {label}", key=f"btn_{key}"):
                        if m_t:
                            save_service(key, m_t, st.session_state.current_staff)
                            st.rerun()
                else:
                    if st.button(label, key=key, use_container_width=True):
                        now_t = datetime.now(BAGHDAD_TZ).strftime("%H:%M")
                        save_service(key, now_t, st.session_state.current_staff)
                        st.rerun()

    st.divider()
    if st.button("🏁 أرشفة وإنهاء الرحلة وإصدار التقرير", type="primary", use_container_width=True):
        if archive_services(flight, reg):
            clear_services
