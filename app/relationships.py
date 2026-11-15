
from app.database import get_connection

def extract_foreign_keys():
    connection = get_connection()
    cursor = connection.cursor()

    query = """
    SELECT
        fk.name AS foreign_key_name,
        ps.name AS parent_schema,
        pt.name AS parent_table,
        pc.name AS parent_column,
        rs.name AS referenced_schema,
        rt.name AS referenced_table,
        rc.name AS referenced_column,
        fkc.constraint_column_id
    FROM sys.foreign_keys fk
    INNER JOIN sys.foreign_key_columns fkc
        ON fk.object_id = fkc.constraint_object_id
    INNER JOIN sys.tables pt
        ON fkc.parent_object_id = pt.object_id
    INNER JOIN sys.schemas ps
        ON pt.schema_id = ps.schema_id
    INNER JOIN sys.columns pc
        ON fkc.parent_object_id = pc.object_id
        AND fkc.parent_column_id = pc.column_id
    INNER JOIN sys.tables rt
        ON fkc.referenced_object_id = rt.object_id
    INNER JOIN sys.schemas rs
        ON rt.schema_id = rs.schema_id
    INNER JOIN sys.columns rc
        ON fkc.referenced_object_id = rc.object_id
        AND fkc.referenced_column_id = rc.column_id
    ORDER BY
        fk.name,
        fkc.constraint_column_id;
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        print("FOREIGN KEY RELATIONSHIPS")
        print("--------------------------------")

        if not rows:
            print("No declared foreign keys found.")
            return []

        relationships = []

        for row in rows:
            relationship = {
                "foreign_key": row[0],
                "parent_table": f"{row[1]}.{row[2]}",
                "parent_column": row[3],
                "referenced_table": f"{row[4]}.{row[5]}",
                "referenced_column": row[6]
            }

            relationships.append(relationship)

            print(
                f"{relationship['parent_table']}."
                f"{relationship['parent_column']}"
                f" -> "
                f"{relationship['referenced_table']}."
                f"{relationship['referenced_column']}"
                f" ({relationship['foreign_key']})"
            )

        print("--------------------------------")
        print(f"Total foreign-key columns: {len(relationships)}")

        return relationships

    finally:
        connection.close()


if __name__ == "__main__":
    extract_foreign_keys()
