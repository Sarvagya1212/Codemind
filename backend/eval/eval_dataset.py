# backend/eval/eval_dataset.py
"""
Comprehensive RAG Evaluation Dataset

50+ ground-truth questions across 10 categories for statistically meaningful evaluation.
Each question includes expected files and answer keywords for automated scoring.

Categories:
1. Authentication (5)
2. Database/Repository (5)  
3. Dependency Injection (5)
4. Services Flow (5)
5. Error Handling (5)
6. Models/Entities (5)
7. Security (5)
8. Configuration (5)
9. Controllers/API (5)
10. General Architecture (5)
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class EvalQuestion:
    """A single evaluation question with ground truth."""
    id: str
    query: str
    category: str
    expected_files: List[str]  # Partial matches work (e.g., "auth" matches "auth.py", "AuthService.java")
    expected_keywords: List[str]  # Keywords expected in a correct answer
    difficulty: str = "medium"  # easy, medium, hard


# =============================================================================
# EVALUATION DATASET - 50+ Questions
# =============================================================================

EVAL_DATASET: List[EvalQuestion] = [
    
    # =========================================================================
    # CATEGORY 1: AUTHENTICATION (5 questions)
    # =========================================================================
    EvalQuestion(
        id="auth_01",
        query="How does user authentication work in this codebase?",
        category="authentication",
        expected_files=["security", "auth", "login", "jwt", "token"],
        expected_keywords=["authenticate", "user", "password", "token", "security"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="auth_02",
        query="Where is the login functionality implemented?",
        category="authentication",
        expected_files=["login", "auth", "controller", "user"],
        expected_keywords=["login", "user", "password", "endpoint"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="auth_03",
        query="How are user credentials validated?",
        category="authentication",
        expected_files=["security", "auth", "user", "password"],
        expected_keywords=["validate", "password", "credential", "check"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="auth_04",
        query="What authentication mechanism is used? Basic auth, JWT, or OAuth?",
        category="authentication",
        expected_files=["security", "auth", "config"],
        expected_keywords=["jwt", "token", "auth", "bearer", "session"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="auth_05",
        query="How are authenticated users identified in requests?",
        category="authentication",
        expected_files=["security", "auth", "user", "principal"],
        expected_keywords=["user", "principal", "context", "request", "header"],
        difficulty="hard"
    ),
    
    # =========================================================================
    # CATEGORY 2: DATABASE / REPOSITORY (5 questions)
    # =========================================================================
    EvalQuestion(
        id="db_01",
        query="How is the database connection configured?",
        category="database",
        expected_files=["config", "database", "application", "properties", "yml"],
        expected_keywords=["database", "connection", "url", "driver", "datasource"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="db_02",
        query="What database is used in this project?",
        category="database",
        expected_files=["config", "application", "properties", "yml", "pom"],
        expected_keywords=["database", "mysql", "postgres", "mongodb", "sql"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="db_03",
        query="Where are the repository interfaces defined?",
        category="database",
        expected_files=["repository", "repo", "dao"],
        expected_keywords=["repository", "interface", "query", "data"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="db_04",
        query="How are database queries executed?",
        category="database",
        expected_files=["repository", "repo", "service"],
        expected_keywords=["query", "find", "save", "delete", "repository"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="db_05",
        query="What ORM or data access technology is used?",
        category="database",
        expected_files=["config", "pom", "build", "application"],
        expected_keywords=["jpa", "hibernate", "spring", "data", "orm"],
        difficulty="medium"
    ),
    
    # =========================================================================
    # CATEGORY 3: DEPENDENCY INJECTION (5 questions)
    # =========================================================================
    EvalQuestion(
        id="di_01",
        query="How are dependencies injected in this project?",
        category="dependency_injection",
        expected_files=["service", "controller", "config"],
        expected_keywords=["autowired", "inject", "bean", "spring", "dependency"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="di_02",
        query="What dependency injection framework is used?",
        category="dependency_injection",
        expected_files=["pom", "build", "config", "application"],
        expected_keywords=["spring", "inject", "di", "ioc", "container"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="di_03",
        query="How are services wired together?",
        category="dependency_injection",
        expected_files=["service", "config", "controller"],
        expected_keywords=["autowired", "service", "inject", "component"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="di_04",
        query="Where are beans or components configured?",
        category="dependency_injection",
        expected_files=["config", "application", "bean"],
        expected_keywords=["bean", "component", "configuration", "spring"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="di_05",
        query="How does the application bootstrap its dependencies?",
        category="dependency_injection",
        expected_files=["application", "main", "config", "bootstrap"],
        expected_keywords=["spring", "boot", "application", "context", "start"],
        difficulty="hard"
    ),
    
    # =========================================================================
    # CATEGORY 4: SERVICES FLOW (5 questions)
    # =========================================================================
    EvalQuestion(
        id="svc_01",
        query="What services are defined in this codebase?",
        category="services",
        expected_files=["service"],
        expected_keywords=["service", "class", "business", "logic"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="svc_02",
        query="How do services interact with each other?",
        category="services",
        expected_files=["service"],
        expected_keywords=["service", "inject", "call", "method", "dependency"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="svc_03",
        query="What is the service layer responsible for?",
        category="services",
        expected_files=["service"],
        expected_keywords=["business", "logic", "service", "layer", "process"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="svc_04",
        query="How does the user service work?",
        category="services",
        expected_files=["user", "service"],
        expected_keywords=["user", "service", "create", "find", "manage"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="svc_05",
        query="What business logic is in the main service classes?",
        category="services",
        expected_files=["service"],
        expected_keywords=["method", "logic", "process", "handle", "execute"],
        difficulty="medium"
    ),
    
    # =========================================================================
    # CATEGORY 5: ERROR HANDLING (5 questions)
    # =========================================================================
    EvalQuestion(
        id="err_01",
        query="How are errors handled in this application?",
        category="error_handling",
        expected_files=["exception", "error", "handler", "controller"],
        expected_keywords=["exception", "error", "catch", "handle", "throw"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="err_02",
        query="What exceptions are defined in the codebase?",
        category="error_handling",
        expected_files=["exception", "error"],
        expected_keywords=["exception", "class", "extends", "error"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="err_03",
        query="How are API errors returned to clients?",
        category="error_handling",
        expected_files=["controller", "handler", "response", "exception"],
        expected_keywords=["error", "response", "status", "message", "http"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="err_04",
        query="Is there a global exception handler?",
        category="error_handling",
        expected_files=["exception", "handler", "advice", "controller"],
        expected_keywords=["global", "handler", "exception", "advice", "controlleradvice"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="err_05",
        query="How are validation errors handled?",
        category="error_handling",
        expected_files=["validation", "exception", "handler"],
        expected_keywords=["validation", "error", "invalid", "constraint"],
        difficulty="hard"
    ),
    
    # =========================================================================
    # CATEGORY 6: MODELS / ENTITIES (5 questions)
    # =========================================================================
    EvalQuestion(
        id="model_01",
        query="What entities or models are defined in this project?",
        category="models",
        expected_files=["entity", "model", "domain"],
        expected_keywords=["entity", "class", "model", "field", "table"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="model_02",
        query="What is the User model structure?",
        category="models",
        expected_files=["user", "entity", "model"],
        expected_keywords=["user", "field", "property", "id", "name"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="model_03",
        query="How are entity relationships defined?",
        category="models",
        expected_files=["entity", "model"],
        expected_keywords=["relationship", "onetomany", "manytoone", "join", "foreign"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="model_04",
        query="What fields does the main entity have?",
        category="models",
        expected_files=["entity", "model"],
        expected_keywords=["field", "column", "property", "id", "string"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="model_05",
        query="Are there any DTOs or transfer objects?",
        category="models",
        expected_files=["dto", "request", "response", "transfer"],
        expected_keywords=["dto", "request", "response", "data", "transfer"],
        difficulty="medium"
    ),
    
    # =========================================================================
    # CATEGORY 7: SECURITY (5 questions)
    # =========================================================================
    EvalQuestion(
        id="sec_01",
        query="How is security configured in this application?",
        category="security",
        expected_files=["security", "config", "auth"],
        expected_keywords=["security", "configure", "http", "authorize"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="sec_02",
        query="What endpoints are protected?",
        category="security",
        expected_files=["security", "config"],
        expected_keywords=["authorize", "authenticated", "permit", "role", "endpoint"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="sec_03",
        query="How are user roles managed?",
        category="security",
        expected_files=["user", "role", "security", "authority"],
        expected_keywords=["role", "authority", "permission", "admin", "user"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="sec_04",
        query="Is CORS configured? How?",
        category="security",
        expected_files=["cors", "config", "security"],
        expected_keywords=["cors", "origin", "allowed", "cross", "header"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="sec_05",
        query="How are passwords stored securely?",
        category="security",
        expected_files=["security", "password", "encoder", "user"],
        expected_keywords=["password", "encoder", "hash", "bcrypt", "encrypt"],
        difficulty="medium"
    ),
    
    # =========================================================================
    # CATEGORY 8: CONFIGURATION (5 questions)
    # =========================================================================
    EvalQuestion(
        id="cfg_01",
        query="What configuration files does this project have?",
        category="configuration",
        expected_files=["application", "config", "properties", "yml"],
        expected_keywords=["config", "properties", "yml", "yaml", "settings"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="cfg_02",
        query="Where are environment-specific settings defined?",
        category="configuration",
        expected_files=["application", "properties", "yml", "profile"],
        expected_keywords=["profile", "environment", "dev", "prod", "config"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="cfg_03",
        query="How is the server port configured?",
        category="configuration",
        expected_files=["application", "properties", "yml"],
        expected_keywords=["port", "server", "8080", "http"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="cfg_04",
        query="What external dependencies are configured?",
        category="configuration",
        expected_files=["pom", "build", "gradle", "application"],
        expected_keywords=["dependency", "spring", "library", "version"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="cfg_05",
        query="How is logging configured?",
        category="configuration",
        expected_files=["application", "logback", "log4j", "properties"],
        expected_keywords=["log", "level", "debug", "info", "logging"],
        difficulty="medium"
    ),
    
    # =========================================================================
    # CATEGORY 9: CONTROLLERS / API (5 questions)
    # =========================================================================
    EvalQuestion(
        id="api_01",
        query="What API endpoints are available?",
        category="api",
        expected_files=["controller"],
        expected_keywords=["endpoint", "mapping", "get", "post", "api"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="api_02",
        query="How are REST endpoints structured?",
        category="api",
        expected_files=["controller", "rest"],
        expected_keywords=["rest", "controller", "mapping", "request", "response"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="api_03",
        query="What HTTP methods are used for CRUD operations?",
        category="api",
        expected_files=["controller"],
        expected_keywords=["get", "post", "put", "delete", "mapping"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="api_04",
        query="How does the API handle request parameters?",
        category="api",
        expected_files=["controller"],
        expected_keywords=["param", "request", "body", "path", "variable"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="api_05",
        query="What response formats does the API return?",
        category="api",
        expected_files=["controller", "response"],
        expected_keywords=["json", "response", "body", "return", "object"],
        difficulty="medium"
    ),
    
    # =========================================================================
    # CATEGORY 10: GENERAL ARCHITECTURE (5 questions)
    # =========================================================================
    EvalQuestion(
        id="arch_01",
        query="What is the overall architecture of this project?",
        category="architecture",
        expected_files=["controller", "service", "repository", "entity"],
        expected_keywords=["layer", "mvc", "architecture", "pattern", "structure"],
        difficulty="medium"
    ),
    EvalQuestion(
        id="arch_02",
        query="What design patterns are used?",
        category="architecture",
        expected_files=["service", "factory", "singleton", "pattern"],
        expected_keywords=["pattern", "design", "factory", "singleton", "repository"],
        difficulty="hard"
    ),
    EvalQuestion(
        id="arch_03",
        query="How is the codebase organized?",
        category="architecture",
        expected_files=["controller", "service", "repository", "entity"],
        expected_keywords=["package", "folder", "structure", "organize", "layer"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="arch_04",
        query="What is the main entry point of the application?",
        category="architecture",
        expected_files=["application", "main"],
        expected_keywords=["main", "application", "springboot", "run", "start"],
        difficulty="easy"
    ),
    EvalQuestion(
        id="arch_05",
        query="How do the different layers communicate?",
        category="architecture",
        expected_files=["controller", "service", "repository"],
        expected_keywords=["inject", "call", "service", "repository", "layer"],
        difficulty="medium"
    ),
]


def get_eval_dataset() -> List[EvalQuestion]:
    """Get the full evaluation dataset."""
    return EVAL_DATASET


def get_questions_by_category(category: str) -> List[EvalQuestion]:
    """Get questions filtered by category."""
    return [q for q in EVAL_DATASET if q.category == category]


def get_questions_by_difficulty(difficulty: str) -> List[EvalQuestion]:
    """Get questions filtered by difficulty."""
    return [q for q in EVAL_DATASET if q.difficulty == difficulty]


def get_dataset_stats() -> dict:
    """Get statistics about the evaluation dataset."""
    categories = {}
    difficulties = {"easy": 0, "medium": 0, "hard": 0}
    
    for q in EVAL_DATASET:
        categories[q.category] = categories.get(q.category, 0) + 1
        difficulties[q.difficulty] = difficulties.get(q.difficulty, 0) + 1
    
    return {
        "total_questions": len(EVAL_DATASET),
        "categories": categories,
        "difficulties": difficulties
    }


if __name__ == "__main__":
    stats = get_dataset_stats()
    print(f"\n📊 Evaluation Dataset Statistics")
    print(f"   Total Questions: {stats['total_questions']}")
    print(f"\n   By Category:")
    for cat, count in stats['categories'].items():
        print(f"      {cat}: {count}")
    print(f"\n   By Difficulty:")
    for diff, count in stats['difficulties'].items():
        print(f"      {diff}: {count}")
