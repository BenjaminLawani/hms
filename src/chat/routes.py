import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
import groq
import json
from .schemas import (
    QueryRequest,
    QueryResponse
)
from src.auth.models import User
from src.common.db import engine, Base
from src.common.security import get_current_user
from src.common.config import DATABASE_URL, GROQ_API_KEY
from sqlalchemy import text, inspect

# Initialize FastAPI chat_router
chat_router = APIRouter(
    prefix="/chat",
    tags=["CHAT"]
)

# Initialize Groq client
groq_api_key = GROQ_API_KEY
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set")

groq_client = groq.Client(api_key=groq_api_key)

# Database connection parameters
DB_CONNECTION_STRING = DATABASE_URL
if not DB_CONNECTION_STRING:
    raise ValueError("DATABASE_URL environment variable not set")

# Get database schema information using SQLAlchemy
def get_db_schema() -> str:
    """Fetch database schema information including tables and columns using SQLAlchemy"""
    inspector = inspect(engine)
    schema_info = {}
    
    # Get all tables
    for table_name in inspector.get_table_names():
        schema_info[table_name] = []
        
        # Get columns for each table
        for column in inspector.get_columns(table_name):
            schema_info[table_name].append({
                "column_name": column["name"],
                "data_type": str(column["type"]),
                "is_nullable": "YES" if column.get("nullable", True) else "NO",
                "default": str(column.get("default", ""))
            })
            
        # Get primary key constraints
        primary_keys = inspector.get_pk_constraint(table_name)
        if primary_keys and primary_keys.get("constrained_columns"):
            schema_info[table_name].append({
                "constraint_type": "PRIMARY KEY",
                "columns": primary_keys["constrained_columns"]
            })
            
        # Get foreign key constraints
        foreign_keys = inspector.get_foreign_keys(table_name)
        for fk in foreign_keys:
            schema_info[table_name].append({
                "constraint_type": "FOREIGN KEY",
                "columns": fk["constrained_columns"],
                "referred_table": fk["referred_table"],
                "referred_columns": fk["referred_columns"]
            })
    
    return json.dumps(schema_info, indent=2)

# Determine if a query can be answered with SQL
def can_answer_with_sql(query: str, schema_info: str) -> bool:
    """Determine if a query can be answered with SQL using the available schema"""
    
    # Ask Groq to determine if the query can be answered with SQL
    assessment_prompt = f"""
You are an expert at understanding database capabilities.
Given a user query and database schema, determine if the query can be answered using SQL.

DATABASE SCHEMA:
{schema_info}

USER QUERY:
{query}

First, think about what data would be needed to answer this query.
Then, check if this data would be available in the database schema provided.

Respond with ONLY "YES" if the query can be answered with SQL using the given schema.
Respond with ONLY "NO" if the query cannot be answered with SQL using the given schema.
"""

    assessment_response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": assessment_prompt}],
        model="llama3-70b-8192",
        temperature=0.1,
        max_tokens=10
    )

    # Extract assessment
    assessment = assessment_response.choices[0].message.content.strip().upper()
    return assessment == "YES"

# Process SQL answerable queries
def process_sql_query(query: str, schema_info: str) -> dict:
    """Generate SQL from natural language, execute it, and generate a response"""
    
    # Step 1: Generate SQL using Groq
    sql_prompt = f"""
You are an expert SQL assistant that converts natural language queries to PostgreSQL queries.
Based on the following database schema and user query, generate a valid PostgreSQL query.
Keeping user security as a priority so passwords should not be included in answers

DATABASE SCHEMA:
{schema_info}

USER QUERY:
{query}

Respond with ONLY the SQL query with no explanation or commentary.
The SQL should be correct PostgreSQL syntax and appropriate for the schema provided.
"""

    sql_response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": sql_prompt}],
        model="llama3-70b-8192",
        temperature=0.1,
        max_tokens=1024
    )

    # Extract SQL query
    sql_query = sql_response.choices[0].message.content.strip()
    
    # Step 2: Execute the SQL query using SQLAlchemy
    try:
        with engine.connect() as connection:
            # Execute the query
            result = connection.execute(text(sql_query))
            
            # Convert results to dictionaries
            if result.returns_rows:
                column_names = result.keys()
                results = [dict(zip(column_names, row)) for row in result.fetchall()]
            else:
                results = []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Step 3: Generate natural language answer using Groq
    answer_prompt = f"""
You are an expert data analyst that explains SQL query results in natural language.

USER QUERY:
{query}

SQL QUERY EXECUTED:
{sql_query}

QUERY RESULTS:
{json.dumps(results, default=str, indent=2)}

Respond with a natural language answer to the user's original question based on these results.
Be direct and concise. Don't mention the SQL or that you ran a query.
Just answer the question naturally as if you're having a conversation.
"""

    answer_response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": answer_prompt}],
        model="llama3-70b-8192",
        temperature=0.3,
        max_tokens=1024
    )

    # Extract answer
    answer = answer_response.choices[0].message.content.strip()
    
    # Convert any non-serializable objects in results to strings
    serializable_results = []
    for row in results:
        serializable_row = {}
        for key, value in row.items():
            # Handle non-serializable types like Decimal, Date, etc.
            if not isinstance(value, (str, int, float, bool, type(None), list, dict)):
                serializable_row[key] = str(value)
            else:
                serializable_row[key] = value
        serializable_results.append(serializable_row)
    
    return {
        "answer": answer,
        "data": serializable_results,
        "used_sql": True
    }

# Process non-SQL answerable queries
def process_non_sql_query(query: str, context: Optional[str] = None) -> dict:
    """Generate a response for queries that can't be answered with SQL"""
    
    # Build prompt with context if provided
    context_info = f"\nADDITIONAL CONTEXT:\n{context}" if context else ""
    
    non_sql_prompt = f"""
You are an intelligent assistant that answers questions that cannot be directly answered using SQL database queries.

USER QUERY:
{query}{context_info}

Respond with a natural language answer to the user's question. Be direct, helpful, and informative.
If you truly cannot answer the question with the information provided, explain what information would be needed.
Your context is a student management system so keep answers within that scope. 
If a question is vague or out of scope, be polite in telling them off.
"""

    # Get response from Groq
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": non_sql_prompt}],
        model="llama3-70b-8192",
        temperature=0.5,
        max_tokens=1024
    )

    # Extract answer
    answer = response.choices[0].message.content.strip()
    
    return {
        "answer": answer,
        "data": [],
        "used_sql": False
    }

# Main function to process all types of queries
def process_query(query: str, context: Optional[str] = None) -> dict:
    """Process a query, determining whether to use SQL or not"""
    # Get schema info
    schema_info = get_db_schema()
    
    # Determine if query can be answered with SQL
    use_sql = can_answer_with_sql(query, schema_info)
    
    if use_sql:
        return process_sql_query(query, schema_info)
    else:
        return process_non_sql_query(query, context)

# Single API route for all queries
@chat_router.post("/query", response_model=QueryResponse)
def query_handler(request: QueryRequest,
                  current_user: User = Depends(get_current_user)):
    """Process any type of query and return appropriate response"""
    result = process_query(request.query, request.context)
    return QueryResponse(**result)
