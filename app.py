import streamlit as st
import sqlite3
from datetime import datetime
import pytz  # مكتبة التعامل مع المناطق الزمنية
from fpdf import FPDF
from io import BytesIO

DB_FILE = "flight_data.db"
# تحديد المنطقة الزمنية لبغداد
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# --- وظائف قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS services (
            key TEXT PRIMARY KEY,
            time TEXT,
            staff TEXT
        )
    """)
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

def archive_services(flight, reg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # الحصول على تاريخ بغداد الحالي
    date = datetime.now(BAGHDAD_TZ).strftime("%d/%m/%Y")

    c.execute("SELECT COUNT(*) FROM archive WHERE flight=? AND reg=? AND date=?", (flight, reg, date))
    exists = c.fetchone()[0]

    if exists > 0:
        st.warning(f"⚠️ الرحلة {flight} مسجلة مسبقاً لهذا اليوم.")
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

# --- محرك PDF ---
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
        pdf.cell(60, 8, r[3], border=1)
        pdf.cell(40, 8, r[4], border=1)
        pdf.cell(80, 8, r[5], border=1, ln=True)
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return BytesIO(pdf_bytes)

# --- إعداد الصفحة ---
init_db()
st.set_page_config(page_title="عمليات محطة بغداد", page_icon="✈️")

# --- تسجيل دخول الموظف ---
if 'staff_confirmed' not in st.session_state:
    st.session_state.staff_confirmed = False

if not st.session_state.staff_confirmed:
    name_input = st.text_input("الرجاء إدخال اسم الموظف:")
    if st.button("دخول"):
        if name_input.strip():
            st.session_state.current_staff = name_input.strip()
            st.session_state.staff_confirmed = True
            st.rerun()
    st.stop()

# --- القائمة الجانبية (Sidebar) ---
with st.sidebar:
    st.title("القائمة الرئيسية")
    app_mode = st.radio("اختر الصفحة:", ["تسجيل الرحلة الحالية", "سجل الرحلات المنفذة"])
    st.divider()
    st.write(f"الموظف: {st.session_state.current_staff}")
    if st.button("تسجيل خروج"):
        st.session_state.staff_confirmed = False
        st.rerun()

# --- الصفحة الأولى: تسجيل البيانات ---
if app_mode == "تسجيل الرحلة الحالية":
    st.title("✈️ تسجيل بيانات الرحلة")
    
    col_f, col_r = st.columns(2)
    flight = col_f.text_input("رقم الرحلة", value="MS616").upper()
    reg = col_r.text_input("التسجيل (Reg)", value="SU-").upper()

    if st.button("➕ رحلة جديدة (مسح الحقول)"):
        clear_services()
        st.rerun()

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

    current_shared_times = load_services()
    cols = st.columns(2)

    for i, (label, key) in enumerate(services_labels):
        if key in current_shared_times:
            recorded = current_shared_times[key]
            cols[i % 2].success(f"{label}\n{recorded['time']} ({recorded['staff']})")
        else:
            if cols[i % 2].button(label, key=key, use_container_width=True):
                # تسجيل الوقت بتوقيت بغداد
                now_t = datetime.now(BAGHDAD_TZ).strftime("%H:%M")
                save_service(key, now_t, st.session_state.current_staff)
                st.rerun()

    st.divider()
    if st.button("✅ إرسال التقرير النهائي وأرشفة البيانات", type="primary", use_container_width=True):
        if not current_shared_times:
            st.warning("⚠️ لا توجد بيانات مسجلة!")
        else:
            if archive_services(flight, reg):
                clear_services()
                st.success("✅ تم حفظ الرحلة في السجل.")
                st.balloons()
                st.rerun()

# --- الصفحة الثانية: سجل الرحلات المنفذة ---
elif app_mode == "سجل الرحلات المنفذة":
    st.title("📂 سجل الرحلات المنفذة (Archives)")
    
    archive = load_archive()
    if not archive:
        st.info("لا توجد رحلات مؤرشفة بعد.")
    else:
        # تجميع البيانات حسب الرحلة والتاريخ
        grouped = {}
        for row in archive:
            group_key = (row[0], row[1], row[2]) # flight, reg, date
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(row)

        for (f_num, r_num, f_date), records in grouped.items():
            with st.expander(f"✈️ رحلة {f_num} | التسجيل {r_num} | بتاريخ {f_date}"):
                # توليد PDF
                pdf_buf = generate_pdf(f_num, r_num, f_date, records)
                st.download_button(
                    label="📥 تحميل تقرير PDF",
                    data=pdf_buf,
                    file_name=f"Report_{f_num}_{f_date}.pdf",
                    mime="application/pdf",
                    key=f"dl_{f_num}_{f_date}"
                )
                
                # عرض التفاصيل في جدول
                for r in records:
                    st.write(f"• **{r[3]}**: {r[4]} (بواسطة: {r[5]})")
