
import mssql_python


# SQL Server configuration
SERVER = "Jeff10400"
DATABASE = "WideWorldImporters"


def get_connection():
    """
    Connect to local SQL Server using Windows Authentication.
    """

    connection_string = (
        f"Server={SERVER};"
        f"Database={DATABASE};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    return mssql_python.connect(connection_string)


def test_connection():
    """
    Test SQL Server connection and return server information.
    """

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                @@SERVERNAME AS ServerName,
                DB_NAME() AS DatabaseName,
                SUSER_SNAME() AS LoginName,
                GETDATE() AS ConnectionTime
        """)

        row = cursor.fetchone()

        print("SQL SERVER CONNECTION SUCCESSFUL")
        print("--------------------------------")
        print(f"Server: {row[0]}")
        print(f"Database: {row[1]}")
        print(f"Login: {row[2]}")
        print(f"Connected at: {row[3]}")

        return True

    except Exception as e:
        print("SQL SERVER CONNECTION FAILED")
        print("--------------------------------")
        print(f"Error: {e}")
        return False

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    test_connection()
