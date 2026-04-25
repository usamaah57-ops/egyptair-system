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

# --- 1. إعدادات الوقت المحلي ---
BAGHDAD_TZ = pytz.timezone('Asia/Baghdad')

# --- 2. الإعدادات العامة للمحطة ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_DIR = "flights_data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

st.set_page_config(page_title="MS Baghdad Ops", page_icon="✈️", layout="centered")

# --- 3. عرض شعار مصر للطيران ---
if os.path.exists("egyptair_plane.jpg"):
    st.image("egyptair_plane.jpg", use_container_width=True)

# --- 4. وظائف إدارة الملفات ---
def save_flight_data(flight_id, data):
    with open(os.path.join(DATA_DIR, f"{flight_id}.json"), "w") as f:
        json.dump(data, f)

def load_flight_data(flight_id):
    path = os.path.join(DATA_DIR, f"{flight_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f: 
            return json.load(f)
    return {}

def get_active_flights():
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    return [os.path.basename(f).replace(".json", "") for f in files]

# --- 5. تسجيل دخول الموظف ---
if 'current_staff' not in st.session_state or not st.session_state.current_staff:
    st.subheader("👤 تسجيل دخول الموظف")
    name_input = st.text_input("الاسم بالكامل للمناوبة:")
    if st.button("دخول للنظام"):
        if name_input:
            st.session_state.current_staff = name_input
            st.rerun()
    st.stop()

# --- 6. إدارة قائمة الرحلات (القائمة الجانبية) ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()

option = st.sidebar.radio("القائمة الرئيسية:", ["الرحلات النشطة", "فتح رحلة جديدة"])

if option == "فتح رحلة جديدة":
    st.subheader("🆕 تسجيل رحلة جديدة")
    new_f = st.text_input("رقم الرحلة (مثال: MS616):").upper().strip()
    new_r = st.text_input("تسجيل الطائرة (مثال: SUGCR):").upper().strip()
    
    if st.button("بدء تسجيل الرحلة"):
        if new_f and new_r:
            today_str = datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y')
            f_id = f"{new_f}_{new_r}_{today_str}"
            
            if f_id in active_flights:
                st.error(f"⚠️ الرحلة {new_f} مسجلة بالفعل اليوم. اخترها من القائمة الجانبية.")
            else:
                save_flight_data(f_id, {
                    "flight_no": new_f, 
                    "reg": new_r, 
                    "date": today_str,
                    "times": {}
                })
                st.session_state.active_id = f_id
                st.rerun()
        else:
            st.warning("يرجى إكمال البيانات أولاً.")
else:
    if active_flights:
        selected = st.sidebar.selectbox("اختر الرحلة للمتابعة:", active_flights)
        st.session_state.active_id = selected
        
        # --- إضافة زر المسح نهائياً ---
        st.sidebar.divider()
        if st.sidebar.button("🗑️ مسح هذه الرحلة من القائمة"):
            file_to_del = os.path.join(DATA_DIR, f"{st.session_state.active_id}.json")
            if os.path.exists(file_to_del):
                os.remove(file_to_del)
                st.sidebar.success("تم مسح الملف بنجاح.")
                st.rerun()
    else:
        st.info("لا توجد رحلات نشطة حالياً.")
        st.stop()

# --- 7. واجهة العمل على الرحلة المختارة ---
if 'active_id' in st.session_state:
    data = load_flight_data(st.session_state.active_id)
    if data:
        st.header(f"✈️ {data.get('flight_no', 'N/A')} | {data.get('reg', 'N/A')}")
        flight_date = data.get('date', datetime.now(BAGHDAD_TZ).strftime('%d-%m-%Y'))
        st.info(f"📅 تاريخ الرحلة: {flight_date}")
        
        services = [
            ("⏱ Chocks ON", "CHOCKS_ON"), ("⚡ GPU Arrival", "GPU_ARRIVAL"),
            ("🔌 APU Start", "APU_START"), ("💨 Air Starter", "AIR_STARTER"),
            ("📦 FWD Open", "FWD_OPEN"), ("🔒 FWD Close", "FWD_CLOSE"),
            ("📦 AFT Open", "AFT_OPEN"), ("🔒 AFT Close", "AFT_CLOSE"),
            ("🚛 Fuel Arrival", "FUEL_ARRIVAL"), ("⛽ Fuel End", "FUEL_END"),
            ("🧹 Cleaning START", "CLEANING_START"), ("✨ Cleaning END", "CLEANING_END"),
            ("🚶 First Pax", "FIRST_PAX"), ("
