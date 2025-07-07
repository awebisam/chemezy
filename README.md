## The Core Premise: The Source Code of Reality

At its heart, **Chemezy is not a game; it is a simulation engine.** Think of it as the source code of reality for the game's universe. While the player experiences a graphical 3D laboratory—a world of gleaming beakers, reactive liquids, and interactive tools—that visual world is merely a high-fidelity renderer for the data this engine produces. The engine's job is not to draw explosions, but to compute the fundamental principles of chemistry and physics that cause them. It is the system's absolute source of truth, a deterministic core that ensures the world behaves consistently, whether for one player or thousands.

Every action a player takes in the 3D lab—pouring a beaker, activating a Bunsen burner, changing the environment to a vacuum—is translated into a simple, text-based command sent to this engine. The visual client asks, "What happens now?" The engine provides the definitive answer.

---

## The Player's Command

Imagine the player in their Unity lab drags a bottle of Water (H₂O) and a shaker of Salt (NaCl) into a beaker under normal conditions. The client-side game doesn't decide what happens. It simply formats and sends a command to the engine's core endpoint:

```
REACT --chemicals [H2O, NaCl] --environment [Earth]
```

A more complex experiment, like attempting to ignite Magnesium (Mg) in a pure carbon dioxide environment, would be just as simple for the engine to understand:

```
REACT --chemicals [Mg, CO2] --environment [Pure_Oxygen] --conditions [ignition_spark]
```

This is the fundamental unit of interaction. The engine receives this command and begins a structured, multi-layered process to determine the result.

---

## The Engine's Logic: A Multi-Layered Defense

The engine's primary design goal is to provide scientifically-grounded results, prioritizing established facts over pure invention. To achieve this, it does not simply ask an LLM "what happens?". It follows a strict, three-layer sequence, moving from memory to fact to reason.

### Layer 1: The Cache (Memory)

The engine first checks its own memory—a database table of previously executed reactions. It generates a unique key from the input (`[H2O, NaCl] + [Earth]`) and queries its cache. If this exact experiment has been run before, the stored result is returned instantly. This is crucial not just for managing cost and latency, but for guaranteeing determinism. For the game world to feel real and fair, the same inputs must produce the same outputs, every single time.

### Layer 2: The Factual Lookup (The Library)

If the experiment is not in the cache, the engine consults a trusted external library: a real chemical database like **PubChem**. It queries the API to see if this is a known, documented reaction. If so, it uses this factual data as the source of truth. "Parsing" this data means mapping real-world properties—like a compound's boiling point, density, or specific safety warnings—directly into our `ReactionResult` schema. This grounds the simulation in verifiable scientific fact wherever possible.

### Layer 3: The Extrapolator (The Reasoning Core)

Only if the reaction is novel—absent from both the cache and the factual database—does the engine engage its reasoning core. This is a carefully constrained LLM program designed not as an oracle, but as an **"intelligent extrapolator."** It is instructed to use first principles and analyze the functional groups of the provided compounds to generate a plausible outcome. It uses the "grammar" of chemistry to predict how a new "word" (a novel molecule) might behave, based on its constituent parts. It is forced to "show its work" and, most importantly, to structure its response according to a rigid schema.

---

## The Engine's Response: The Structured Data Packet

The engine never responds with a simple sentence. Its output is always a predictable, machine-readable JSON packet that the 3D client can unambiguously interpret. Each key in this packet has a specific purpose.

```json
{
  "request_id": "c4a2b-11e8-a8d5-f2801f1b9fd1",
  "products": [
    { "formula": "H2", "name": "Hydrogen Gas", "state": "gas" },
    { "formula": "NaOH", "name": "Sodium Hydroxide", "state": "aqueous" }
  ],
  "effects": [
    "fizz",
    "fire",
    "color_change_red",
    "rapid_temperature_increase"
  ],
  "state_change": null,
  "description": "A vigorous exothermic reaction occurs, releasing flammable hydrogen gas which ignites.",
  "is_world_first": true
}
```

- **`products`**: An array detailing the new substances created. This is the fundamental chemical change.
- **`effects`**: An array of transient phenomena. `fire` is an effect; the underlying products are what burn. This distinction allows the client to trigger temporary visual and audio events.
- **`state_change`**: A fundamental transformation of a substance (e.g., from liquid to `viscous_goo`). This is separated from effects because it represents a persistent change in the substance's properties.
- **`is_world_first`**: The boolean flag that tells the client to celebrate a player's unique contribution to the game's collective knowledge.

---

## The Technology Stack: From Request to Response

To build this engine, we need a stack where each component performs a distinct, critical role.

### FastAPI (The API Gateway)

This will be the front door to our engine. Its role is to handle all incoming HTTP requests from the Unity client. We use it because its tight integration with **Pydantic** allows us to rigorously define and automatically validate the structure of our data. Its native asynchronous support is also vital for efficiently handling long-running calls to external APIs or the LLM without blocking other player requests.

### User Authentication (JWT & Passlib)

Before any reaction is processed, we must know who is asking. This system handles user registration and login, issuing a **JSON Web Token (JWT)** upon successful authentication. Every subsequent request requires this token. This is essential for ownership, linking discoveries to specific users and opening the door for future social features like leaderboards or shared laboratories.

### PostgreSQL & SQLModel (The Persistent Memory)

This is the engine's long-term memory. A relational database is necessary to permanently store the `User` table, the `ReactionCache`, and the `Discovery` ledger. We use **SQLModel** as the ORM because it allows us to define our database tables using the same Pydantic-style syntax as our API, creating a single, unified source of truth for data models that reduces bugs and accelerates development.

### PubChem API (The Factual Library)

This is our connection to established scientific fact. The engine will use a simple Python library like `requests` to query the PubChem API for data on known compounds and reactions. This is **Layer 2** of our logic, ensuring that if a reaction is already known to science, we use that ground truth.

### DSPy (The Reasoning Core)

This is the most critical component and the heart of Layer 3. We are **programming the LLM**, not just prompting it.

- **Define a Signature**: This forces the LLM to return a structured JSON object that matches our `ReactionResult` schema, eliminating unreliable free-text responses.
- **Implement ChainOfThought**: We instruct the model to first reason through the chemical principles it is applying before generating the final output. This makes the LLM's reasoning process auditable, which is invaluable for debugging and refinement.
- **Build a Module**: We compose these elements into a reusable **DSPy program** that represents our "intelligent extrapolator," a predictable and reliable component in our larger system.

---

## The Discovery System: The Engine's Ledger

The `is_world_first` flag is the output of the engine's internal discovery system. This system functions as the official history book of the game's universe, written by the players themselves. When a reaction result is generated, the engine checks the `effects` list against its master "Discoverable Effect Schema." For each valid effect, it queries the permanent Discovery ledger. If an effect like `"crystallization"` has never been logged by any player before, the engine carves a new entry into the ledger—

```text
(effect: "crystallization", user_id: 123, timestamp: ...)
```

—and sets `is_world_first: true` in the response. This grants players a powerful sense of permanence and legacy.

---

## The Bridge to the Visual World

The 3D Unity client receives the final JSON packet and acts as an expert translator, orchestrating a symphony of visuals and sounds. It iterates through the `effects` array and triggers the corresponding assets. It sees `"fire"` and spawns a dynamic particle system. It sees `"fizz"` and plays an escalating bubbling sound. It sees `"rapid_temperature_increase"` and applies a shimmering heat-haze shader to the air above the beaker. The client brings the data to life, transforming a structured text response into a visceral, satisfying spectacle.

The 3D world is the stage, but the intelligence, the memory, and the rules all reside here, in the text-based simulator.
