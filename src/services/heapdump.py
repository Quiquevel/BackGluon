import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.clientunique import client
from urllib3.exceptions import InsecureRequestWarning
from fastapi.responses import FileResponse, JSONResponse
from src.services.commonfunctions import (
    delete_pod,
    rename_and_move_files,
    get_my_pid,
    websocket_connection,
    automatic_delete,
    oc_login,
    oc_rsync,
    validate_file_size
)
from shuttlelib.utils.logger import logger
import urllib3, urllib.parse, subprocess

MEDIA_TYPE_OCTET_STREAM = "application/octet-stream"
REQUIRED_TOOLS_1 = "Required tool jstack is not available in the pod."
END_URL = '&stdin=true&stderr=true&stdout=true&tty=false'

urllib3.disable_warnings(InsecureRequestWarning)

async def generate_heapdump(url, token, namespace, pod, action, delete):
    dump_command = "jcmd 1 GC.heap_dump /opt/produban/heapdumpPRO; gzip -f heapdumpPRO"
    dump_command_encoded = urllib.parse.quote(dump_command, safe='')

    request_url = (
        f'{url}/api/v1/namespaces/{namespace}/pods/{pod}/exec?'
        f'command=/bin/bash&command=-c&command={dump_command_encoded}'
        '&stdin=true&stderr=true&stdout=true&tty=false'
    )

    ws_connect, data = await websocket_connection(token, request_url)
    print(f"Data from websocket: {data}")

    # Convertir la lista de bytes a una cadena para analizarla
    data_str = ''.join(d.decode('utf-8', errors='ignore') for d in data)

    # Verificar si hay errores relacionados con jcmd o gzip
    if "command not found" in data_str.lower() or "exit status 1" in data_str:
        ws_connect.close()
        return JSONResponse(
            content={"status": "error", "message": "Required tools jcmd and jmap are not available in the pod."},
            status_code=500
        )
    
    login_command = ["oc", "login", "--token=" + token, "--server=" + url, "--namespace=" + namespace, "--insecure-skip-tls-verify=true"]
    login_process = subprocess.Popen(login_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr = login_process.communicate()

    if login_process.returncode != 0:
        return JSONResponse(content={"status": "error", "message": "Login failed."}, status_code=500)

    try:
        process = subprocess.run(["oc", "rsync", "--delete", f"{pod}:/opt/produban/heapdumpPRO.gz", "."], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if process.returncode == 0:
            original_file = "heapdumpPRO.gz"
            new_file = await rename_and_move_files(namespace, pod, original_file, action)

            if delete:
                delete_pod(pod)
                
            return FileResponse(f"/app/downloads/{namespace}/{new_file}", media_type=MEDIA_TYPE_OCTET_STREAM, filename = new_file) 
        else:
            return JSONResponse(content={"status": "error", "message": "RSYNC command failed."}, status_code=500)

    except subprocess.CalledProcessError as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

    finally:
        ws_connect.close()
    
async def generate_threaddump(url, token, namespace, pod, action, delete):
    # Command to generate the ThreadDump
    dump_command = (
        "threaddump.d/0.start_threaddump.sh > DUMP-1 || exit 1; "
        "sleep 3; threaddump.d/0.start_threaddump.sh > DUMP-2 || exit 1; "
        "sleep 5; threaddump.d/0.start_threaddump.sh > DUMP-3 || exit 1; "
        "tar -czvf ThreadDump.gz DUMP-1 DUMP-2 DUMP-3"
    )
    dump_command_encoded = urllib.parse.quote(dump_command, safe='')

    # URL to run the command
    request_url = f'{url}/api/v1/namespaces/{namespace}/pods/{pod}/exec?'
    request_url += f'command=/bin/bash&command=-c&command={dump_command_encoded}'
    request_url += END_URL

    try:
        ws_connect, data = await websocket_connection(token, request_url)

        if data is None:
            return JSONResponse(content={"status": "error", "message": REQUIRED_TOOLS_1}, status_code=500)

        # OC Login
        login_succeeded = oc_login(url, token, namespace)
        if not login_succeeded:
            return JSONResponse(content={"status": "error", "message": "Login to OpenShift failed."}, status_code=500)

        # Synchronize the pod's ThreadDump.gz file
        rsync_succeeded = oc_rsync(pod, "/opt/produban/ThreadDump.gz")
        if rsync_succeeded:
            # Check downloaded file size
            local_file = "ThreadDump.gz"
            if validate_file_size(local_file):
                # Rename and move the file if valid
                new_file = await rename_and_move_files(namespace, pod, local_file, action)
                if delete:
                    delete_pod(pod)
                return FileResponse(f"/app/downloads/{namespace}/{new_file}", media_type=MEDIA_TYPE_OCTET_STREAM, filename=new_file)
            else:
                return JSONResponse(content={"status": "error", "message": REQUIRED_TOOLS_1}, status_code=500)
        else:
            return JSONResponse(content={"status": "error", "message": "Failed to synchronize ThreadDump file."}, status_code=500)
    
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Unexpected error occurred: {str(e)}"}, status_code=500)

    finally:
        # Close WebSocket connection
        if ws_connect:
            ws_connect.close()

async def generate_heapdump_dg(url, token, namespace, pod, action, delete):
    # Running the command on the target pod
    request_url = f'{url}/api/v1/namespaces/{namespace}/pods/{pod}/exec?'
    request_url += END_URL

    ws_connect, data = await websocket_connection(token, request_url)

    if data is None:
        return JSONResponse(content={"status": "error", "message": "Required tools jcmd and jmap are not available in the pod."}, status_code=500)

    login_command = ["oc", "login", "--token=" + token, "--server=" + url, "--namespace=" + namespace, "--insecure-skip-tls-verify=true"]
    login_process = subprocess.Popen(login_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.info(f"I'm going to try to log in at {url}, in the namespace {namespace}.")
    stderr = login_process.communicate()

    if login_process.returncode != 0:
        logger.error(f"Login failed. Error message: {stderr}")
    else:
        logger.info("Login succeeded.")

        #Copy the dump to the destination pod and download it locally.
        try:
            #Identify pid´s process for JBOSS
            pid = await get_my_pid(pod)
            
            # HeadDump generation and compression for a pod.
            exec_command = subprocess.run(["oc", "rsh", pod, "sh", "-c", "jmap -dump:format=b,file=/tmp/jvm.hprof {}; gzip -f -c /tmp/jvm.hprof > /tmp/jvm.hprof.gz".format(pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if exec_command.returncode == 0:
                logger.info("HeadDump has run fine on the pod")
                process = subprocess.run(["oc", "rsync", "{}:/tmp/jvm.hprof.gz".format(pod), "."], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if process.returncode == 0:
                    logger.info("RSYNC command completed successfully")
                    # Rename the generic pod´s name and move it to downloads´s folder.
                    original_file= "jvm.hprof.gz"
                    new_file = await rename_and_move_files(namespace, pod, original_file, action)
                    
                    if delete:
                        delete_pod(pod)
                    return FileResponse(f"/app/downloads/{namespace}/{new_file}", media_type=MEDIA_TYPE_OCTET_STREAM, filename = new_file)
                else:
                    logger.error(f"RSYNC command failed with the message: {process.stderr}")
            else:
                logger.error(f"Exec command failed with the message: {exec_command.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"{e.output}")

    #Close websocket    
    ws_connect.close()
    return data

async def generate_threaddump_dg(url, token, namespace, pod, action, delete):
    # Command to generate the ThreadDump in DataGrid
    dump_command = (
        "for i in $(seq 1 10); do jstack -l {} >> /tmp/jstack.out; sleep 2; done; "
        "gzip -f -c /tmp/jstack.out > /tmp/jstack.out.gz"
    )

    try:
        # WebSocket connection to run command on pod
        request_url = f'{url}/api/v1/namespaces/{namespace}/pods/{pod}/exec?'
        request_url += END_URL
        ws_connect, data = await websocket_connection(token, request_url)

        if data is None:
            return JSONResponse(content={"status": "error", "message": REQUIRED_TOOLS_1}, status_code=500)

        # OC Login
        login_succeeded = oc_login(url, token, namespace)
        if not login_succeeded:
            return JSONResponse(content={"status": "error", "message": "Login to OpenShift failed."}, status_code=500)

        # Get the PID of the JBOSS process
        pid = await get_my_pid(pod)

        # Run the command to generate the ThreadDump
        dump_command_with_pid = dump_command.format(pid)
        dump_command_encoded = urllib.parse.quote(dump_command_with_pid, safe='')

        exec_url = f'{url}/api/v1/namespaces/{namespace}/pods/{pod}/exec?'
        exec_url += f'command=/bin/bash&command=-c&command={dump_command_encoded}'
        exec_url += END_URL

        ws_exec, exec_data = await websocket_connection(token, exec_url)

        if exec_data is None:
            return JSONResponse(content={"status": "error", "message": "Failed to execute ThreadDump."}, status_code=500)

        # Sync jstack.out.gz file from pod
        rsync_succeeded = oc_rsync(pod, "/tmp/jstack.out.gz")
        if rsync_succeeded:
            # Check downloaded file size
            local_file = "jstack.out.gz"
            if validate_file_size(local_file):
                # Rename and move the file if valid
                new_file = await rename_and_move_files(namespace, pod, local_file, action)
                if delete:
                    delete_pod(pod)
                return FileResponse(f"/app/downloads/{namespace}/{new_file}", media_type=MEDIA_TYPE_OCTET_STREAM, filename=new_file)
            else:
                return JSONResponse(content={"status": "error", "message": "ThreadDump file is too small, probably empty."}, status_code=500)
        else:
            return JSONResponse(content={"status": "error", "message": "Failed to synchronize ThreadDump file."}, status_code=500)

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Unexpected error occurred: {str(e)}"}, status_code=500)

    finally:
        # Close WebSocket connection
        if ws_connect:
            ws_connect.close()
        if ws_exec:
            ws_exec.close()

async def getheapdump(functional_environment, cluster , region, namespace, pod, action, delete):
    url = client.clusters[functional_environment][cluster][region]["url"]
    token =  client.clusters[functional_environment][cluster][region]["token"]

    if action =="1":
        automatic_delete()
        logger.info(f"I'm going to get a HeapDump from pod {pod} from namespace {namespace}")
        logger.info(f"And for that I have the client instantiated and I have the url: {url} and my secret token")
        data_obtained = await generate_heapdump(url, token, namespace, pod[0], action,  delete)
        print("Return of heapdump function")
        return data_obtained
    elif action =="2":
        automatic_delete()
        logger.info(f"I'm going to get a HeapDump from pod {pod} from namespace {namespace}")
        logger.info(f"And for that I have the client instantiated and I have the url: {url}")
        data_obtained = await generate_threaddump(url, token, namespace, pod[0], action, delete)
        return data_obtained
    elif action =="3":
        automatic_delete()
        logger.info(f"I'm going to get a HeapDump from pod {pod} from namespace {namespace}")
        logger.info(f"And for that I have the client instantiated and I have the url: {url}")
        data_obtained = await generate_heapdump_dg(url, token, namespace, pod[0], action, delete)
        return data_obtained
    elif action =="4":
        automatic_delete()
        logger.info(f"I'm going to get a HeapDump from pod {pod} from namespace {namespace}")
        logger.info(f"And for that I have the client instantiated and I have the url: {url}")
        data_obtained = await generate_threaddump_dg(url, token, namespace, pod[0], action, delete)
        return data_obtained
    else:
        logger.error("The 'ACTION' parameter has not been set or has a invalid value")