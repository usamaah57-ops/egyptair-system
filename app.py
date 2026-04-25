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
ARCHIVE_DIR = "pdf_archive"

for folder in [DATA_DIR, ARCHIVE_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️", layout="centered")

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
    st.subheader("👤 تسجيل دخول الموظف")
    name_input = st.text_input("أدخل اسمك الكامل:")
    if st.button("دخول للنظام"):
        if name_input:
            st.session_state.current_staff = name_input
            st.rerun()
    st.stop()

# --- 6. إدارة الرحلات (المنطق المطور لمنع التكرار) ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()

menu = st.sidebar.radio("القائمة:", ["الرحلات النشطة", "فتح رحلة جديدة"])

if menu == "فتح رحلة جديدة":
    st.subheader("🆕 تسجيل رحلة جديدة")
    f_no = st.text_input("رقم الرحلة (مثلاً MS628):").upper().strip()
    f_reg = st.text_input("تسجيل الطائرة (مثلاً SUGCR):").upper().strip()
    
    if st.button("بدء الرحلة"):
        if f_no and f_reg:
            today = datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y')
            f_id = f"{f_no}_{f_reg}_{today}"
            
            # فحص إذا كانت الرحلة موجودة بالفعل لمنع تكرارها
            if any(f_id in f for f in active_flights):
                st.warning(f"⚠️ الرحلة {f_no} مفتوحة بالفعل! يرجى اختيارها من 'الرحلات النشطة'.")
            else:
                save_flight_data(f_id, {"flight_no": f_no, "reg": f_reg, "date": today, "times": {}})
                st.session_state.active_id = f_id
                st.success("تم بدء الرحلة بنجاح.")
                st.rerun()
        else:
            st.error("يرجى إدخال رقم الرحلة والتسجيل.")

else:
    if active_flights:
        # ترتيب الرحلات بحيث تظهر الأحدث دائماً
        selected_flight = st.sidebar.selectbox("اختر رحلة للمتابعة:", sorted(active_flights, reverse=True))
        st.session_state.active_id = selected_flight
        
        if st.sidebar.button("🗑️ حذف الرحلة الحالية"):
            os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
            st.rerun()
    else:
        st.info("لا توجد رحلات نشطة.")

# --- 7. أرشيف الـ PDF ---
st.sidebar.divider()
st.sidebar.subheader("📂 الأرشيف (المنجزة)")
archived_files = sorted(glob.glob(os.path.join(ARCHIVE_DIR, "*.pdf")), reverse=True)
if archived_files:
    for pdf_path in archived_files[:5]: # عرض آخر 5 رحلات فقط لتقليل الزحام
        file_name = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            st.sidebar.download_button(label=f"📄 {file_name[:20]}...", data=f, file_name=file_name, mime="application/pdf", key=file_name)

# --- 8. واجهة العمل (Auto-Save) ---
if 'active_id' in st.session_state and st.session_state.active_id in get_active_flights():
    data = load_flight_data(st.session_state.active_id)
    if data:
        st.header(f"✈️ {data['flight_no']} | {data['reg']}")
        st.info(f"📅 التاريخ: {data.get('date')} | 👷 الموظف الحالي: {st.session_state.current_staff}")
        
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
        if st.button("📧 إرسال التقرير النهائي للمحطة", type="primary", use_container_width=True):
            try:
                pdf = FPDF()
                pdf.add_page()
                if os.path.exists(image_path):
                    pdf.image(image_path, x=10, y=10, w=190)
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

                os.rename(pdf_name, os.path.join(ARCHIVE_DIR, pdf_name))
                os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
                
                st.success("✅ تم الإرسال والأرشفة بنجاح.")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
