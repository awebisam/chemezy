# Chemezy Backend - Product Overview

Chemezy is a chemistry simulation game backend that serves as "the source code of reality" for the Chemezy universe. Players interact with a 3D frontend to perform chemical experiments, while this backend provides the scientific intelligence and deterministic reaction calculations.

## Core Purpose
- Process chemical reaction requests from the SvelteKit frontend
- Generate scientifically accurate reaction outcomes using AI and real chemical data
- Maintain a discovery system where players can be the first to trigger unique reactions
- Cache reactions for deterministic results (same inputs = same outputs)

## Key Features
- **Two-layer processing**: Memory cache for known reactions, AI reasoning for new ones
- **RAG system**: Uses PubChem database for real chemical data
- **Discovery tracking**: Records world-first reactions and attributes them to players
- **JWT authentication**: User management and secure API access
- **Rate limiting**: Prevents abuse while maintaining performance

## API Response Format
All reactions return structured JSON with:
- `products`: New chemicals created
- `state_of_product`: Final state of main product
- `effects`: Visual/audio effects for the frontend (fizzing, fire, color changes)
- `explanation`: Educational content for players
- `is_world_first`: Flag for unique discoveries