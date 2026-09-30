# Local Agent Rules (MVP Phase Patch)

## 📌 Core Context

1. **Project Phase**: Strictly **MVP (Minimum Viable Product)** core verification phase.
2. **Ultimate Goal**: Validate core business flows at maximum speed with minimum code volume. Speed and simplicity take priority over perfect architecture.

## ⚠️ Project-Specific Overrides and Additions

These rules supplement or override the global `AGENTS.md` for this project:

1. **Hardcoding Authorization**
   - To achieve maximum speed, if hardcoding a configuration such as an API base URL, platform enum, or price tier saves more than 10 lines of abstraction, hardcoding is preferred and allowed during the MVP phase.

2. **Conditional Reuse Exemption**
   - For repeated logic under 5 lines, or for business cases expected to diverge soon, keeping the duplication is allowed. Avoid abstractions that add complexity without reducing maintenance cost.

3. **Tech Stack**
   - **Front-end**: Vue 3 with `<script setup>` and pure JavaScript; use the Composition API and lightweight composables.
   - **Back-end/Scripts**: Python 3.11+, managed by `uv`.
   - **UI**: Prioritize interaction flows. Pixel-perfect matching, complex animations, and non-fatal transition states are out of scope for MVP verification.

## 🤖 MVP Self-Correction

- Can this be solved with a one-liner or a simpler implementation?
- Did I create a generic component with 10+ props for only two simple pages? If so, simplify it.
- Am I adding defensive handling for a non-fatal edge case that is not relevant to MVP validation? If so, keep the handling minimal.

## Project-Specific Validation and Git Additions

- Under the global validation rules, default to the smallest targeted test or check directly related to the change. Run the full test suite only for production deployment, high-risk changes, or when explicitly requested.
- Do not use destructive commands such as `git reset --hard` or `git checkout --` unless explicitly requested.
- Before committing, inspect the diff and confirm that it contains no unrelated files or generated artifacts.
