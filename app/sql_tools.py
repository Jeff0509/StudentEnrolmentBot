
from app.database import get_connection

def execute_readonly_query(sql, params=None):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        columns = [
            column[0]
            for column in cursor.description
        ]

        rows = cursor.fetchall()

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    finally:
        if connection:
            connection.close()


def build_date_filter(start_date=None, end_date=None):
    """
    Build safe parameterised date conditions.

    The end date is inclusive.
    """

    conditions = []
    params = []

    if start_date:
        conditions.append("i.InvoiceDate >= ?")
        params.append(start_date)

    if end_date:
        conditions.append(
            "i.InvoiceDate < DATEADD(day, 1, ?)"
        )
        params.append(end_date)

    if conditions:
        return " AND " + " AND ".join(conditions), params

    return "", params

def get_sales_summary(start_date=None, end_date=None):

    date_filter, params = build_date_filter(
        start_date,
        end_date
    )

    sql = f"""
        SELECT
            YEAR(i.InvoiceDate) AS SalesYear,
            SUM(il.ExtendedPrice) AS TotalRevenue,
            SUM(il.Quantity) AS UnitsSold,
            COUNT(DISTINCT i.InvoiceID) AS InvoiceCount
        FROM Sales.Invoices AS i
        INNER JOIN Sales.InvoiceLines AS il
            ON i.InvoiceID = il.InvoiceID
        WHERE i.IsCreditNote = 0
        {date_filter}
        GROUP BY YEAR(i.InvoiceDate)
        ORDER BY SalesYear;
    """

    return execute_readonly_query(sql, params)


def get_top_selling_products(start_date=None, end_date=None):

    date_filter, params = build_date_filter(
        start_date,
        end_date
    )

    sql = f"""
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
        {date_filter}
        GROUP BY
            si.StockItemID,
            si.StockItemName
        ORDER BY TotalRevenue DESC;
    """

    return execute_readonly_query(sql, params)


def get_monthly_sales_summary(start_date=None, end_date=None):

    date_filter, params = build_date_filter(
        start_date,
        end_date
    )

    sql = f"""
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
        {date_filter}
        GROUP BY
            YEAR(i.InvoiceDate),
            MONTH(i.InvoiceDate)
        ORDER BY SalesMonth;
    """

    return execute_readonly_query(sql, params)


def get_sales_by_stock_group(start_date=None, end_date=None):

    date_filter, params = build_date_filter(
        start_date,
        end_date
    )

    sql = f"""
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
        {date_filter}
        GROUP BY sg.StockGroupName
        ORDER BY TotalRevenue DESC;
    """

    return execute_readonly_query(sql, params)

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