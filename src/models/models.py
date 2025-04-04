"""
This module contains the data model for user accounts.
"""
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from shuttlelib.utils.logger import logger

bearer = HTTPBearer()

class HeapDumpModel(BaseModel):
    """
    HeapDumpModel represents the structure of a heap dump request in the system.

    Attributes:
        functionalenvironment (str): The functional environment where the heap dump is requested (e.g., production, staging).
        cluster (str): The name of the cluster where the heap dump is to be performed.
        region (str): The geographical region of the cluster.
        namespace (str): The namespace within the cluster where the pod resides.
        pod (list): A list of pod names targeted for the heap dump.
        action (str): The action to be performed, typically related to heap dump operations.
        ldap (str): The LDAP identifier of the user requesting the heap dump.
        delete (bool): Indicates whether the heap dump should be deleted after processing. Defaults to False.
    """
    functionalenvironment: str
    cluster: str
    region: str
    namespace: str
    pod: list
    action: str
    ldap: str
    delete: bool=False
    
class EnvList(BaseModel):
    """
    env_list is a model class that represents an environment configuration.

    Attributes:
        ldap (str): The LDAP (Lightweight Directory Access Protocol) string 
            used for identifying or connecting to a directory service.
    """
    ldap: str
    
class ClusterList(BaseModel):
    """
    Represents a cluster list model with attributes for functional environment and LDAP.

    Attributes:
        functionalenvironment (str): The functional environment associated with the cluster.
        ldap (str): The LDAP (Lightweight Directory Access Protocol) identifier for the cluster.
    """
    functionalenvironment: str
    ldap: str
    
class RegionList(BaseModel):
    """
    region_list is a data model representing the details of a region.

    Attributes:
        functionalenvironment (str): The functional environment associated with the region (e.g., production, staging).
        cluster (str): The cluster name or identifier for the region.
        ldap (str): The LDAP (Lightweight Directory Access Protocol) identifier for the region.
    """
    functionalenvironment: str
    cluster: str
    ldap: str
    
class NamespaceList(BaseModel):
    """
    Represents a namespace configuration with details about the functional environment, 
    cluster, region, and LDAP.

    Attributes:
        functionalenvironment (str): The functional environment of the namespace.
        cluster (str): The cluster associated with the namespace.
        region (str): The geographical region of the namespace.
        ldap (str): The LDAP identifier for the namespace.
    """
    functionalenvironment: str
    cluster: str
    region: str
    ldap: str
    
class MicroserviceList(BaseModel):
    """
    MicroserviceList is a data model representing the details of a microservice.

    Attributes:
        functionalenvironment (str): The functional environment where the microservice operates (e.g., development, staging, production).
        cluster (str): The name of the cluster where the microservice is deployed.
        region (str): The geographical region of the deployment.
        namespace (str): The namespace within the cluster for the microservice.
        ldap (str): The LDAP group or identifier associated with the microservice.
    """
    functionalenvironment: str
    cluster: str
    region: str
    namespace: str
    ldap: str
    
class PodList(BaseModel):
    """
    PodList is a data model representing the details of a pod in a Kubernetes environment.

    Attributes:
        functionalenvironment (str): The functional environment where the pod is deployed (e.g., development, staging, production).
        cluster (str): The name of the Kubernetes cluster where the pod resides.
        region (str): The geographical region of the cluster.
        namespace (str): The Kubernetes namespace in which the pod is located.
        microservices (str): The name of the microservice associated with the pod.
        ldap (str): The LDAP identifier associated with the pod or its owner.
    """
    functionalenvironment: str
    cluster: str
    region: str
    namespace: str
    microservices: str
    ldap: str
    
class HistDump(BaseModel):
    """
    HistDump is a data model representing historical dump information.

    Attributes:
        namespace (str): The namespace associated with the historical dump.
        ldap (str): The LDAP (Lightweight Directory Access Protocol) identifier.
    """
    namespace: str
    ldap: str
    
class DownloadDump(BaseModel):
    """
    DownloadDump is a model representing the metadata required to download a dump file.

    Attributes:
        namespace (str): The namespace where the dump file is located.
        file_name (str): The name of the dump file to be downloaded.
        ldap (str): The LDAP identifier of the user requesting the download.
    """
    namespace: str
    file_name: str
    ldap: str