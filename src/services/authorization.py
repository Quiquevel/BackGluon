from fastapi import HTTPException, responses, status
from fastapi.encoders import jsonable_encoder
from src.services.clientunique import entity_id
from shuttlelib.middleware.authorization import is_authorized_user

async def authorizationtreatment(auth, ldap):            
    match entity_id:
        case "spain":
            if auth:        
                isdevops = await is_authorized_user(token=auth.credentials, uid=ldap, almteam="sanes_devops")
                if isdevops == False:            
                    isestruct = await is_authorized_user(token=auth.credentials, uid=ldap, almteam="sanes_cambios_estructurales")            
                    if isestruct == False:
                        raise HTTPException(status_code=403, detail="User not authorized")
                return responses.JSONResponse(status_code=status.HTTP_200_OK,content=jsonable_encoder({"detail": "Authorized User"}))
            else:
                raise HTTPException(status_code=400, detail="Token not exist")
        case _:
            return responses.JSONResponse(status_code=status.HTTP_200_OK,content=jsonable_encoder({"detail": "Authorized User"}))  