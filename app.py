import streamlit as st

# --- INICIALIZACIÓN DE LA MEMORIA (SESSION STATE) ---
# Esto evita que la app se reinicie al pulsar botones
if 'fase' not in st.session_state:
    st.session_state.fase = 1
if 'preguntas_ia' not in st.session_state:
    st.session_state.preguntas_ia = []
if 'respuestas_enfermeria' not in st.session_state:
    st.session_state.respuestas_enfermeria = {}

# --- INTERFAZ PRINCIPAL ---
st.title("🏥 TriajeClinico.ai - Anamnesis Dirigida")

# ---------------------------------------------------------
# FASE 1: CONSTANTES Y MOTIVO DE CONSULTA
# ---------------------------------------------------------
st.markdown("### 1️⃣ Triaje Inicial (Enfermería)")

with st.container(border=True):
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
   # NUEVO: Checkbox de control
medicion_disponible = st.checkbox("¿Dispone de dispositivos de medición? (Tensión, pulsómetro, etc.)", value=False)

if medicion_disponible:
    st.markdown("#### 2. Constantes Vitales")
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    with col_v1:
        fc = st.number_input("Frec. Cardíaca (bpm)", 30, 250, 80)
    with col_v2:
        tas = st.number_input("Tensión Sistólica", 40, 300, 120)
    with col_v3:
        spo2 = st.number_input("SpO2 (%)", 50, 100, 98)
    with col_v4:
        temp = st.number_input("Temp (ºC)", 30.0, 45.0, 36.5, step=0.1)
else:
    # Si no hay medición, asignamos 'None' o un valor neutro para que la IA lo sepa
    fc = tas = spo2 = temp = None
    st.info("ℹ️ El triaje se realizará basándose exclusivamente en la sintomatología declarada.")

    motivo = st.text_input("Motivo de consulta principal (Breve)", placeholder="Ej: Dolor abdominal y vómitos desde hace 2 horas")

# Botón para saltar a la Fase 2
if st.session_state.fase == 1:
    if st.button("Generar Preguntas Clave", type="primary", use_container_width=True):
        if motivo:
            with st.spinner("Analizando síntomas y generando cuestionario..."):
                # AQUÍ LLAMAREMOS AL 'MOTOR A' EN EL FUTURO
                # Por ahora, simulamos que la IA nos devuelve estas preguntas:
                st.session_state.preguntas_ia = [
                    "¿El dolor es mayor a 7 sobre 10?",
                    "¿El abdomen está duro o rígido a la palpación?",
                    "¿Ha habido presencia de sangre en vómitos o heces?"
                ]
                st.session_state.fase = 2 # Pasamos a la siguiente fase
                st.rerun() # Forzamos recarga para mostrar las preguntas
        else:
            st.warning("⚠️ Introduce un motivo de consulta para continuar.")

# ---------------------------------------------------------
# FASE 2: CUESTIONARIO DINÁMICO Y DIAGNÓSTICO
# ---------------------------------------------------------
if st.session_state.fase == 2:
    st.markdown("### 2️⃣ Cuestionario Dirigido (Generado por IA)")
    
    with st.container(border=True):
        st.info(f"**Motivo registrado:** {motivo}")
        st.markdown("Responde rápidamente a las siguientes cuestiones:")
        
        # Generamos los selectores dinámicamente según lo que diga la IA
        for i, pregunta in enumerate(st.session_state.preguntas_ia):
            # Guardamos las respuestas en el diccionario
            st.session_state.respuestas_enfermeria[pregunta] = st.radio(
                pregunta, 
                ["Sí", "No", "No valorable"], 
                horizontal=True,
                key=f"q_{i}" # Key única obligatoria en Streamlit
            )

    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        # Botón por si el enfermero se equivoca y quiere empezar de cero
        if st.button("🔙 Reiniciar Triaje", use_container_width=True):
            st.session_state.fase = 1
            st.session_state.preguntas_ia = []
            st.rerun()

    with col_btn2:
        # Botón para lanzar el dictamen final
        if st.button("Evaluar Triaje Final", type="primary", use_container_width=True):
            with st.spinner("Calculando prioridad y diagnóstico diferencial..."):
                
                # AQUÍ LLAMAREMOS AL 'MOTOR B' EN EL FUTURO
                
                # Simulación de salida para visualizar la interfaz:
                st.success("✅ Evaluación completada.")
                st.error("🚨 PRIORIDAD: NARANJA (Atención < 10 min)")
                
                with st.expander("📄 Ver Informe Médico Preliminar", expanded=True):
                    st.markdown("**Diagnóstico Diferencial Sugerido:**")
                    st.markdown("- Apendicitis aguda\n- Úlcera péptica perforada\n- Cólico biliar")
                    st.markdown("**Banderas Rojas Detectadas:**")
                    st.markdown("- Abdomen rígido + Taquicardia (posible peritonitis)")