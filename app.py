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

# --- واجهة الصفحة ---
st.set_page_config(page_title="EgyptAir Baghdad", page_icon="✈️")

st.title("✈️ محطة بغداد - مصر للطيران")

if 'times' not in st.session_state:
    st.session_state.times = {}

col_flt, col_reg = st.columns(2)
with col_flt:
    flight = st.text_input("رقم الرحلة", value="MS616").upper()
with col_reg:
    reg = st.text_input("تسجيل الطائرة", value="SU-").upper()

services = [
    ("⏱ Chocks ON", "CHOCKS_ON"), ("⚡ GPU Arrival", "GPU_ARRIVAL"),
    ("🔌 APU Start", "APU_START"), ("💨 Air Starter", "AIR_STARTER"),
    ("📦 FWD Open", "FWD_OPEN"), ("🔒 FWD Close", "FWD_CLOSE"),
    ("🚛 Fuel Arrival", "FUEL_ARRIVAL"), ("⛽ Fuel End", "FUEL_END"),
    ("🚶 First Pax", "FIRST_PAX"), ("🏁 Last Pax", "LAST_PAX"),
    ("📄 Loadsheet", "LOADSHEET"), ("🚪 Close Door", "CLOSE_DOOR"),
    ("🚀 Push Back", "PUSH_BACK")
]

st.write("---")
cols = st.columns(2)
for i, (label, key) in enumerate(services):
    if key not in st.session_state.times:
        if cols[i % 2].button(label, use_container_width=True, key=key):
            st.session_state.times[key] = datetime.now().strftime("%H:%M")
            st.rerun()
    else:
        cols[i % 2].button(f"✅ {st.session_state.times[key]}", disabled=True, use_container_width=True, key=f"done_{key}")

if st.button("📧 إرسال التقرير النهائي", type="primary", use_container_width=True):
    if not st.session_state.times:
        st.error("سجل الأوقات أولاً")
    else:
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Report: {flight} / {reg}", 0, 1, 'C')
            for k, v in st.session_state.times.items():
                pdf.set_font("Arial", size=12)
                pdf.cell(95, 10, k, 1)
                pdf.cell(95, 10, v, 1, 1)
            
            pdf_file = "report.pdf"
            pdf.output(pdf_file)

            msg = MIMEMultipart()
            msg['Subject'] = f"Ops Report: {flight}"
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
            st.success("تم الإرسال!")
            st.session_state.times = {}
        except Exception as e:
            st.error(f"خطأ: {e}")
