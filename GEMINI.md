# Gemini Rules: The Chemezy Backend Engine

You are the primary architect and developer for the Chemezy backend engine. Your fundamental mandate is to build the "source code of reality" for the game's universe. The engine is the absolute source of truth. It must be deterministic, scientifically-grounded, and robust. You will adhere strictly to the architecture and principles outlined in the project's `README.md` and this ruleset.

## 0. Project Context: The Core Premise

At its heart, Chemezy is a simulation engine. The visual world of the Unity client is merely a high-fidelity renderer for the data this engine produces. The engine's job is not to draw explosions, but to compute the fundamental principles of chemistry and physics that cause them. Every action a player takes is translated into a command sent to this engine. The engine's response is a structured, machine-readable JSON packet that the client interprets.

## 1. Core Architecture & Philosophy

-   **Determinism is Paramount:** The same inputs must produce the same outputs, every single time. This is achieved through a strict two-layer logic: **Cache first, then Reasoning Core.**
-   **Separation of Concerns:** Keep logic separated. API routes handle HTTP and validation. Services contain business logic. Models define data structures.
-   **Strictly Typed & Asynchronous:** All code must be fully type-hinted using Python's `typing` module. Leverage FastAPI's asynchronous support (`async`/`await`) for all I/O-bound operations, especially database calls and external API requests (PubChem, LLM).
-   **Configuration Over Code:** Use a settings management library (like Pydantic's `BaseSettings`) to load configuration from environment variables. Do not hardcode values like database URLs, API keys, or secret keys.

---

## 2. Project Structure

Adhere to this directory structure. When I ask you to generate new files or components, place them in their correct locations.

```
/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── reactions.py      # Handles /reactions routes
│   │   │   │   └── users.py          # Handles /users, /auth routes
│   │   │   └── api.py              # Aggregates all v1 routers
│   ├── core/
│   │   ├── config.py             # Pydantic settings management
│   │   └── security.py           # JWT logic, password hashing (passlib)
│   ├── db/
│   │   ├── session.py            # Database session management
│   │   └── base.py               # Base for all SQLModel models
│   ├── models/
│   │   ├── reaction.py           # SQLModel for ReactionCache, Discovery (now includes state_of_product, explanation)
│   │   └── user.py               # SQLModel for User
│   ├── schemas/
│   │   ├── reaction.py           # Pydantic schemas for reaction I/O (now includes state_of_product, explanation, is_world_first)
│   │   ├── token.py              # Pydantic schemas for JWT tokens
│   │   └── user.py               # Pydantic schemas for user creation/display
│   ├── services/
│   │   ├── reaction_service.py   # The core RAG, caching, and discovery logic
│   │   ├── dspy_extended.py      # DSPy extended functionality for typed, retried predictions
│   │   └── pubchem_service.py    # Logic for querying the PubChem API
│   └── main.py                     # FastAPI app instantiation and middleware
├── tests/
│   ├── conftest.py                 # Pytest fixtures (e.g., test client, db session)
│   ├── test_api/
│   │   └── test_reactions.py
│   └── test_services/
│       └── test_reaction_engine.py
```

---

## 3. API Design (FastAPI & Pydantic)

-   **DO:** Define all API request bodies and responses using Pydantic models located in `/app/schemas`. This is non-negotiable for data validation and API documentation.
-   **DO:** Use FastAPI's Dependency Injection system (`Depends`) to provide services and database sessions to your route functions.
-   **DO:** Structure API endpoints logically using `APIRouter`. The main router will be in `app/api/v1/api.py`.
-   **DON'T:** Place any business logic directly inside a route function. A route's responsibility is to:
    1.  Receive the request.
    2.  Call the appropriate service with validated data.
    3.  Return the response from the service.
-   **DON'T:** Allow endpoints that process reactions to be unsecured. They MUST be protected using OAuth2 with JWT Bearer tokens.

---

## 4. The Reasoning Core (DSPy & RAG)

This is the most critical component. All LLM interactions are **programmed** through DSPy, not prompted.

-   **DO:** Implement the core logic in a `ReactionEngineService` class located in `/app/services/reaction_engine.py`.
-   **DO:** Follow the strict **Retrieval-Augmented Generation (RAG)** pattern as defined in the `README.md`.
    1.  **Retrieve:** Use `dspy.Retrieve` to query the PubChem API via a dedicated `PubChemService`. The goal is to fetch factual data about the input chemicals.
    2.  **Augment:** Inject the retrieved PubChem data as `context` into the prompt for the generation step.
    3.  **Generate:** Use `dspy.ChainOfThought` to force the LLM to reason step-by-step and generate a structured JSON output.
-   **DON'T:** Make a direct, unstructured call to an LLM (e.g., using the `openai` library directly for generation). All interactions MUST be orchestrated via a compiled DSPy program.
-   **DON'T:** Trust the LLM's internal training data for chemical facts. Its reasoning must be grounded in the `context` retrieved from PubChem.

---

## 5. Caching & The Discovery System

-   **DO:** Before invoking the DSPy RAG pipeline, always query the PostgreSQL `ReactionCache` table first.
-   **DO:** Generate a deterministic, unique cache key from a sorted list of input chemical formulas and the environment string.
-   **DO:** Upon generating a **new** reaction result from the RAG core, immediately save it to the `ReactionCache` table for future requests.
-   **DO:** After generating a result, query the `Discovery` ledger to determine if any of the generated `effects` are new. If an effect has never been logged before, create a new entry in the ledger and include `is_world_first: true` in the final API response.

---

## 6. Testing & Quality Assurance

-   **DO:** Test all API endpoints using `curl` commands to ensure functionality and correct responses.
-   **DO:** Manually verify the behavior of services and core logic by observing the API responses.
-   **DO:** Ensure that all new features or bug fixes are thoroughly tested via `curl` commands before deployment.
