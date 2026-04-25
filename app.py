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

# --- 1. إعدادات المنطقة والوقت (توقيت بغداد) ---
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# --- 2. إعدادات المحطة والإيميل ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_DIR = "flights_data"
ARCHIVE_DIR = "pdf_archive"

# إنشاء المجلدات اللازمة
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
            with open(path, "r") as f: 
                return json.load(f)
        except:
            return None
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
    if st.button("دخول للنظام"):
        if name_input:
            st.session_state.current_staff = name_input
            st.rerun()
    st.stop()

# --- 6. إدارة الرحلات (Sidebar) ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()

menu = st.sidebar.radio("القائمة الرئيسية:", ["الرحلات النشطة", "فتح رحلة جديدة"])

if menu == "فتح رحلة جديدة":
    st.subheader("🆕 تسجيل رحلة جديدة")
    f_no = st.text_input("رقم الرحلة:").upper().strip()
    f_reg = st.text_input("تسجيل الطائرة:").upper().strip()
    
    if st.button("بدء الرحلة"):
        if f_no and f_reg:
            today = datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y')
            f_id = f"{f_no}_{f_reg}_{today}"
            
            if f_id in active_flights:
                st.sidebar.warning("⚠️ هذه الرحلة مفتوحة بالفعل.")
            else:
                save_flight_data(f_id, {"flight_no": f_no, "reg": f_reg, "date": today, "times": {}})
                st.session_state.active_id = f_id
                st.rerun()

else:
    if active_flights:
        selected_flight = st.sidebar.selectbox("اختر رحلة نشطة:", active_flights)
        st.session_state.active_id = selected_flight
        if st.sidebar.button("🗑️ حذف الرحلة الحالية"):
            os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
            st.rerun()
    else:
        st.info("لا توجد رحلات نشطة حالياً.")

# --- 7. قسم الأرشيف (الرحلات المنجزة) في Sidebar ---
st.sidebar.divider()
st.sidebar.subheader("📂 أرشيف الرحلات المنجزة")
archived_files = sorted(glob.glob(os.path.join(ARCHIVE_DIR, "*.pdf")), reverse=True)

if archived_files:
    for pdf_path in archived_files:
        file_name = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            st.sidebar.download_button(
                label=f"📄 {file_name[:25]}...", # اختصار الاسم للعرض
                data=f,
                file_name=file_name,
                mime="application/pdf",
                key=file_name
            )
else:
    st.sidebar.info("الأرشيف فارغ حالياً.")

# --- 8. واجهة تسجيل الأوقات (Auto-Save) ---
if 'active_id' in st.session_state:
    data = load_flight_data(st.session_state.active_id)
    if data:
        st.header(f"✈️ {data.get('flight_no')} | {data.get('reg')}")
        f_date = data.get('date', datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y'))
        st.info(f"📅 التاريخ: {f_date} | 💾 الحفظ تلقائي")
        
        services = [
            ("⏱ Chocks ON", "CHOCKS_ON"), ("⚡ GPU Arrival", "GPU_ARRIVAL"),
            ("🔌 APU Start", "APU_START"), ("💨 Air Starter", "AIR_STARTER"),
            ("📦 FWD Open", "FWD_OPEN"), ("🔒 FWD Close", "FWD_CLOSE"),
            ("📦 AFT Open", "AFT_OPEN"), ("🔒 AFT Close", "AFT_CLOSE"),
            ("🚛 Fuel Arrival", "FUEL_ARRIVAL"), ("⛽ Fuel End", "FUEL_END"),
            ("🧹 Cleaning START", "CLEANING_START"), ("✨ Cleaning END", "CLEANING_END"),
            ("🚶 First Pax", "FIRST_PAX"), ("🏁 Last Pax", "LAST_PAX"),
            ("📄 Loadsheet", "LOADSHEET"), ("🚪 Close Door", "CLOSE_DOOR"),
            ("🚜 Pushback Truck", "PUSHBACK_TRUCK
