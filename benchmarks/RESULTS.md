# SynapLang vs Python 3.12 Benchmarks

Generated automatically by `benchmarks/benchmark_vs_python.py`.


### Benchmark Results Summary Table

| Benchmark Task | Python Tokens | SynapLang Tokens | Python Time (ms) | Synap Wasm Time (ms) | Speedup |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Recursive Fibonacci (n=25)** | 39 | 60 | 35.35 ms | 1.29 ms | **27.44x** |
| **Iterative Factorial (n=12)** | 39 | 71 | 0.15 ms | 0.06 ms | **2.44x** |
| **Array Sum (10,000 Elements)** | 24 | 112 | 2.62 ms | 0.12 ms | **21.67x** |
| **Bubble Sort (300 Elements)** | 75 | 185 | 0.24 ms | 0.19 ms | **1.26x** |
| **Point Struct Distance Squared (5,000 iterations)** | 70 | 128 | 5.86 ms | 0.19 ms | **31.60x** |

### Key Architectural Insights:
- **Zero Indentation Fragility:** S-expressions completely eliminate Python's `IndentationError` when LLMs perform surgical refactorings.
- **WebAssembly Speed:** Algorithms with tight loops and memory arrays benefit from Wasmtime JIT compilation down to native machine code.
- **Self-Healing Diagnostics:** When broken, SynapLang emits structured JSON compiler errors with exact node locations and `suggested_fix` payloads.
