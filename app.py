import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# --- إعدادات الإيميل (بياناتك) ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"

# --- إعدادات الواجهة ---
st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️")

st.title("✈️ منظومة عمليات محطة بغداد")
st.info("نظام تسجيل أوقات الخدمات الأرضية - مصر للطيران")

# --- إدارة البيانات (Session State) ---
if 'times' not in st.session_state:
    st.session_state.times = {}

# إدخال بيانات الرحلة
c1, c2 = st.columns(2)
with c1:
    flight = st.text_input("رقم الرحلة", value="MS616").upper()
with c2:
    reg = st.text_input("تسجيل الطائرة (Reg)", value="SU-").upper()

st.divider()

# الأزرار (مرتبة لتناسب شاشة الموبايل)
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
    if key not in st.session_state.times:
        if cols[i % 2].button(label, use_container_width=True):
            st.session_state.times[key] = datetime.now().strftime("%H:%M")
            st.rerun()
    else:
        cols[i % 2].button(f"✅ {st.session_state.times[key]}", disabled=True, use_container_width=True)

st.divider()

# عرض ملخص سريع
if st.session_state.times:
    st.write("📋 الأوقات المسجلة حالياً:")
    df = pd.DataFrame(st.session_state.times.items(), columns=["الخدمة", "الوقت"])
    st.table(df)

# زر الإرسال النهائي
if st.button("📧 إنهاء الرحلة وإرسال التقرير", type="primary", use_container_width=True):
    if not st.session_state.times:
        st.warning("⚠️ سجل بعض الأوقات أولاً!")
    else:
        try:
            # توليد PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Station Operations Report", 0, 1, 'C')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(63, 10, f"Flight: {flight}", 1, 0, 'C')
            pdf.cell(63, 10, f"Reg: {reg}", 1, 0, 'C')
            pdf.cell(64, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C')
            pdf.ln(10)
            
            for s, t in st.session_state.times.items():
                pdf.cell(95, 10, s.replace("_", " "), 1)
                pdf.cell(95, 10, t, 1, 1, 'C')
            
            pdf_file = f"Report_{flight.replace('/', '-')}.pdf"
            pdf.output(pdf_file)

            # إرسال إيميل
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"Ops Report: {flight} | {reg}"
            
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

            st.success("✅ تم الإرسال بنجاح! تم تصفير البيانات لرحلة جديدة.")
            st.session_state.times = {}
            os.remove(pdf_file)
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ حدث خطأ: {e}")
