import streamlit as st
from groq import Groq
import datetime
import json
from fpdf import FPDF
import base64
import sqlite3

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="TriajeClinico.ai | HCE", page_icon="🏥", layout="wide")
st.markdown("""<style>.stDeployButton {display:none;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

# --- 2. GESTOR DE BASE DE DATOS (AHORA CON NOMBRE Y SIP) ---
def init_db():
    conn = sqlite3.connect('historial_clinico.db', check_same_thread=False)
    c = conn.cursor()
    # AÑADIMOS COLUMNAS DE IDENTIFICACIÓN
    c.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            nombre TEXT,
            sip TEXT,
            edad INTEGER,
            dolor INTEGER,
            sintomas TEXT,
            prioridad TEXT,
            diagnostico TEXT,
            pdf_blob BLOB
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

def guardar_paciente(nombre, sip, edad, dolor, sintomas, resultado_ia, pdf_bytes):
    """Guarda la ficha completa con identificación."""
    c = conn.cursor()
    c.execute('''
        INSERT INTO pacientes (fecha, nombre, sip, edad, dolor, sintomas, prioridad, diagnostico, pdf_blob)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        nombre,
        sip,
        edad,
        dolor,
        sintomas,
        resultado_ia.get('color_triaje'),
        resultado_ia.get('cie10_descripcion'),
        pdf_bytes
    ))
    conn.commit()

def obtener_historial():
    c = conn.cursor()
    c.execute('SELECT * FROM pacientes ORDER BY id DESC')
    return c.fetchall()

# --- 3. DISEÑO DEL INFORME (CON DATOS PERSONALES) ---
class PDFInforme(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SERVICIO DE SALUD - INFORME DE PRE-ADMISIÓN', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Sistema de Triaje Inteligente v4.0 | Documento Provisional', 0, 0, 'C')

def crear_pdf_completo(datos_ia, sintomas, nombre, sip, edad, dolor):
    pdf = PDFInforme()
    pdf.add_page()
    
    # 1. CAJA DE FILIACIÓN (DATOS PERSONALES)
    pdf.set_fill_color(240, 248, 255) # Azulito clínico muy suave
    pdf.rect(10, 25, 190, 25, 'F')
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 8, f"PACIENTE: {nombre.upper()}", 0, 0)
    pdf.cell(95, 8, f"Nº SIP/DNI: {sip}", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, f"Edad: {edad} años", 0, 0)
    pdf.cell(50, 8, f"Fecha: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0)
    pdf.cell(50, 8, f"ID Triaje: #{int(datetime.datetime.now().timestamp())}", 0, 1)
    pdf.ln(10)
    
    # 2. MOTIVO DE CONSULTA
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '1. MOTIVO DE CONSULTA (ANAMNESIS)', 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Línea separadora
    pdf.ln(2)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, f"El paciente refiere: {sintomas}\n\nNivel de dolor declarado: {dolor}/10 (Escala EVA)")
    pdf.ln(5)
    
    # 3. JUICIO CLÍNICO IA
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '2. VALORACIÓN DE TRIAJE', 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    
    color = datos_ia.get('color_triaje', 'VERDE')
    pdf.set_font('Arial', 'B', 14)
    if color == 'ROJO': pdf.set_text_color(220, 50, 50)
    elif color == 'NARANJA': pdf.set_text_color(255, 128, 0)
    elif color == 'AMARILLO': pdf.set_text_color(204, 204, 0)
    else: pdf.set_text_color(0, 128, 0)
    
    pdf.cell(0, 10, f"PRIORIDAD ASIGNADA: {color}", 0, 1)
    pdf.set_text_color(0,0,0)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.write(8, "Sospecha Diagnóstica (CIE-10): ")
    pdf.set_font('Arial', '', 11)
    pdf.write(8, f"{datos_ia.get('cie10_codigo')} - {datos_ia.get('cie10_descripcion')}\n")
    pdf.ln(2)
    
    # Caja gris para el razonamiento
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font('Arial', 'I', 10)
    pdf.multi_cell(0, 6, f"Razonamiento Algorítmico: {datos_ia.get('razonamiento')}", 1, 'L', True)
    pdf.ln(5)
    
    # 4. PLAN
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '3. PLAN DE ACTUACIÓN RECOMENDADO', 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, datos_ia.get('accion'))
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. CONEXIÓN GROQ ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("❌ Falta API Key")
    st.stop()

def motor_triaje(sintomas, dolor, edad):
    prompt = f"""
    Eres MÉDICO DE URGENCIAS. Paciente {edad} años, dolor {dolor}/10. Síntomas: {sintomas}.
    Asigna CIE-10 más probable.
    Salida JSON estricta:
    {{
        "color_triaje": "ROJO"|"NARANJA"|"AMARILLO"|"VERDE",
        "cie10_codigo": "Código",
        "cie10_descripcion": "Nombre patología",
        "accion": "Instrucción clínica",
        "razonamiento": "Justificación breve"
    }}
    """
    try:
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0, response_format={"type": "json_object"}
        )
        return json.loads(chat.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

# --- 5. INTERFAZ ---
st.title("Sistema de Triaje Hospitalario")
st.markdown("---")
st.caption("v4.0 | Motor Analítico: Llama-3 70B | Entorno de Producción")
tab1, tab2 = st.tabs(["➕ NUEVA ADMISIÓN", "🗂️ HISTORIA CLÍNICA"])

# --- PESTAÑA 1: NUEVO INGRESO ---
with tab1:
    # SECCIÓN DE DATOS PERSONALES (NUEVA)
    with st.container(border=True):
        st.subheader("Datos de Filiación")
        col_id1, col_id2, col_id3 = st.columns([2, 1, 1])
        with col_id1:
            nombre = st.text_input("Nombre y Apellidos", placeholder="Ej: Juan Pérez García")
        with col_id2:
            sip = st.text_input("Nº SIP / DNI", placeholder="Ej: 12345678-A")
        with col_id3:
            edad = st.number_input("Edad", 0, 110, 30)

    # SECCIÓN CLÍNICA
    with st.container(border=True):
        st.subheader("Evaluación Clínica")
        col_clin1, col_clin2 = st.columns([1, 2])
        with col_clin1:
            dolor = st.slider("Escala de Dolor (EVA)", 0, 10, 5, help="0 es sin dolor, 10 es el peor dolor imaginable")
            st.caption("Seleccione la intensidad del dolor")
        with col_clin2:
            sintomas = st.text_area("Anamnesis (Síntomas)", height=100, placeholder="Describa qué le ocurre, desde cuándo y cómo empezó...")

    # BOTÓN DE ACCIÓN
    
if st.button("Procesar Triaje y Emitir Informe", type="primary", use_container_width=True):
        if nombre and sip and sintomas:
            with st.spinner("🔄 Procesando datos con Llama-3 y Protocolos Médicos..."):
                resultado = motor_triaje(sintomas, dolor, edad)
                
                if "error" not in resultado:
                    # 1. Crear PDF
                    pdf_bytes = crear_pdf_completo(resultado, sintomas, nombre, sip, edad, dolor)
                    
                    # 2. Guardar en BD
                    guardar_paciente(nombre, sip, edad, dolor, sintomas, resultado, pdf_bytes)
                    
                    # 3. Feedback Visual
                    color = resultado.get('color_triaje')
                    if color == "ROJO": st.error(f"⚠️ PRIORIDAD MÁXIMA: {color}")
                    elif color == "NARANJA": st.warning(f"⚠️ PRIORIDAD ALTA: {color}")
                    elif color == "AMARILLO": st.warning(f"PRIORIDAD MEDIA: {color}")
                    else: st.success(f"PRIORIDAD BAJA: {color}")
                    
                    st.toast("Paciente registrado correctamente", icon="✅")
                    
                    # 4. Descarga
                    b64 = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/pdf;base64,{b64}" download="Informe_{nombre.replace(" ","_")}.pdf"><button style="background-color:#2e7d32;color:white;padding:12px;border:none;border-radius:5px;cursor:pointer;width:100%">📄 DESCARGAR INFORME OFICIAL</button></a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("Error al conectar con el motor de IA.")
        else:
            st.warning("⚠️ Por favor, rellene los campos de Nombre, SIP y Síntomas para poder emitir un informe legal.")

# --- PESTAÑA 2: HISTORIAL ---
with tab2:
    st.subheader("Listado de Pacientes Atendidos")
    if st.button("🔄 Actualizar listado"):
        st.rerun()

    casos = obtener_historial()
    
    if casos:
        for caso in casos:
            # Estructura de 'caso': 
            # id(0), fecha(1), nombre(2), sip(3), edad(4), dolor(5), sintomas(6), prioridad(7), diagnostico(8), pdf(9)
            id_caso = caso[0]
            nombre_paciente = caso[2]
            prioridad = caso[7]
            
            icono = "⚪"
            if prioridad == "ROJO": icono = "🔴"
            elif prioridad == "NARANJA": icono = "🟠"
            elif prioridad == "AMARILLO": icono = "🟡"
            elif prioridad == "VERDE": icono = "🟢"
            
            with st.expander(f"{icono} {caso[1]} | {nombre_paciente} (SIP: {caso[3]})"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**Diagnóstico:** {caso[8]}")
                    st.caption(f"Síntomas: {caso[6]}")
                with c2:
                    st.download_button(
                        label="📄 VER INFORME",
                        data=caso[9],
                        file_name=f"Informe_{nombre_paciente}_{id_caso}.pdf",
                        mime="application/pdf",
                        key=f"hist_{id_caso}"
                    )
    else:
        st.info("No hay registros en la base de datos.")