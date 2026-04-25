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
import glob

# --- الإعدادات ---
EMAIL_SENDER = "usama_ghh@yahoo.com"
EMAIL_PASSWORD = "dvfsxhdlzhcrqpys" 
EMAIL_RECEIVER = "Baghdad_kk@egyptair.com"
DATA_DIR = "flights_data" # مجلد خاص لكل رحلة

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

st.set_page_config(page_title="MS Baghdad Multi-Ops", page_icon="✈️")

# وظائف التعامل مع ملفات الرحلات المتعددة
def save_flight_data(flight_id, data):
    filename = os.path.join(DATA_DIR, f"{flight_id}.json")
    with open(filename, "w") as f:
        json.dump(data, f)

def load_flight_data(flight_id):
    filename = os.path.join(DATA_DIR, f"{flight_id}.json")
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def get_active_flights():
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    return [os.path.basename(f).replace(".json", "") for f in files]

# --- مرحلة تسجيل الموظف ---
if 'current_staff' not in st.session_state or not st.session_state.current_staff:
    st.subheader("👤 تسجيل دخول الموظف")
    name_input = st.text_input("الاسم بالكامل:")
    if st.button("تأكيد"):
        st.session_state.current_staff = name_input
        st.rerun()
    st.stop()

# --- واجهة اختيار الرحلة ---
st.sidebar.title(f"👷 {st.session_state.current_staff}")
active_flights = get_active_flights()

option = st.sidebar.radio("إدارة الرحلات:", ["فتح رحلة جديدة", "الرحلات النشطة حالياً"])

if option == "فتح رحلة جديدة":
    st.subheader("🆕 تسجيل رحلة جديدة")
    new_f = st.text_input("رقم الرحلة (مثلاً MS616):").upper()
    new_r = st.text_input("تسجيل الطائرة (Reg):").upper()
    if st.button("بدء الرحلة"):
        f_id = f"{new_f}_{new_r}_{datetime.now().strftime('%H%M')}"
        save_flight_data(f_id, {"flight_no": new_f, "reg": new_r, "times": {}})
        st.session_state.active_id = f_id
        st.rerun()

else:
    if not active_flights:
        st.info("لا توجد رحلات نشطة حالياً.")
        st.stop()
    st.session_state.active_id = st.sidebar.selectbox("اختر الرحلة للمتابعة:", active_flights)

# --- واجهة العمل على الرحلة المختارة ---
if 'active_id' in st.session_state:
    data = load_flight_data(st.session_state.active_id)
    st.header(f"✈️ {data['flight_no']} | {data['reg']}")
    
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

    cols = st.columns(2)
    for i, (label, key) in enumerate(services_labels):
        if key in data['times']:
            rec = data['times'][key]
            cols[i % 2].success(f"{label}\n{rec['time']} ({rec['staff']})")
        else:
            if cols[i % 2].button(label, key=f"{st.session_state.active_id}_{key}", use_container_width=True):
                data['times'][key] = {"time": datetime.now().strftime("%H:%M"), "staff": st.session_state.current_staff}
                save_flight_data(st.session_state.active_id, data)
                st.rerun()

    st.divider()
    
    if st.button("📧 إنهاء وإرسال تقرير هذه الرحلة", type="primary", use_container_width=True):
        # توليد PDF وإرسال (نفس الكود السابق مع استخدام بيانات data['times'])
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Report: {data['flight_no']}", 0, 1, 'C')
            pdf.ln(10)
            
            for s, info in sorted(data['times'].items()):
                pdf.cell(80, 10, s, 1)
                pdf.cell(40, 10, info['time'], 1, 0, 'C')
                pdf.cell(70, 10, info['staff'], 1, 1, 'C')

            pdf_file = f"Report_{st.session_state.active_id}.pdf"
            pdf.output(pdf_file)
            
            # (كود الإرسال...)
            # بعد نجاح الإرسال:
            os.remove(os.path.join(DATA_DIR, f"{st.session_state.active_id}.json"))
            st.success("تم الإرسال وحذف الرحلة من القائمة النشطة.")
            st.rerun()
        except Exception as e:
            st.error(f"خطأ: {e}")
