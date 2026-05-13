import streamlit as st
# --- MOTOR A: EL ENTREVISTADOR (Poner al principio del archivo) ---
def motor_a_entrevistador(motivo, fc, tas, spo2, temp):
    prompt_entrevista = f"""
    Eres un médico experto en triaje de urgencias. Tu objetivo es generar 3 preguntas CLAVE de Sí/No para un paciente.
    
    DATOS ACTUALES:
    - Motivo: {motivo}
    - Constantes: FC:{fc}, TAS:{tas}, SpO2:{spo2}, Temp:{temp}
    
    INSTRUCCIONES:
    1. Si falta alguna constante vital (pone "No medido"), pregunta por síntomas físicos relacionados (ej: si no hay TAS, preguntar por mareo).
    2. Las preguntas deben descartar emergencias vitales (Banderas Rojas).
    3. Responde ÚNICAMENTE con un JSON: {{"preguntas": ["P1", "P2", "P3"]}}
    """
    try:
        import google.generativeai as genai
        import json
        model = genai.GenerativeModel('gemini-2.5-pro')
        respuesta = model.generate_content(
            prompt_entrevista,
            generation_config={"response_mime_type": "application/json", "temperature": 0.5}
        )
        return json.loads(respuesta.text).get("preguntas", [])
    except Exception as e:
        return [f"Error de IA: {str(e)}"]
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
if st.session_state.fase == 1:
    st.markdown("### 1️⃣ Triaje Inicial (Enfermería)")

    # Bloque de Constantes Vitales Independientes
    with st.container(border=True):
        st.markdown("#### Parámetros Biométricos")
        st.caption("Deje en 0 aquellos parámetros que no haya podido medir.")
        
        col_v1, col_v2, col_v3, col_v4 = st.columns(4)
        with col_v1:
            fc = st.number_input("FC (bpm)", 0, 250, 0)
        with col_v2:
            tas = st.number_input("TAS (mmHg)", 0, 300, 0)
        with col_v3:
            spo2 = st.number_input("SpO2 (%)", 0, 100, 0)
        with col_v4:
            temp = st.number_input("Temp (ºC)", 0.0, 45.0, 0.0, step=0.1)

    # Bloque de Motivo de Consulta
    with st.container(border=True):
        st.markdown("#### Motivo de la Urgencia")
        motivo = st.text_input("¿Qué le ocurre al paciente?", placeholder="Ej: Dolor abdominal fuerte...")

    # Botón para generar preguntas
    if st.button("Generar Preguntas Clave", type="primary", use_container_width=True):
        if motivo:
            with st.spinner("Generando cuestionario dirigido..."):
                # 1. Limpiamos los datos
                def limpiar(v): return v if v > 0 else "No medido"
                
                # 2. Llamamos a la IA
                preguntas_generadas = motor_a_entrevistador(
                    motivo, 
                    limpiar(fc), 
                    limpiar(tas), 
                    limpiar(spo2), 
                    limpiar(temp)
                )
                
                # 3. GUARDAMOS EN MEMORIA (Esto es lo que te faltaba)
                st.session_state.preguntas_ia = preguntas_generadas
                
                # 4. Guardamos el resto de datos
                st.session_state.datos_iniciales = {
                    "motivo": motivo,
                    "fc": limpiar(fc),
                    "tas": limpiar(tas),
                    "spo2": limpiar(spo2),
                    "temp": limpiar(temp)
                }
                
                st.session_state.fase = 2
                st.rerun()
        else:
            st.warning("⚠️ El motivo de consulta es obligatorio para orientar las preguntas.")

# ---------------------------------------------------------
# FASE 2: CUESTIONARIO DINÁMICO Y DIAGNÓSTICO
# ---------------------------------------------------------
if st.session_state.fase == 2:
    st.markdown("### 2️⃣ Cuestionario Dirigido (Generado por IA)")
    
    with st.container(border=True):
        # Usamos la memoria guardada para que no desaparezca el motivo
        st.info(f"**Motivo registrado:** {st.session_state.datos_iniciales['motivo']}")
        st.markdown("Responde rápidamente a las siguientes cuestiones:")
        
        # EL BUCLE CRÍTICO: Aquí es donde se dibujan las preguntas de la IA
        if st.session_state.preguntas_ia:
            for i, pregunta in enumerate(st.session_state.preguntas_ia):
                # Guardamos la respuesta directamente en el estado
                st.session_state.respuestas_enfermeria[pregunta] = st.radio(
                    pregunta, 
                    ["No", "Sí", "No valorable"], # El 'No' por defecto es más seguro
                    horizontal=True,
                    key=f"pregunta_{i}" # ¡ESTO ES VITAL!
                )
        else:
            st.error("⚠️ No se han podido cargar las preguntas. Reintente el triaje.")