""" Get Method of HelloMoon controller route. """

from pydantic import BaseModel, Field

class MoonResponse(BaseModel):
    """
        Successful Response helloMoon
    """

    status: str = Field(json_schema_extra={"description":"status of the response",'examples': ['OK']})
    message: str = Field(json_schema_extra={"description":"The message to be returned",'examples': ['Hello There Moon']})
