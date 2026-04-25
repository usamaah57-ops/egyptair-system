import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import json
import glob
from streamlit_autorefresh import st_autorefresh # يتطلب تثبيت streamlit-autorefresh

# --- 1. إعدادات المنطقة والوقت ---
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# --- 2. إعدادات المجلدات والإيميل ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_DIR = "flights_data"
ARCHIVE_DIR = "pdf_archive"

for folder in [DATA_DIR, ARCHIVE_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️", layout="centered")

# --- ميزة التحديث التلقائي كل 10 ثوانٍ لمزامنة الفريق ---
# ملاحظة: إذا لم تكن المكتبة مثبتة، سيعمل الكود بشكل طبيعي بدون تحديث تلقائي
try:
    st_autorefresh(interval=10000, key="data_refresh")
except:
    pass

# --- 3. عرض الشعار ---
image_path = "egyptair_plane.jpg"
if os.path.exists(image_path):
    st.image(image_path, use_container_width=True)

# --- 4. وظائف إدارة البيانات ---
def save_flight_data(flight_id, data):
    path = os.path.join(DATA_DIR, f"{flight_id}.json")
    with open(path, "w") as f:
        json.dump(data, f)

def load_flight_data(flight_id):
    path = os.path.join(DATA_DIR, f"{flight_id}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: return None
    return None

def get_active_flights():
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    return [os.path.basename(f).replace(".json", "") for f in files]

# --- 5. تسجيل دخول الموظف ---
if 'current_staff' not in st.session_state:
    st.session_state.current_staff = ""

if not st.session_state.current_staff:
    st.subheader("👤 تسجيل دخول الموظف للمناوبة")
    name_input = st.text_input("أدخل اسمك الكامل:")
    if st.button("دخول"):
        if name_input:
            st.session_state.current_staff = name_input
            st.rerun()
    st.stop()

# --- 6. القائمة الجانبية (Sidebar) ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()
menu = st.sidebar.radio("القائمة:", ["الرحلات النشطة", "فتح رحلة جديدة"])

if menu == "فتح رحلة جديدة":
    f_no = st.text_input("رقم الرحلة:").upper().strip()
    f_reg = st.text_input("التسجيل:").upper().strip()
    if st.button("بدء الرحلة"):
        if f_no and f_reg:
            today = datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y')
            f_id = f"{f_no}_{f_reg}_{today}"
            if any(f_id in f for f in active_flights):
                st.warning("⚠️ هذه الرحلة مفتوحة بالفعل.")
            else:
                save_flight_data(f_id, {"flight_no": f_no, "reg": f_reg, "date": today, "times": {}})
                st.session_state.active_id = f_id
                st.rerun()
else:
    if active_flights:
        st.session_state.active_id = st.sidebar.selectbox("اختر رحلة:", sorted(active_flights, reverse=True))
        if st.sidebar.button("🗑️ حذف الرحلة"):
            os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
            st.rerun()

# --- 7. أرشيف الـ PDF مع ميزة الحذف ---
st.sidebar.divider()
st.sidebar.subheader("📂 الأرشيف")
archived_files = sorted(glob.glob(os.path.join(ARCHIVE_DIR, "*.pdf")), reverse=True)
for pdf_path in archived_files[:5]:
    file_name = os.path.basename(pdf_path)
    col_down, col_del = st.sidebar.columns([4, 1])
    with open(pdf_path, "rb") as f:
        col_down.download_button(label=f"📄 {file_name[:10]}", data=f, file_name=file_name, key=f"dl_{file_name}")
    if col_del.button("❌", key=f"del_{file_name}"):
        os.remove(pdf_path)
        st.rerun()

# --- 8. واجهة العمل (مزامنة فورية + قفل الأزرار) ---
if 'active_id' in st.session_state and st.session_state.active_id in get_active_flights():
    data = load_flight_data(st.session_state.active_id)
    if data:
        st.header(f"✈️ {data.get('flight_no')} | {data.get('reg')}")
        st.caption(f"📅 التاريخ: {data.get('date')} | 🔄 التحديث: تلقائي كل 10ث")
        
        services = [
            ("⏱ Chocks ON", "CHOCKS_ON"), ("⚡ GPU Arrival", "GPU_ARRIVAL"),
            ("🔌 APU Start", "APU_START"), ("💨 Air Starter", "AIR_STARTER"),
            ("📦 FWD Open", "FWD_OPEN"), ("🔒 FWD Close", "FWD_CLOSE"),
            ("📦 AFT Open", "AFT_OPEN"), ("🔒 AFT Close", "AFT_CLOSE"),
            ("🚛 Fuel Arrival", "FUEL_ARRIVAL"), ("⛽ Fuel End", "FUEL_END"),
            ("🧹 Cleaning START", "CLEANING_START"), ("✨ Cleaning END", "CLEANING_END"),
            ("🚶 First Pax", "FIRST_PAX"), ("🏁 Last Pax", "LAST_PAX"),
            ("📄 Loadsheet", "LOADSHEET"), ("🚪 Close Door", "CLOSE_DOOR"),
            ("🚜 Pushback Truck", "PUSHBACK_TRUCK"), ("🚀 Push Back", "PUSH_BACK")
        ]

        cols = st.columns(2)
        for i, (label, key) in enumerate(services):
            current_times = data.get('times', {})
            if key in current_times:
                rec = current_times[key]
                cols[i % 2].success(f"✅ {label}\n{rec['time']} - {rec['staff']}")
            else:
                if cols[i % 2].button(label, key=f"btn_{st.session_state.active_id}_{key}", use_container_width=True):
                    # إعادة قراءة الملف قبل الحفظ للتأكد من عدم قيام زميل آخر بالتسجيل في نفس الثانية
                    fresh_data = load_flight_data(st.session_state.active_id)
                    if fresh_data and key not in fresh_data.get('times', {}):
                        if 'times' not in fresh_data: fresh_data['times'] = {}
                        fresh_data['times'][key] = {
                            "time": datetime.now(BAGHDAD_TZ).strftime("%H:%M"),
                            "staff": st.session_state.current_staff
                        }
                        save_flight_data(st.session_state.active_id, fresh_data)
                        st.rerun()

        st.divider()
        
        # --- 9. التقارير ---
        def generate_pdf(f_data):
            pdf = FPDF()
            pdf.add_page()
            if os.path.exists(image_path): pdf.image(image_path, x=10, y=10, w=190); pdf.ln(80)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, f"Flight Report: {f_data['flight_no']} - {f_data['date']}", 0, 1, 'C')
            pdf.ln(10)
            for s_key, val in sorted(f_data.get('times', {}).items()):
                pdf.cell(80, 10, s_key.replace("_", " "), 1)
                pdf.cell(40, 10, val['time'], 1, 0, 'C')
                pdf.cell(70, 10, val['staff'], 1, 1, 'C')
            return pdf

        c1, c2 = st.columns(2)
        if c1.button("📧 إرسال الإيميل", use_container_width=True):
            try:
                pdf = generate_pdf(data)
                pdf_name = f"Report_{data['flight_no']}.pdf"
                pdf.output(pdf_name)
                msg = MIMEMultipart()
                msg['From'] = EMAIL_SENDER; msg['To'] = EMAIL_RECEIVER
                msg['Subject'] = f"Ops Report: {data['flight_no']} | {data['date']}"
                with open(pdf_name, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read()); encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={pdf_name}")
                    msg.attach(part)
                server = smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465)
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg); server.quit()
                os.remove(pdf_name)
                st.success("✅ تم الإرسال.")
            except Exception as e: st.error(f"❌ خطأ: {e}")

        if c2.button("📂 أرشفة وإنهاء", type="primary", use_container_width=True):
            pdf = generate_pdf(data)
            pdf.output(os.path.join(ARCHIVE_DIR, f"Report_{st.session_state.active_id}.pdf"))
            os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
            st.success("✅ تمت الأرشفة.")
            st.balloons()
            st.rerun()
