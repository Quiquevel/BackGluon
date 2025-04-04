import os
from shuttlelib.openshift.client import OpenshiftClient

entity_id = os.getenv("ENTITY_ID", "spain")
if entity_id is None:
    raise ValueError("ENTITY_ID environment variable is not set")
client = OpenshiftClient(entity_id=entity_id)

def getenvironmentsclusterslist():
    environment_list = []
    cluster_dict = {}
    region_dict = {}

    for environment in client.clusters.keys():
        environment_list.append(environment.lower())
        clusters = list(client.clusters[environment])
        cluster_dict[environment.lower()] = sorted(set(x.lower() for x in clusters))

        for cluster in clusters:
            clusterdata = client.clusters[environment][cluster]
            regions = list(clusterdata)
            if environment.lower() not in region_dict:
                region_dict[environment.lower()] = {}
            region_dict[environment.lower()][cluster.lower()] = sorted(set(region.lower() for region in regions))

    environment_list = sorted(environment_list)
    return environment_list, cluster_dict, region_dict