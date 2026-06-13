memory = []

def add_to_memory(question, sql, result, explanation):
    memory.append({
        "question": question,
        "sql": sql,
        "result": result,
        "explanation": explanation
    })

def get_memory():
    return memory[-3:]  # last 3 conversations