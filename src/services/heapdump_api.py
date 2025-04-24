from fastapi.responses import FileResponse, JSONResponse
from shuttlelib.utils.logger import logger
from pathlib import Path
import os, datetime, subprocess
from kubernetes.stream import stream
from src.services.clientunique import client as shuttle_client
from kubernetes import client as k8s_client

MEDIA_TYPE_OCTET_STREAM = "application/octet-stream"

async def getheapdump_api(functional_environment, cluster, region, namespace, pod, action, delete):
    # Usar shuttle_client para obtener la URL y el token
    url = shuttle_client.clusters[functional_environment][cluster][region]["url"]
    token = shuttle_client.clusters[functional_environment][cluster][region]["token"]

    # Configurar el cliente Kubernetes usando k8s_client
    configuration = k8s_client.Configuration()
    configuration.host = url
    configuration.verify_ssl = False
    configuration.api_key = {"authorization": "Bearer " + token}
    k8s_client.Configuration.set_default(configuration)
    kube_client = k8s_client.CoreV1Api()

    if action == "1":
        automatic_delete()
        logger.info(f"I'm going to get a HeapDump from pod {pod} from namespace {namespace}")
        logger.info(f"Using Kubernetes API with url: {url}")
        data_obtained = await generate_heapdump(kube_client, namespace, pod[0], action, delete)
        print("Return of heapdump function")
        return data_obtained
    else:
        logger.error("The 'ACTION' parameter has not been set or has an invalid value")
        
async def generate_heapdump(kube_client, namespace, pod, delete):
    if delete:
        delete_pod(kube_client, namespace, pod)

    dump_command = "jcmd 1 GC.heap_dump /opt/produban/heapdumpPRO; gzip -f /opt/produban/heapdumpPRO"

    try:
        # Ejecutar el comando en el pod para generar el HeapDump
        exec_command = ["/bin/bash", "-c", dump_command]
        stream(
            kube_client.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        logger.info(f"HeapDump generado y comprimido en pod {pod}")

        # Ruta del archivo generado en el pod
        heapdump_path = "/opt/produban/heapdumpPRO.gz"

        # Verificar si el archivo existe en el pod remoto
        exec_command = ["ls", heapdump_path]
        response = stream(
            kube_client.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        if "No such file or directory" in response.read_stdout():
            logger.error(f"El archivo {heapdump_path} no existe en el pod {pod}.")
            return JSONResponse(content={"status": "error", "message": "Archivo no encontrado en el pod remoto"}, status_code=500)

        # Descargar el archivo desde el pod remoto al contenedor del microservicio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gz") as temp_file:
            temp_file_path = temp_file.name
            exec_command = ["cat", heapdump_path]
            response = stream(
                kube_client.connect_get_namespaced_pod_exec,
                pod,
                namespace,
                command=exec_command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False  # Asegúrate de que esto esté configurado correctamente
            )
            
            # Leer los datos del objeto WSClient y escribirlos en el archivo temporal
            while True:
                chunk = response.read_stdout()
                if not chunk:  # Si no hay más datos, salir del bucle
                    logger.error("No se recibieron datos del pod remoto.")
                    return JSONResponse(content={"status": "error", "message": "No se recibieron datos del pod remoto"}, status_code=500)
                temp_file.write(chunk)

        logger.info(f"HeapDump descargado desde el pod {pod} a {temp_file_path}")
    except Exception as e:
        logger.error(f"Error al generar o preparar el HeapDump para descarga: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
        
async def rename_and_move_files(namespace, pod, original_file, action):
    file_type = "HeapDump" if action in ["1", "3"] else "ThreadDump"
    # Time for renamed files.
    now = datetime.datetime.now()
    date = now.strftime("%Y%m%d_%H%M")
    
    new_file = f"{file_type}-{pod}-{date}.gz"
    downloads_dir = Path("/app/downloads")
    namespace_dir = downloads_dir / namespace
    new_file_path = namespace_dir / new_file

    if not namespace_dir.exists():
        namespace_dir.mkdir(parents=True, exist_ok=True)

    os.rename(original_file, new_file_path)
    logger.info("Renaming finished")

    # Command to grant permissions
    os.chmod(downloads_dir, 0o777)

    return new_file

def delete_pod(kube_client, namespace, pod):
    try:
        kube_client.delete_namespaced_pod(name=pod, namespace=namespace)
        logger.info("Pod successfully deleted")
    except Exception as e:
        logger.error(f"Failed to delete pod: {e}")

def automatic_delete():
    folder = "/app/downloads"
    try:
        subprocess.run(["find", folder, "-type", "f", "-mtime", "+30", "-exec", "rm", "{}", ";"])
        logger.info(f'Older files in {folder} successfully erased.')
    except subprocess.CalledProcessError as e:
        logger.error(f'Error executing command: {e}')
