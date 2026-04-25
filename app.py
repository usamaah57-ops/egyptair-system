import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import json

# --- الإعدادات ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_FILE = "active_flight_data.json"

st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️")

# وظائف التعامل مع الملف المشترك (هذا هو سر المزامنة)
def save_shared_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_shared_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

# تحديث بيانات الجلسة من الملف المشترك في كل "تحميل" للصفحة
st.session_state.times = load_shared_data()

if 'staff_confirmed' not in st.session_state:
    st.session_state.staff_confirmed = False
if 'current_staff' not in st.session_state:
    st.session_state.current_staff = ""

# --- التصميم العلوي ---
if os.path.exists("egyptair_plane.jpg"):
    st.image("egyptair_plane.jpg", use_container_width=True)

st.title("✈️ عمليات محطة بغداد")

# --- خطوة تسجيل الاسم ---
if not st.session_state.staff_confirmed:
    st.subheader("👤 تسجيل دخول الموظف")
    name_input = st.text_input("يرجى إدخال اسمك بالكامل للمناوبة:")
    if st.button("تأكيد ودخول للنظام"):
        if name_input.strip():
            st.session_state.current_staff = name_input.strip()
            st.session_state.staff_confirmed = True
            st.rerun()
        else:
            st.error("⚠️ يجب إدخال الاسم للمتابعة")
    st.stop()

# --- واجهة العمليات بعد الدخول ---
st.write(f"👷 الموظف الحالي: **{st.session_state.current_staff}**")

c1, c2 = st.columns(2)
with c1:
    flight = st.text_input("رقم الرحلة", value="MS616").upper()
with c2:
    reg = st.text_input("التسجيل (Reg)", value="SU-").upper()

st.divider()

# الأزرار والخدمات
services_labels = [
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

# إعادة تحميل البيانات قبل رسم الأزرار لضمان المزامنة
current_shared_times = load_shared_data()

cols = st.columns(2)
for i, (label, key) in enumerate(services_labels):
    # إذا كانت الخدمة مسجلة في الملف المشترك (من قبل أي زميل)
    if key in current_shared_times:
        recorded = current_shared_times[key]
        # يختفي الزر ويظهر مكانه نص المعلومات
        cols[i % 2].success(f"{label}\n{recorded['time']} ({recorded['staff']})")
    else:
        # إذا لم تكن مسجلة، يظهر الزر للجميع
        if cols[i % 2].button(label, key=key, use_container_width=True):
            now_t = datetime.now().strftime("%H:%M")
            # تحديث الملف المشترك فوراً
            current_shared_times[key] = {"time": now_t, "staff": st.session_state.current_staff}
            save_shared_data(current_shared_times)
            st.rerun()

st.divider()

# زر الإرسال النهائي
if st.button("📧 إرسال التقرير النهائي وتنظيف البيانات", type="primary", use_container_width=True):
    if not current_shared_times:
        st.warning("⚠️ لا توجد بيانات!")
    else:
        try:
            # توليد PDF (نفس الكود السابق)
            pdf = FPDF()
            pdf.add_page()
            if os.path.exists("egyptair_plane.jpg"):
                pdf.image("egyptair_plane.jpg", x=10, y=10, w=190)
                pdf.ln(80)
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Station Operations Report", 0, 1, 'C')
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(63, 10, f"Flight: {flight}", 1, 0, 'C')
            pdf.cell(63, 10, f"Reg: {reg}", 1, 0, 'C')
            pdf.cell(64, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C')
            pdf.ln(5)
            
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(80, 10, "Service", 1, 0, 'C', True)
            pdf.cell(40, 10, "Time (LT)", 1, 0, 'C', True)
            pdf.cell(70, 10, "Staff", 1, 1, 'C', True)
            
            pdf.set_font("Arial", size=10)
            for s_key in sorted(current_shared_times.keys()):
                val = current_shared_times[s_key]
                pdf.cell(80, 10, s_key.replace("_", " "), 1)
                pdf.cell(40, 10, val['time'], 1, 0, 'C')
                pdf.cell(70, 10, val['staff'], 1, 1, 'C')

            pdf_file = f"Report_{flight.replace('/', '-')}.pdf"
            pdf.output(pdf_file)

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

            # مسح البيانات المشتركة بعد الإرسال بنجاح
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            st.success("✅ تم إرسال التقرير وتصفير المنظومة للرحلة القادمة.")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"❌ خطأ: {e}")
