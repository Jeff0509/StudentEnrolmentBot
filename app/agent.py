
import json

from app.deepseek import get_client, MODEL
from app.rag import search_knowledge

from app.memory import (
    initialise_memory,
    get_history,
    save_message
)

from app.sql_tools import (
    get_sales_summary,
    get_top_selling_products,
    get_monthly_sales_summary,
    get_sales_by_stock_group
)


# -------------------------------------------------
# 1. Approved SQL tools
# -------------------------------------------------

DATE_PARAMETERS = {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "description": "Optional start date in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "description": "Optional inclusive end date in YYYY-MM-DD format."
        }
    },
    "required": []
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "Get annual sales revenue, units sold and invoice count, optionally filtered by invoice date.",
            "parameters": DATE_PARAMETERS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_selling_products",
            "description": "Get the top 10 selling products by revenue, optionally filtered by invoice date.",
            "parameters": DATE_PARAMETERS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_sales_summary",
            "description": "Get monthly sales revenue, units sold and invoice count, optionally filtered by invoice date.",
            "parameters": DATE_PARAMETERS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_by_stock_group",
            "description": "Get sales revenue, units sold and invoice count by stock group, optionally filtered by invoice date.",
            "parameters": DATE_PARAMETERS
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "get_sales_summary": get_sales_summary,
    "get_top_selling_products": get_top_selling_products,
    "get_monthly_sales_summary": get_monthly_sales_summary,
    "get_sales_by_stock_group": get_sales_by_stock_group
}


# -------------------------------------------------
# 2. Retrieve local business knowledge
# -------------------------------------------------

def retrieve_business_knowledge(question, top_k=4):

    try:
        matches = search_knowledge(
            question,
            top_k=top_k
        )

        context_parts = []

        for index, match in enumerate(matches, start=1):

            context_parts.append(
                f"""
DOCUMENT SOURCE {index}
File: {match['source']}
Location: {match['location']}

Content:
{match['text']}
"""
            )

        return "\n".join(context_parts)

    except Exception as error:

        print(f"RAG retrieval warning: {error}")
        return ""


# -------------------------------------------------
# 3. Execute approved SQL tools
# -------------------------------------------------

def execute_tool(tool_name, arguments):

    if tool_name not in AVAILABLE_FUNCTIONS:
        raise ValueError(
            f"Tool not allowed: {tool_name}"
        )

    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")

    allowed_arguments = {"start_date", "end_date"}

    if not set(arguments).issubset(allowed_arguments):
        raise ValueError("Unsupported tool arguments.")

    start_date = arguments.get("start_date")
    end_date = arguments.get("end_date")

    from datetime import date

    for field_name, value in (
        ("start_date", start_date),
        ("end_date", end_date)
    ):
        if value is not None:
            parsed_date = date.fromisoformat(value)

            if parsed_date.isoformat() != value:
                raise ValueError(
                    f"{field_name} must use YYYY-MM-DD format."
                )

    if start_date and end_date and start_date > end_date:
        raise ValueError(
            "Start date cannot be later than end date."
        )

    return AVAILABLE_FUNCTIONS[tool_name](
        start_date=start_date,
        end_date=end_date
    )

# -------------------------------------------------
# 4. Combined RAG + SQL + Memory Agent
# -------------------------------------------------


def ask_agent(
    question,
    conversation_id="demo-session",
    date_filter=None
):
    initialise_memory()

    # 1. Retrieve relevant business documents locally
    document_context = retrieve_business_knowledge(
        question,
        top_k=4
    )

    # 2. Retrieve previous conversation messages
    history = get_history(
        conversation_id,
        max_messages=10
    )

    system_prompt = f"""
You are a business intelligence assistant for
Microsoft WideWorldImporters.

Use the retrieved document context when relevant.
Use the approved SQL tools for live database figures.
You must not invent figures or claim that a query was run
unless a SQL tool actually returned the data.

Use conversation history to understand follow-up questions.
Explain business results clearly.

DOCUMENT CONTEXT:
{document_context}

DASHBOARD DATE FILTER:
{date_filter or "No dashboard date filter selected."}

If a dashboard date filter is provided, use its start_date
and end_date arguments when calling sales SQL tools.

If the user explicitly requests a different date range,
use the dates specified in the user's question instead.

If neither is provided, retrieve the full available history.
"""

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    messages.extend(history)
    messages.append({
        "role": "user",
        "content": question
    })

    client = get_client()

    # 3. Keep the actual data returned by SQL tools
    tool_results = []

    # 4. Run the DeepSeek tool-calling loop
    for _ in range(5):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            stream=False
        )

        assistant_message = response.choices[0].message

        messages.append(
            assistant_message.model_dump(exclude_none=True)
        )

        # No more tool calls: we have the final answer
        if not assistant_message.tool_calls:
            answer = assistant_message.content or ""

            save_message(
                conversation_id,
                "user",
                question
            )

            save_message(
                conversation_id,
                "assistant",
                answer
            )

            return {
                "answer": answer,
                "tool_results": tool_results
            }

        # Execute each requested SQL tool
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments

            try:
                result = execute_tool(
                    tool_name,
                    arguments
                )

                # Support either direct results or
                # the existing success/data result format.
                if (
                    isinstance(result, dict)
                    and "success" in result
                ):
                    if result["success"]:
                        data = result.get("data")
                        error = None
                    else:
                        data = None
                        error = result.get("error")
                else:
                    data = result
                    error = None

                if error is None:
                    tool_results.append({
                        "tool_name": tool_name,
                        "data": data
                    })
                    tool_content = {
                        "success": True,
                        "data": data
                    }
                else:
                    tool_content = {
                        "success": False,
                        "error": str(error)
                    }

            except Exception as error:
                tool_content = {
                    "success": False,
                    "error": str(error)
                }

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    tool_content,
                    default=str
                )
            })

    raise RuntimeError(
        "The agent reached the maximum number of tool-calling rounds."
    )

# -------------------------------------------------
# 5. Test
# -------------------------------------------------

if __name__ == "__main__":

    conversation_id = "demo-session"

    question = (
    "Can you summarize the top three products "
    "you just identified?"
    )

    print("\nWIDE WORLD IMPORTERS AI ASSISTANT")
    print("=" * 60)

    answer = ask_agent(
        question,
        conversation_id
    )

    print("\nAI ANSWER")
    print("=" * 60)

    print(answer)
