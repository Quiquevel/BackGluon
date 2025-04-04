import os, ssl, pytz, subprocess, codecs, datetime
from websocket import WebSocket
from pathlib import Path
from dateutil.relativedelta import relativedelta
from shuttlelib.utils.logger import logger
from src.services.clientunique import client

async def get_clusters():
    functional_environment=os.getenv("ENVIRONMENT")
    entity_id=os.getenv("ENTITY_ID")
 
    clusters = await client.get_resource(resource="clusters", functional_environment=functional_environment, cluster=None)
    cluster_list = []
    for cluster in clusters.keys():
        regions = list(clusters[cluster].keys())
        cluster_list.append({"name": cluster, "region": regions})
 
    return cluster_list, entity_id, functional_environment

def execute_in_pod(pod, command):
    oc_exec_command = f"oc exec {pod} -- {command}"
    
    try:
        process = subprocess.Popen(oc_exec_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        exit_code, error = process.communicate()

        if process.returncode != 0:
            logger.error(f"Error executing command: {error}")
            return []

        lines = exit_code.split('\n')
        clean_lines = [line.strip() for line in lines if line.strip()]
        return clean_lines

    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        return []

def automatic_delete():
    folder = "/app/downloads"
    try:
        subprocess.run(["find", folder, "-type", "f", "-mtime", "+30", "-exec", "rm", "{}", ";"])
        logger.info(f'Older files in {folder} succefully erased.')
    except subprocess.CalledProcessError as e:
        logger.error(f'Error executing command: {e}')

async def get_namespaces(cluster, functional_environment, region):
    global client
    namespace_list = await client.get_resource(functional_environment=functional_environment, resource="namespaces", region=region, cluster=cluster)
    if region in namespace_list:
        namespaces_names = [dic['metadata']['name'] for dic in namespace_list[region]['items']]
    else:
        logger.error(f"Region '{region}' not found in namespace list.")
        namespaces_names = []
    return namespaces_names

async def get_microservices(cluster, functional_environment, region, namespace):
    global client
    
    # Get deployments.
    deployments_list = await client.get_resource(resource="deployments", functional_environment=functional_environment, region=region, cluster=cluster, namespace=namespace)
    deployments_names = [dic['metadata']['name'] for dic in deployments_list[region]['items']]
    
    # Get deploymentconfigs.
    deploymentconfigs_list = await client.get_resource(resource="deploymentconfigs", functional_environment=functional_environment, region=region, cluster=cluster, namespace=namespace)
    deploymentconfigs_names = [dic['metadata']['name'] for dic in deploymentconfigs_list[region]['items']]
    
    # Combine the results.
    microservices_names = deployments_names + deploymentconfigs_names
    
    return microservices_names

async def get_podnames(functional_environment, cluster, region, namespace, microservices):
    global client
    pod_list = await client.get_resource(resource="pods", functional_environment=functional_environment, region=region, cluster=cluster, namespace=namespace)
    pod_names = [dic['metadata']['name'] for dic in pod_list[region]['items']]
    podsresult = list(filter(lambda x: microservices in x, pod_names))
    return podsresult

async def rename_and_move_files(namespace, pod, original_file, action):
    file_type = "HeapDump" if action in ["1", "3"] else "ThreadDump"
    #Time for renamed files.
    now: datetime = datetime.datetime.now()
    date = now.strftime("%Y%m%d_%H%M")
    
    new_file = f"{file_type}-{pod}-{date}.gz"
    downloads_dir = Path("/app/downloads")
    namespace_dir = downloads_dir / namespace
    new_file_path = namespace_dir / new_file

    if not namespace_dir.exists():
        namespace_dir.mkdir(parents=True, exist_ok=True)

    os.rename(original_file, new_file_path)
    logger.info("Renaming finished")

    move_command = ["mv", str(new_file_path), str(new_file_path)]
    subprocess.Popen(move_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Command to grant permissions
    permission_command = ["chmod", "-R", "777", "/app/downloads/"]
    subprocess.Popen(permission_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return new_file

#Identify pid´s process for JBOSS pods
async def get_my_pid(pod):
    try:
        proc = subprocess.run(["oc", "rsh", pod, "pgrep", "-f", "Djboss.modules.system.pkgs"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        pid = proc.stdout.decode('utf-8').strip()
        logger.info(f"The process ID is: {pid}")
        return pid
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: {e}")
        return None

def fromtimestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, tz=pytz.utc)

# Delete files x days older for mantainance.
def clean_old_files(directory, days=30):
    now = datetime.datetime.now()
    deleted_files = []
    for root, dirs, files in os.walk(directory):
        dirs = [dir for dir in dirs if dir]
        for file in files:
            file_path = os.path.join(root, *dirs, file)
            creation_time = fromtimestamp(os.path.getctime(file_path))
            delta = relativedelta(now, creation_time)
            if delta.days > days:
                os.remove(file_path)
                deleted_files.append(file_path)

    return deleted_files

# Connecting using WebSocket
async def websocket_connection(token, request_url):
    headers = {
        "Authorization": "Bearer " + token,
        "Connection": "upgrade",
        "Upgrade": "SPDY/4.8",
        "X-Stream-Protocol-Version": "channel.k8s.io",
        "charset": "utf-8"
    }

    ws = WebSocket.websocket(sslopt={"cert_reqs": ssl.CERT_NONE})
    ws.connect(request_url.replace("https", "wss"), header=headers)
    data = []
    while ws.connected != False:
        recv = ws.recv()
        if recv != '':
            data.append(recv)
    return ws, data

def delete_pod(pod):
    delete = subprocess.run(["oc", "delete", "pod", codecs.encode(pod, "utf-8")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if delete.returncode == 0:
        logger.info("Deleting the correct pod")
    else:
        logger.error("Pod deleting failed")
        
def oc_login(url, token, namespace):
    """Authenticate with OpenShift using `oc login`."""
    login_command = [
        "oc", "login", "--token=" + token, "--server=" + url,
        "--namespace=" + namespace, "--insecure-skip-tls-verify=true"
    ]
    login_process = subprocess.Popen(login_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, stderr = login_process.communicate()

    if login_process.returncode != 0:
        logger.error(f"Login failed. Error: {stderr.decode('utf-8')}")
        return False
    logger.info("Login succeeded")
    return True

def oc_rsync(pod, remote_file_path):
    """Sync a pod file using `oc rsync`."""
    try:
        process = subprocess.run(
            ["oc", "rsync", f"{pod}:{remote_file_path}", "."],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if process.returncode == 0:
            logger.info("RSYNC command completed successfully")
            return True
        else:
            logger.error(f"RSYNC command failed with error: {process.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"RSYNC process failed: {e.output}")
        return False

def validate_file_size(file_path, min_size_kb=1):
    """Validate that the file has a minimum size to consider it valid."""
    if os.path.exists(file_path):
        file_size_kb = os.path.getsize(file_path) / 1024  # Tamaño en KB
        logger.info(f"File {file_path} has size: {file_size_kb} KB")
        return file_size_kb > min_size_kb
    logger.error(f"File {file_path} does not exist.")
    return False