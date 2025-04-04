""" Get Method of HelloWorld controller route. """

from pydantic import BaseModel, Field

class HelloResponse(BaseModel):
    """
    Successful Response helloWorld
    """

    status: str = Field(json_schema_extra={"description":"status of the response",'examples': ['OK']})
    message: str = Field(json_schema_extra={"description":"The message to be returned",'examples': ['Hello there World']})
