import google.generativeai as genai

# Tu clave
api_key = "AIzaSyCQVGQZ39u_tpgkwfoRcaWzJtfvjd51unE"
genai.configure(api_key=api_key)

print("--- PREGUNTANDO A GOOGLE QUÉ MODELOS TIENES DISPONIBLES ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Disponible: {m.name}")
except Exception as e:
    print(f"❌ Error grave: {e}")
print("---------------------------------------------------------")