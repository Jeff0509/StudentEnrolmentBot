
import os
import json

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("DEEPSEEK_API_KEY")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")


def get_client():
    if not API_KEY:
        raise ValueError(
            "DEEPSEEK_API_KEY is missing. "
            "Please check your .env file."
        )

    return OpenAI(
        api_key=API_KEY,
        base_url="https://api.deepseek.com"
    )


def ask_deepseek(question, catalogue=None):

    client = get_client()

    if catalogue is None:
        catalogue_file = PROJECT_ROOT / "database_catalogue.json"

        if not catalogue_file.exists():
            raise FileNotFoundError(
                "database_catalogue.json not found. "
                "Run: python -m app.catalogue"
            )

        with catalogue_file.open(
            "r", encoding="utf-8"
        ) as file:
            catalogue = json.load(file)

    database_context = json.dumps(
        catalogue,
        ensure_ascii=False,
        indent=2
    )

    system_prompt = """
    You are a database analysis assistant.

    You are connected to a SQL Server data warehouse.

    Your responsibilities:
    1. Understand the database schema.
    2. Explain tables and columns.
    3. Identify possible table relationships.
    4. Suggest appropriate SQL joins when asked.

    Important rules:
    - Use only the supplied database metadata.
    - Do not invent tables or columns.
    - Distinguish declared foreign keys from inferred relationships.
    - Do not claim that you executed SQL.
    - If metadata is insufficient, say so.
    - Give clear explanations suitable for a data engineer.
    """

    user_prompt = f"""
    DATABASE CATALOGUE:
    {database_context}

    USER QUESTION:
    {question}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        stream=False
    )

    return response.choices[0].message.content


if __name__ == "__main__":

    question = (
        "Explain how the business operates. "
           " What is the main business processes and KPIs."
           " Try to find any design defects e.g. data integrity, missing constraints, missing primary keys and missing foreign keys."
           " Try to summarize how the business is doing in the latest fiscal period."
    )

    print("Sending question to DeepSeek...")
    print("--------------------------------")

    answer = ask_deepseek(question)

    print(answer)
