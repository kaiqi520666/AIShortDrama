# Local Agent Rules (MVP Phase Patch)

## 📌 Core Context
1. **Project Phase**: Strictly **MVP (Minimum Viable Product)** core verification phase.
2. **Ultimate Goal**: Validate core business flows at maximum speed with minimum code volume. Speed and simplicity > perfect architecture.

## ⚠️ Global Rules Overrides
*The following rules override or patch the global AGENTS.md for this specific project:*

1. **Hardcoding Authorization**:
   - To achieve maximum speed, if hardcoding a configuration (e.g., API base URL, platform enums, price tiers) saves over 10 lines of abstraction, **hardcoding is preferred and allowed** in this stage.
2. **Conditional Exemption for Reuse**:
   - While global rules enforce "extract at 2+ instances", **you may keep duplicate code** if the repeated logic is under 5 lines or if the two business cases are expected to diverge soon. Avoid over-engineering components.
3. **Tech Stack Specs**:
   - **Front-end**: Vue 3 (`<script setup>`) with pure JS. Fully utilize Composition API and lightweight Composables.
   - **Back-end/Scripts**: Python 3.11+, fully managed by `uv`.
   - **UI Tolerance**: Focus on interaction flows. Ignore perfect visual pixel-matching, complex animations, or non-fatal transition states.

## 🤖 MVP Self-Correction (Before Output)
- [ ] Can I solve this using a single line (One-liner via ternary, `??`, `?.`, list comprehension) or a cruder method?
- [ ] Did I build a complex, generic component with 10+ props just to handle 2 simple pages? (If yes, simplify it immediately)
- [ ] Am I wasting time writing overly safe error-handling for non-fatal edge cases? (If yes, let it fail or just print a basic log)