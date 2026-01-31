import os
import sys
import math
import json
from datetime import datetime

# --- CONFIGURACIÓN ---
NOMBRE_CARPETA_BIBLIOTECA = "_BIBLIOTECA"
CARPETA_EXPORTACION = "_EXPORTS_NOTEBOOK"

# CANTIDAD DE TRANSCRIPCIONES POR ARCHIVO DE TEXTO
# 100 es un buen balance. Si un canal tiene 1000 videos, creará 10 archivos.
TRANSCRIPCIONES_POR_TXT = 100

# Separador semántico optimizado para NotebookLM/RAG
SEPARADOR_TRANSCRIPCION = "\n\n---\n[FIN DE TRANSCRIPCION]\n---\n\n"


def validar_archivo_procesado(contenido):
    """
    Verifica que el archivo sea una transcripción procesada por limpiar.py.
    Los archivos válidos comienzan con '# ' (título markdown).
    """
    return contenido.strip().startswith("# ")


def extraer_titulo_de_contenido(contenido):
    """Extrae el título del archivo markdown (primera línea sin #)."""
    primera_linea = contenido.split('\n')[0]
    return primera_linea.lstrip('# ').strip()


def consolidar_proyectos(base_dir=None):
    """
    Consolida archivos .md de _BIBLIOTECA en volúmenes .txt para NotebookLM.

    Args:
        base_dir: Directorio base donde están los proyectos.
                  Si es None, usa el directorio actual.
    """
    if base_dir is None:
        base_dir = os.getcwd()

    # Validar que el directorio existe
    if not os.path.isdir(base_dir):
        print(f"❌ Error: El directorio '{base_dir}' no existe.")
        return

    ruta_export = os.path.join(base_dir, CARPETA_EXPORTACION)

    if not os.path.exists(ruta_export):
        os.makedirs(ruta_export)

    print(f"📚 [CONSOLIDAR] Iniciando segmentación inteligente.")
    print(f"📂 Base: {base_dir}")
    print(f"📂 Salida: {CARPETA_EXPORTACION}/")
    print(f"⚙️  Configuración: ~{TRANSCRIPCIONES_POR_TXT} transcripciones por volumen.\n")

    # Manifest para tracking
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "base_directory": base_dir,
        "projects": {}
    }

    # Escanear carpetas de proyectos
    proyectos = [f.path for f in os.scandir(base_dir) if f.is_dir()]

    for proyecto in proyectos:
        nombre_proyecto = os.path.basename(proyecto)

        # Ignorar carpetas de sistema/ocultas y la de exportación
        if nombre_proyecto.startswith(('.', '__', 'env')) or nombre_proyecto == CARPETA_EXPORTACION:
            continue

        ruta_biblioteca = os.path.join(proyecto, NOMBRE_CARPETA_BIBLIOTECA)

        # Verificar si existe la biblioteca procesada
        if not os.path.exists(ruta_biblioteca):
            continue

        # 1. Obtener archivos .md limpios
        # NOTA: El ordenamiento alfabético funciona como cronológico porque
        # limpiar.py genera nombres con formato YYYYMMDD_titulo [IDIOMA].md
        archivos_md = [f for f in os.listdir(ruta_biblioteca) if f.endswith(".md")]
        archivos_md.sort()  # Orden cronológico por prefijo YYYYMMDD_

        if not archivos_md:
            print(f"💨 {nombre_proyecto}: Biblioteca vacía (ejecuta limpiar.py primero).")
            continue

        # 2. Calcular volúmenes necesarios
        total_archivos = len(archivos_md)
        total_volumenes = math.ceil(total_archivos / TRANSCRIPCIONES_POR_TXT)

        print(f"📦 Procesando: {nombre_proyecto}")
        print(f"   📊 Total: {total_archivos} transcripciones -> {total_volumenes} volúmenes")

        # Tracking para manifest
        volumenes_generados = []
        archivos_omitidos = []

        # 3. Generar los volúmenes
        for i in range(total_volumenes):
            inicio = i * TRANSCRIPCIONES_POR_TXT
            fin = inicio + TRANSCRIPCIONES_POR_TXT
            lote = archivos_md[inicio:fin]

            numero_volumen = i + 1
            nombre_salida = f"{nombre_proyecto}_Vol{numero_volumen:02d}.txt"
            ruta_salida = os.path.join(ruta_export, nombre_salida)

            textos_unidos = []
            indice_volumen = []  # Para el índice al final
            archivos_incluidos = 0

            # Encabezado del Archivo para la IA
            textos_unidos.append(f"=== COLECCIÓN: {nombre_proyecto} ===\n")
            textos_unidos.append(f"=== VOLUMEN: {numero_volumen} de {total_volumenes} ===\n")
            textos_unidos.append(f"=== CONTENIDO: Transcripciones {inicio+1} a {inicio + len(lote)} ===\n\n")

            # Procesar cada archivo del lote
            for idx, archivo in enumerate(lote):
                # Indicador de progreso
                print(f"   Procesando volumen {numero_volumen}: {idx+1}/{len(lote)}...", end='\r')

                ruta_completa = os.path.join(ruta_biblioteca, archivo)
                try:
                    with open(ruta_completa, 'r', encoding='utf-8') as f:
                        contenido = f.read()

                    # Validar que es un archivo procesado por limpiar.py
                    if not validar_archivo_procesado(contenido):
                        archivos_omitidos.append(archivo)
                        continue

                    # Extraer título para el índice
                    titulo = extraer_titulo_de_contenido(contenido)
                    indice_volumen.append(f"{inicio + archivos_incluidos + 1}. {titulo}")

                    # Añadir contenido
                    textos_unidos.append(contenido)
                    archivos_incluidos += 1

                    # Agregar separador solo si NO es el último archivo
                    if idx < len(lote) - 1:
                        textos_unidos.append(SEPARADOR_TRANSCRIPCION)

                except Exception as e:
                    print(f"\n⚠️ Error leyendo {archivo}: {e}")
                    archivos_omitidos.append(archivo)

            # Agregar índice al final del volumen
            if indice_volumen:
                textos_unidos.append("\n\n" + "="*60 + "\n")
                textos_unidos.append("=== ÍNDICE DE ESTE VOLUMEN ===\n")
                textos_unidos.append("="*60 + "\n\n")
                textos_unidos.append("\n".join(indice_volumen))
                textos_unidos.append("\n")

            # Escribir archivo final
            with open(ruta_salida, 'w', encoding='utf-8') as f_out:
                f_out.write("".join(textos_unidos))

            volumenes_generados.append(nombre_salida)
            print(f"   ✅ Volumen {numero_volumen}: {archivos_incluidos} transcripciones" + " "*20)

        # Agregar al manifest
        manifest["projects"][nombre_proyecto] = {
            "total_transcripciones": total_archivos,
            "volumenes": volumenes_generados,
            "archivos_omitidos": archivos_omitidos if archivos_omitidos else None
        }

        if archivos_omitidos:
            print(f"   ⚠️  {len(archivos_omitidos)} archivos omitidos (no válidos)")

    # Guardar manifest
    manifest_path = os.path.join(ruta_export, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✨ ¡Listo! Archivos generados en: {CARPETA_EXPORTACION}/")
    print(f"📋 Manifest guardado en: {CARPETA_EXPORTACION}/manifest.json")


if __name__ == "__main__":
    # Permitir especificar directorio base como argumento
    if len(sys.argv) > 1:
        consolidar_proyectos(sys.argv[1])
    else:
        consolidar_proyectos()
