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

def oc_login(url, token):
    # Crear un directorio temporal para KUBECONFIG
    kubeconfig_dir = "/tmp/.kube"
    os.makedirs(kubeconfig_dir, exist_ok=True)
    kubeconfig_path = os.path.join(kubeconfig_dir, "config")
    os.environ["KUBECONFIG"] = kubeconfig_path

    # Ejecutar el comando oc login
    command = ["oc", "login", url, "--token", token, "--insecure-skip-tls-verify=true"]
    subprocess.run(command)

def get_pods(namespace):
    command = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
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
    region = "bo2"
    url = "https://api.san01darwin.san.pro.bo2.paas.cloudcenter.corp:6443"
    namespace = "sanes-adnproductos-pro"

    # Obtener el token (si es necesario para la autenticación con el clúster de OpenShift)
    token = await fetch_token_and_print(functionalenvironment, cluster, region, url, namespace)

    # Iniciar sesión en el clúster de OpenShift en bo2
    oc_login(url, token)

    # Obtener los pods en el namespace especificado
    pods = get_pods(namespace)

    for pod in pods['items']:
        pod_name = pod['metadata']['name']
        memory_usage = get_pod_memory_usage(pod_name, namespace)
        print(f"Pod: {pod_name}, Memory Usage: {memory_usage}Mi")

        # Reiniciar los pods que consumen más de 2GB (2048Mi)
        if memory_usage > 2048:
            print(f"Restarting pod {pod_name} as it is using more than 2GB of memory.")
            delete_pod(pod_name, namespace)

if __name__ == "__main__":
    # Ejecuta la función main en un entorno asíncrono
    asyncio.run(main())