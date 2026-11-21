# SynapLang vs Python 3.12 Benchmarks

Generated automatically by `benchmarks/benchmark_vs_python.py`.


### Benchmark Results Summary Table

| Benchmark Task | Python Tokens | SynapLang Tokens | Python Time (ms) | Synap Wasm Time (ms) | Speedup |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Recursive Fibonacci (n=25)** | 39 | 60 | 27.89 ms | 1.21 ms | **23.13x** |
| **Iterative Factorial (n=12)** | 39 | 71 | 0.18 ms | 0.05 ms | **3.67x** |
| **Array Sum (10,000 Elements)** | 24 | 112 | 2.34 ms | 0.09 ms | **25.06x** |
| **Bubble Sort (300 Elements)** | 75 | 185 | 0.26 ms | 0.14 ms | **1.84x** |
| **Point Struct Distance Squared (5,000 iterations)** | 70 | 128 | 4.74 ms | 0.14 ms | **34.06x** |

### Key Architectural Insights:
- **Zero Indentation Fragility:** S-expressions completely eliminate Python's `IndentationError` when LLMs perform surgical refactorings.
- **WebAssembly Speed:** Algorithms with tight loops and memory arrays benefit from Wasmtime JIT compilation down to native machine code.
- **Self-Healing Diagnostics:** When broken, SynapLang emits structured JSON compiler errors with exact node locations and `suggested_fix` payloads.
