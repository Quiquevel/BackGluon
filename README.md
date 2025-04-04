# Darwin Microservice for python

## Index
<!-- TOC -->

- [Darwin Microservice for python](#darwin-microservice-for-python)
  - [Index](#index)
  - [1. Execution of the Local Microservice (non-IDE)](#1-execution-of-the-local-microservice-non-ide)
  - [2. Microservice Configuration](#2-microservice-configuration)
  - [3. Microservice dependencies](#3-microservice-dependencies)
  - [4. Darwin](#4-darwin)
    - [i. Use of Darwin components](#i-use-of-darwin-components)
      - [a) Logs](#a-logs)
      - [b) Traceability](#b-traceability)
      - [c) Endpoint exclusion of the security component](#c-endpoint-exclusion-of-the-security-component)
      - [d) Exceptions](#d-exceptions)
  - [5. Building an API Rest](#5-building-an-api-rest)
    - [i. Development and registration of controllers](#i-development-and-registration-of-controllers)
    - [ii. API versioning](#ii-api-versioning)
      - [iii. Controllers documentation and API exposure in Openapi](#iii-controllers-documentation-and-api-exposure-in-openapi)
        - [OpenAPI Documentation](#openapi-documentation)
        - [OpenAPI Specification](#openapi-specification)
  - [6. Code test](#6-code-test)
  - [7. Santander trusted certificates **IMPORTANT**](#7-santander-trusted-certificates-important)

<!-- /TOC -->

## 1. Execution of the Local Microservice (non-IDE)

The following command allows the microservice to be run locally from a shell or a CMD

````commandline
pipenv run python -m asgi
````

Once the service has been lifted it is possible to send requests via CURL:

CURL:

````commandline
curl --location --request GET 'http://127.0.0.1:8080/v1/regards/hello_world' \
--header 'x-b3-traceid: f32197c9a3cb99f7' \
--header 'app-init: app-init' \
--header 'contact-point: contact-point' \
--header 'session-id: session' \
--header 'x-clientId: cliente' \
--header 'x-santander-channel: channel' \
--header 'Authorization: Bearer [TOKEN-JWT]'
````

**Tip**: Sending a request to the microservice requires a valid Bearer [TOKEN-JWT] for some endpoints.

## 2. Microservice Configuration

The microservice configuration is carried out through kubernetes ConfigMaps. A ConfigMap is a dictionary of key-value pairs that can be used to configure the microservice. The content of the ConfigMap must be using environment variables in the microservice. The ConfigMap is referenced in the deployment.yaml file of the microservice.
For more information about ConfigMaps, please visit the [official documentation](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/#configure-all-key-value-pairs-in-a-configmap-as-container-environment-variables).

## 3. Microservice dependencies

As a dependency manager we use [Pipenv](https://pipenv-es.readthedocs.io/es/latest/).
All package dependencies must be in the locked versions and included in the Pipfile files. They must be placed under **packages** section.

Example of the file ```Pipfile```

```yml
[[source]]
name = "pypi"
url = "https://nexus.alm.europe.cloudcenter.corp/repository/pypi-public/simple"
verify_ssl = false

[packages]
fastapi-health = "~=0.4.0"
pytest = "~=8.1.1"
```

> Is not recommended to use * as version in the dependencies, because it can cause problems in the future.

## 4. Darwin

Darwin is a component that helps us to encapsulates the traceability, logging, security and error management components
in a single class to be integrated all together in FastAPI microservices.

### i. Use of Darwin components

#### a) Logs

In order to use the darwinLogging component, the darwin_logging module must be imported and the FastAPI app object passed to it following form:

````python
import logging
from fastapi import FastAPI # main.py
"""Importing Logging component"""
from darwin_logging.DarwinLogs import DarwinLogs

log = logging.getLogger("app logger")

"""Creating FastAPI application"""
app = FastAPI(title=__name__)

"""Initializing logging component"""
DarwinLogs(app) # the application object of fastapi is introduced by the component.

"""Printing logs"""
log.info("This function is amazing")
log.debug("This function is amazing")
log.error("This function is amazing")
log.info({'dict': True, 'number_test': 1})
log.debug({'dict': True, 'number_test': 1})
log.error({'dict': True, 'number_test': 1})

````

> In order to print debug traces you must to set the environment variable LOG_LEVEL to debug value

#### b) Traceability

The traceability component automatically processes the entry request heads and stores them in a form temporary while the request is active and at the end it returns them to the response heads in case of any of them it would have been amended.

For exit requests from the microservice it is necessary to use a handler which automatically grazes the heads to be propagated.

In order to make any request to exit from the microservice, the module request_handler of the following must be imported

```request_frommicro.py```

````python
from darwin_logging import make_request # request_frommicro.py

def callingOtherMicro():
  url = "http://example.com"
  headers = { "my_header": "hello_world" }

  response = make_request(method = 'GET', url = url, headers = headers) # example of GET    
  
  response = make_request(method = 'POST', json = { "data": "data" }, url = url, headers = headers) # example of POST
  
  return response
````

#### c) Endpoint exclusion of the security component

To include endpoints within the whitelist it is necessary to include the lower case name of the function or class that defines the endpoint in the micro-service configuration.
Example:

```python
import os
from fastapi import FastAPI
from src.darwin_token_validation import DarwinTokenValidation

app = FastAPI(title="FastAPI")

os.environ["DARWIN_SECURITY_WHITE_LIST"] = '["/hello_word"]' #<-- include in the configuration of the microservice the name of the operation path that defines the endpoint.

DarwinTokenValidation(app)

@app.get("/hello_world")
@app.post("/hello_world")
async def main(): #<-- Function defining the endpoint without authorization
    return {"response" : "Hello, World!",
            "method" : "GET/POST"}

```

**Note**:

If you also want to particularize at method level (GET, POST, PUT, etc.), add the method in capital letters as a key-value option as follows:

Example:

```python

os.environ["DARWIN_SECURITY_WHITE_LIST"] = "[{'path' : '/hello_world' , 'method' : 'GET'}]" #<-- Only THE GET method of the hello_world endpoint would be included.

```

#### d) Exceptions

DarwinException also provides a generic exception for the web applications that correspond to various errors.

Most common TPs:

- ***DarwinException***: The DarwinException serves as a comprehensive exception handler designed to address unclassified exceptions within our application. It encapsulates various forms of error exceptions, ensuring robust error handling and facilitating resilience, flexibility and maintainability.

The `DarwinException` accept 6 types of optional parameters:

- ***error_name*** (str): Error name appropriate for the exception to be handled. (Tip): It result to the class Exception name raised as default if no value is provided.
- ***status_code*** (str): Status code of the response to return.
- ***internal_code*** (int): Internal code chosen by the user.
- ***short_message*** (any): Brief error message.
- ***detailed_message*** (str): Detailed error message.
- ***map_extended_messaged*** (dict): Custom field in dictionary format.

In order to use the darwin exception, it is necessary to import the darwin_exception module and to launch the exception via a raise statement.

Example:

````python
from darwin_error_handler.darwin_exception import DarwinException

def requestFormatIsOk(request):
    if hasattr(request, "headers"):
        pass
    else:
        # Exception without optional parameters
        raise DarwinException() 
    if hasattr(request, "payload"):
        pass
    else:
        # Exception with optional parameters
        raise DarwinException(error_name="BadRequestDarwinException", status_code=400, internal_code=-3, short_message="Bad Request", detailed_message="The request must contain the payload attribute", map_extended_messaged={})
````

In the first case for Exception without optional parameters, we will receive the following error response:

Darwin Format

```json
{
    "appName": "PythonTest",
    "timeStamp": "2024-04-22T08:49:53.615479",
    "errorName": "DarwinException",
    "internalCode": -1,
    "shortMessage": "None",
    "detailedMessage": "None",
    "mapExtendedMessaged": {},
    "status": 500
}
```

Gluon Format

```json
{
    "errors":[{    
        "code": 500,
        "description": "None",
        "level": "error",
        "message": "2024-04-22T08:49:53.615479-PythonTest-DarwinException-None"
    }]
}
```

In the second case for Exception with optional parameters, we will receive the following error response:

Darwin Format

```json
{
    "appName": "PythonTest",
    "timeStamp": "2024-04-22T08:59:53.823352",
    "errorName": "BadRequestDarwinException",
    "internalCode": -3,
    "shortMessage": "Bad Request",
    "detailedMessage": "The request must contain the payload attribute",
    "mapExtendedMessaged": {},
    "status": 400
}
```

Gluon Format

```json
{
    "errors":[{    
        "code": 400,
        "description": "Bad Request",
        "level": "error",
        "message": "2024-04-22T08:59:53.823352-PythonTest-BadRequestDarwinException-The request must contain the payload attribute"
    }]
}
```

#### e) Composer

The previous functionalities and capabilities are collected insde the `Darwin Composer` library. The `Darwin Composer`automatically enables said functionalities, *logging*, *security*, *traceability* and *exceptions*; and also configures other capabilities such as:

- Health check endpoint
- [OpenAPI documentation](#openapi-documentation)
- [CORS](https://fastapi.tiangolo.com/tutorial/cors/) middleware
- [Routing](#i-development-and-registration-of-controllers)

The `Darwin Composer` accepts 3 required parameters:

- **app**: A FastAPI instance
- **config**: A JSON object with configuration parameters
- **routes**: A list of RoteClass objects

The **config** object has the following parameters:

| Name                   | Description                                                                   | Type    | Default value     |
|------------------------|-------------------------------------------------------------------------------| ------- | ------------------|
| version                | Version of the microservice. Should be imported from your version.py file.    | {Str}   | "0.0.0"           |
| cors.enable            | Enables/disables cors middleware.                                             | {Bool}  | True              |
| openapi.enable         | Enables/disables custom openapi documentation.                                | {Bool}  | True              |
| openapi.title          | Title of the microservice to show in docs.                                    | {Str}   | "FastAPI Restful Swagger Demo" |
| openapi.description    | Description of the microservice to show in docs.                              | {Str}   | "A Demo for the FastAPI-Restful Swagger Demo" |
| openapi.contact.name   | Name of the author/maintainer of the microservice.                            | {Str}   | "-"              |
| openapi.contact.url    | Contact information url/email.                                                | {Str}   | "-"              |
| i18n.enable            | Enables/disables i18n middleware. It will override configuration made through environment variables. | {Bool}  | False             |
| i18n.fallback          | Fallback language for internationalization.                                   | {Str}   | "en"              |

> [!WARNING]  
> For Internationalization to work, translation files must be set, Eg. `es.json`
> The default location of these files is `/etc/i18n/locales`. This location can be set through environment variables.
> Check the Darwin documentation for more information.

Here is an example of a *config* object:

```python

from version import __version__

config = {
     "version": __version__,
     "cors": {
          "enable": False
     },
     "openapi": {
          "enable": True,
          "title": "Some App",
          "description": "It does some cool stuff",
          "contact": {
               "name": "myName",
               "url": "myurl"
          }
     },
     "i18n": {
          "enable": True,
          "fallback": "en",
     }
}
```

The **RouteClass** class is also imported from `Darwin Composer`. Its use is further explained [here](#i-development-and-registration-of-controllers).

Here is an example on how to use the **DarwinComposer** class, having imported both the **config** object and the **routers** list from different files.

```python
from fastapi import FastAPI
from darwin_composer.DarwinComposer import DarwinComposer
from src.resources.routers import routers
from src.app.config.composer_config import config as composer_config

app = FastAPI()

DarwinComposer(app, config=composer_config, routers=routers)
```

## 5. Building an API Rest

To build a Rest API, the APIRouter class will be used, which allows the controllers to be grouped into routers by doing
the most modular, straightforward and simple development. In addition, the design will adhere to the structure of guidelines defined by the archetype.

### i. Development and registration of controllers

The definition of the routes that make up the controllers will be carried out within the sub-directory **resources**, grouping them together
By affinity, for example, if two controllers were created, named *HelloWorld* and *helloMoon*, it would make sense
they were grouped into a file called regards.

The following steps are required to define the controllers:

1. Import the APIRouter class from the *fastapi* library.
2. Create the router object from the APIRouter class.
3. Decorate the path operation functions defined with the router object and also specify the resource path.

Example.

```regards.py```

```python

from fastapi import APIRouter

HelloWorldRouter = APIRouter()

@HelloWorldRouter.get("/hello_world")
def get_message():
  pass

@HelloWorldRouter.post("/hello_world")
def post_message():
  pass


HelloMoonRouter = APIRouter()
```

Once the routers and path operation functions have been created, they must be registered in the *main* of the application following
the following steps:

1. Import all ofthe Router definitions in a *routers.py* file
2. Import the RouterClass from darwin_composer
3. Create a list of RouteClass with all your Router definitions. Indicate the tag section groups the routers belong. This provides enhanced readability and navigation of the API documentation.
4. Import the routers list in the *main.py* file and feed it into the composer.

Example:

```python
from .regards import HelloWorldRouter, HelloMoonRouter
from darwin_composer.DarwinComposer import RouteClass

routers = [
    RouteClass(HelloWorldRouter, ["QA", "REGARDS"]),
    RouteClass(HelloMoonRouter, ["QA", "REGARDS"])
]

```

```python
from fastapi import FastAPI
from darwin_composer.DarwinComposer import DarwinComposer
from src.resources.routers import routers
from src.app.config.composer_config import config as composer_config

app = FastAPI()

DarwinComposer(app, config=composer_config, routers=routers)
```

### ii. API versioning

It is important to maintain control of API versions in order for there to be retrocompatibility. In this way, the old versions of the API, with the new versions, are accessible. For this purpose, it is recommended that the path of the api be set as follows:

*/{version}/{api-id}/{path_to_resource}

- {version}: api version
- {api-id}: identifies the api among all those exposed in a Gateway
- {path_to_resource}: rest of the path to the api resource to invoke

#### iii. Controllers documentation and API exposure in Openapi

The microservice offers a highly efficient development experience with automatic generation of OpenAPI documentation, made possible with it integration with Pydantic and FastAPI for data validation and serialization. Describing the API documentation is facilitated by defining Pydantic class models and this will be carried out within the sub-directory **docs** . This approach ensures clarity and coherence in the API documentation.

##### OpenAPI Documentation

The microservice automatically generates detailed documentation for your API endpoints based on the defined route handlers and Pydantic models. This documentation is available in two formats:

1. **Swagger UI (Docs Path)**: It generates an interactive Swagger UI interface at `/docs`, allowing for exploration and testing of the API endpoints directly from their web browser.
2. **ReDoc (ReDoc Path)**: Additionally, It generates a clean and user-friendly ReDoc interface at `/redoc`, providing a structured view of the API documentation for better readability and navigation.

##### OpenAPI Specification

It also generates the OpenAPI schema in JSON format, which is available at `/openapi.json`.

**Example of using Pydantic models for each defined route handler.**

Python file where the specifications of the POST method of the helloWorld controller are defined

> docs/openapi/helloPOST.py

```python
""" Make the sum of two numbers. """

from pydantic import BaseModel, Field

class SumRequest(BaseModel):
    number_a: int = Field(json_schema_extra={"description":"integer number",'examples': [1]})
    number_b: int = Field(json_schema_extra={"description":"integer number",'examples': [2]})

class SumResponse(BaseModel):
    operation: str = Field(json_schema_extra={"description":"operation performed with both numbers",'examples': ['sum']})  
    number_a: int = Field(json_schema_extra={"description":"integer number",'examples': [1]})
    number_b: int = Field(json_schema_extra={"description":"integer number",'examples': [2]})
    result: int = Field(json_schema_extra={"description":"The result of the sum",'examples': [3]})

```

Importing the python file to the POST method of the helloWorld controller

```python
import logging
from fastapi import APIRouter
from docs.openapi.helloPOST import SumResponse, SumRequest

logger = logging.getLogger(__name__)

HelloWorldRouter = APIRouter()

@HelloWorldRouter.post("/v1/regards/hello_world",response_model=SumResponse)
async def sum_numbers(request:SumRequest):
    """
    POST method for the helloWorld endpoint.
    """

    logger.info("Calling to Hello World Sum Service")
    result = hello_world_sum(request.number_a, request.number_b)

    return JSONResponse(content={
                                    "operation": "sum",
                                    "number_a": request.number_a,
                                    "number_b": request.number_b,
                                    "result": result
                                }, status_code=200)

```

The result in swagger ui is as follows:

<p align="center">
<img src="./images/U.JPG" alt="U" width="800"/>
</p>

> It is very important to include the `Pydantic class models` in the `path operations / function parameters`.

## 6. Code test

To perform the unit tests defined in each microservice, whether or not they are event-based microservices,
the following command must be executed

````commandline
pipenv run python -m pytest
````

## 7. Santander trusted certificates **IMPORTANT**

The certificate is signed by the Issuing Certificate authority, and this it what guarantees the keys. Now when someone wants your public keys, you send them the certificate, they verify the signature on the certificate, and if it verifies, then they can trust your keys.

To consume some of our services we need to add ```SANTANDER_CA_CERTS.pem``` to python as a trusted certificates. We are going to explain how to add it to *Python* in your computer.

* Locate ```SANTANDER_CA_CERTS.pem``` in a directory on your computer, by example:

    ```sh
    C:\Users\x264489\SANTANDER_CA_CERTS.pem
    ```

* Add the certificate path to Python envinroment typing the following comands:

    ```sh
    $  SETX SSL_CERT_FILE "C:\Users\x264489\SANTANDER_CA_CERTS.pem"
    $  SETX REQUESTS_CA_BUNDLE "C:\Users\x264489\SANTANDER_CA_CERTS.pem"
    ```

That's all

> The Santander Docker Python image contains our Certificate, by this reason we dont have to do anything.
> This step is very important because if you dont do this you cannot consume Santander Services.
