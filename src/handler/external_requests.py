"""_summary_

    Raises:
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        _type_: _description_
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from src.services.commonfunctions import get_podnames, get_microservices, get_namespaces
from src.services.heapdump import getheapdump
from src.services.authorization import authorizationtreatment
from src.services.historical import get_hist_dumps, get_download_dump
from src.services.clientunique import getenvironmentsclusterslist
from src.services.heapdump_api import getheapdump_api
from src.models.models import HeapDumpModel, EnvList, ClusterList, RegionList, NamespaceList, MicroserviceList, PodList, HistDump, DownloadDump
import urllib3

bearer = HTTPBearer()
urllib3.disable_warnings()

UNAUTHORIZED_USER_ERROR = "User not authorized"
ENVIRONMENT_LIST, CLUSTER_DICT, REGION_DICT = getenvironmentsclusterslist()

pod_exec = APIRouter(tags=["v1"], prefix="/api/v1/dumps")

    
@pod_exec.post("/heapdump")
async def execute_heapdump(target: HeapDumpModel, authorization: str = Depends(bearer)):
    """
    Executes a heap dump operation on a specified pod.

    Args:
        target (heapdumpmodel): The model containing details about the functional environment, cluster, region, namespace, pod, action, and delete flag.
        authorization (str): The authorization token provided by the user.

    Raises:
        HTTPException: If the user is not authorized to perform the operation.

    Returns:
        dict: The result of the heap dump operation.
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if isdevops == False:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return await getheapdump(functional_environment=target.functionalenvironment, cluster=target.cluster, region=target.region, namespace=target.namespace, pod=target.pod, action=target.action, delete=target.delete)

@pod_exec.post("/environment_list")
async def get_environment_list(target: EnvList, authorization: str = Depends(bearer)):  
    """_summary_

    Args:
        target (env_list): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if not isdevops:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return {"environments": ENVIRONMENT_LIST}

@pod_exec.post("/cluster_list")
async def get_cluster_list(target: ClusterList, authorization: str = Depends(bearer)): 
    """_summary_

    Args:
        target (ClusterList): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if not isdevops:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    clusters = CLUSTER_DICT.get(target.functionalenvironment, [])
    return {"clusters": clusters}

@pod_exec.post("/region_list")
async def get_region_list(target: RegionList, authorization: str = Depends(bearer)):  
    """_summary_

    Args:
        target (region_list): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if not isdevops:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    regions = REGION_DICT.get(target.functionalenvironment, {}).get(target.cluster, [])
    return {"regions": regions}

@pod_exec.post("/namespace_list")
async def get_namespace_list(target: NamespaceList, authorization: str = Depends(bearer)):  
    """_summary_

    Args:
        target (namespace_list): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if isdevops == False:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return await get_namespaces(functional_environment=target.functionalenvironment, cluster=target.cluster, region=target.region)

@pod_exec.post("/microservices_list")
async def get_microservice_list(target: MicroserviceList, authorization: str = Depends(bearer)):
    """_summary_

    Args:
        target (MicroserviceList): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if isdevops == False:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return await get_microservices(functional_environment=target.functionalenvironment, cluster=target.cluster, region=target.region, namespace=target.namespace)

@pod_exec.post("/pod_list")
async def get_pod_list(target: PodList, authorization: str = Depends(bearer)):
    """_summary_

    Args:
        target (PodList): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if isdevops == False:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return await get_podnames(functional_environment=target.functionalenvironment, cluster=target.cluster, region=target.region, namespace=target.namespace, microservices=target.microservices)

@pod_exec.post("/historical_dumps")
async def recover_hist_dumps(target: HistDump, authorization: str = Depends(bearer)):
    """_summary_

    Args:
        target (HistDump): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if isdevops == False:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return await get_hist_dumps(namespace=target.namespace)

@pod_exec.post("/download_dump")
async def download_dump(target: DownloadDump, authorization: str = Depends(bearer)):
    """_summary_

    Args:
        target (DownloadDump): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if isdevops == False:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return await get_download_dump(namespace=target.namespace, file_name=target.file_name)

@pod_exec.post("/heapdump_api")
async def execute_heapdump_api(target: HeapDumpModel, authorization: str = Depends(bearer)):
    """_summary_

    Args:
        target (heapdumpmodel): _description_
        authorization (str, optional): _description_. Defaults to Depends(bearer).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    isdevops = await authorizationtreatment(auth=authorization, ldap=target.ldap)
    if isdevops == False:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_USER_ERROR)
    return await getheapdump_api(functional_environment=target.functionalenvironment, cluster=target.cluster, region=target.region, namespace=target.namespace, pod=target.pod, action=target.action, delete=target.delete)