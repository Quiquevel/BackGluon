"""
Module: composer_config

This module defines the configuration settings for the FastAPI application, including:
- OpenAPI documentation settings (title, description, contact information).
- CORS (Cross-Origin Resource Sharing) settings.
- Internationalization (i18n) settings.
- Application versioning.

The configuration is used by the DarwinComposer to initialize and manage the application.

Attributes:
    description (str): A detailed description of the application, including its purpose, parameters, and endpoints.
    config (dict): A dictionary containing the application's configuration settings, such as version, CORS, OpenAPI, and i18n options.

Dependencies:
    - version: Provides the application version (`__version__`).
    - global_config: Contains global configuration settings for the application.
"""

from version import __version__
from ..config import global_config

description = """
FASTAPI BASE model de pruebas

### SUMMARY
With the help of this microservice, pod stack dumps can be pulled and downloaded.
Use:
The parameters and possible values are:

  "functionalEnvironment": “dev, pre, pro”
  "cluster": "ohe (only for dev & pre), bks (only for dev & pre), probks, dmzbbks, azure, prodarwin, dmzbdarwin, confluent, proohe, dmzbohe, dmzbazure, ocp05azure”
  "region": "bo1, bo2",
  "namespace": "pod's namespace",
  "pod": ["pod's name"],
  "action": "1, 2, 3, 4"

### ENDPOINTS

* **almastatus:** Get status info of soul POD.

### PARAMETERS
* **project**: namespaces's name
* **env**: ohe (only for dev & pre), bks (only for dev & pre), probks, dmzbbks, azure, prodarwin, dmzbdarwin, confluent, proohe, dmzbohe, dmzbazure, ocp05azure
* **namespace**: Pod's namespace
* **pod**: pod's name
* **action**: Action to perform (1 - HeapDump, 2 - ThreadDump, 3 - HeapDump DataGrid, 4 - ThreadDump DataGrid)
"""

config = {
     "version": __version__,
     "cors": {
          "enable": True
     },
     "openapi": {
          "enable": True,
          "title": "JVM Dumps",
          "description": description,
          "contact": {
               "name": "Enrique Velasco",
               "url": "myurl"
          }
     },
     "i18n": {
          "enable": False,
          "fallback": "en",
     }
}
