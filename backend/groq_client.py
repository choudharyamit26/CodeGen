import os
from dotenv import load_dotenv
import traceback
import re
from typing import List, Optional, Tuple

# LangChain imports
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError(
        "GROQ_API_KEY environment variable is not set. Please set it in your environment or .env file."
    )

# Initialize LangChain Groq LLM
llm = ChatGroq(
    api_key=api_key,
    model="deepseek-r1-distill-llama-70b",
    temperature=0.3,
    max_tokens=3000,
)


# Pydantic models for structured outputs
class CodeAnalysis(BaseModel):
    """Analysis of what type of code to generate"""

    language: str = Field(description="Programming language (python, javascript, java)")
    requires_framework: bool = Field(description="Whether a web framework is needed")
    framework: Optional[str] = Field(description="Specific framework if needed")
    frontend_framework: Optional[str] = Field(
        description="Frontend framework (react, vue, angular)"
    )
    code_type: str = Field(
        description="Type of code: simple_function, web_api, script, algorithm"
    )
    components_needed: List[str] = Field(description="List of components to generate")
    ui_type: Optional[str] = Field(description="UI type: html, react, vue, angular")


class StackDetection(BaseModel):
    """Detection of technology stack"""

    backend_language: str = Field(description="Backend programming language")
    framework: str = Field(description="Web framework to use")
    frontend_framework: Optional[str] = Field(
        description="Frontend framework (react, vue, angular, html)"
    )
    use_framework: bool = Field(
        description="Whether to use a framework or core language"
    )
    use_database: bool = Field(description="Whether database operations are needed")


# Create structured output parser
analysis_parser = JsonOutputParser(pydantic_object=CodeAnalysis)
stack_parser = JsonOutputParser(pydantic_object=StackDetection)

# Enhanced prompt templates
ANALYSIS_TEMPLATE = """
You are an expert software architect. Analyze this request and determine what type of code to generate.

Request: {description}

Analyze and return a JSON response with:
- language: The programming language (python, javascript, java)
- requires_framework: true if this needs a web framework (API, server, endpoints), false for simple functions/scripts
- framework: specific framework name if needed (fastapi, flask, django, express, spring)
- frontend_framework: frontend framework if needed (react, vue, angular, or null for plain HTML)
- code_type: one of "simple_function", "web_api", "script", "algorithm", "utility"
- components_needed: array of components needed ["ui_code", "db_schema", "backend_code", "db_queries", "tech_docs", "er_diagram"]
- ui_type: frontend type (html, react, vue, angular)

Key indicators:
- Simple functions: "function", "print", "calculate", "loop", "algorithm"
- Web APIs: "api", "server", "endpoint", "web", "rest", "http"
- Database: "database", "schema", "sql", "queries", "er diagram", "entity relationship"
- Frontend frameworks: "react", "vue", "angular", "component"
- Plain HTML: "html", "css", "webpage" (without framework mentions)

{format_instructions}
"""

STACK_DETECTION_TEMPLATE = """
Based on this description, determine the optimal technology stack:

Description: {description}

Consider these rules:
1. Use core language (no framework) for: simple functions, scripts, algorithms, calculations, basic utilities
2. Use web framework for: APIs, servers, web applications, endpoints, REST services
3. Frontend frameworks: React for complex UIs, Vue for moderate complexity, Angular for enterprise apps
4. Default frameworks: Python->FastAPI, JavaScript->Express, Java->Spring
5. Database indicators: "database", "sql", "schema", "er", "entity"

Return JSON with:
- backend_language: programming language
- framework: framework name (or "none" for core language)
- frontend_framework: react, vue, angular, html, or null
- use_framework: boolean indicating if backend framework should be used
- use_database: boolean indicating if database operations are needed

{format_instructions}
"""

# Create prompt templates
analysis_prompt = PromptTemplate(
    template=ANALYSIS_TEMPLATE,
    input_variables=["description"],
    partial_variables={
        "format_instructions": analysis_parser.get_format_instructions()
    },
)

stack_prompt = PromptTemplate(
    template=STACK_DETECTION_TEMPLATE,
    input_variables=["description"],
    partial_variables={"format_instructions": stack_parser.get_format_instructions()},
)

# Create chains
analysis_chain = analysis_prompt | llm | analysis_parser
stack_chain = stack_prompt | llm | stack_parser

# Code generation prompt templates
CODE_GENERATION_PROMPTS = {
    "simple_function": {
        "name": "Simple Function Generator",
        "description": "Generates simple standalone functions and scripts",
        "prompt_template": """
You are an expert {language} developer. Generate a clean, simple {language} function or script.

Requirements: {description}

Rules:
- Use only standard library (no external dependencies)
- Create standalone, executable code
- Include clear variable names and comments
- For "print X times" requests, use simple loops
- Output ONLY the code, no explanations

Code:
""",
    },
    "web_api": {
        "name": "Web API Generator",
        "description": "Generates web APIs and server applications",
        "prompt_template": """
You are an expert backend developer specializing in {language} and {framework}.

Requirements: {description}

Generate production-ready {framework} code with:
- Clean API structure
- Proper error handling
- RESTful endpoints
- Input validation
- CORS configuration for frontend integration

Output ONLY the code:
""",
    },
    "core_script": {
        "name": "Core Script Generator",
        "description": "Generates core language scripts without frameworks",
        "prompt_template": """
You are an expert {language} developer. Create a core {language} script using only standard library.

Requirements: {description}

Rules:
- No external libraries or frameworks
- Clean, readable code
- Proper error handling
- Include main execution block if appropriate

Output ONLY the code:
""",
    },
}

# Enhanced Database and UI generation prompts
DB_SCHEMA_PROMPT = ChatPromptTemplate.from_template(
    """
You are a database architect. Generate a comprehensive PostgreSQL schema for this application:

Requirements: {description}

Create:
- Well-normalized tables with appropriate relationships
- Primary keys and foreign key constraints
- Proper data types and constraints (NOT NULL, UNIQUE, CHECK)
- Indexes for performance optimization
- Comments explaining table purposes
- Sample data insertion statements

Output ONLY SQL DDL statements:
"""
)

ER_DIAGRAM_PROMPT = ChatPromptTemplate.from_template(
    """
You are a database architect. Generate an Entity-Relationship (E-R) diagram description for this application:

Requirements: {description}

Create a detailed E-R diagram description including:
- Entities with their attributes (mark primary keys with underline notation)
- Relationships between entities (one-to-one, one-to-many, many-to-many)
- Cardinality and participation constraints
- Entity types (strong, weak)
- Relationship attributes if applicable

Format as:
1. ENTITIES:
   - EntityName (primary_key, attribute1, attribute2, ...)
   
2. RELATIONSHIPS:
   - Entity1 --relationship_name--> Entity2 [cardinality]
   
3. CONSTRAINTS:
   - List any specific business rules or constraints

Also provide Mermaid ER diagram syntax:

```mermaid
erDiagram
    ENTITY1 {{
        type attribute1
        type attribute2
    }}
    ENTITY2 {{
        type attribute1
        type attribute2
    }}
    ENTITY1 ||--o{{ ENTITY2 : relationship
```

Output the complete E-R diagram description and Mermaid syntax:
"""
)

# Frontend framework-specific prompts
UI_HTML_PROMPT = ChatPromptTemplate.from_template(
    """
You are a frontend developer. Generate responsive HTML/CSS/JavaScript code:

Requirements: {description}

Create:
- Clean, semantic HTML5 structure
- Modern CSS with flexbox/grid layout
- Vanilla JavaScript for interactivity
- Mobile-responsive design
- Accessibility features (ARIA labels, semantic tags)
- Modern styling with CSS variables

Output ONLY the complete HTML file with embedded CSS and JavaScript:
"""
)

UI_REACT_PROMPT = ChatPromptTemplate.from_template(
    """
You are a React developer. Generate a modern React component:

Requirements: {description}

Create:
- Functional React component with hooks
- State management using useState/useEffect
- Props interface with TypeScript-style comments
- Event handlers and form validation
- Responsive design with CSS modules or styled-components
- Accessibility features
- Error boundaries where appropriate

Generate both:
1. Main component file (.jsx)
2. CSS module file (.module.css) if needed

Output ONLY the complete React code:
"""
)

UI_VUE_PROMPT = ChatPromptTemplate.from_template(
    """
You are a Vue.js developer. Generate a Vue 3 component with Composition API:

Requirements: {description}

Create:
- Vue 3 Single File Component (.vue)
- Composition API with <script setup>
- Reactive data using ref/reactive
- Computed properties and watchers
- Event handling and form validation
- Scoped CSS styling
- TypeScript support comments
- Accessibility features

Output ONLY the complete .vue file:
"""
)

UI_ANGULAR_PROMPT = ChatPromptTemplate.from_template(
    """
You are an Angular developer. Generate Angular component with TypeScript:

Requirements: {description}

Create:
- Angular component with TypeScript
- Component decorator with proper metadata
- Template with Angular directives and bindings
- Component styling (SCSS/CSS)
- Service integration examples
- Form handling with reactive forms
- Interface/model definitions
- Accessibility features

Generate:
1. Component TypeScript file (.component.ts)
2. Template file (.component.html)
3. Styles file (.component.scss)
4. Interface file (.interface.ts) if needed

Output ONLY the complete Angular component files:
"""
)

DB_QUERIES_PROMPT = ChatPromptTemplate.from_template(
    """
You are a database expert. Generate optimized PostgreSQL queries and operations:

Requirements: {description}

Generate comprehensive database operations:

1. CRUD OPERATIONS:
   - SELECT queries (simple and complex with JOINs)
   - INSERT statements (single and batch)
   - UPDATE operations (conditional updates)
   - DELETE operations (safe deletion with constraints)

2. ADVANCED QUERIES:
   - Aggregation queries (COUNT, SUM, AVG, GROUP BY)
   - Subqueries and CTEs (Common Table Expressions)
   - Window functions if applicable
   - Indexing recommendations

3. STORED PROCEDURES/FUNCTIONS:
   - Reusable database functions
   - Triggers for data integrity

4. PERFORMANCE OPTIMIZATION:
   - Query optimization tips
   - Index suggestions
   - Explain plan analysis

Output ONLY SQL queries and database operations:
"""
)

TECH_DOCS_PROMPT = ChatPromptTemplate.from_template(
    """
You are a technical writer. Generate comprehensive documentation:

Requirements: {description}

Include:
- Project Overview and Architecture
- Technology Stack Explanation
- Setup and Installation Instructions
- API Documentation (if applicable)
- Database Schema Documentation
- Frontend Component Documentation
- Usage Examples and Code Samples
- Deployment Instructions
- Testing Guidelines
- Troubleshooting Guide

Output ONLY the documentation in Markdown format:
"""
)


def remove_think_tags(text: str) -> str:
    """Remove content between <think> and </think> tags"""
    cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned_text.strip()


async def analyze_request(description: str) -> CodeAnalysis:
    """Use LangChain to analyze the request and determine what to generate"""
    try:
        result = await analysis_chain.ainvoke({"description": description})
        return CodeAnalysis(**result)
    except Exception as e:
        # Fallback to basic analysis
        return CodeAnalysis(
            language="python",
            requires_framework=False,
            framework=None,
            frontend_framework=None,
            code_type="simple_function",
            components_needed=["backend_code"],
            ui_type=None,
        )


async def detect_stack_with_langchain(
    description: str,
) -> Tuple[str, str, bool, Optional[str]]:
    """Use LangChain to detect optimal technology stack"""
    try:
        result = await stack_chain.ainvoke({"description": description})
        stack = StackDetection(**result)
        return (
            stack.backend_language,
            stack.framework,
            stack.use_framework,
            stack.frontend_framework,
        )
    except Exception as e:
        # Fallback to original detection
        lang, fw, use_fw = detect_stack_fallback(description)
        frontend_fw = detect_frontend_framework(description)
        return lang, fw, use_fw, frontend_fw


def detect_frontend_framework(description: str) -> Optional[str]:
    """Detect frontend framework from description"""
    description_lower = description.lower()

    if "react" in description_lower:
        return "react"
    elif "vue" in description_lower:
        return "vue"
    elif "angular" in description_lower:
        return "angular"
    elif any(
        keyword in description_lower for keyword in ["html", "webpage", "website"]
    ):
        return "html"

    return None


def detect_stack_fallback(description: str) -> Tuple[str, str, bool]:
    """Fallback stack detection using original logic"""
    description_lower = description.lower()

    # Simple function indicators
    simple_indicators = [
        "function",
        "print",
        "calculate",
        "loop",
        "algorithm",
        "script",
    ]
    is_simple = any(indicator in description_lower for indicator in simple_indicators)

    # Detect language
    if "javascript" in description_lower or "node" in description_lower:
        language = "javascript"
        framework = "express"
    elif "java" in description_lower and "javascript" not in description_lower:
        language = "java"
        framework = "spring"
    else:
        language = "python"
        framework = "fastapi"

    use_framework = not is_simple and any(
        keyword in description_lower
        for keyword in ["api", "server", "web", "endpoint", "rest"]
    )

    return language, framework, use_framework


def determine_generation_types(analysis: CodeAnalysis) -> dict:
    """Convert analysis to generation types dictionary"""
    generate_types = {
        "ui_code": "ui_code" in analysis.components_needed,
        "db_schema": "db_schema" in analysis.components_needed,
        "backend_code": "backend_code" in analysis.components_needed,
        "db_queries": "db_queries" in analysis.components_needed,
        "tech_docs": "tech_docs" in analysis.components_needed,
        "er_diagram": "er_diagram" in analysis.components_needed,
    }

    # Ensure at least backend_code is generated for code requests
    if not any(generate_types.values()):
        generate_types["backend_code"] = True

    return generate_types


async def generate_ui_code(
    description: str, frontend_framework: Optional[str] = None
) -> str:
    """Generate UI code using appropriate framework"""
    try:
        # Determine which prompt to use based on framework
        if frontend_framework == "react":
            prompt = UI_REACT_PROMPT
        elif frontend_framework == "vue":
            prompt = UI_VUE_PROMPT
        elif frontend_framework == "angular":
            prompt = UI_ANGULAR_PROMPT
        else:
            prompt = UI_HTML_PROMPT

        chain = prompt | llm | StrOutputParser()
        result = await chain.ainvoke({"description": description})
        return remove_think_tags(result)
    except Exception as e:
        raise Exception(f"UI code generation failed: {str(e)}")


async def generate_db_schema(description: str) -> str:
    """Generate database schema using LangChain"""
    try:
        chain = DB_SCHEMA_PROMPT | llm | StrOutputParser()
        result = await chain.ainvoke({"description": description})
        return remove_think_tags(result)
    except Exception as e:
        raise Exception(f"DB schema generation failed: {str(e)}")


async def generate_er_diagram(description: str) -> str:
    """Generate E-R diagram description and Mermaid syntax"""
    try:
        chain = ER_DIAGRAM_PROMPT | llm | StrOutputParser()
        result = await chain.ainvoke({"description": description})
        return remove_think_tags(result)
    except Exception as e:
        raise Exception(f"E-R diagram generation failed: {str(e)}")


async def generate_backend_code(
    description: str, language: str, framework: str, analysis: CodeAnalysis
) -> str:
    """Generate backend code using LangChain with intelligent routing"""
    try:
        # Choose appropriate prompt based on analysis
        if analysis.code_type == "simple_function" or not analysis.requires_framework:
            template = CODE_GENERATION_PROMPTS["simple_function"]["prompt_template"]
        elif analysis.requires_framework:
            template = CODE_GENERATION_PROMPTS["web_api"]["prompt_template"]
        else:
            template = CODE_GENERATION_PROMPTS["core_script"]["prompt_template"]

        prompt = PromptTemplate.from_template(template)
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke(
            {
                "description": description,
                "language": language,
                "framework": framework if analysis.requires_framework else "none",
            }
        )

        return remove_think_tags(result)
    except Exception as e:
        raise Exception(f"Backend code generation failed: {str(e)}")


async def generate_db_queries(description: str) -> str:
    """Generate database queries using LangChain"""
    try:
        chain = DB_QUERIES_PROMPT | llm | StrOutputParser()
        result = await chain.ainvoke({"description": description})
        return remove_think_tags(result)
    except Exception as e:
        raise Exception(f"DB queries generation failed: {str(e)}")


async def generate_technical_docs(description: str) -> str:
    """Generate technical documentation using LangChain"""
    try:
        chain = TECH_DOCS_PROMPT | llm | StrOutputParser()
        result = await chain.ainvoke({"description": description})
        return remove_think_tags(result)
    except Exception as e:
        raise Exception(f"Documentation generation failed: {str(e)}")


# Legacy functions for backward compatibility
def detect_language(description: str) -> str:
    """Legacy function - use detect_stack_with_langchain instead"""
    language, _, _ = detect_stack_fallback(description)
    return language


def detect_framework(language: str, description: str) -> str:
    """Legacy function - use detect_stack_with_langchain instead"""
    _, framework, _ = detect_stack_fallback(description)
    return framework


def detect_stack(description: str):
    """Legacy function - use detect_stack_with_langchain instead"""
    language, framework, _ = detect_stack_fallback(description)
    return language, framework


async def generate_components(
    description: str,
    backend_language: str = None,
    framework: str = None,
    generate_types: dict = None,
):
    """
    Enhanced component generation using LangChain analysis
    """
    results = {
        "ui_code": None,
        "db_schema": None,
        "backend_code": None,
        "db_queries": None,
        "tech_docs": None,
        "er_diagram": None,
    }

    try:
        # Use LangChain to analyze the request
        analysis = await analyze_request(description)

        # Override with provided parameters if available
        if backend_language:
            analysis.language = backend_language
        if framework:
            analysis.framework = framework

        # Determine what to generate
        if not generate_types:
            generate_types = determine_generation_types(analysis)

        # Generate components based on analysis
        if generate_types.get("ui_code"):
            results["ui_code"] = await generate_ui_code(
                description, analysis.frontend_framework
            )

        if generate_types.get("db_schema"):
            results["db_schema"] = await generate_db_schema(description)

        if generate_types.get("er_diagram"):
            results["er_diagram"] = await generate_er_diagram(description)

        if generate_types.get("backend_code"):
            results["backend_code"] = await generate_backend_code(
                description, analysis.language, analysis.framework or "none", analysis
            )

        if generate_types.get("db_queries"):
            results["db_queries"] = await generate_db_queries(description)

        if generate_types.get("tech_docs"):
            results["tech_docs"] = await generate_technical_docs(description)

        return results, generate_types, analysis

    except Exception as e:
        raise Exception(
            f"Component generation failed: {str(e)}\n{traceback.format_exc()}"
        )


# Additional utility functions
async def generate_core_language_code(description: str, language: str) -> str:
    """Generate core language code without frameworks"""
    analysis = CodeAnalysis(
        language=language,
        requires_framework=False,
        framework=None,
        frontend_framework=None,
        code_type="simple_function",
        components_needed=["backend_code"],
        ui_type=None,
    )
    return await generate_backend_code(description, language, "none", analysis)


async def generate_fullstack_app(
    description: str, backend_lang: str = "python", frontend_fw: str = "react"
) -> dict:
    """Generate a complete fullstack application"""
    results = {}

    # Override analysis for fullstack generation
    analysis = CodeAnalysis(
        language=backend_lang,
        requires_framework=True,
        framework="fastapi" if backend_lang == "python" else "express",
        frontend_framework=frontend_fw,
        code_type="web_api",
        components_needed=[
            "ui_code",
            "db_schema",
            "backend_code",
            "db_queries",
            "tech_docs",
            "er_diagram",
        ],
        ui_type=frontend_fw,
    )

    generate_types = {
        "ui_code": True,
        "db_schema": True,
        "backend_code": True,
        "db_queries": True,
        "tech_docs": True,
        "er_diagram": True,
    }

    return await generate_components(
        description, backend_lang, analysis.framework, generate_types
    )
