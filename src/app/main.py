from fastapi import FastAPI, responses
from src.resources.routers import routers
from darwin_composer.DarwinComposer import DarwinComposer
from src.app.config.composer_config import config as composer_config

app = FastAPI(
                docs_url="/docs",
                redoc_url="/api/v1/redocs",
                title="jvmdumps",
                version="1.0",
                openapi_url="/api/v1/openapi.json",
                contact={ "name" : "SRE CoE DevSecOps","email" : "SRECoEDevSecOps@gruposantander.com"},
              )

DarwinComposer(app, config=composer_config, routers=routers)

@app.get("/")
async def docs_redirect():
   return responses.RedirectResponse(url='docs')