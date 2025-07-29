import asyncio
import os
from groq import Groq
from dotenv import load_dotenv
import traceback
import re
import json

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError(
        "GROQ_API_KEY environment variable is not set. Please set it in your environment or .env file."
    )
client = Groq(api_key=api_key)


def remove_think_tags(text: str) -> tuple[str, list[str]]:
    """
    Removes content between <think> and </think> tags from the input text.
    Returns a tuple containing the cleaned text and a list of extracted think tag contents.

    Args:
        text (str): The input text containing <think> tags.

    Returns:
        tuple[str, list[str]]: A tuple where the first element is the text with think tags
                              and their contents removed, and the second element is a list
                              of the contents inside the think tags.
    """
    import re

    # Find all content between <think> and </think> tags
    think_contents = re.findall(r"<think>(.*?)</think>", text, re.DOTALL)

    # Remove <think> tags and their contents
    cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    return cleaned_text


def determine_generation_types(prompt: str) -> dict:
    """Analyze the prompt to determine which components to generate."""
    prompt = prompt.lower()
    generate_types = {
        "ui_code": False,
        "db_schema": False,
        "backend_code": False,
        "db_queries": False,
        "tech_docs": False,
    }

    # Keyword-based detection
    if re.search(r"\b(ui|frontend|html|css|javascript|react|interface)\b", prompt):
        generate_types["ui_code"] = True
    if re.search(r"\b(database|schema|tables|sql schema|db design)\b", prompt):
        generate_types["db_schema"] = True
    if re.search(
        r"\b(backend|api|server|python|javascript|java|go|django|flask|fastapi|express|spring|gin)\b",
        prompt,
    ):
        generate_types["backend_code"] = True
    if re.search(
        r"\b(queries|sql|database queries|crud|select|insert|update|delete)\b", prompt
    ):
        generate_types["db_queries"] = True
    if re.search(r"\b(documentation|docs|technical docs|readme|guide)\b", prompt):
        generate_types["tech_docs"] = True

    # If no specific type is detected and prompt is not empty, generate all components
    if not any(generate_types.values()) and prompt.strip():
        generate_types = {key: True for key in generate_types}

    return generate_types


def generate_ui_code(description: str) -> str:
    try:
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert web developer that generates clean HTML/CSS/JS code from wireframe descriptions.",
                },
                {
                    "role": "user",
                    "content": f"Generate responsive UI code for this description:\n\n{description}\n\nOutput ONLY raw code without markdown or additional text.",
                },
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        return remove_think_tags(response.choices[0].message.content)
    except Exception as e:
        raise Exception(
            f"Grok UI code generation failed: {str(e)}\n{traceback.format_exc()}"
        )


def generate_db_schema(description: str) -> str:
    try:
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a database architect that generates SQL schema from application requirements.",
                },
                {
                    "role": "user",
                    "content": f"Generate PostgreSQL schema with relationships for this application:\n\n{description}\n\nInclude only SQL code without explanations.",
                },
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return remove_think_tags(response.choices[0].message.content)
    except Exception as e:
        raise Exception(
            f"Grok DB schema generation failed: {str(e)}\n{traceback.format_exc()}"
        )


def generate_backend_code(description: str, language: str, framework: str) -> str:
    try:
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert backend developer proficient in {language} and {framework}. Generate clean, production-ready backend code.",
                },
                {
                    "role": "user",
                    "content": f"Generate backend code in {language} using {framework} for this application:\n\n{description}\n\nOutput ONLY raw code without markdown or additional text.",
                },
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        return remove_think_tags(response.choices[0].message.content)
    except Exception as e:
        raise Exception(
            f"Grok backend code generation failed: {str(e)}\n{traceback.format_exc()}"
        )


def generate_db_queries(description: str) -> str:
    try:
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a database expert that generates optimized PostgreSQL queries.",
                },
                {
                    "role": "user",
                    "content": f"Generate PostgreSQL queries (SELECT, INSERT, UPDATE, DELETE) for this application:\n\n{description}\n\nInclude only SQL code without explanations.",
                },
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return remove_think_tags(response.choices[0].message.content)
    except Exception as e:
        raise Exception(
            f"Grok DB queries generation failed: {str(e)}\n{traceback.format_exc()}"
        )


def generate_technical_docs(description: str) -> str:
    try:
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical writer that generates clear and concise documentation for software applications.",
                },
                {
                    "role": "user",
                    "content": f"Generate technical documentation for this application:\n\n{description}\n\nInclude only the documentation text without additional comments.",
                },
            ],
            temperature=0.4,
            max_tokens=4000,
        )
        return remove_think_tags(response.choices[0].message.content)
    except Exception as e:
        raise Exception(
            f"Grok documentation generation failed: {str(e)}\n{traceback.format_exc()}"
        )


async def generate_components(
    description: str, backend_language: str, framework: str, generate_types: dict = None
):
    """
    Generate specified components based on the description and optional generate_types.
    If generate_types is not provided, determine types from the prompt.
    Returns a dictionary with generated components and their status.
    """
    results = {
        "ui_code": None,
        "db_schema": None,
        "backend_code": None,
        "db_queries": None,
        "tech_docs": None,
    }

    if not generate_types:
        generate_types = determine_generation_types(description)

    try:
        if generate_types.get("ui_code"):
            results["ui_code"] = await asyncio.to_thread(generate_ui_code, description)
        if generate_types.get("db_schema"):
            results["db_schema"] = await asyncio.to_thread(
                generate_db_schema, description
            )
        if generate_types.get("backend_code"):
            results["backend_code"] = await asyncio.to_thread(
                generate_backend_code, description, backend_language, framework
            )
        if generate_types.get("db_queries"):
            results["db_queries"] = await asyncio.to_thread(
                generate_db_queries, description
            )
        if generate_types.get("tech_docs"):
            results["tech_docs"] = await asyncio.to_thread(
                generate_technical_docs, description
            )

        return results, generate_types
    except Exception as e:
        raise Exception(
            f"Component generation failed: {str(e)}\n{traceback.format_exc()}"
        )
