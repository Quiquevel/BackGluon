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
        data_obtained = await generate_heapdump_api(kube_client, namespace, pod[0], action, delete)
        print("Return of heapdump function")
        return data_obtained
    else:
        logger.error("The 'ACTION' parameter has not been set or has an invalid value")
        
async def generate_heapdump_api(kube_client, namespace, pod, action, delete):
    # Primero, eliminar cualquier archivo existente
    cleanup_command = "rm -f /opt/produban/heapdumpPRO /opt/produban/heapdumpPRO.gz"
    
    try:
        stream(
            kube_client.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=["/bin/bash", "-c", cleanup_command],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        logger.info(f"Old heapdump files removed in pod {pod}")
    except Exception as e:
        logger.warning(f"Could not clean previous heapdump: {e}")

    # Luego ejecutar la generación del heapdump
    dump_command = "jcmd 1 GC.heap_dump /opt/produban/heapdumpPRO; gzip -f /opt/produban/heapdumpPRO"

    exec_command = [
        "/bin/bash",
        "-c",
        dump_command
    ]

    try:
        resp = stream(
            kube_client.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        logger.info(f"Command output: {resp}")

        if "command not found" in resp.lower() or "exit status 1" in resp:
            return JSONResponse(
                content={"status": "error", "message": "Required tools jcmd and gzip are not available in the pod."},
                status_code=500
            )

        # Descargar el archivo generado
        with open("heapdumpPRO.gz", "wb") as file:
            try:
                if isinstance(resp, str):
                    file.write(resp.encode("utf-8"))
                elif hasattr(resp, "read"):
                    file.write(resp.read())
                else:
                    raise TypeError(f"Unsupported type for `resp`: {type(resp)}")
            except Exception as e:
                logger.error(f"Error writing file: {e}")
                return JSONResponse(
                    content={"status": "error", "message": "Failed to write heapdump file."},
                    status_code=500
                )

        original_file = "heapdumpPRO.gz"
        new_file = await rename_and_move_files(namespace, pod, original_file, action)

        if delete:
            delete_pod(kube_client, namespace, pod)

        return FileResponse(
            f"/app/downloads/{namespace}/{new_file}",
            media_type=MEDIA_TYPE_OCTET_STREAM,
            filename=new_file
        )

    except Exception as e:
        logger.error(f"Error during heapdump generation: {e}")
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