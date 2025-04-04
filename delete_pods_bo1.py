import json, subprocess, os, asyncio
from shuttlelib.openshift.client import OpenshiftClient

entity_id = os.getenv("ENTITY_ID")
client = OpenshiftClient(entity_id=entity_id)

async def get_token(functionalenvironment, cluster, region):
    token = client.clusters[functionalenvironment][cluster][region]["token"]
    return token

async def fetch_token_and_print(functionalenvironment, cluster, region, url, namespace):
    token = await get_token(functionalenvironment, cluster, region)
    print(json.dumps({"token": token, "url": url, "namespace": namespace}))
    return token

def get_pods(namespace, token):
    command = ["kubectl", "get", "pods", "-n", namespace, "-o", "json", "--token", token]
    result = subprocess.run(command, capture_output=True, text=True)
    pods = json.loads(result.stdout)
    return pods

def get_pod_memory_usage(pod_name, namespace):
    command = ["kubectl", "top", "pod", pod_name, "-n", namespace, "--no-headers"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        memory_usage = result.stdout.split()[2]  # Third column is memory usage
        memory_usage_mb = int(memory_usage.replace('Mi', ''))
        return memory_usage_mb
    return 0

def delete_pod(pod_name, namespace):
    command = ["oc", "delete", "pod", pod_name, "-n", namespace]
    subprocess.run(command)

async def main():
    functionalenvironment = "pro"
    cluster = "prodarwin"
    region = "bo1"
    url = "https://api.san01darwin.san.pro.bo1.paas.cloudcenter.corp:6443"
    namespace = "sanes-adnproductos-pro"

    # Get token (if needed for authentication with the OpenShift cluster)
    token = await fetch_token_and_print(functionalenvironment, cluster, region, url, namespace)
    # Get pods in the specified namespace
    pods = get_pods(namespace, token)

    for pod in pods['items']:
        pod_name = pod['metadata']['name']
        memory_usage = get_pod_memory_usage(pod_name, namespace)
        print(f"Pod: {pod_name}, Memory Usage: {memory_usage}Mi")

        # Restart pods consuming more than 2GB (2048Mi)
        if memory_usage > 2048:
            print(f"Restarting pod {pod_name} as it is using more than 2GB of memory.")
            delete_pod(pod_name, namespace)

if __name__ == "__main__":
    # Ejecuta la función main en un entorno asíncrono
    asyncio.run(main())