
from pathlib import Path
import mssql_python

from app.database import get_connection


def inspect_schema():
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            s.name AS SchemaName,
            t.name AS TableName,
            c.column_id AS ColumnOrder,
            c.name AS ColumnName,
            ty.name AS DataType,
            c.max_length AS MaxLength,
            c.is_nullable AS IsNullable,
            CASE WHEN pk.column_id IS NOT NULL
                 THEN 1 ELSE 0 END AS IsPrimaryKey
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
        ORDER BY s.name, t.name, c.column_id;
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        output = []
        current_table = None

        for row in rows:
            schema, table, order, column, datatype, length, nullable, is_pk = row
            table_name = f"{schema}.{table}"

            if table_name != current_table:
                output.append(f"\nTABLE: {table_name}")
                current_table = table_name

            pk_label = " PRIMARY KEY" if is_pk else ""
            null_label = "NULL" if nullable else "NOT NULL"

            output.append(
                f"  {column} | {datatype} | "
                f"Length: {length} | {null_label}{pk_label}"
            )

        report = "\n".join(output)

        log_folder = Path("logs")
        log_folder.mkdir(exist_ok=True)

        report_path = log_folder / "database_schema.txt"
        report_path.write_text(report, encoding="utf-8")

        print(f"Schema inspection completed.")
        print(f"Tables discovered: {len(set(row[0] + '.' + row[1] for row in rows))}")
        print(f"Report saved to: {report_path.resolve()}")

    finally:
        connection.close()


if __name__ == "__main__":
    inspect_schema()
