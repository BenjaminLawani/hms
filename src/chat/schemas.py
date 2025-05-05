from pydantic import BaseModel, Field
from typing import List, Dict,Any, Optional

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    context: Optional[str] = Field(None, description="Additional context for non-SQL questions")

class QueryResponse(BaseModel):
    answer: str = Field(..., description="Natural language answer to the query")
    data: List[Dict[str, Any]] = Field(default=[], description="Query results if SQL was used")
    used_sql: bool = Field(..., description="Whether SQL was used to answer the query")