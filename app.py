import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# --- الإعدادات الشخصية ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"

# --- إعدادات الصفحة ---
st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️", layout="centered")

# تنسيق CSS للأزرار لتناسب شاشات الموبايل
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 3.5em;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_mode=True)

st.title("✈️ منظومة محطة بغداد")
st.subheader("تسجيل أوقات العمليات الأرضية")

# إدارة حالة البيانات
if 'times' not in st.session_state:
    st.session_state.times = {}

# بيانات الرحلة
c1, c2 = st.columns(2)
with c1:
    flight = st.text_input("رقم الرحلة", value="MS616").upper()
with c2:
    reg = st.text_input("تسجيل الطائرة (Reg)", value="SU-").upper()

st.divider()

# القائمة الكاملة للخدمات
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

# عرض الأزرار مع منع تكرار المعرفات (حل مشكلة Duplicate ID)
cols = st.columns(2)
for i, (label, key) in enumerate(services):
    if key not in st.session_state.times:
        if cols[i % 2].button(label, key=f"btn_{key}"):
            st.session_state.times[key] = datetime.now().strftime("%H:%M")
            st.rerun()
    else:
        # زر معطل يظهر الوقت الذي تم تسجيله
        cols[i % 2].button(f"✅ {label} ({st.session_state.times[key]})", key=f"done_{key}", disabled=True)

st.divider()

# زر الإرسال النهائي
if st.button("📧 إنهاء وإرسال التقرير النهائي", type="primary", use_container_width=True, key="main_send"):
    if not st.session_state.times:
        st.error("⚠️ يرجى تسجيل وقت خدمة واحدة على الأقل قبل الإرسال.")
    else:
        try:
            # إنشاء الـ PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 15, "EgyptAir Baghdad Operations Report", 0, 1, 'C')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(63, 10, f"Flight: {flight}", 1, 0, 'C', True)
            pdf.cell(63, 10, f"Reg: {reg}", 1, 0, 'C', True)
            pdf.cell(64, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C', True)
            pdf.ln(10)
            
            for s_name, t_val in st.session_state.times.items():
                pdf.cell(95, 10, s_name.replace("_", " "), 1)
                pdf.cell(95, 10, t_val, 1, 1, 'C')
            
            pdf_file = f"Report_{flight.replace('/', '-')}.pdf"
            pdf.output(pdf_file)

            # إرسال الإيميل
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"Final Ops Report: {flight} | {reg}"
            
            with open(pdf_file, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={pdf_file}")
                msg.attach(part)

            server = smtplib.SMTP_SSL('smtp.mail.yahoo.com', 465)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

            st.success("✅ تم إرسال التقرير بنجاح للمحطة!")
            st.session_state.times = {} # تصفير البيانات لرحلة جديدة
            os.remove(pdf_file)
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ خطأ في الإرسال: {e}")
