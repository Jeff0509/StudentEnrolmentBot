
from app.database import get_connection

def extract_database_metadata():
    connection = get_connection()
    cursor = connection.cursor()

    query = """
    SELECT
        s.name AS schema_name,
        t.name AS table_name,
        c.column_id,
        c.name AS column_name,
        ty.name AS data_type,
        c.max_length,
        c.is_nullable,
        CASE WHEN pk.column_id IS NOT NULL
             THEN 1 ELSE 0 END AS is_primary_key
    FROM sys.tables t
    INNER JOIN sys.schemas s
        ON t.schema_id = s.schema_id
    INNER JOIN sys.columns c
        ON t.object_id = c.object_id
    INNER JOIN sys.types ty
        ON c.user_type_id = ty.user_type_id
    LEFT JOIN (
        SELECT
            ic.object_id,
            ic.column_id
        FROM sys.indexes i
        INNER JOIN sys.index_columns ic
            ON i.object_id = ic.object_id
            AND i.index_id = ic.index_id
        WHERE i.is_primary_key = 1
    ) pk
        ON c.object_id = pk.object_id
        AND c.column_id = pk.column_id
    ORDER BY
        s.name,
        t.name,
        c.column_id;
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        metadata = {}

        for row in rows:
            table_name = f"{row[0]}.{row[1]}"

            if table_name not in metadata:
                metadata[table_name] = []

            metadata[table_name].append({
                "column": row[3],
                "data_type": row[4],
                "max_length": row[5],
                "nullable": bool(row[6]),
                "primary_key": bool(row[7])
            })

        print(f"Tables discovered: {len(metadata)}")
        print("--------------------------------")

        for table, columns in metadata.items():
            print(f"\nTABLE: {table}")

            for col in columns:
                pk = " [PK]" if col["primary_key"] else ""
                nullable = "NULL" if col["nullable"] else "NOT NULL"

                print(
                    f"  {col['column']} | "
                    f"{col['data_type']} | "
                    f"{nullable}{pk}"
                )

        return metadata

    finally:
        connection.close()


if __name__ == "__main__":
    extract_database_metadata()
