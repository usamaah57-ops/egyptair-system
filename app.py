import streamlit as st
import sqlite3
from datetime import datetime
import pytz
from fpdf import FPDF
from io import BytesIO

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

# --- إعداد الصفحة ---
init_db()
st.set_page_config(page_title="عمليات محطة بغداد", layout="wide")

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

# --- القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    app_mode = st.radio("التنقل:", ["تسجيل الرحلة", "الرحلات المنفذة"])
    st.divider()
    manual_mode = st.toggle("تفعيل التعديل اليدوي ✍️")
    st.info(f"الموظف: {st.session_state.current_staff}")

# --- واجهة تسجيل الرحلة ---
if app_mode == "تسجيل الرحلة":
    st.title("✈️ تسجيل بيانات الرحلة")
    
    col_f, col_r = st.columns(2)
    flight = col_f.text_input("رقم الرحلة", value="MS616")
    reg = col_r.text_input("التسجيل", value="SU-")

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
                # في حال كانت الخدمة مسجلة
                recorded = current_data[key]
                st.success(f"✅ {label}: {recorded['time']}")
                
                # إذا كان وضع التعديل مفعلاً، تظهر أزرار الحذف أو التعديل
                if manual_mode:
                    new_time = st.text_input(f"تعديل وقت {label}", value=recorded['time'], key=f"edit_{key}")
                    col_edit, col_del = st.columns(2)
                    if col_edit.button("حفظ التعديل", key=f"save_{key}"):
                        save_service(key, new_time, st.session_state.current_staff)
                        st.rerun()
                    if col_del.button("حذف", key=f"del_{key}"):
                        delete_service(key)
                        st.rerun()
            else:
                # في حال لم تكن مسجلة
                if manual_mode:
                    # إدخال يدوي بالكامل
                    manual_t = st.text_input(f"إدخال وقت {label} (HH:MM)", key=f"man_{key}")
                    if st.button(f"تسجيل {label} يدوياً", key=f"btn_man_{key}"):
                        if manual_t:
                            save_service(key, manual_t, st.session_state.current_staff)
                            st.rerun()
                else:
                    # تسجيل تلقائي بضغطة زر
                    if st.button(label, key=key, use_container_width=True):
                        now_t = datetime.now(BAGHDAD_TZ).strftime("%H:%M")
                        save_service(key, now_t, st.session_state.current_staff)
                        st.rerun()

    st.divider()
    if st.button("✅ أرشفة وإنهاء الرحلة", type="primary", use_container_width=True):
        if archive_services(flight, reg):
            clear_services()
            st.success("تمت الأرشفة بنجاح")
            st.rerun()

# --- واجهة الرحلات المنفذة (نفس الكود السابق مع عرض منظم) ---
elif app_mode == "الرحلات المنفذة":
    st.title("📂 سجل الرحلات")
    archive = load_archive()
    # ... (يمكنك وضع نفس كود العرض السابق هنا)
    for row in archive:
        st.write(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}: {row[4]}")
