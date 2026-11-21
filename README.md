# ⚡ SynapLang: The AI-Native Programming Language

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Target: WebAssembly](https://img.shields.io/badge/target-WebAssembly-654FF0.svg)](https://webassembly.org/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> *"Human code is legacy. Software is no longer written for human eyes—it is synthesized by neural models and executed on bare metal. SynapLang is the first programming language built from scratch for Large Language Models and autonomous coding agents."*

---

## 🌌 The Vision

For over seventy years, programming languages were designed to cater to human biological limitations:
* **Indentation & Formatting Fragility:** Python relies on significant whitespace. A single misplaced space during surgical line diffs breaks program execution.
* **Syntactic Entropy:** Human languages provide 10 different ways to write a simple loop. AI models waste probability mass debating cosmetic styles rather than algorithmic correctness.
* **Token Fragmentation:** Human punctuation cascades (`}}});`) get shredded into multiple fragmented BPE tokens, bloating context windows and slowing down inference.
* **Opaque Error Traces:** Compilers print English essays with ASCII arrows. AI agents cannot parse unstructured prose reliably in autonomous feedback loops.

**AIL changes everything:**
1. **Homoiconic S-Expressions:** The syntax *is* the Abstract Syntax Tree (AST). 1:1 bijection. Zero parsing ambiguity.
2. **Machine-Readable Diagnostics:** When an error occurs, the compiler outputs structured **JSON** with exact AST locations and actionable suggested fixes for instant self-healing.
3. **Bare-Metal Speed with WebAssembly:** Directly compiles to WebAssembly (`.wat` / Wasm) for near-C execution performance inside a sandboxed environment.
4. **Strict Static Typing:** Catch 100% of type bugs at compile time (`i32`, `f64`, `bool`).

---

## 🏗️ Architecture Pipeline

```mermaid
flowchart LR
    A["🤖 AI Agent\n(Generates S-Expressions)"] --> B["🔍 Lark Parser\n(AST Generation)"]
    B --> C["🛡️ Strict Type Checker\n(Diagnostics Engine)"]
    C -- "Compile Error" --> D["📄 Machine JSON Diagnostic\n(Immediate Self-Healing)"]
    D --> A
    C -- "Valid AST" --> E["⚙️ WebAssembly Codegen\n(Emits .wat)"]
    E --> F["🚀 Wasmtime Runtime\n(Near-Native Speed)"]
```

---

## 🥊 Human Languages vs. AIL

| Dimension | Legacy Human Languages (Python / JS / C++) | AIL (AI-Native Language) |
| :--- | :--- | :--- |
| **Primary Consumer** | Human eyes & short-term memory | LLMs & Autonomous AI Agents |
| **Parsing Precedence** | Complex operator precedence tables | Unambiguous Tree / S-expressions |
| **Whitespace Impact** | Significant indentation errors | Whitespace invariant |
| **Compiler Feedback** | Human prose & ASCII error strings | **Structured JSON diagnostics with auto-fix hints** |
| **Execution Model** | Slow dynamic runtime or heavy toolchains | **Blazing-fast sandboxed WebAssembly (Wasm)** |
| **Context Window Cost**| Heavy boilerplate & token fragmentation | Minimal token overhead, maximum semantic density |

---

## ⚡ Quickstart in 10 Seconds

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/ai-lang.git
cd ai-lang
pip install -r requirements.txt
```

### 2. Run an Example (Fibonacci)
```bash
python src/cli.py run examples/fibonacci.ail --fn main
# Output: 55
```

### 3. Check Code with Machine JSON Diagnostics
```bash
python src/cli.py check examples/fibonacci.ail --json
```
Output:
```json
{
  "status": "ok",
  "message": "Type check passed successfully"
}
```

If you introduce a type error, the compiler outputs actionable structured data:
```json
{
  "status": "error",
  "error_type": "TypeMismatch",
  "message": "Binary operator '+' requires identical operand types, got 'i32' and 'f64'",
  "location": {
    "line": 3,
    "column": 12
  },
  "context": {
    "node": "BinaryOp",
    "expected_type": "i32",
    "found_type": "f64"
  },
  "suggested_fix": "Ensure both operands are of the same arithmetic type ('i32')"
}
```

---

## 💻 Language Syntax at a Glance

### Recursive Fibonacci:
```lisp
(fn fib (n: i32) -> i32
  (if (<= n 1)
    n
    (+ (call fib (- n 1))
       (call fib (- n 2)))))

(fn main () -> i32
  (call fib 10))
```

### While Loop Accumulator:
```lisp
(fn sum_up_to (n: i32) -> i32
  (let total: i32 0)
  (let i: i32 1)
  (while (<= i n)
    (set total (+ total i))
    (set i (+ i 1)))
  total)

(fn main () -> i32
  (call sum_up_to 100))
```

---

## 🧪 Running Automated Tests

Run the full automated test suite with `pytest`:
```bash
pytest
```
All 19 tests verify arithmetic, nested precedence, control flow, recursion, type checking, and automated agent self-healing loops.

---

## 🤝 Contributing & Community

AIL is 100% open-source and community-driven. Check out [CONTRIBUTING.md](CONTRIBUTING.md) to get started on Good First Issues!

## 📜 License
Distributed under the permissive **MIT License**. See [LICENSE](LICENSE) for details.
