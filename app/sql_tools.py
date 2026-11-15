
from app.database import get_connection


def execute_readonly_query(sql):
    """
    Execute a predefined read-only SQL query.
    Return results as a list of dictionaries.
    """

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(sql)

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    finally:
        if connection:
            connection.close()


def get_sales_summary():
    """
    Annual invoiced sales summary.
    Excludes credit notes.
    """

    sql = """
        SELECT
            YEAR(i.InvoiceDate) AS SalesYear,
            SUM(il.ExtendedPrice) AS TotalRevenue,
            SUM(il.Quantity) AS UnitsSold,
            COUNT(DISTINCT i.InvoiceID) AS InvoiceCount

        FROM Sales.Invoices AS i

        INNER JOIN Sales.InvoiceLines AS il
            ON i.InvoiceID = il.InvoiceID

        WHERE i.IsCreditNote = 0

        GROUP BY YEAR(i.InvoiceDate)

        ORDER BY SalesYear;
    """

    return execute_readonly_query(sql)


def get_top_selling_products():
    """
    Return the top 10 products by invoiced sales revenue.
    Excludes credit notes.
    """

    sql = """
        SELECT TOP (10)
            si.StockItemID,
            si.StockItemName,
            SUM(il.Quantity) AS UnitsSold,
            SUM(il.ExtendedPrice) AS TotalRevenue

        FROM Sales.InvoiceLines AS il

        INNER JOIN Sales.Invoices AS i
            ON il.InvoiceID = i.InvoiceID

        INNER JOIN Warehouse.StockItems AS si
            ON il.StockItemID = si.StockItemID

        WHERE i.IsCreditNote = 0

        GROUP BY
            si.StockItemID,
            si.StockItemName

        ORDER BY TotalRevenue DESC;
    """

    return execute_readonly_query(sql)


def get_monthly_sales_summary():
    sql = """
        SELECT
            DATEFROMPARTS(
                YEAR(i.InvoiceDate),
                MONTH(i.InvoiceDate),
                1
            ) AS SalesMonth,
            SUM(il.ExtendedPrice) AS TotalRevenue,
            SUM(il.Quantity) AS UnitsSold,
            COUNT(DISTINCT i.InvoiceID) AS InvoiceCount
        FROM Sales.Invoices AS i
        INNER JOIN Sales.InvoiceLines AS il
            ON i.InvoiceID = il.InvoiceID
        WHERE i.IsCreditNote = 0
        GROUP BY
            YEAR(i.InvoiceDate),
            MONTH(i.InvoiceDate)
        ORDER BY SalesMonth;
    """

    return execute_readonly_query(sql)

def get_sales_by_stock_group():
    sql = """
        SELECT
            sg.StockGroupName,
            SUM(il.ExtendedPrice) AS TotalRevenue,
            SUM(il.Quantity) AS UnitsSold,
            COUNT(DISTINCT i.InvoiceID) AS InvoiceCount
        FROM Sales.Invoices AS i
        INNER JOIN Sales.InvoiceLines AS il
            ON i.InvoiceID = il.InvoiceID
        INNER JOIN Warehouse.StockItems AS si
            ON il.StockItemID = si.StockItemID
        INNER JOIN Warehouse.StockItemStockGroups AS sisg
            ON si.StockItemID = sisg.StockItemID
        INNER JOIN Warehouse.StockGroups AS sg
            ON sisg.StockGroupID = sg.StockGroupID
        WHERE i.IsCreditNote = 0
        GROUP BY sg.StockGroupName
        ORDER BY TotalRevenue DESC;
    """
    return execute_readonly_query(sql)

if __name__ == "__main__":

    print("\nANNUAL SALES SUMMARY")
    print("=" * 60)

    for row in get_sales_summary():
        print(row)

    print("\nTOP 10 SELLING PRODUCTS")
    print("=" * 60)

    for row in get_top_selling_products():
        print(row)

    print("\nMONTHLY SALES SUMMARY")

    for row in get_monthly_sales_summary():
        print(row)

    print("\nSALES BY STOCK GROUP")
    for row in get_sales_by_stock_group():
        print(row)