import streamlit as st
import google.generativeai as genai
import json
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
    
    # --- MOTOR B: EL EVALUADOR ---
def motor_b_evaluador(datos_iniciales, respuestas):
    prompt_final = f"""
    Eres un Jefe de Urgencias. Evalúa este triaje.
    DATOS INICIALES: {datos_iniciales}
    RESPUESTAS: {respuestas}
    TAREAS:
    1. Color triaje (ROJO, NARANJA, AMARILLO, VERDE).
    2. Informe: Sospechas (3), Alertas, Plan.
    Responde ÚNICAMENTE JSON: {{"color": "C", "informe": {{"sospechas": [], "alertas": [], "plan": ""}}}}
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        res = model.generate_content(prompt_final, generation_config={"response_mime_type": "application/json"})
        return json.loads(res.text)
    except Exception as e:
        return {"error": str(e)}

        
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
                st.session_state.respuestas_enfermeria = {}
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

# --- FINAL DEL ARCHIVO (FASE 2) ---
if st.session_state.fase == 2:
    st.markdown("### 2️⃣ Cuestionario Dirigido")
    
    with st.container(border=True):
        st.info(f"**Motivo:** {st.session_state.datos_iniciales['motivo']}")
        
        if st.session_state.preguntas_ia:
            for i, p in enumerate(st.session_state.preguntas_ia):
                # Guardamos la respuesta en el diccionario
                st.session_state.respuestas_enfermeria[p] = st.radio(
                    p, 
                    ["No", "Sí", "No valorable"], 
                    horizontal=True, 
                    key=f"p_{i}"
                )
        else:
            st.error("⚠️ No hay preguntas cargadas.")

    # ESTAS COLUMNAS DEBEN ESTAR DENTRO DEL IF DE LA FASE 2
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔙 Reiniciar Triaje", use_container_width=True):
            st.session_state.fase = 1
            st.rerun()
            
    with col2:
        if st.button("Evaluar Triaje Final", type="primary", use_container_width=True):
            with st.spinner("Generando informe médico..."):
                # LLAMADA AL MOTOR B
                res = motor_b_evaluador(
                    st.session_state.datos_iniciales, 
                    st.session_state.respuestas_enfermeria
                )
                
                if "error" not in res:
                    st.divider()
                    # Mostrar Prioridad
                    color = res['color']
                    if color == "ROJO": st.error(f"🚨 PRIORIDAD: {color}")
                    elif color == "NARANJA": st.warning(f"⚠️ PRIORIDAD: {color}")
                    else: st.success(f"✅ PRIORIDAD: {color}")
                    
                    # Informe Desplegable
                    with st.expander("📄 INFORME CLÍNICO DETALLADO", expanded=True):
                        st.markdown("### Sospechas Clínicas")
                        for s in res['informe']['sospechas']: st.write(f"📍 {s}")
                        
                        st.markdown("### Alertas (Red Flags)")
                        for a in res['informe']['alertas']: st.write(f"🚩 {a}")
                        
                        st.info(f"**Plan de Acción:** {res['informe']['plan']}")
                else:
                    st.error(f"Error en el servidor: {res['error']}")