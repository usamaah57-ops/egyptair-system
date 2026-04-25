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

# --- إعدادات الوقت المحلي ---
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# --- الإعدادات العامة ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_DIR = "flights_data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️")

# --- عرض الصورة ---
if os.path.exists("egyptair_plane.jpg"):
    st.image("egyptair_plane.jpg", use_container_width=True)

# وظائف البيانات
def save_flight_data(flight_id, data):
    with open(os.path.join(DATA_DIR, f"{flight_id}.json"), "w") as f:
        json.dump(data, f)

def load_flight_data(flight_id):
    path = os.path.join(DATA_DIR, f"{flight_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {}

def get_active_flights():
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    return [os.path.basename(f).replace(".json", "") for f in files]

# --- تسجيل دخول الموظف ---
if 'current_staff' not in st.session_state or not st.session_state.current_staff:
    st.subheader("👤 تسجيل دخول الموظف")
    name_input = st.text_input("الاسم بالكامل للمناوبة:")
    if st.button("دخول"):
        if name_input:
            st.session_state.current_staff = name_input
            st.rerun()
    st.stop()

# --- إدارة الرحلات ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()

option = st.sidebar.radio("القائمة الرئيسية:", ["الرحلات النشطة", "فتح رحلة جديدة"])

if option == "فتح رحلة جديدة":
    st.subheader("🆕 تسجيل رحلة جديدة اليوم")
    new_f = st.text_input("رقم الرحلة (Flight No):").upper().strip()
    new_r = st.text_input("تسجيل الطائرة (Reg):").upper().strip()
    
    if st.button("بدء تسجيل الرحلة"):
        if new_f and new_r:
            # إنشاء معرف فريد يعتمد على رقم الرحلة والتاريخ فقط (بدون الثواني لمنع التكرار)
            today_str = datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y')
            f_id = f"{new_f}_{today_str}"
            
            # التحقق إذا كان الملف موجود مسبقاً
            if f_id in active_flights:
                st.error(f"⚠️ الرحلة {new_f} مسجلة بالفعل لتاريخ اليوم {today_str}. يرجى اختيارها من قائمة الرحلات النشطة.")
            else:
                save_flight_data(f_id, {
                    "flight_no": new_f, 
                    "reg": new_r, 
                    "date": today_str,
                    "times": {}
                })
                st.session_state.active_id = f_id
                st.success(f"تم فتح الرحلة {new_f} بنجاح.")
                st.rerun()
        else:
            st.warning("يرجى إدخال رقم الرحلة والتسجيل.")

else: # قسم الرحلات النشطة
    if active_flights:
        selected = st.sidebar.selectbox("اختر الرحلة للمتابعة:", active_flights)
        st.session_state.active_id = selected
    else:
        st.info("لا توجد رحلات نشطة حالياً. قم بفتح رحلة جديدة.")
        st.stop()

# --- واجهة العمل على الرحلة ---
if 'active_id' in st.session_state:
    data = load_flight_data(st.session_state.active_id)
    if data:
        st.header(f"✈️ {data['flight_no']} | {data['reg']}")
        st.info(f"📅 تاريخ الرحلة: {data['date']}")
        
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
                    now_baghdad = datetime.now(BAGHDAD_TZ).strftime("%H:%M")
                    data['times'][key] = {"time": now_baghdad, "staff": st.session_state.current_staff}
                    save_flight_data(st.session_state.active_id, data)
                    st.rerun()

        st.divider()
        
        if st.button("📧 إرسال التقرير النهائي للمحطة", type="primary", use_container_width=True):
            try:
                pdf = FPDF()
                pdf.add_page()
                if os.path.exists("egyptair_plane.jpg"):
                    pdf.image("egyptair_plane.jpg", x=10, y=10, w=190)
                    pdf.ln(80)
                
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, "Station Operations Report", 0, 1, 'C')
                pdf.ln(5)
                
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(63, 10, f"Flight: {data['flight_no']}", 1, 0, 'C')
                pdf.cell(63, 10, f"Reg: {data['reg']}", 1, 0, 'C')
                pdf.cell(64, 10, f"Date: {data['date']}", 1, 1, 'C')
                pdf.ln(10)
                
                pdf.set_fill_color(200, 220, 255)
                pdf.cell(80, 10, "Service", 1, 0, 'C', True)
                pdf.cell(40, 10, "Time (LT)", 1, 0, 'C', True)
                pdf.cell(70, 10, "Staff", 1, 1, 'C', True)
                
                pdf.set_font("Arial", size=10)
                for s_key in sorted(data['times'].keys()):
                    val = data['times'][s_key]
                    pdf.cell(80, 10, s_key.replace("_", " "), 1)
                    pdf.cell(40, 10, val['time'], 1, 0, 'C')
                    pdf.cell(70, 10, val['staff'], 1, 1, 'C')

                pdf_name = f"Report_{st.session_state.active_id}.pdf"
                pdf.output(pdf_name)
                
                # الإرسال
                msg = MIMEMultipart()
                msg['From'] = EMAIL_SENDER
                msg['To'] = EMAIL_RECEIVER
                msg['Subject'] = f"Ops Report: {data['flight_no']} | {data['reg']} | {data['date']}"
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

                # حذف ملف البيانات بعد الإرسال
                os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
                st.success("✅ تم إرسال التقرير بنجاح.")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ حدث خطأ: {e}")
