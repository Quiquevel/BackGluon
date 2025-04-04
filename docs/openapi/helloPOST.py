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
