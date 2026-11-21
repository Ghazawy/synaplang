# Contributing to AIL (AI-Native Programming Language)

Welcome to the forefront of AI-native systems programming! 🚀

We believe the future of software development will be driven by autonomous coding agents. By contributing to AIL, you are helping build the foundational infrastructure for agentic computing.

---

## 🎯 Good First Issues & Roadmap

Here are exciting areas where we welcome community pull requests:

1. **Arrays & Linear Memory Allocation:**
   - Add native support for fixed-size and dynamic arrays in WebAssembly linear memory (`(array: i32 [1, 2, 3])`).
2. **String Primitives:**
   - Implement UTF-8 string encoding and string-view operations targeting Wasm memory.
3. **GBNF Grammar Exporter:**
   - Build a CLI command `ail export-gbnf` that exports `grammar/syntax.lark` into `.gbnf` format for direct use in `llama.cpp` and `Ollama` for 100% constrained decoding.
4. **Interactive REPL:**
   - Create a live interactive terminal REPL for quick experimentation.
5. **Standard Library Expansion:**
   - Mathematical utilities (e.g., `sqrt`, `pow`, bitwise operators).

---

## 🛠️ Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/ai-lang.git
   cd ai-lang
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the test suite:**
   ```bash
   pytest
   ```

---

## 📋 Pull Request Guidelines

1. Ensure all existing tests pass (`pytest`).
2. Add new unit tests in `tests/` covering your added language feature.
3. Keep code modular, strictly typed, and clearly commented.
4. Update `docs/` and `README.md` if syntax or CLI flags are modified.

Thank you for contributing to the open-source AI ecosystem!
