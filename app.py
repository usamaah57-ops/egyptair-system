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

# --- إعدادات الوقت والمنطقة ---
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_DIR = "flights_data"
ARCHIVE_DIR = "pdf_archive"

for folder in [DATA_DIR, ARCHIVE_DIR]:
    if not os.path.exists(folder): os.makedirs(folder)

st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️")

# --- عرض الشعار ---
if os.path.exists("egyptair_plane.jpg"):
    st.image("egyptair_plane.jpg", use_container_width=True)

# --- وظائف إدارة البيانات (منع التكرار) ---
def save_flight_data(flight_id, data):
    with open(os.path.join(DATA_DIR, f"{flight_id}.json"), "w") as f:
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

# --- تسجيل دخول الموظف ---
if 'current_staff' not in st.session_state: st.session_state.current_staff = ""

if not st.session_state.current_staff:
    name_input = st.text_input("👤 اسم موظف النوبة:")
    if st.button("دخول"):
        if name_input:
            st.session_state.current_staff = name_input
            st.rerun()
    st.stop()

# --- منع تكرار الرحلة ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()
menu = st.sidebar.radio("القائمة:", ["الرحلات النشطة", "فتح رحلة جديدة"])

if menu == "فتح رحلة جديدة":
    f_no = st.text_input("رقم الرحلة:").upper().strip()
    f_reg = st.text_input("التسجيل:").upper().strip()
    if st.button("بدء الرحلة"):
        if f_no and f_reg:
            today = datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y')
            # المعرف يعتمد على (الرحلة + التسجيل + التاريخ) لضمان عدم التكرار
            f_id = f"{f_no}_{f_reg}_{today}"
            
            if f_id in active_flights:
                st.warning(f"⚠️ الرحلة {f_no} مفتوحة بالفعل لهذا اليوم. يمكنك العثور عليها في 'الرحلات النشطة'.")
            else:
                save_flight_data(f_id, {"flight_no": f_no, "reg": f_reg, "date": today, "times": {}})
                st.session_state.active_id = f_id
                st.success("تم فتح الرحلة بنجاح")
                st.rerun()
else:
    if active_flights:
        st.session_state.active_id = st.sidebar.selectbox("اختر رحلة:", active_flights)
        if st.sidebar.button("🗑️ حذف الرحلة"):
            os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
            st.rerun()
    else:
        st.info("لا توجد رحلات نشطة.")
        st.stop()

# --- واجهة تسجيل الأوقات (Auto-Save) ---
if 'active_id' in st.session_state:
    data = load_flight_data(st.session_state.active_id)
    if data:
        st.header(f"✈️ {data['flight_no']} | {data['reg']}")
        st.info(f"📅 التاريخ: {data['date']}")
        
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
            if key in data['times']:
                rec = data['times'][key]
                cols[i % 2].success(f"{label}\n{rec['time']} ({rec['staff']})")
            else:
                if cols[i % 2].button(label, key=f"{st.session_state.active_id}_{key}", use_container_width=True):
                    data['times'][key] = {"time": datetime.now(BAGHDAD_TZ).strftime("%H:%M"), "staff": st.session_state.current_staff}
                    save_flight_data(st.session_state.active_id, data) # حفر لحظي
                    st.rerun()

        st.divider()
        if st.button("📧 إرسال التقرير النهائي والأرشفة", type="primary", use_container_width=True):
            try:
                pdf = FPDF()
                pdf.add_page()
                if os.path.exists("egyptair_plane.jpg"):
                    pdf.image("egyptair_plane.jpg", x=10, y=10, w=190)
                    pdf.ln(80)
                
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, f"Flight Report: {data['flight_no']} / {data['date']}", 0, 1, 'C')
                pdf.ln(10)
                
                for s_key in sorted(data['times'].keys()):
                    val = data['times'][s_key]
                    pdf.cell(80, 10, s_key.replace("_", " "), 1)
                    pdf.cell(40, 10, val['time'], 1, 0, 'C')
                    pdf.cell(70, 10, val['staff'], 1, 1, 'C')

                pdf_name = f"Report_{st.session_state.active_id}.pdf"
                pdf.output(pdf_name)
                
                # إرسال الإيميل
                msg = MIMEMultipart()
                msg['From'] = EMAIL_SENDER
                msg['To'] = EMAIL_RECEIVER
                msg['Subject'] = f"Ops Report: {data['flight_no']} | {data['date']}"
                with open(pdf_name, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={pdf_name}")
                    msg.attach(part)
                
                server = smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465)
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()

                # أرشفة وحذف
                os.rename(pdf_name, os.path.join(ARCHIVE_DIR, pdf_name))
                os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
                st.success("تم الإرسال والأرشفة بنجاح!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")
