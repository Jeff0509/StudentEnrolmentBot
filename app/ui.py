
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st

from app.agent import ask_agent
from app.memory import (
    create_conversation,
    get_history,
    get_recent_conversations
)
from app.sql_tools import (
    get_monthly_sales_summary,
    get_top_selling_products
)


st.set_page_config(
    page_title="Wide World Importers AI",
    page_icon="🤖",
    layout="wide"
)


# --------------------------------------------------
# Dashboard data
# --------------------------------------------------

@st.cache_data(ttl=300)
def load_monthly_sales():
    return get_monthly_sales_summary()


@st.cache_data(ttl=300)
def load_top_products():
    return get_top_selling_products()


# --------------------------------------------------
# Conversation initialisation
# --------------------------------------------------

if "conversation_id" not in st.session_state:
    conversation_id = str(uuid.uuid4())
    create_conversation(conversation_id)
    st.session_state.conversation_id = conversation_id


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.title("WWI AI Assistant")

    st.caption("WideWorldImporters Business Intelligence")

    st.divider()

    if st.button(
        "＋ New conversation",
        use_container_width=True
    ):
        new_id = str(uuid.uuid4())
        create_conversation(new_id)

        st.session_state.conversation_id = new_id
        st.rerun()

    st.subheader("Recent conversations")

    conversations = get_recent_conversations(limit=20)

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

    st.caption(
        "AI powered by DeepSeek\n\n"
        "Database: SQL Server\n\n"
        "Sample data: WideWorldImporters"
    )


# --------------------------------------------------
# Main page
# --------------------------------------------------

st.title("🤖 WideWorldImporters AI Assistant")

st.markdown(
    "Business intelligence dashboard and AI data assistant."
)

dashboard_tab, chat_tab = st.tabs([
    "📊 Dashboard",
    "💬 AI Chat"
])


# ==================================================
# DASHBOARD TAB
# ==================================================

with dashboard_tab:

    st.header("Sales Performance")

    st.caption(
        "Data retrieved directly from SQL Server. "
        "Dashboard data is cached for 5 minutes."
    )

    try:

        monthly_data = load_monthly_sales()
        product_data = load_top_products()

        monthly_df = pd.DataFrame(monthly_data)
        products_df = pd.DataFrame(product_data)

        if monthly_df.empty:
            st.warning("No monthly sales data was returned.")
        else:

            monthly_df["TotalRevenue"] = pd.to_numeric(
                monthly_df["TotalRevenue"]
            )

            monthly_df["UnitsSold"] = pd.to_numeric(
                monthly_df["UnitsSold"]
            )

            monthly_df["InvoiceCount"] = pd.to_numeric(
                monthly_df["InvoiceCount"]
            )

            total_revenue = monthly_df["TotalRevenue"].sum()
            total_units = monthly_df["UnitsSold"].sum()
            total_invoices = monthly_df["InvoiceCount"].sum()

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Total Invoiced Revenue",
                f"${total_revenue:,.2f}"
            )

            col2.metric(
                "Units Sold",
                f"{total_units:,.0f}"
            )

            col3.metric(
                "Invoice Count",
                f"{total_invoices:,.0f}"
            )

            st.divider()

            st.subheader("Monthly Sales Trend")

            monthly_chart = px.line(
                monthly_df,
                x="SalesMonth",
                y="TotalRevenue",
                markers=True,
                title="Monthly Invoiced Revenue"
            )

            monthly_chart.update_layout(
                xaxis_title="Month",
                yaxis_title="Revenue",
                hovermode="x unified"
            )

            st.plotly_chart(
                monthly_chart,
                use_container_width=True
            )

        st.divider()

        st.subheader("Top 10 Products by Revenue")

        if products_df.empty:
            st.warning("No product data was returned.")
        else:

            products_df["TotalRevenue"] = pd.to_numeric(
                products_df["TotalRevenue"]
            )

            products_df["UnitsSold"] = pd.to_numeric(
                products_df["UnitsSold"]
            )

            product_chart = px.bar(
                products_df.sort_values("TotalRevenue"),
                x="TotalRevenue",
                y="StockItemName",
                orientation="h",
                title="Top 10 Products by Invoiced Revenue"
            )

            product_chart.update_layout(
                xaxis_title="Revenue",
                yaxis_title="Product",
                showlegend=False
            )

            st.plotly_chart(
                product_chart,
                use_container_width=True
            )

            st.subheader("Product Details")

            st.dataframe(
                products_df,
                use_container_width=True,
                hide_index=True
            )

    except Exception as error:

        st.error(
            f"Unable to load dashboard data: {error}"
        )


# ==================================================
# AI CHAT TAB
# ==================================================

with chat_tab:

    st.subheader("Ask your business data assistant")

    st.caption(
        "Ask questions about sales, customers, "
        "products, suppliers and inventory."
    )

    st.caption(
        f"Conversation ID: "
        f"{st.session_state.conversation_id}"
    )

    history = get_history(
        st.session_state.conversation_id,
        max_messages=100
    )

    for message in history:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "Ask a business question..."
    )

    if question:

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner("Analysing your question..."):

                try:

                    answer = ask_agent(
                        question,
                        conversation_id=(
                            st.session_state.conversation_id
                        )
                    )

                    st.markdown(answer)

                except Exception as error:

                    st.error(
                        f"An error occurred: {error}"
                    )
