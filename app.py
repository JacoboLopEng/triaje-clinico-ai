import streamlit as st
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

# --- 4. CONEXIÓN GEMINI ---
import google.generativeai as genai


try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Usamos Gemini 1.5 Pro, ideal para razonamiento clínico complejo
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
except Exception as e:
    st.error("❌ Error configurando Gemini")
    st.stop()

def motor_triaje(sintomas, dolor, edad):
    prompt_completo = f"""
    Actúa como un Jefe de Urgencias Hospitalarias experto en Triaje Avanzado.
    
    INSTRUCCIONES DE RAZONAMIENTO CLÍNICO:
    1. Analiza los síntomas y crúzalos con antecedentes médicos.
    2. Identifica "Banderas Rojas" (Red Flags). Busca patologías subyacentes críticas (ej. isquemia, sepsis, shock embólico).
    3. Si hay contradicciones (ej. riesgo embólico vs sangrado), evalúa la fisiopatología.
    4. El 'plan de actuación' NUNCA debe contener medicación contraindicada para la etiología principal.

    EJEMPLO DE RAZONAMIENTO ESPERADO:
    - Paciente 74 años, dolor 9/10, sangre oscura, FA sin Sintrom.
    - Salida ideal -> Prioridad: ROJO. CIE-10: K55.0 (Isquemia vascular). Razonamiento: El riesgo embólico por FA sin medicar, más dolor agudo desproporcionado, sugiere oclusión arterial aguda. Acción: Prohibido anticoagulantes si hay sangrado activo. TAC urgente. Aviso a cirugía.

    Paciente real a evaluar:
    Edad: {edad} años. 
    Nivel de dolor: {dolor}/10. 
    Anamnesis: {sintomas}.

    Debes devolver UNICAMENTE un JSON estricto con esta estructura:
    {{
        "color_triaje": "ROJO"|"NARANJA"|"AMARILLO"|"VERDE",
        "cie10_codigo": "Código",
        "cie10_descripcion": "Nombre patología",
        "accion": "Instrucción clínica",
        "razonamiento": "Justificación clínica basada en banderas rojas"
    }}
    """

    try:
        # Forzamos a Gemini a responder en formato JSON
        respuesta = model.generate_content(
            prompt_completo,
            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        return json.loads(respuesta.text)
    except Exception as e:
        return {"error": str(e)}

# --- 5. INTERFAZ DE USUARIO (HOSPITAL GRADE) ---

# 5.1. BARRA LATERAL (SIDEBAR)
with st.sidebar:
    st.title("TriajeClinico.ai")
    st.caption("Sistema de Gestión de Urgencias")
    st.markdown("---")
    
    # Menú de navegación clínico
    menu = st.radio(
        "Panel de Navegación", 
        ["Centro de Operaciones", "Nueva Admisión", "Historial de Pacientes"]
    )
    
    st.markdown("---")
    # Simulación de sesión de usuario (Trazabilidad)
    st.info("👨‍⚕️ Facultativo en turno:\n\n**Dr. Jacobo**\n\nID Colegiado: 4600-UPV")
    st.caption(f"Fecha: {datetime.datetime.now().strftime('%d/%m/%Y')}")

# 5.2. ENRUTAMIENTO DE PANTALLAS

# Pantalla 1: DASHBOARD (NUEVA)
if menu == "Centro de Operaciones":
    st.header("Centro de Operaciones")
    st.markdown("Visión general de la planta de Urgencias en tiempo real.")
    
    casos = obtener_historial()
    total_pacientes = len(casos)
    
    # KPIs Rápidos
    col1, col2, col3 = st.columns(3)
    col1.metric("Pacientes Atendidos (Turno)", total_pacientes)
    col2.metric("Tiempo Medio Espera", "14 min") # Dato simulado por ahora
    col3.metric("Saturación de Planta", f"{min(total_pacientes * 5, 100)}%") # Dato simulado
    
    st.markdown("---")
    st.subheader("Últimos Registros Clínicos")
    if casos:
        # Mostramos los últimos 5 de forma limpia
        for caso in casos[:5]:
            st.markdown(f"**{caso[1]}** | Paciente: {caso[2]} | Prioridad IA: **{caso[7]}**")
    else:
        st.info("No hay actividad registrada en este turno.")

# Pantalla 2: FORMULARIO DE ADMISIÓN (REDISEÑADO)
elif menu == "Nueva Admisión":
    st.header("Protocolo de Admisión y Triaje")
    st.markdown("Cumplimente los datos del paciente para la evaluación algorítmica inicial.")
    
    # Contenedor 1: Filiación
    with st.container(border=True):
        st.markdown("#### 1. Datos de Filiación")
        col_id1, col_id2, col_id3 = st.columns([2, 1, 1])
        with col_id1:
            nombre = st.text_input("Nombre y Apellidos completos")
        with col_id2:
            sip = st.text_input("Nº SIP / Pasaporte")
        with col_id3:
            edad = st.number_input("Edad (Años)", 0, 120, 30)

    # Contenedor 2: Clínica
    with st.container(border=True):
        st.markdown("#### 2. Evaluación Clínica Básica")
        col_clin1, col_clin2 = st.columns([1, 2])
        with col_clin1:
            dolor = st.slider("Escala Visual Analógica (EVA)", 0, 10, 5)
            st.caption("0: Sin dolor | 10: Dolor insoportable")
        with col_clin2:
            sintomas = st.text_area("Anamnesis de Enfermería", height=100, placeholder="Motivo de consulta principal y desarrollo de los síntomas...")

    st.markdown("<br>", unsafe_allow_html=True) # Espaciado limpio

    # Botón Principal de Acción
    if st.button("Procesar Triaje Algorítmico", type="primary", use_container_width=True):
        if nombre and sip and sintomas:
            with st.spinner("Procesando constantes y anamnesis con IA Clínica..."):
                resultado = motor_triaje(sintomas, dolor, edad)
                
                if "error" not in resultado:
                    pdf_bytes = crear_pdf_completo(resultado, sintomas, nombre, sip, edad, dolor)
                    guardar_paciente(nombre, sip, edad, dolor, sintomas, resultado, pdf_bytes)
                    
                    color = resultado.get('color_triaje')
                    if color == "ROJO": st.error(f"PRIORIDAD CRÍTICA (Nivel 1): {color} - ATENCIÓN INMEDIATA")
                    elif color == "NARANJA": st.warning(f"PRIORIDAD MUY URGENTE (Nivel 2): {color} - MAX 10 MIN")
                    elif color == "AMARILLO": st.warning(f"PRIORIDAD URGENTE (Nivel 3): {color} - MAX 60 MIN")
                    else: st.success(f"PRIORIDAD ESTÁNDAR: {color} - ESPERA SEGURA")
                    
                    # Descarga del PDF con diseño formal
                    b64 = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/pdf;base64,{b64}" download="Historia_{sip}.pdf" style="text-decoration: none;"><div style="background-color:#005a9c;color:white;padding:12px;border-radius:4px;text-align:center;font-weight:bold;margin-top:15px;">📥 DESCARGAR HISTORIA CLÍNICA FIRMADA</div></a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("Error de comunicación con el servidor central de diagnóstico.")
                    st.code(f"Fallo en el motor Gemini: {resultado.get('error')}")
        else:
            st.warning("Requisito legal: Los campos de Identificación y Anamnesis son obligatorios.")
            st.code(f"Diagnóstico de ingeniería: {resultado.get('error')}")

# Pantalla 3: HISTORIAL (REDISEÑADO)
elif menu == "Historial de Pacientes":
    st.header("Archivo Histórico de Pacientes")
    st.markdown("Registro inmutable de atenciones en Urgencias.")
    
    casos = obtener_historial()
    
    if casos:
        for caso in casos:
            id_caso, fecha, nombre_p, sip_p, edad_p, dolor_p, sintomas_p, prioridad, diagnostico, pdf = caso
            
            # Asignación de colores corporativos según prioridad
            color_borde = "grey"
            if prioridad == "ROJO": color_borde = "red"
            elif prioridad == "NARANJA": color_borde = "orange"
            elif prioridad == "AMARILLO": color_borde = "#d4b800"
            elif prioridad == "VERDE": color_borde = "green"
            
            # Tarjetas de paciente clínicas (usando markdown y HTML seguro)
            st.markdown(f"""
            <div style="border-left: 5px solid {color_borde}; padding: 10px; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                <strong>{fecha} | {nombre_p} (SIP: {sip_p})</strong><br>
                <span style="color: #555; font-size: 0.9em;">CIE-10: {diagnostico}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón de descarga adosado a la tarjeta
            st.download_button(
                label="Recuperar Informe PDF",
                data=pdf,
                file_name=f"Historia_{sip_p}_{fecha[:10]}.pdf",
                mime="application/pdf",
                key=f"hist_{id_caso}"
            )
            st.markdown("---")
    else:
        st.info("La base de datos del archivo se encuentra vacía.")