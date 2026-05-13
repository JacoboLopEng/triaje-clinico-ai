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
                # Limpiamos los datos para enviarlos a la IA
                def limpiar(v): return v if v > 0 else "No medido"
                
                preguntas = motor_a_entrevistador(
                motivo, 
                limpiar(fc), 
                limpiar(tas), 
                limpiar(spo2), 
                limpiar(temp)
                )
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
        st.info(f"**Motivo registrado:** {st.session_state.datos_iniciales['motivo']}")
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