import os
import sys
import re

# --- CONFIGURACIÓN ---
CARPETAS_IGNORAR = {'__pycache__', '.git', '.vscode', 'env', 'venv', '_BIBLIOTECA', '_EXPORTS_NOTEBOOK'}
EXTENSIONES_SUBS = ('.vtt', '.srt')
NOMBRE_CARPETA_BIBLIOTECA = "_BIBLIOTECA"

# Marcadores inútiles a filtrar (case-insensitive)
MARCADORES_INUTILES = {
    '[music]', '[applause]', '[laughter]', '[cheering]', '[silence]',
    '[inaudible]', '[crosstalk]', '[noise]', '[background noise]',
    '[foreign]', '[speaking foreign language]', '[no audio]',
    '[pause]', '[sighs]', '[coughs]', '[clears throat]',
}

# Umbral de pausa en segundos para separar párrafos
UMBRAL_PAUSA_PARRAFO = 2.5


def parsear_tiempo_vtt(tiempo_str):
    """Convierte timestamp VTT (HH:MM:SS.mmm) a segundos."""
    try:
        partes = tiempo_str.split(':')
        horas = int(partes[0])
        minutos = int(partes[1])
        segundos = float(partes[2])
        return horas * 3600 + minutos * 60 + segundos
    except:
        return None


def capitalizar_oraciones(texto):
    """Capitaliza la primera letra después de . ? ! y al inicio."""
    if not texto:
        return texto

    # Capitalizar inicio
    texto = texto[0].upper() + texto[1:] if len(texto) > 1 else texto.upper()

    # Capitalizar después de puntuación final
    resultado = []
    capitalizar_siguiente = False

    for i, char in enumerate(texto):
        if capitalizar_siguiente and char.isalpha():
            resultado.append(char.upper())
            capitalizar_siguiente = False
        else:
            resultado.append(char)

        if char in '.?!' and i < len(texto) - 1:
            capitalizar_siguiente = True

    return ''.join(resultado)


def limpiar_texto_vtt(contenido):
    """
    Limpia el contenido VTT y lo convierte en párrafos coherentes.
    Usa las pausas entre timestamps para detectar cambios de párrafo.
    """
    regex_tiempo_linea = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})')
    regex_etiquetas = re.compile(r'<[^>]+>')
    regex_atributos_linea = re.compile(r'align:\w+|position:\d+%')

    # Primera pasada: extraer bloques con timestamps
    bloques = []
    tiempo_actual_fin = None
    texto_bloque_actual = []
    lineas_vistas = set()

    lineas = contenido.splitlines()
    i = 0

    while i < len(lineas):
        linea = lineas[i].strip()

        # Saltar líneas de metadatos
        if (not linea or
            linea == "WEBVTT" or
            linea.startswith("Kind:") or
            linea.startswith("Language:") or
            linea.isdigit()):
            i += 1
            continue

        # Detectar línea de timestamp
        match_tiempo = regex_tiempo_linea.search(linea)
        if match_tiempo:
            tiempo_inicio = parsear_tiempo_vtt(match_tiempo.group(1))
            tiempo_fin = parsear_tiempo_vtt(match_tiempo.group(2))

            # Verificar si hay pausa significativa (nuevo párrafo)
            if tiempo_actual_fin is not None and tiempo_inicio is not None:
                pausa = tiempo_inicio - tiempo_actual_fin
                if pausa >= UMBRAL_PAUSA_PARRAFO and texto_bloque_actual:
                    # Guardar bloque actual y empezar nuevo párrafo
                    bloques.append({
                        'texto': texto_bloque_actual.copy(),
                        'es_nuevo_parrafo': True
                    })
                    texto_bloque_actual = []
                    lineas_vistas = set()

            tiempo_actual_fin = tiempo_fin
            i += 1
            continue

        # Procesar línea de texto
        # Quitar atributos de posición que a veces quedan en la línea
        linea = regex_atributos_linea.sub('', linea).strip()

        # Quitar etiquetas HTML
        texto_plano = regex_etiquetas.sub('', linea)

        # Reemplazar entidades HTML
        texto_plano = (texto_plano
            .replace('&nbsp;', ' ')
            .replace('&amp;', '&')
            .replace('&#39;', "'")
            .replace('&quot;', '"')
            .replace('  ', ' ')
            .strip())

        # Filtrar marcadores inútiles
        if texto_plano.lower() in MARCADORES_INUTILES:
            i += 1
            continue

        # También filtrar si contiene solo un marcador
        texto_sin_marcador = texto_plano
        for marcador in MARCADORES_INUTILES:
            texto_sin_marcador = texto_sin_marcador.lower().replace(marcador, '').strip()
        if not texto_sin_marcador:
            i += 1
            continue

        # Deduplicar
        if texto_plano and texto_plano not in lineas_vistas:
            texto_bloque_actual.append(texto_plano)
            lineas_vistas.add(texto_plano)

        i += 1

    # Agregar último bloque
    if texto_bloque_actual:
        bloques.append({
            'texto': texto_bloque_actual,
            'es_nuevo_parrafo': False
        })

    # Segunda pasada: unir líneas en párrafos
    parrafos = []

    for bloque in bloques:
        if not bloque['texto']:
            continue

        # Unir todas las líneas del bloque en un párrafo
        parrafo = ' '.join(bloque['texto'])

        # Limpiar espacios múltiples
        parrafo = re.sub(r'\s+', ' ', parrafo).strip()

        if parrafo:
            parrafos.append(parrafo)

    # Unir párrafos con doble salto de línea
    texto_final = '\n\n'.join(parrafos)

    # Capitalizar oraciones
    texto_final = capitalizar_oraciones(texto_final)

    return texto_final


def obtener_info_archivo(nombre_archivo):
    idioma = "ES"
    if ".en." in nombre_archivo.lower() or "_en." in nombre_archivo.lower():
        idioma = "EN"
    elif ".es." in nombre_archivo.lower() or "_es." in nombre_archivo.lower():
        idioma = "ES"
    nombre_base = os.path.splitext(os.path.splitext(nombre_archivo)[0])[0]
    return nombre_base, idioma


def procesar_directorio(base_dir=None):
    """
    Procesa todos los archivos VTT/SRT en el directorio y sus subdirectorios.

    Args:
        base_dir: Directorio base donde buscar archivos.
                  Si es None, usa el directorio actual.
    """
    if base_dir is None:
        base_dir = os.getcwd()

    # Validar que el directorio existe
    if not os.path.isdir(base_dir):
        print(f"❌ Error: El directorio '{base_dir}' no existe.")
        return

    print(f"🚀 [LIMPIAR] Iniciando procesamiento en: {base_dir}")
    print(f"⚙️  Configuración: Pausa para nuevo párrafo = {UMBRAL_PAUSA_PARRAFO}s\n")

    contador = 0
    errores = 0

    # Primero contar total de archivos para progreso
    total_archivos = 0
    for raiz, dirs, archivos in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in CARPETAS_IGNORAR]
        if NOMBRE_CARPETA_BIBLIOTECA in raiz:
            continue
        total_archivos += sum(1 for a in archivos if a.endswith(EXTENSIONES_SUBS))

    print(f"📊 Encontrados {total_archivos} archivos para procesar.\n")

    for raiz, dirs, archivos in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in CARPETAS_IGNORAR]

        if NOMBRE_CARPETA_BIBLIOTECA in raiz:
            continue

        # Obtener nombre del proyecto actual
        proyecto_actual = os.path.basename(raiz) if raiz != base_dir else "raíz"

        archivos_subs = [a for a in archivos if a.endswith(EXTENSIONES_SUBS)]
        if archivos_subs:
            print(f"📦 Procesando: {proyecto_actual} ({len(archivos_subs)} archivos)")

        for idx, archivo in enumerate(archivos_subs):
            # Indicador de progreso
            print(f"   {idx+1}/{len(archivos_subs)}: {archivo[:50]}...", end='\r')

            ruta_origen = os.path.join(raiz, archivo)
            try:
                with open(ruta_origen, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido_raw = f.read()

                texto_limpio = limpiar_texto_vtt(contenido_raw)
                if not texto_limpio:
                    continue

                nombre_base, idioma = obtener_info_archivo(archivo)

                # Guardar en _BIBLIOTECA
                carpeta_salida = os.path.join(raiz, NOMBRE_CARPETA_BIBLIOTECA)
                if not os.path.exists(carpeta_salida):
                    os.makedirs(carpeta_salida)

                nombre_salida = f"{nombre_base} [{idioma}].md"
                ruta_salida = os.path.join(carpeta_salida, nombre_salida)

                with open(ruta_salida, 'w', encoding='utf-8') as f_out:
                    f_out.write(f"# {nombre_base}\n")
                    f_out.write(f"**Idioma:** {idioma}\n")
                    f_out.write(f"**Fuente:** {archivo}\n")
                    f_out.write("---\n\n")
                    f_out.write(texto_limpio)

                contador += 1
            except Exception as e:
                print(f"\n❌ Error en {archivo}: {e}")
                errores += 1

        if archivos_subs:
            print(f"   ✅ {proyecto_actual}: {len(archivos_subs)} archivos procesados" + " "*30)

    print(f"\n✨ [LIMPIAR] Fin.")
    print(f"   ✅ Procesados: {contador}")
    if errores:
        print(f"   ❌ Errores: {errores}")


if __name__ == "__main__":
    # Permitir especificar directorio base como argumento
    if len(sys.argv) > 1:
        procesar_directorio(sys.argv[1])
    else:
        procesar_directorio()
