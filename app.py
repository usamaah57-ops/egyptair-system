import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# --- إعدادات الإيميل الخاصة بك ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"

# --- إعدادات واجهة الصفحة ---
st.set_page_config(page_title="EgyptAir Baghdad Ops", page_icon="✈️", layout="centered")

# ستايل الأزرار لتبدو احترافية على الموبايل
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 3.5em;
        font-size: 18px;
        font-weight: bold;
        border-radius: 12px;
        border: 2px solid #0054a6;
        margin-bottom: 5px;
    }
    </style>
""", unsafe_allow_mode=True)

st.title("✈️ مصر للطيران - محطة بغداد")
st.subheader("منظومة تسجيل العمليات الأرضية")

# --- إدارة البيانات (Session State) ---
if 'times' not in st.session_state:
    st.session_state.times = {}

# إدخال بيانات الرحلة
col_flt, col_reg = st.columns(2)
with col_flt:
    flight = st.text_input("رقم الرحلة", value="MS616").upper()
with col_reg:
    reg = st.text_input("تسجيل الطائرة (Reg)", value="SU-").upper()

st.divider()

# قائمة الخدمات الأرضية المعتمدة
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

# عرض الأزرار في شبكة (Grid)
cols = st.columns(2)
for i, (label, key) in enumerate(services):
    if key not in st.session_state.times:
        # إضافة key=key هنا هو الحل لمشكلة الخطأ الأحمر
        if cols[i % 2].button(label, use_container_width=True, key=key):
            st.session_state.times[key] = datetime.now().strftime("%H:%M")
            st.rerun()
    else:
        # زر معطل يظهر الوقت المسجل لمنع التكرار
        cols[i % 2].button(f"✅ {label} ({st.session_state.times[key]})", 
                           disabled=True, use_container_width=True, key=f"done_{key}")

st.divider()

# زر الإرسال والإنهاء
if st.button("📧 إرسال التقرير النهائي وتصفير البيانات", type="primary", use_container_width=True, key="send_btn"):
    if not st.session_state.times:
        st.warning("⚠️ يرجى تسجيل وقت خدمة واحدة على الأقل قبل الإرسال.")
    else:
        with st.spinner("جاري توليد التقرير وإرساله للمحطة..."):
            try:
                # 1. إنشاء ملف PDF منظم
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 15, "EgyptAir - Baghdad Station Report", 0, 1, 'C')
                pdf.ln(5)
                
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(63, 12, f"Flight: {flight}", 1, 0, 'C', True)
                pdf.cell(63, 12, f"Reg: {reg}", 1, 0, 'C', True)
                pdf.cell(64, 12, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C', True)
                pdf.ln(10)
                
                pdf.set_fill_color(200, 220, 255)
                pdf.cell(95, 10, "Service Name", 1, 0, 'C', True)
                pdf.cell(95, 10, "Time (Local)", 1, 1, 'C', True)
                
                pdf.set_font("Arial", size=11)
                for s_key, t_val in st.session_state.times.items():
                    pdf.cell(95, 10, s_key.replace("_", " "), 1)
                    pdf.cell(95, 10, t_val, 1, 1, 'C')
                
                safe_name = flight.replace("/", "-")
                pdf_file = f"Report_{safe_name}.pdf"
                pdf.output(pdf_file)

                # 2. إرسال الإيميل عبر سيرفر ياهو
                msg = MIMEMultipart()
                msg['From'] = EMAIL_SENDER
                msg['To'] = EMAIL_RECEIVER
                msg['Subject'] = f"Ops Report: {flight} | {reg} | {datetime.now().strftime('%d/%m/%Y')}"
                
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

                st.success(f"✅ تم إرسال تقرير الرحلة {flight} بنجاح إلى {EMAIL_RECEIVER}")
                st.session_state.times = {} # مسح البيانات لبدء رحلة جديدة
                os.remove(pdf_file) # حذف الملف المؤقت
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ فشل الإرسال: {e}")
