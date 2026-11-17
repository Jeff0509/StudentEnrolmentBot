
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
    get_sales_by_stock_group,
    get_top_customers,
    get_sales_by_customer_category,
    get_sales_comparison
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

COMPARISON_DATE_PARAMETERS = {
    "type": "object",
    "properties": {
        "current_start_date": {
            "type": "string",
            "description": "Start date of the current period, YYYY-MM-DD."
        },
        "current_end_date": {
            "type": "string",
            "description": "Inclusive end date of the current period, YYYY-MM-DD."
        },
        "comparison_start_date": {
            "type": "string",
            "description": "Start date of the comparison period, YYYY-MM-DD."
        },
        "comparison_end_date": {
            "type": "string",
            "description": "Inclusive end date of the comparison period, YYYY-MM-DD."
        }
    },
    "required": [
        "current_start_date",
        "current_end_date",
        "comparison_start_date",
        "comparison_end_date"
    ],
    "additionalProperties": False
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_customers",
            "description": "Get the top 10 customers by revenue, optionally filtered by invoice date.",
            "parameters": DATE_PARAMETERS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_by_customer_category",
            "description": "Get sales revenue, units sold and invoice count by customer category, optionally filtered by invoice date.",
            "parameters": DATE_PARAMETERS
        }
    },
    {
    "type": "function",
    "function": {
        "name": "get_sales_comparison",
        "description": (
            "Compare sales between two date periods. "
            "Returns revenue, units sold, invoice count, "
            "absolute differences and percentage changes. "
            "Use this tool when the user asks to compare "
            "sales between years, months or other date ranges."
        ),
        "parameters": COMPARISON_DATE_PARAMETERS
    }
},
]

AVAILABLE_FUNCTIONS = {
    "get_sales_summary": get_sales_summary,
    "get_top_selling_products": get_top_selling_products,
    "get_monthly_sales_summary": get_monthly_sales_summary,
    "get_sales_by_stock_group": get_sales_by_stock_group,
    "get_top_customers": get_top_customers,
    "get_sales_by_customer_category": get_sales_by_customer_category,
    "get_sales_comparison": get_sales_comparison
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

from datetime import date

def execute_tool(tool_name, arguments):
    """
    Execute an approved SQL tool with validated date parameters.
    """

    if tool_name not in AVAILABLE_FUNCTIONS:
        raise ValueError(f"Unknown tool: {tool_name}")

    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")

    if tool_name == "get_sales_comparison":
        allowed_arguments = {
            "current_start_date",
            "current_end_date",
            "comparison_start_date",
            "comparison_end_date"
        }

        required_arguments = allowed_arguments

    else:
        allowed_arguments = {"start_date", "end_date"}
        required_arguments = set()

    unexpected = set(arguments) - allowed_arguments

    if unexpected:
        raise ValueError(
            f"Unexpected arguments: {unexpected}"
        )

    missing = required_arguments - set(arguments)

    if missing:
        raise ValueError(
            f"Missing required arguments: {missing}"
        )

    # Validate all supplied dates.
    for key, value in arguments.items():

        if not isinstance(value, str):
            raise ValueError(
                f"{key} must be a date string in YYYY-MM-DD format."
            )

        try:
            parsed_date = date.fromisoformat(value)

            if parsed_date.isoformat() != value:
                raise ValueError()

        except ValueError:
            raise ValueError(
                f"Invalid date for {key}: {value}. "
                "Expected YYYY-MM-DD."
            )

    # Validate the date range.
    if tool_name == "get_sales_comparison":

        if arguments["current_start_date"] > arguments["current_end_date"]:
            raise ValueError(
                "Current period start date must not be after end date."
            )

        if arguments["comparison_start_date"] > arguments["comparison_end_date"]:
            raise ValueError(
                "Comparison period start date must not be after end date."
            )

    else:

        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise ValueError(
                "Start date must not be after end date."
            )

    function = AVAILABLE_FUNCTIONS[tool_name]

    return function(**arguments)


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

SALES COMPARISON INSTRUCTIONS:

When the user asks to compare sales between two periods,
use the get_sales_comparison tool.

For example:
- Compare sales in 2025 against 2024.
- Compare this quarter with the previous quarter.
- Compare January 2025 with January 2024.

You must provide all four date parameters:
current_start_date,
current_end_date,
comparison_start_date,
comparison_end_date.

Use inclusive end dates.

Do not calculate sales differences or percentage changes yourself.
Use the results returned by the SQL tool.

Clearly explain:
- Revenue difference and percentage change.
- Units sold difference and percentage change.
- Invoice count difference and percentage change.

Never invent figures.

SALES CHANGE INVESTIGATION:

When the user asks why sales increased or decreased,
investigate the underlying sales data using approved SQL tools.

If a previous sales comparison exists in the conversation,
reuse its exact current and comparison date ranges.

Otherwise, determine the two periods from the user's question.
If the periods are unclear, ask the user to clarify.

For a sales change investigation:

1. Call get_sales_comparison to establish the overall change,
   if the comparison results are not already available.

2. Call get_top_customers for the current period.

3. Call get_top_customers for the comparison period.

4. Call get_sales_by_stock_group for the current period.

5. Call get_sales_by_stock_group for the comparison period.

Use the same date ranges consistently across all five analyses.

Compare customer and stock group revenue between the two periods.

Identify:
- Customers with the largest revenue increases.
- Customers with the largest revenue decreases.
- Stock groups with the largest revenue increases.
- Stock groups with the largest revenue decreases.

Explain which customers and stock groups contributed most
to the overall sales change.

Important:
- Use actual SQL results, not assumptions.
- Do not claim causation without supporting evidence.
- Do not assume that the top 10 customers represent all sales.
- Explain when the available data is insufficient.
- Clearly distinguish observations from possible explanations.
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
