# Chemezy: The Backend Basis (aka, The Brains of the Operation)

## Welcome, Future Alchemist!

So, you've stumbled upon the secret sauce, the digital DNA, the very **source code of reality** for the Chemezy universe. Yes, that's right. While your players are busy oohing and aahing over pretty explosions and bubbling concoctions in their fancy 3D lab, *this* is where the magic (and the science, mostly the science) actually happens.

Think of me as the grumpy, highly intelligent, and slightly overworked librarian of chemical reactions. The Unity client? Oh, that's just the flashy tour guide. It asks me, "Hey, what happens if I mix water and salt?" And I, in my infinite wisdom (and with a little help from some very smart AI), tell it *exactly* what happens. No, I don't draw the pretty pictures; I just provide the immutable, deterministic truth. Every. Single. Time.

## The Player's Command: My Daily To-Do List

Your players, bless their cotton socks, think they're running experiments. In reality, they're just sending me very polite (or sometimes very rude, depending on their code) text messages.

For example, when they drag `H₂O` and `NaCl` into a beaker under normal conditions, I get something like this:

```
> REACT --chemicals [H2O, NaCl] --environment [Earth]
```

And if they try to set Magnesium on fire in a CO2 environment (spoiler: it's a bad idea, but I'll still tell them *why* it's a bad idea):

```
> REACT --chemicals [Mg, CO2] --environment [Pure_Oxygen] --conditions [ignition_spark]
```

My job? To take that command and, with the precision of a Swiss watch and the speed of a caffeinated cheetah, figure out the cosmic truth.

## My Inner Workings: A Two-Step Program (for Chemical Reactions)

I'm not just some random number generator. Oh no. I'm a sophisticated, two-layered marvel of modern engineering.

1.  **Layer 1: The "Have I Seen This Before?" Cache (My Memory Palace)**
    Before I even *think* about doing any heavy lifting, I check my memory. I generate a super-secret, super-unique key from the player's request (like `[H2O, NaCl] + [Earth]`) and see if I've already calculated this exact reaction. If I have, *BAM!* Instant answer. This isn't just about being lazy (though I do enjoy a good nap); it's about **determinism**. The same inputs *must* produce the same outputs. Otherwise, the universe breaks, and nobody wants that.

2.  **Layer 2: The "Okay, Let's Think This Through" Reasoning Core (My Brain, Powered by AI and the Internet)**
    If it's a new one, I roll up my digital sleeves and engage my **Retrieval-Augmented Generation (RAG)** system. It's like having a super-smart intern who also has access to Wikipedia, but only the *really* reliable parts.
    *   **Retrieval:** I ping the mighty PubChem database. "Hey PubChem, tell me everything about H₂O and NaCl!" PubChem, being the good sport it is, sends me all the juicy scientific details.
    *   **Augmentation:** I then take all that factual goodness from PubChem and inject it directly into my thought process. It's like giving the AI a cheat sheet, but for science.
    *   **Generation:** Finally, my LLM (Large Language Model, not "Llama Llama Mama" as some of my less-informed colleagues call it) gets to work. It doesn't just make stuff up; it uses the provided facts to reason, step-by-step, and generate a structured JSON output. It's forced to "show its work" and stick to the script.

## My Output: The Truth, The Whole Truth, and Nothing But the JSON

I'm a stickler for format. My responses are always predictable, machine-readable JSON packets. The 3D client knows exactly what to do with them.

```json
{
  "products": [
    { "chemical_id": 3, "molecular_formula": "NaCl(aq)", "quantity": 1.0 }
  ],
  "state_of_product": "aqueous solution",
  "effects": [
    { "effect_type": "state_change", "product_chemical_id": 2, "final_state": "aqueous" }
  ],
  "explanation": "When table salt (NaCl) is added to water (H2O), it dissolves to form an aqueous solution of sodium chloride, where the Na+ and Cl- ions are surrounded by water molecules.",
  "is_world_first": false
}
```

*   **`products`**: The new stuff that appeared. Because, you know, conservation of mass and all that.
*   **`state_of_product`**: What's the final state of the main product? Is it a gooey mess? A fluffy cloud? I'll tell you.
*   **`effects`**: The flashy bits! Fizzing, fire, color changes. These are temporary, like a good magic trick. The client uses these to make pretty lights and sounds.
*   **`explanation`**: My little "fun fact" for the tips section. Because learning is fun, right? (Don't answer that.)
*   **`is_world_first`**: The golden ticket! If a player triggers an effect that no one else has ever seen before, this flag screams "CELEBRATE! YOU'RE A PIONEER!"

## The Tech Stack: My Glorious Components

I'm built from the finest digital components, each playing a crucial role:

*   **FastAPI (The Bouncer):** My front door. It handles all the incoming requests, makes sure they're properly formatted (no funny business!), and efficiently shuffles them off to the right place. It's super fast, just like its name suggests.
*   **User Authentication (JWT & Passlib):** Before you can blow things up (chemically speaking), I need to know who you are. This handles logins and registrations, giving out fancy JWT tokens. It's all about ownership, baby!
*   **PostgreSQL & SQLModel (My Long-Term Memory):** This is where I store all the important stuff: users, cached reactions, and the sacred "Discovery" ledger. SQLModel makes sure my data is always in tip-top shape.
*   **PubChem API (My Science Textbook):** My direct line to real-world chemical data. It's like having a super-smart, always-available chemistry professor on speed dial.
*   **DSPy (My Inner Monologue Orchestrator):** This is where the real AI magic happens. I don't just "prompt" an LLM; I *program* it using DSPy to ensure it thinks logically, uses the facts I give it, and gives me back exactly what I need.
*   **Alembic (My Database Janitor):** Keeps my database schema tidy and up-to-date. No more manual table changes for me!

## The Discovery System: Writing History, One Reaction at a Time

That `is_world_first` flag? That's my pride and joy! It means a player has done something truly unique. My Discovery system is like the official historian of the Chemezy universe. If an effect has never been logged before, I record it, attribute it to the player, and then that player gets bragging rights!

## The Bridge to the Visual World: Making Data Pretty

Once I've done all my hard work, I send my pristine JSON packet back to the 3D Unity client. The client then takes my cold, hard data and turns it into a dazzling display of visual and auditory awesomeness. It sees "fire" and makes a fire. It sees "fizz" and makes a fizzing sound. It sees "rapid_temperature_increase" and applies a shimmering heat-haze shader to the air above the beaker. It's like a translator, but for explosions.

## Quick Start (Because Who Reads Long Docs Anyway?)

Want to get me up and running? Here's the super-fast version:

1.  **Get the Code:** Clone this repo (you know the drill).
2.  **Environment:** Copy `.env.example` to `.env` and fill in the blanks (especially `SECRET_KEY` – make it long and random, like my thoughts after a particularly complex reaction).
3.  **Database:**
    ```bash
    docker-compose up postgres -d # Start the database
    sleep 10 # Give it a moment to wake up
    pip install -r requirements.txt # Get my dependencies
    alembic upgrade head # Set up my database tables
    ```
4.  **Run Me!**
    ```bash
    uvicorn app.main:app --reload # Watch me work!
    ```
    I'll be chilling at `http://localhost:8000`. Check out the API docs at `http://localhost:8000/docs`.

## Testing (Because Even I Need to Prove Myself)

Forget those complicated test frameworks. We're going old-school, with the raw power of `curl`!

1.  **Register a User (if you haven't already):**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/register" \
         -H "Content-Type: application/json" \
         -d '{"username": "abisam", "email": "abisam@example.com", "password": "abisam"}'
    ```

2.  **Login and Get Your Precious Token:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/auth/token" \
         -H "Content-Type: application/x-www-form-urlencoded" \
         -d "username=abisam&password=abisam"
    ```
    (Copy that `access_token` – it's your golden ticket!)

3.  **Make Me React! (The Fun Part):**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/reactions/react" \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
         -H "Content-Type: application/json" \
         -d '{"reactants": [{"chemical_id": 1, "quantity": 1.0}, {"chemical_id": 2, "quantity": 1.0}], "environment": "Earth (Normal)"}'
    ```

4.  **Check My Memory (The Cache):**
    ```bash
    curl -X GET "http://localhost:8000/api/v1/reactions/cache" \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
    ```

5.  **See My Stats (How Busy I've Been):**
    ```bash
    curl -X GET "http://localhost:8000/api/v1/reactions/stats" \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
    ```

## Why is This So Awesome? (Besides My Charming Personality)

*   **It's Smart:** I use AI, but I make sure it's grounded in real science. No random nonsense here!
*   **It's Fast:** Thanks to caching, I can answer repeat questions in a blink.
*   **It's Fair:** Same inputs, same outputs. Always.
*   **It's Secure:** Your data (and my secrets) are safe with me.
*   **It's Funny:** (Okay, maybe that's just me.)
