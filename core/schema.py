def extract_schema(connection):
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    schema = ""

    for (table,) in tables:
        cursor.execute(f"DESCRIBE {table}")
        columns = cursor.fetchall()
        col_names = [col[0] for col in columns]

        schema += f"Table {table}({', '.join(col_names)})\n"

    return schema