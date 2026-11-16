
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st

from datetime import date
from app.agent import ask_agent
from app.memory import (
    create_conversation,
    get_history,
    get_recent_conversations
)


# ============================================================
# 1. STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="WideWorldImporters AI",
    page_icon="🤖",
    layout="wide"
)


# ============================================================
# 2. SESSION STATE
# ============================================================

if "conversation_id" not in st.session_state:
    conversation_id = str(uuid.uuid4())

    create_conversation(conversation_id)

    st.session_state.conversation_id = conversation_id


# ============================================================
# 3. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🤖 WWI AI Assistant")

    st.caption(
        "WideWorldImporters Business Intelligence"
    )

    st.divider()

    # New conversation
    if st.button(
        "＋ New conversation",
        use_container_width=True
    ):

        new_id = str(uuid.uuid4())

        create_conversation(new_id)

        st.session_state.conversation_id = new_id

        st.rerun()

    # Recent conversations
    st.subheader("Recent conversations")

    conversations = get_recent_conversations(
        limit=20
    )

    conversation_ids = [
        item["conversation_id"]
        for item in conversations
    ]

    current_id = st.session_state.conversation_id

    if current_id not in conversation_ids:
        conversation_ids.insert(0, current_id)

    selected_id = st.selectbox(
        "Select a conversation",
        options=conversation_ids,
        index=conversation_ids.index(current_id),
        format_func=lambda x: x[:8] + "..."
    )

    if selected_id != current_id:

        st.session_state.conversation_id = selected_id

        st.rerun()

    st.divider()

    st.subheader("📅 Sales Date Filter")

    use_date_filter = st.checkbox(
        "Apply invoice date filter",
        value=False
    )

    dashboard_date_filter = None

    if use_date_filter:

        selected_dates = st.date_input(
            "Select invoice date range",
            value=(
                date(2013, 1, 1),
                date.today()
            ),
            help="The end date is inclusive."
        )

        if len(selected_dates) == 2:

            start_date, end_date = selected_dates

            if start_date > end_date:
                st.error("Start date must be before end date.")

            else:
                dashboard_date_filter = {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }

    st.divider()

    st.caption(
        "AI powered by DeepSeek\n\n"
        "Database: SQL Server\n\n"
        "Data source: WideWorldImporters"
    )


# ============================================================
# 4. MAIN PAGE HEADER
# ============================================================

st.title("🤖 WideWorldImporters AI Assistant")

st.markdown(
    """
    Ask questions about:

    - Sales performance
    - Customers and suppliers
    - Products and stock groups
    - Revenue trends
    - Inventory
    - Business operations
    """
)

st.caption(
    f"Conversation ID: {st.session_state.conversation_id}"
)

st.divider()


# ============================================================
# 5. DISPLAY CONVERSATION HISTORY
# ============================================================

history = get_history(
    st.session_state.conversation_id,
    max_messages=100
)

for message in history:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================
# 6. CHART RENDERING FUNCTION
# ============================================================

def display_tool_results(tool_results):

    for tool_result in tool_results:

        tool_name = tool_result["tool_name"]

        data = tool_result["data"]

        if not data:
            continue

        df = pd.DataFrame(data)

        # Convert revenue to numeric
        if "TotalRevenue" in df.columns:

            df["TotalRevenue"] = pd.to_numeric(
                df["TotalRevenue"],
                errors="coerce"
            )

        st.divider()

        # ----------------------------------------------------
        # 6.1 MONTHLY SALES
        # ----------------------------------------------------

        if tool_name == "get_monthly_sales_summary":

            df["SalesMonth"] = pd.to_datetime(
                df["SalesMonth"]
            )

            df = df.sort_values(
                "SalesMonth"
            )

            st.subheader(
                "📈 Monthly Sales Dashboard"
            )

            col1, col2, col3 = st.columns(3)

            total_revenue = df["TotalRevenue"].sum()

            total_units = df["UnitsSold"].sum()

            total_invoices = df["InvoiceCount"].sum()

            col1.metric(
                "Total Revenue",
                f"${total_revenue:,.2f}"
            )

            col2.metric(
                "Units Sold",
                f"{total_units:,.0f}"
            )

            col3.metric(
                "Invoices",
                f"{total_invoices:,.0f}"
            )

            fig = px.line(
                df,
                x="SalesMonth",
                y="TotalRevenue",
                title="Monthly Revenue Trend",
                markers=True,
                labels={
                    "SalesMonth": "Month",
                    "TotalRevenue": "Revenue ($)"
                },
                hover_data={
                    "UnitsSold": True,
                    "InvoiceCount": True
                }
            )

            fig.update_yaxes(
                autorange=True,
                tickformat=",.0f"
            )

            fig.update_layout(
                hovermode="x unified",
                xaxis_title="Sales Month",
                yaxis_title="Revenue ($)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader(
                "Monthly Sales Data"
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # 6.2 ANNUAL SALES
        # ----------------------------------------------------

        elif tool_name == "get_sales_summary":

            st.subheader(
                "📊 Annual Sales Performance"
            )

            df = df.sort_values(
                "SalesYear"
            )

            fig = px.bar(
                df,
                x="SalesYear",
                y="TotalRevenue",
                title="Annual Revenue",
                labels={
                    "SalesYear": "Year",
                    "TotalRevenue": "Revenue ($)"
                },
                hover_data=[
                    "UnitsSold",
                    "InvoiceCount"
                ]
            )

            fig.update_layout(
                xaxis=dict(type="category"),
                yaxis_title="Revenue ($)",
                xaxis_title="Sales Year"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader(
                "Annual Sales Data"
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # 6.3 SALES BY STOCK GROUP
        # ----------------------------------------------------

        elif tool_name == "get_sales_by_stock_group":

            st.subheader(
                "📦 Sales by Stock Group"
            )

            df = df.sort_values(
                "TotalRevenue",
                ascending=True
            )

            fig = px.bar(
                df,
                x="TotalRevenue",
                y="StockGroupName",
                orientation="h",
                title="Revenue by Product Group",
                labels={
                    "TotalRevenue": "Revenue ($)",
                    "StockGroupName": "Stock Group"
                },
                hover_data=[
                    "UnitsSold",
                    "InvoiceCount"
                ]
            )

            fig.update_layout(
                xaxis_title="Revenue ($)",
                yaxis_title="Stock Group"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader(
                "Stock Group Data"
            )

            st.dataframe(
                df.sort_values(
                    "TotalRevenue",
                    ascending=False
                ),
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # 6.4 TOP SELLING PRODUCTS
        # ----------------------------------------------------

        elif tool_name == "get_top_selling_products":

            st.subheader(
                "🏆 Top 10 Selling Products"
            )

            df = df.sort_values(
                "TotalRevenue",
                ascending=True
            )

            fig = px.bar(
                df,
                x="TotalRevenue",
                y="StockItemName",
                orientation="h",
                title="Top Products by Revenue",
                labels={
                    "TotalRevenue": "Revenue ($)",
                    "StockItemName": "Product"
                },
                hover_data=[
                    "UnitsSold"
                ]
            )

            fig.update_layout(
                xaxis_title="Revenue ($)",
                yaxis_title="Product"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader(
                "Product Sales Data"
            )

            st.dataframe(
                df.sort_values(
                    "TotalRevenue",
                    ascending=False
                ),
                use_container_width=True,
                hide_index=True
            )

                # ----------------------------------------------------
        # 6.5 TOP CUSTOMERS
        # ----------------------------------------------------

        elif tool_name == "get_top_customers":

            st.subheader(
                "🏆 Top 10 Customers"
            )

            df = df.sort_values(
                "TotalRevenue",
                ascending=True
            )

            # Customer revenue chart
            fig = px.bar(
                df,
                x="TotalRevenue",
                y="CustomerName",
                orientation="h",
                title="Top 10 Customers by Revenue",
                labels={
                    "TotalRevenue": "Revenue ($)",
                    "CustomerName": "Customer"
                },
                hover_data=[
                    "UnitsSold",
                    "InvoiceCount"
                ]
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            # Customer KPI metrics
            total_customer_revenue = df["TotalRevenue"].sum()
            total_customer_units = df["UnitsSold"].sum()
            total_customer_invoices = df["InvoiceCount"].sum()

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Revenue - Top 10",
                f"${total_customer_revenue:,.2f}"
            )

            col2.metric(
                "Units Purchased",
                f"{total_customer_units:,.0f}"
            )

            col3.metric(
                "Invoices",
                f"{total_customer_invoices:,.0f}"
            )

            st.dataframe(
                df.sort_values(
                    "TotalRevenue",
                    ascending=False
                ),
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # 6.6 SALES BY CUSTOMER CATEGORY
        # ----------------------------------------------------

        elif tool_name == "get_sales_by_customer_category":

            st.subheader(
                "👥 Sales by Customer Category"
            )

            df = df.sort_values(
                "TotalRevenue",
                ascending=True
            )

            fig = px.bar(
                df,
                x="TotalRevenue",
                y="CustomerCategoryName",
                orientation="h",
                title="Revenue by Customer Category",
                labels={
                    "TotalRevenue": "Revenue ($)",
                    "CustomerCategoryName": "Customer Category"
                },
                hover_data=[
                    "UnitsSold",
                    "InvoiceCount",
                    "CustomerCount"
                ]
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.dataframe(
                df.sort_values(
                    "TotalRevenue",
                    ascending=False
                ),
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# 7. CHAT INPUT AND AGENT EXECUTION
# ============================================================

question = st.chat_input(
    "Ask a business question..."
)

if question:

    # Display user question
    with st.chat_message("user"):

        st.markdown(question)

    # Generate assistant response
    with st.chat_message("assistant"):

        with st.spinner(
            "Analysing your question..."
        ):

            try:

                result = ask_agent(
                    question,
                    conversation_id=st.session_state.conversation_id,
                    date_filter=dashboard_date_filter
                )

                # Display AI explanation
                st.markdown(
                    result["answer"]
                )

                # Display charts and SQL data
                display_tool_results(
                    result["tool_results"]
                )

            except Exception as error:

                st.error(
                    f"An error occurred: {error}"
                )
