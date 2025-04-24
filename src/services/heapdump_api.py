from fastapi.responses import JSONResponse
from shuttlelib.utils.logger import logger
from pathlib import Path
from kubernetes import client as k8s_client
from kubernetes import config
from kubernetes.client.exceptions import ApiException
from src.services.clientunique import client as shuttle_client
from kubernetes.stream import stream
import logging, subprocess, tempfile, os, asyncio, functools

media_type_app = "application/octet-stream"

logger = logging.getLogger(__name__)

async def getheapdump_api(functional_environment, cluster, region, namespace, pod, action, delete):
    url = shuttle_client.clusters[functional_environment][cluster][region]["url"]
    token = shuttle_client.clusters[functional_environment][cluster][region]["token"]

    # Configuración del cliente de Kubernetes
    configuration = k8s_client.Configuration()
    configuration.host = url
    configuration.verify_ssl = False
    configuration.api_key = {"authorization": "Bearer " + token}
    k8s_client.Configuration.set_default(configuration)
    kube_client = k8s_client.CoreV1Api()

    if action == "1":
        #automatic_delete()
        logger.info(f"Obteniendo HeapDump del pod {pod} en el namespace {namespace}")
        logger.info(f"Usando la API de Kubernetes con URL: {url}")
        return await generate_heapdump(kube_client, namespace, pod[0], delete)
    else:
        logger.error("El parámetro 'ACTION' no está configurado o tiene un valor inválido")
        return JSONResponse(content={"status": "error", "message": "Acción inválida"}, status_code=400)

# --- Helper para ejecutar stream en un executor usando functools.partial ---
async def _run_stream_exec_partial(func_to_run, *args, **kwargs):
    """
    Ejecuta una función bloqueante (como stream) con sus args/kwargs
    en un executor usando functools.partial.
    """
    loop = asyncio.get_running_loop()
    # Crea una función parcial que incluye la función original y todos sus argumentos
    # Esta función parcial ya no necesita argumentos cuando se llame.
    partial_func = functools.partial(func_to_run, *args, **kwargs)
    # Ejecuta la función parcial en el executor
    return await loop.run_in_executor(None, partial_func)

async def generate_heapdump(core_v1_api: k8s_client.CoreV1Api, namespace: str, pod: str, delete: bool):
    """
    Genera un heap dump en un pod remoto, lo comprime y lo copia al pod local.
    """
    # (Lógica de delete_pod si aplica)
    # if delete: ...

    dump_command = "jcmd 1 GC.heap_dump /opt/produban/heapdumpPRO && gzip -f /opt/produban/heapdumpPRO"
    heapdump_path_remote = "/opt/produban/heapdumpPRO.gz"
    local_temp_file_path = None

    try:
        # --- 1. Ejecutar generación y compresión ---
        logger.info(f"Ejecutando comando de dump en {pod}: {dump_command}")
        exec_command_dump = ["/bin/bash", "-c", dump_command]

        # Llama al helper pasando 'stream' y TODOS sus argumentos/kwargs
        # El helper usará partial para empaquetarlos para run_in_executor
        ws_client_dump = await _run_stream_exec_partial(
            stream,  # La función a ejecutar en el executor
            # --- Argumentos para 'stream' ---
            core_v1_api.connect_get_namespaced_pod_exec, # 1er arg posicional para stream
            pod,                                         # 2do arg posicional para stream
            namespace,                                   # 3er arg posicional para stream
            # **kwargs para 'stream'
            command=exec_command_dump,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False
            # --- Fin de argumentos para 'stream' ---
        )

        # --- Esperar a que el comando termine y verificar errores ---
        # (El bucle while ws_client_dump.is_open(): ... permanece igual)
        dump_stdout = ""
        dump_stderr = ""
        while ws_client_dump.is_open():
            ws_client_dump.update(timeout=1)
            if ws_client_dump.peek_stdout():
                dump_stdout += ws_client_dump.read_stdout()
            if ws_client_dump.peek_stderr():
                dump_stderr += ws_client_dump.read_stderr()
            if not ws_client_dump.peek_stdout() and not ws_client_dump.peek_stderr():
                 await asyncio.sleep(0.5)
                 if not ws_client_dump.peek_stdout() and not ws_client_dump.peek_stderr():
                     break
        ws_client_dump.close()

        if dump_stderr:
            logger.error(f"Error durante la generación/compresión del dump en {pod}. Stderr: {dump_stderr}")
            if "command not found" in dump_stderr or "Error" in dump_stderr or "failed" in dump_stderr:
                 return JSONResponse(content={"status": "error", "message": f"Fallo al generar/comprimir heapdump: {dump_stderr}"}, status_code=500)
            else:
                 logger.warning(f"Mensajes en Stderr durante dump (podría ser no fatal): {dump_stderr}")
        logger.info(f"Comando de dump completado en {pod}.")


        # --- 2. Copiar el archivo (Leer de remoto -> Escribir localmente) ---
        logger.info(f"Iniciando copia de {heapdump_path_remote} desde {pod}...")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".gz", mode='wb') as temp_file:
            local_temp_file_path = temp_file.name
            logger.info(f"Fichero temporal local creado: {local_temp_file_path}")

            exec_command_cat = ["cat", heapdump_path_remote]
            # Llama al helper de nuevo para el comando 'cat'
            ws_client_cat = await _run_stream_exec_partial(
                stream, # La función a ejecutar en el executor
                # --- Argumentos para 'stream' ---
                core_v1_api.connect_get_namespaced_pod_exec, # 1er arg
                pod,                                         # 2do arg
                namespace,                                   # 3er arg
                # **kwargs para 'stream'
                command=exec_command_cat,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False # MUY IMPORTANTE
                # --- Fin de argumentos para 'stream' ---
            )

            # (El bucle while ws_client_cat.is_open(): ... para leer/escribir permanece igual)
            bytes_recibidos = 0
            cat_stderr = ""
            try:
                while ws_client_cat.is_open():
                    ws_client_cat.update(timeout=5)

                    # Revisar Stderr primero
                    if ws_client_cat.peek_stderr():
                        error_chunk_bytes = ws_client_cat.read_stderr() # Leemos bytes
                        # Logueamos el tipo por si acaso, aunque esperamos bytes
                        # logger.debug(f"stderr chunk type: {type(error_chunk_bytes)}")
                        cat_stderr += error_chunk_bytes.decode('utf-8', errors='replace') # Decodificamos para texto
                        if "No such file or directory" in cat_stderr:
                            logger.error(f"Error en 'cat': Fichero {heapdump_path_remote} no encontrado en {pod}. Stderr: {cat_stderr}")
                            break

                    # Revisar Stdout
                    if ws_client_cat.peek_stdout():
                        stdout_chunk = ws_client_cat.read_stdout() # Leemos el chunk

                        # --- VERIFICACIÓN CRÍTICA ---
                        if stdout_chunk: # Asegurarse de que no sea None o vacío
                            logger.debug(f"Received stdout chunk type: {type(stdout_chunk)}, length: {len(stdout_chunk)}")

                            if isinstance(stdout_chunk, bytes):
                                # --- CASO CORRECTO ---
                                temp_file.write(stdout_chunk) # Escribir bytes directamente
                                bytes_recibidos += len(stdout_chunk)
                            elif isinstance(stdout_chunk, str):
                                # --- CASO INCORRECTO E INESPERADO ---
                                logger.error("¡ERROR FATAL: Se recibió 'str' desde stdout stream cuando se esperaban 'bytes'!")
                                logger.error(f"Contenido (parcial): {stdout_chunk[:200]}") # Loguea parte para diagnóstico
                                # No podemos continuar porque escribir str corrompería el fichero binario .gz
                                raise TypeError("Flujo de datos binarios corrupto: se recibió str en lugar de bytes desde stdout.")
                            else:
                                # Tipo inesperado
                                logger.error(f"Tipo de dato inesperado recibido desde stdout: {type(stdout_chunk)}")
                                raise TypeError(f"Tipo de dato inesperado desde stdout: {type(stdout_chunk)}")
                        # else: logger.debug("read_stdout devolvió chunk vacío o None")

                    # Condición de salida (sin cambios)
                    if not ws_client_cat.peek_stdout() and not ws_client_cat.peek_stderr():
                        await asyncio.sleep(0.5)
                        if not ws_client_cat.peek_stdout() and not ws_client_cat.peek_stderr():
                            logger.info("No hay más datos en stdout/stderr, finalizando lectura.")
                            break
            finally:
                # Código de cierre/flush/fsync (sin cambios)
                ws_client_cat.close()
                temp_file.flush()
                os.fsync(temp_file.fileno())

            # (Resto de verificaciones post-copia sin cambios)
            logger.info(f"Copia finalizada. Total bytes recibidos: {bytes_recibidos}")
            # ... (verificación de cat_stderr, bytes_recibidos) ...

    # (Bloques except permanecen igual)
    except ApiException as e:
        logger.exception(f"Error de API de Kubernetes durante el proceso para pod {pod}: {e}")
        if local_temp_file_path and os.path.exists(local_temp_file_path):
            try: os.remove(local_temp_file_path)
            except OSError: pass
        return JSONResponse(content={"status": "error", "message": f"Error API K8s: {e.reason}"}, status_code=e.status)
    except Exception as e:
        # Importante: Loguear la excepción completa con logger.exception
        logger.exception(f"Error inesperado durante el proceso para pod {pod}: {e}")
        if local_temp_file_path and os.path.exists(local_temp_file_path):
            try: os.remove(local_temp_file_path)
            except OSError: pass
        # Devuelve el mensaje de error real en la respuesta para depuración
        return JSONResponse(content={"status": "error", "message": f"Error inesperado: {str(e)}"}, status_code=500)


def delete_pod(kube_client, namespace, pod):
    """Elimina un pod usando la API de Kubernetes."""
    try:
        kube_client.delete_namespaced_pod(name=pod, namespace=namespace)
        logger.info("Pod eliminado exitosamente")
    except Exception as e:
        logger.error(f"Error al eliminar el pod: {e}")

def automatic_delete():
    """Elimina archivos antiguos en la carpeta de descargas."""
    folder = Path("/opt/produban/downloads")
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Carpeta {folder} creada.")
    try:
        subprocess.run(["find", str(folder), "-type", "f", "-mtime", "+30", "-exec", "rm", "{}", ";"])
        logger.info(f"Archivos antiguos en {folder} eliminados exitosamente.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al eliminar archivos: {e}")
