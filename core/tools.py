tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "Execute a SELECT SQL query on MySQL database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string"
                    }
                },
                "required": ["query"]
            }
        }
    }
]