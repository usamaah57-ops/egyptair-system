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

# --- 1. إعدادات المنطقة والوقت ---
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# --- 2. إعدادات المحطة ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_DIR = "flights_data"
ARCHIVE_DIR = "pdf_archive" # مجلد للأرشفة الدائمة

# إنشاء المجلدات إذا لم تكن موجودة
for folder in [DATA_DIR, ARCHIVE_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️")

# التحديث التلقائي كل 30 ثانية لمزامنة الأجهزة
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# --- 3. وظائف الحماية والبيانات ---
def save_flight_data(flight_id, data):
    path = os.path.join(DATA_DIR, f"{flight_id}.json")
    with open(path, "w") as f:
        json.dump(data, f)

def load_flight_data(flight_id):
    path = os.path.join(DATA_DIR, f"{flight_id}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f: 
                return json.load(f)
        except:
            return None # في حال كان الملف تالفاً
    return None

def get_active_flights():
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    return [os.path.basename(f).replace(".json", "") for f in files]

# --- 4. تسجيل الدخول ---
if 'current_staff' not in st.session_state:
    st.session_state.current_staff = ""

if not st.session_state.current_staff:
    st.image("egyptair_plane.jpg", use_container_width=True) if os.path.exists("egyptair_plane.jpg") else None
    name_input = st.text_input("👤 أدخل اسمك لبدء النوبة:")
    if st.button("دخول"):
        if name_input:
            st.session_state.current_staff = name_input
            st.rerun()
    st.stop()

# --- 5. إدارة الرحلات ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()

option = st.sidebar.radio("الخيارات:", ["الرحلات النشطة", "فتح رحلة جديدة"])

if option == "فتح رحلة جديدة":
    new_f = st.text_input("رقم الرحلة:").upper().strip()
    new_r = st.text_input("التسجيل:").upper().strip()
    if st.button("بدء"):
        if new_f and new_r:
            today = datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y')
            f_id = f"{new_f}_{new_r}_{today}"
            save_flight_data(f_id, {"flight_no": new_f, "reg": new_r, "date": today, "times": {}})
            st.session_state.active_id = f_id
            st.rerun()
else:
    if active_flights:
        st.session_state.active_id = st.sidebar.selectbox("اختر رحلة:", active_flights)
        if st.sidebar.button("🗑️ حذف يدوي"):
            os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
            st.rerun()
    else:
        st.info("لا توجد رحلات نشطة.")
        st.stop()

# --- 6. واجهة العمل ---
if 'active_id' in st.session_state:
    data = load_flight_data(st.session_state.active_id)
    if data:
        st.header(f"✈️ {data['flight_no']} | {data['reg']}")
        
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
                    save_flight_data(st.session_state.active_id, data)
                    st.rerun()

        st.divider()
        if st.button("📧 إرسال التقرير النهائي وأرشفته", type="primary", use_container_width=True):
            try:
                pdf = FPDF()
                pdf.add_page()
                # إضافة الصورة للـ PDF
                if os.path.exists("egyptair_plane.jpg"):
                    pdf.image("egyptair_plane.jpg", x=10, y=10, w=190)
                    pdf.ln(80)
                
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, f"Report: {data['flight_no']} - {data['reg']}", 0, 1, 'C')
                pdf.ln(5)
                
                for s_key in sorted(data['times'].keys()):
                    val = data['times'][s_key]
                    pdf.cell(80, 10, s_key, 1)
                    pdf.cell(40, 10, val['time'], 1, 0, 'C')
                    pdf.cell(70, 10, val['staff'], 1, 1, 'C')

                pdf_name = f"Report_{st.session_state.active_id}.pdf"
                pdf.output(pdf_name)
                
                # إرسال الإيميل
                msg = MIMEMultipart()
                msg['From'] = EMAIL_SENDER
                msg['To'] = EMAIL_RECEIVER
                msg['Subject'] = f"Ops Report: {data['flight_no']} | {data['reg']}"
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

                # أرشفة نسخة وحذف الأصل
                os.rename(pdf_name, os.path.join(ARCHIVE_DIR, pdf_name))
                os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
                st.success("تم الإرسال والأرشفة بنجاح!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"خطأ في الإرسال: {e}. تم حفظ البيانات، حاول مجدداً.")
