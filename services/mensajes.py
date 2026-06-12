from services.supabase_client import supabase
from services.gemini import get_respuesta

def procesar_mensaje(numero_usuario: str, numero_club: str, nombre: str, mensaje: str) -> str:
    print(f"[MSG] De: {numero_usuario} | Para: {numero_club} | Texto: {mensaje}")

    club_res = supabase.table("clubs")\
        .select("*")\
        .eq("whatsapp_number", numero_club)\
        .eq("activo", True)\
        .single()\
        .execute()

    if not club_res.data:
        print(f"[ERROR] Club no encontrado para número: {numero_club}")
        return "Lo siento, este servicio no está disponible."

    club = club_res.data
    club_id = club["id"]
    system_prompt = club["system_prompt"]
    print(f"[CLUB] Encontrado: {club['nombre']}")

    conv_res = supabase.table("conversaciones")\
        .select("*")\
        .eq("club_id", club_id)\
        .eq("numero_usuario", numero_usuario)\
        .execute()

    if conv_res.data:
        conversacion = conv_res.data[0]
        historial = conversacion["historial"]
        print(f"[CONV] Historial existente: {len(historial)} mensajes")
    else:
        historial = []
        print(f"[CONV] Conversación nueva")
        supabase.table("conversaciones").insert({
            "club_id": club_id,
            "numero_usuario": numero_usuario,
            "nombre_usuario": nombre,
            "historial": []
        }).execute()

    respuesta = get_respuesta(system_prompt, historial, mensaje, club_id=club_id)
    print(f"[GEMINI] Respuesta: {respuesta[:80]}...")

    historial.append({"role": "user", "content": mensaje})
    historial.append({"role": "assistant", "content": respuesta})
    historial = historial[-10:]

    supabase.table("conversaciones")\
        .update({"historial": historial, "nombre_usuario": nombre})\
        .eq("club_id", club_id)\
        .eq("numero_usuario", numero_usuario)\
        .execute()

    return respuesta