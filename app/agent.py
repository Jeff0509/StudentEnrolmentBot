
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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "Get annual sales revenue, units sold and invoice count.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_selling_products",
            "description": "Get the top 10 selling products ranked by revenue.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_sales_summary",
            "description": "Get monthly sales revenue, units sold and invoice count, ordered by month.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_by_stock_group",
            "description": "Get sales revenue, units sold and invoice count grouped by product stock group.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
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
        raise ValueError(f"Unknown tool: {tool_name}")

    if arguments not in ("", "{}"):
        raise ValueError(
            f"Unexpected arguments for tool: {tool_name}"
        )

    return AVAILABLE_FUNCTIONS[tool_name]()


# -------------------------------------------------
# 4. Combined RAG + SQL + Memory Agent
# -------------------------------------------------


def ask_agent(question, conversation_id="demo-session"):
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
