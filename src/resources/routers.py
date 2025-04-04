from src.handler.external_requests import pod_exec
from darwin_composer.DarwinComposer import RouteClass

routers = [
    RouteClass(pod_exec, ["v1"])
]