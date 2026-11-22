# RFC-0001: SynapLang Production Architecture & Advanced Language Specification

**RFC Identifier**: SYNAP-RFC-0001  
**Author(s)**: Lead Systems Architect & Compiler Specialist  
**Status**: Authoritative Technical Specification  
**Version**: 1.0.0  
**Target Milestone**: v0.2.0 – v1.0.0  
**Repository**: [https://github.com/Ghazawy/synaplang](https://github.com/Ghazawy/synaplang)  
**Date**: November 2026  

---

## 1. Executive Summary & Architectural Rationale

### 1.1 The AI-Native Programming Thesis
SynapLang (AIL) is engineered from first principles as an **AI-native programming language targeting WebAssembly (Wasm32)** for verifiable, deterministic, and high-performance autonomous agent execution.

Traditional programming languages designed for human software engineers present severe structural impediments to Large Language Model (LLM) code generation and automated tool execution:
1. **Syntactic and Indentation Fragility**: In languages like Python, subtle token misalignments, whitespace drift, or off-by-one indentations cause unrecoverable syntax and scoping errors during token sampling.
2. **Ambiguous Abstract Syntax Bijection**: Complex infix grammars with deep operator precedence hierarchies create non-linear mapping between textual tokens and semantic abstract syntax trees (ASTs).
3. **Opaque Error Feedback**: Standard compiler diagnostics are human-centric, unstructured, and noisy, requiring multi-turn conversational repair cycles that rapidly exhaust token budgets and degrade agent reasoning context.
4. **Heavyweight Virtualization**: Running untrusted guest code via Docker containers, virtual machines, or native OS processes incurs prohibitive cold-start latency (100ms - 2s), high RAM footprints, and significant security exposure.

SynapLang resolves these foundational flaws through a four-pillar design:
* **Homoiconic S-Expression Grammar**: Zero indentation sensitivity, uniform prefix syntax `(operator operand...)`, and explicit parenthetical boundaries guarantee a 1:1 structural bijection between the token stream and the AST.
* **Grammar-Constrained Decoding (GBNF)**: A formal context-free grammar allows inference engines (`llama.cpp`, Ollama, vLLM) to mask invalid logits during sampling, guaranteeing **0% syntax errors** at the token generation level.
* **Machine-Readable JSON Compiler Diagnostics**: Type checking and compilation failures emit structured JSON schemas containing exact line/column locations, node identifiers, expected vs. found types, and actionable `suggested_fix` instructions for zero-shot autonomous self-healing.
* **Deterministic WebAssembly Sandboxing**: Compiling directly to WebAssembly Text (`.wat`) and executing via JIT runtimes (Wasmtime) delivers near-native performance (up to 34x faster than Python 3.12) with sub-millisecond cold starts and strictly isolated linear memory.

### 1.2 Purpose of this Specification
This RFC formalizes the complete technical blueprint required to transition SynapLang from its current v0.1.0 prototype into an enterprise-grade, production-ready programming language and runtime ecosystem. It details the target compiler pipeline, grammar formalization, module system, advanced static typing enhancements, memory architecture, standard library, and concrete language examples.

---

## 2. Current vs. Target Compiler Architecture

### 2.1 Current Architecture (v0.1.0 Baseline)
The initial implementation of SynapLang is authored in Python 3.10+ and comprises five discrete stages:

```
[ Synap Source (.ail) ]
          │
          ▼  Stage 1: Lexing & Parsing (Lark LALR(1) + ASTBuilder in src/parser.py)
[ Abstract Syntax Tree (src/ail_ast.py) ]
          │
          ▼  Stage 2: Static Type Checking (3-Pass TypeChecker in src/type_checker.py)
    Pass 0: Struct registration & field offset cataloging
    Pass 1: Function signature cataloging
    Pass 2: Lexical scope checking, type inference & propagation
          ├──── Error ───► Structured JSON Diagnostic (stderr / API)
          │
          ▼ (Validated AST)
[ WebAssembly Text Generation (WasmCodegen in src/codegen_wasm.py) ]
    - Static String Table emission
    - Runtime helper emission (_alloc_arr, _alloc_struct, _str_concat)
    - Instruction emission (.wat)
          │
          ▼  Stage 3: JIT Execution (Runner in src/runner.py)
    - Wasmtime Engine, Store, and Linker instantiation
    - Host function binding ("env": print_str, println_str, print_i32, print_f64)
    - Execution of exported WebAssembly function
```

#### Verified Strengths of Baseline:
* Fast iterative prototyping with Lark LALR(1).
* Accurate source-location tracking (`SourceLocation(line, column)`).
* Fully working end-to-end execution verified across 41 automated unit tests.
* Clean separation of concerns between parsing, static analysis, codegen, and host execution.

#### Architectural Bottlenecks in Baseline:
1. **Python Host Overhead**: Compiling via Python incurs interpreter startup latency (~50-100ms) and dependency management overhead (`wasmtime-py`, `lark`).
2. **Single-File Compilation**: The compiler processes a single `.ail` file into a single `.wat` module; there is no support for imports, multi-file projects, or incremental compilation.
3. **Absence of Optimization Passes**: The AST is translated directly to WAT without constant folding, dead code elimination, or common subexpression elimination.
4. **Monotonic Heap**: Memory allocations use a global monotonic bump pointer (`$heap_ptr`) without reclamation or deallocation.
5. **Simulated Playground**: The web interface in `site/app.js` runs pre-canned JavaScript closures rather than executing the actual compiler inside the browser.

---

### 2.2 Target Architecture (v0.5.0 – v1.0.0 Production)
The target architecture introduces a two-phase evolution:

```
                        ┌────────────────────────────────────────────────────────┐
                        │              Target Compilation Pipeline               │
                        └────────────────────────────────────────────────────────┘

     [ Module Source (.ail) ]               [ Imported Modules / stdlib ]
                 │                                        │
                 └───────────────────┬────────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │    Lexer & Parser (Rust / C++)    │
                   │  Zero-copy UTF-8 S-Expr parser    │
                   └─────────────────┬─────────────────┘
                                     │ AST
                                     ▼
                   ┌───────────────────────────────────┐
                   │ Module Resolver & Dependency Graph│
                   │ Cycle detection, topological sort │
                   └─────────────────┬─────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │ Multi-Pass Bidirectional Type     │
                   │ Checker & Monomorphization Engine │
                   └─────────────────┬─────────────────┘
                                     │ Typed AST (TAST)
                                     ▼
                   ┌───────────────────────────────────┐
                   │   Synap Intermediate Rep (SIR)    │
                   │ SSA form, CFG, Inlining, DCE, C-Fold│
                   └─────────────────┬─────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
   ┌────────────────────────────────┐ ┌────────────────────────────────┐
   │    Direct Binary Wasm Emitter  │ │    Optimized WAT Text Emitter  │
   │  (wasm-encoder / Wasm binary)  │ │   Human-readable / LLM verify  │
   └────────────────┬───────────────┘ └────────────────┬───────────────┘
                    │                                  │
                    └────────────────┬─────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │     Execution & Sandbox Engine    │
                   │  - Wasmtime (Server / CLI / Edge) │
                   │  - WebAssembly (Browser / V8 / JSC│
                   │  - WASI 0.2 / Component Model     │
                   └───────────────────────────────────┘
```

#### Key Architecture Components:

1. **Rust-Based Core Compiler (`synapc`)**:
   - Written in modern memory-safe Rust with zero external runtime dependencies.
   - Compiles both as a standalone native binary (`synapc`) and to `wasm32-unknown-unknown` (`synapc.wasm`).
   - The compiled Wasm binary can run directly inside web browsers (enabling a 100% genuine in-browser playground), Node.js, Cloudflare Workers, and in-agent execution loops with sub-millisecond execution.

2. **Synap Intermediate Representation (SIR)**:
   - Linear Static Single Assignment (SSA) form.
   - Enables standard compiler optimization passes:
     * **Constant Folding & Propagation**: Pre-computes static arithmetic and string literals at compile time.
     * **Dead Code Elimination (DCE)**: Prunes unused module exports, unreachable pattern match arms, and unused functions.
     * **Function Inlining**: Automatically inlines small leaf functions and higher-order function arguments (`map`, `filter`).
     * **Escape Analysis**: Distinguishes stack-allocatable structs/arrays from heap allocations.

3. **Multi-Target Code Emission**:
   - Direct binary encoding via `wasm-encoder`, generating compressed `.wasm` binaries without requiring external tools (`wat2wasm`).
   - Full `.wat` generation preserved for debugging, auditing, and LLM verification.

---

## 3. Formal Language Grammar & Syntax Formalization

### 3.1 Lexical Specifications & Tokens
SynapLang source files are UTF-8 encoded text streams. Whitespace comprises spaces, tabs, carriage returns, and newlines. Whitespace is insignificant except as a token delimiter.

#### Lexical Rules:
* **Line Comments**: Initiated by a semicolon `;` and extend to the end of the line.
* **Identifiers**: Match `[a-zA-Z_][a-zA-Z0-9_-]*`. Special characters `?`, `!`, and `->` are permitted in function names and predicates (e.g. `empty?`, `panic!`, `to-string`).
* **Integer Literals (`i32`)**: Match `-?[0-9]+` (decimal) or `0x[0-9a-fA-F]+` (hexadecimal).
* **Float Literals (`f64`)**: Match `-?[0-9]+\.[0-9]+([eE][+-]?[0-9]+)?`.
* **Boolean Literals (`bool`)**: `true` and `false`.
* **String Literals (`string`)**: Enclosed in double quotes `"..."`, supporting standard escape sequences (`\"`, `\\`, `\n`, `\t`, `\r`, `\0`, `\xHH`).

### 3.2 Formal EBNF Grammar Specification
The formal grammar of SynapLang is defined below in Extended Backus-Naur Form (EBNF):

```ebnf
(* ========================================== *)
(* SynapLang Production EBNF Specification   *)
(* ========================================== *)

Module          ::= "(" "module" ModulePath ModuleBody* ")"
                  | TopLevelDef*

ModuleBody      ::= ImportDef | ExportDef | TopLevelDef

ImportDef       ::= "(" "import" ( StringLiteral | ModulePath ) ( "(" SymbolList ")" | ":as" Identifier | "::" "[" SymbolList "]" ) ")"
ExportDef       ::= "(" "export" SymbolList ")"
SymbolList      ::= ( Identifier | ModulePath )+
ModulePath      ::= Identifier ("::" Identifier)*

TopLevelDef     ::= StructDef
                  | EnumDef
                  | FunctionDef
                  | GlobalLet

Type            ::= PrimitiveType
                  | ModulePath
                  | GenericType
                  | FunctionType

PrimitiveType   ::= "i32" | "f64" | "bool" | "string" | "void"
GenericType     ::= ( Identifier | ModulePath ) "<" TypeList ">"
TypeList        ::= Type ("," Type)*
                  | Type+
FunctionType    ::= "(" ( "fn" | "fn-type" ) ( "[" Type* "]" | "(" Type* ")" ) "->" Type ")"

StructDef       ::= "(" "struct" Identifier TypeParams? FieldList ")"
FieldList       ::= FieldDef*
FieldDef        ::= "[" Identifier ":" Type "]"
                  | "(" Identifier ":" Type ")"

EnumDef         ::= "(" "enum" Identifier TypeParams? VariantList ")"
VariantList     ::= VariantDef+
VariantDef      ::= Identifier
                  | "(" Identifier FieldList ")"

TypeParams      ::= "[" Identifier+ "]"

FunctionDef     ::= "(" "fn" Identifier TypeParams? "(" ParamList ")" "->" Type Expr+ ")"
ParamList       ::= (ParamDef)*
ParamDef        ::= "[" Identifier ":" Type "]"
                  | "(" Identifier ":" Type ")"
                  | Identifier ":" Type

GlobalLet       ::= "(" "let" Identifier ":" Type Expr ")"

Expr            ::= Literal
                  | Identifier
                  | ModulePath
                  | LetExpr
                  | SetExpr
                  | BinaryExpr
                  | UnaryExpr
                  | IfExpr
                  | WhileExpr
                  | BlockExpr
                  | CallExpr
                  | MatchExpr
                  | ReturnExpr
                  | StructNewExpr
                  | StructGetExpr
                  | StructSetExpr
                  | ArrayNewExpr
                  | ArrayGetExpr
                  | ArraySetExpr
                  | ArrayLenExpr
                  | ArrayLitExpr

Literal         ::= IntegerLiteral | FloatLiteral | BooleanLiteral | StringLiteral

LetExpr         ::= "(" "let" Identifier ( ":" Type )? Expr ")"
                  | "(" "let" "(" Identifier ":" Type ")" Expr ")"

SetExpr         ::= "(" "set" Identifier Expr ")"

BinaryExpr      ::= "(" BinaryOp Expr Expr ")"
BinaryOp        ::= "+" | "-" | "*" | "/" | "%"
                  | "==" | "!=" | "<" | "<=" | ">" | ">="
                  | "and" | "or" | "bit-and" | "bit-or" | "bit-xor" | "shl" | "shr"

UnaryExpr       ::= "(" UnaryOp Expr ")"
UnaryOp         ::= "neg" | "not" | "bit-not"

IfExpr          ::= "(" "if" Expr Expr Expr? ")"

WhileExpr       ::= "(" "while" Expr Expr+ ")"

BlockExpr       ::= "(" "block" Expr+ ")"
                  | "(" "do" Expr+ ")"

CallExpr        ::= "(" "call" Expr Expr* ")"
                  | "(" ( Identifier | ModulePath ) ( "<" TypeList ">" )? Expr* ")"

MatchExpr       ::= "(" "match" Expr MatchArm+ ")"
MatchArm        ::= "(" Pattern Expr+ ")"

Pattern         ::= Literal
                  | "_"
                  | Identifier
                  | "(" Identifier Pattern* ")"

ReturnExpr      ::= "(" "return" Expr ")"

StructNewExpr   ::= "(" "struct_new" Identifier Expr* ")"
                  | "(" "new" Identifier Expr* ")"

StructGetExpr   ::= "(" "struct_get" Expr Identifier ")"
                  | "(" "." Expr Identifier ")"

StructSetExpr   ::= "(" "struct_set" Expr Identifier Expr ")"

ArrayNewExpr    ::= "(" "arr_new" ( "<" Type ">" )? Expr ")"
ArrayGetExpr    ::= "(" "arr_get" Expr Expr ")"
ArraySetExpr    ::= "(" "arr_set" Expr Expr Expr ")"
ArrayLenExpr    ::= "(" "arr_len" Expr ")"
ArrayLitExpr    ::= "(" "array" ( "<" Type ">" )? Expr* ")"
```

### 3.2.1 EBNF Grammar Reconciliation & Formal Semantics
To ensure deterministic parsing and complete alignment between grammar definitions, code examples, and LLM code generation patterns, the EBNF formalization incorporates four critical syntax reconciliation rules:

1. **Dual TypeList Flexibility (`Result<f64, string>` and `Result<f64 string>`)**:
   - `TypeList` cleanly supports both comma-delimited `Type ("," Type)*` AND whitespace-delimited `Type+`.
   - LLMs frequently alternate between comma-delimited types (`Result<f64, string>`, `Pair<i32, bool>`) and whitespace-separated S-expression styles (`Result<f64 string>`, `Pair<i32 bool>`).
   - The grammar parses both identically without ambiguity or parser conflicts, preventing syntax failure on diverse prompt formatting.

2. **Explicit Generic Type Arguments on Calls (`CallExpr`)**:
   - `CallExpr` explicitly permits optional generic type arguments: `(fn_name ["<" TypeList ">"] arg1 arg2 ...)`.
   - This formally validates generic constructor and allocation invocations such as `(vec_new<i32> 4)`, `(arr_new<f64> 100)`, and `(coll::queue_new<Point> 16)`.

3. **Hierarchical Qualified Paths (`ModulePath`)**:
   - `ModulePath` formalizes `Identifier ("::" Identifier)*`.
   - The `::` separator is permitted in module declarations (`(module math::geometry ...)`), selective and bracketed imports (`(import math::geometry::[Point, distance])` or `(import "std::math" (sqrt sin))`), and qualified expression/type references (`coll::Queue<i32>`, `math::geometry::distance`).

4. **Unified Function Type Signatures (`FunctionType`)**:
   - `FunctionType` reconciles both `(fn [Type*] -> Type)` / `(fn-type [Type*] -> Type)` and parenthesized forms `(fn (Type*) -> Type)` / `(fn-type (Type*) -> Type)`.
   - This ensures 100% syntactic parity across all documentation examples, higher-order function definitions (`map`, `filter`), and formal specifications.

### 3.3 GBNF Alignment (Grammar-Constrained Decoding)
To ensure 100% syntactic correctness during LLM generation, SynapLang maintains an official GBNF grammar (`grammar/synap.gbnf`). When querying local models via `llama.cpp` or Ollama, the model's logits are strictly constrained to this grammar.

Key enhancements for production GBNF alignment:
1. **Generic and Enum Expansion**: Include `(enum ...)` and `(match ...)` rules in `grammar/synap.gbnf`.
2. **Whitespace and Comment Robustness**: Support inline `;` comments without breaking token sequences.
3. **Number Literals**: Strict regular expressions for float exponents and negative numbers.

---

## 4. Module and Packaging System

### 4.1 Module Definition & Declaration
Every SynapLang file conceptually defines a module. Explicit module naming is supported via the top-level `(module ...)` form:

```lisp
(module math::geometry
  (export Point distance area)
  
  (struct Point
    [x: f64]
    [y: f64])
    
  (fn distance (p1: Point p2: Point) -> f64
    (let dx: f64 (- (struct_get p2 x) (struct_get p1 x)))
    (let dy: f64 (- (struct_get p2 y) (struct_get p1 y)))
    (sqrt (+ (* dx dx) (* dy dy))))
)
```

### 4.2 Import and Export Semantics

#### Selective Imports:
Imports specify relative file paths, module paths, or standard library identifiers, importing specific symbols into the current lexical scope via symbol lists or bracketed module path syntax:
```lisp
(import "std::math" (sqrt sin cos PI))
(import math::geometry::[Point, distance])
(import math::geometry (Point distance))
(import "./models/user.ail" (User create_user))
```

#### Qualified / Aliased Imports:
Namespaces prevent symbol collisions across large multi-agent projects:
```lisp
(import "std::collections" :as coll)

(fn build_queue () -> void
  (let q: coll::Queue<i32> (coll::queue_new<i32> 64))
  ...)
```

#### Re-exports:
Modules can aggregate and re-export symbols from submodules:
```lisp
(module std
  (import "std::core" (abs min max))
  (import "std::io" (println print))
  (export abs min max println print))
```

### 4.3 Multi-File Compilation & Link-Time Consolidation
The compiler resolves imports according to the following deterministic algorithm:
1. **Dependency Resolution**: Parse the root module, scan all `(import ...)` statements, and recursively locate referenced source files.
2. **Cycle Detection**: Construct a Directed Acyclic Graph (DAG) of module dependencies. If a cycle $A \to B \to A$ is detected, emit a structured JSON diagnostic (`CircularDependencyError`).
3. **Topological Ordering**: Flatten the dependency graph into a topological sequence where dependencies precede dependents.
4. **Namespace Mangling & Linking**:
   - Symbols are internally qualified with their canonical module path (e.g., `math::geometry::distance` $\to$ `$math_geometry_distance`).
   - Private module functions (not declared in `(export ...)`) are hidden from external module symbol tables.
   - All modules are linked and consolidated into a single WebAssembly module with a unified linear memory space, shared type table, and function table.

---

## 5. Advanced Typing Enhancements

### 5.1 Parametric Polymorphism (Generics)
SynapLang v0.1.0 only supports monomorphic `arr_i32`. Production workloads require generic collections and algorithms.

#### Generic Syntax:
```lisp
;; Generic struct definition
(struct Pair [T U]
  [first: T]
  [second: U])

;; Generic function definition
(fn identity [T] (x: T) -> T
  x)

;; Generic array allocation
(let numbers: Array<f64> (arr_new<f64> 100))
(let points: Array<Point> (arr_new<Point> 10))
```

#### WebAssembly Compilation Strategy: Monomorphization
SynapLang adopts **monomorphization** (specialization) rather than boxing or pointer-tagging erasure:
* When the type checker encounters `Array<f64>` and `Array<Point>`, it generates specialized runtime layouts:
  - `Array<i32>`: 4-byte element stride, loaded via `i32.load`.
  - `Array<f64>`: 8-byte element stride, loaded via `f64.load`.
  - `Array<Point>`: 4-byte pointer stride, loaded via `i32.load`.
* Monomorphization guarantees **zero boxing overhead**, optimal CPU cache locality, and natural WebAssembly instruction selection without dynamic runtime dispatch penalties.

#### 64-Bit Float Array Memory Layout & Strict 8-Byte Alignment:
In WebAssembly (Wasm32), 64-bit floating point instructions (`f64.load` and `f64.store`) require or strongly benefit from 8-byte natural alignment. Misaligned memory operations incur CPU execution penalties and violate SIMD vector alignment expectations (`v128`).

SynapLang formally mandates **strict 8-byte alignment** for all `Array<f64>` instances:
```
Memory Layout for Array<f64>:
Byte Offset:   -8          -4              0               8               16
Payload:       [padding]   [length: i32]   [elem 0: f64]   [elem 1: f64]   ...
Type:          4 bytes     i32 (4 bytes)   f64 (8 bytes)   f64 (8 bytes)   f64 (8 bytes)
Alignment:     aligned(8)  aligned(4)      aligned(8)      aligned(8)      aligned(8)
```

1. **Base Pointer Alignment Constraint**:
   When allocating an `Array<f64>`, the runtime allocator aligns the element base pointer (`$ptr`) such that `($ptr & 7) == 0` (i.e. strictly divisible by 8).
2. **Length Header Offset**:
   The 32-bit array length is stored at `($ptr - 4)`. A 4-byte padding word is placed at `($ptr - 8)` if necessary, guaranteeing that the previous memory block end and the current array's length/elements remain on an 8-byte boundary.
3. **Hardware Efficiency**:
   Ensuring `$ptr % 8 == 0` allows the WebAssembly JIT compiler (Wasmtime, V8) to emit native aligned scalar and SIMD SSE/AVX/NEON load/store instructions without unaligned access micro-faults or trapping.

---

### 5.2 Algebraic Data Types (Sum Types / Tagged Unions)
Sum types allow modeling data that can take one of several discrete variants.

#### Syntax:
```lisp
;; Standard Option Type
(enum Option [T]
  None
  (Some [value: T]))

;; Standard Result Type for Error Handling
(enum Result [T E]
  (Ok [value: T])
  (Err [error: E]))

;; Custom Domain Union
(enum Shape
  (Circle [radius: f64])
  (Rectangle [width: f64] [height: f64])
  Point)
```

#### Memory Layout of Sum Types:
Sum types are laid out in linear memory as a **tagged union record**:
```
┌─────────────────────────┬────────────────────────────────────────┐
│ Tag / Discriminant      │ Payload Bytes                          │
│ (4 bytes, i32)          │ (max(sizeof(Variant_i)) bytes)         │
├─────────────────────────┼────────────────────────────────────────┤
│ 0x00000001 (Circle)     │ radius: f64 (8 bytes)                  │
├─────────────────────────┼────────────────────────────────────────┤
│ 0x00000002 (Rectangle)  │ width: f64 (8 bytes) + height: f64 (8) │
└─────────────────────────┴────────────────────────────────────────┘
```
1. **Discriminant**: A 32-bit unsigned integer (`0`, `1`, `2`, ...) identifying the active variant.
2. **Payload**: A buffer sized to the maximum memory footprint of all declared variants, naturally aligned to an 8-byte boundary.

---

### 5.3 Pattern Matching Syntax & Semantics
Pattern matching provides declarative, type-safe destructuring of sum types and composite data.

#### Syntax:
```lisp
(fn compute_area (s: Shape) -> f64
  (match s
    ((Circle r)
      (* 3.14159265 (* r r)))
    ((Rectangle w h)
      (* w h))
    (Point
      0.0)))

(fn unwrap_or [T] (opt: Option<T> default_val: T) -> T
  (match opt
    ((Some val) val)
    (None default_val)))
```

#### Compiler Semantic Rules:
1. **Exhaustiveness Checking**: The type checker proves that every possible variant of the enum is covered by at least one arm. Omission of a variant triggers an `InexhaustiveMatch` JSON diagnostic with the list of missing patterns.
2. **Unreachable Pattern Detection**: Any pattern arm appearing after a wildcard `_` or a duplicate pattern triggers an `UnreachablePattern` warning/error.
3. **Variable Binding**: Variables bound inside a pattern (e.g. `r`, `w`, `h`) are introduced into the lexical scope of that specific arm with their statically resolved types.

#### WebAssembly Codegen Strategy:
* For dense sequential variant tags ($0, 1, 2, \dots$), the compiler emits a `br_table` instruction, executing in $O(1)$ constant time.
* For sparse or complex guard patterns, the compiler emits a balanced binary decision tree of `br_if` instructions ($O(\log N)$).

---

### 5.4 First-Class Function Types & Closures
Supporting higher-order functional programming allows agents to author elegant data transformation pipelines (`map`, `filter`, `reduce`).

#### Syntax & Types:
```lisp
;; Function accepting a predicate function type
(fn filter_array [T] (arr: Array<T> predicate: (fn-type [T] -> bool)) -> Array<T>
  (let len: i32 (arr_len arr))
  (let out: Array<T> (arr_new<T> len))
  (let i: i32 0)
  (let out_idx: i32 0)
  (while (< i len)
    (let item: T (arr_get arr i))
    (if (call predicate item)
      (block
        (arr_set out out_idx item)
        (set out_idx (+ out_idx 1))))
    (set i (+ i 1)))
  out)
```

#### WebAssembly Indirect Call Architecture:
1. **Function Table (`table`)**:
   Top-level functions whose references are passed as arguments are indexed into the WebAssembly function table:
   ```wasm
   (table (export "table") 128 funcref)
   (elem (i32.const 0) $is_even $is_positive $square)
   ```
2. **`call_indirect` Emission**:
   Function calls via dynamic references load the table index and execute via `call_indirect`:
   ```wasm
   (call_indirect (type $fn_i32_to_bool) (local.get $item) (local.get $fn_index))
   ```
3. **Fat Closures**:
   Closures that capture variables from enclosing scopes are represented as a two-word fat pointer:
   `[code_table_index: i32] + [captured_env_pointer: i32]`. The environment pointer is passed as an implicit first parameter.

---

## 6. WebAssembly Runtime Execution Model & Memory Architecture

### 6.1 Linear Memory Layout & Segment Partitioning
SynapLang organizes its 32-bit linear WebAssembly memory into deterministic, contiguous regions:

```
0x00000000 ┌───────────────────────────────────────────────┐
           │ Null Pointer Guard Page & Traps (1024 Bytes)   │ <-- Any read/write traps immediately
0x00000400 ├───────────────────────────────────────────────┤
           │ Static String & Constant Data Segment          │ <-- Statically emitted (data ...)
           │ [length: i32] [utf8 bytes] [\0] [padding]     │
<static_end>├───────────────────────────────────────────────┤
           │ Type Metadata & RTTI Table                     │ <-- Tagged union discriminants & sizes
<heap_base>├───────────────────────────────────────────────┤
           │                                               │
           │ Dynamic Heap Allocation Region                │ <-- Managed by Allocator
           │ (Arrays, Structs, Strings, Enums)             │
           │                                               │
           ▼                                               ▼
           │ ─── Memory Growth Direction (memory.grow) ───►│
0x01000000 └───────────────────────────────────────────────┘ (16 MiB default max_pages boundary)
```

#### Segment Details:
1. **Null Pointer Guard Page (`0x0000 - 0x03FF`)**:
   The first 1,024 bytes are permanently unmapped for allocations. Any dereference of pointer `0` (null) or pointers $< 1024$ triggers an immediate WebAssembly runtime trap, preventing null-pointer bugs.
2. **Static Data Segment (`0x0400 - <static_end>`)**:
   String literals and constant structures are stored here at compile time via WebAssembly data segments `(data (i32.const offset) "...")`.
3. **Dynamic Heap (`<heap_base> - <limit>`)**:
   Begins at `max(1024, static_end)`. All runtime allocations (`arr_new`, `struct_new`, `str_concat`) operate within this region.

---

### 6.2 Allocator Evolution Strategy

#### Stage 1: Hardened Bump Allocator with Correct Bounds (v0.2.0)
* Correct existing bugs identified in Survey 1 & 2:
  - Dynamically calculate the exact number of pages required when allocating objects larger than 512 KiB:
    $$\Delta\text{pages} = \left\lceil \frac{(\text{heap\_ptr} + \text{needed}) - (\text{memory.size} \times 65536)}{65536} \right\rceil$$
  - Check the return code of `memory.grow`. If it returns `-1`, trigger a deterministic `unreachable` trap instead of silently advancing `$heap_ptr`.
  - Add auto-grow checks to `_str_concat`.

#### Stage 2: Scoped Arena Allocators (v0.5.0)
In autonomous agent execution, the vast majority of allocations exist only for the duration of a single tool execution or turn:
```lisp
(with-arena
  (let temp_list: Array<f64> (arr_new<f64> 50000))
  (process temp_list)
  ;; All memory allocated inside with-arena is instantly reset at block exit
)
```
* **Arena Mechanics**: Maintains a local allocation watermark (bump offset). Entering `(with-arena ...)` snapshots the current heap pointer; exiting the block resets the watermark to the snapshot with **zero CPU deallocation overhead** and zero heap fragmentation.
* **Scoped Arena Escape Semantics**:
  Dangling pointers to deallocated arena memory represent a catastrophic memory safety hazard. SynapLang resolves escape hazards through two complementary mechanisms:
  1. **Compile-Time Escape Analysis (Static Restriction)**: The static type checker tracks the lexical lifetime scope of every allocated reference. If an expression inside `(with-arena ...)` attempts to return a local arena-allocated reference, or assign it to an outer-scope variable, the compiler rejects the code with an `ArenaEscapeError` structured diagnostic:
     ```json
     {
       "error": "ArenaEscapeError",
       "message": "Cannot escape reference 'temp_list' from local arena scope to outer scope",
       "suggested_fix": "Use (arena_promote expr) to copy to parent arena or allocate outside with-arena"
     }
     ```
  2. **Explicit Copy Promotion (`(arena_promote expr)`)**: When data synthesized inside an arena must survive past block exit (e.g. returning a final processed vector or computed string), the program wraps the expression in `(arena_promote expr)`. The runtime performs a deep copy of the structure directly into the enclosing (parent) arena or heap before resetting the child arena watermark, returning a valid reference whose lifetime matches the outer scope.

#### Stage 3: Two-Level Segregated Fit (TLSF) General-Purpose Allocator (v1.0.0)
For long-lived persistent agents, server processes, and complex multi-turn REPL sessions, SynapLang integrates a lightweight, deterministic Two-Level Segregated Fit (TLSF) allocator:
* Provides bounded $O(1)$ time complexity for both allocation (`malloc`) and deallocation (`free`).
* Two-level segregated free lists indexed by first-level (power of two) and second-level linear size classes.
* Eliminates linear memory leaks in persistent multi-turn REPL and server sessions.

#### TLSF Deallocation Triggers:
Deallocation in SynapLang with TLSF is triggered deterministically through three coordinated mechanisms:
1. **Explicit Deallocation Intrinsics (`(free ptr)` / `(dealloc ptr)`)**:
   In low-level or standard library data structure implementations (e.g., dynamic `Vector<T>` resizing, `HashMap<K, V>` bucket reallocation), explicit intrinsics directly invoke the TLSF `free()` routine to reclaim capacity immediately.
2. **Compile-Time Affine/Linear Ownership Tracking**:
   SynapLang's type checker enforces affine move semantics for non-primitive heap structures. When an owned heap structure is consumed by a function or reaches the end of its lexical scope without being moved or returned, the compiler automatically injects a TLSF deallocation call, achieving deterministic reclamation with zero garbage collection pauses.
3. **RAII Scope-Exit Block Cleanup**:
   Block constructs automatically record heap allocations with local lifetimes. Upon exiting a block, any non-escaping variables managed by TLSF are freed in reverse allocation order, preventing memory leaks across iterative loops.

---

### 6.3 Array Bounds Checking Implementation
All array reads (`arr_get`) and writes (`arr_set`) MUST enforce memory safety at the instruction level. Note that in valid WebAssembly Text (WAT) format, folded `if` control instructions require an explicit `(then ...)` wrapper block.

#### WebAssembly Hardened Implementation:
```wasm
;; Hardened Array Get Function
(func $arr_get_checked (param $arr i32) (param $idx i32) (result i32)
  ;; 1. Check array pointer validity
  (if (i32.lt_u (local.get $arr) (i32.const 1024))
    (then
      (unreachable) ;; Null or guard-page pointer trap
    )
  )
  ;; 2. Load array length stored at (arr - 4)
  ;; 3. Check unsigned bounds: index must be strictly less than length
  (if (i32.ge_u (local.get $idx) (i32.load (i32.sub (local.get $arr) (i32.const 4))))
    (then
      (unreachable) ;; Out-of-bounds index trap
    )
  )
  ;; 4. Compute element address and load 32-bit element
  (i32.load (i32.add (local.get $arr) (i32.mul (local.get $idx) (i32.const 4))))
)

;; Hardened Array Set Function
(func $arr_set_checked (param $arr i32) (param $idx i32) (param $val i32)
  (if (i32.lt_u (local.get $arr) (i32.const 1024))
    (then
      (unreachable)
    )
  )
  (if (i32.ge_u (local.get $idx) (i32.load (i32.sub (local.get $arr) (i32.const 4))))
    (then
      (unreachable)
    )
  )
  (i32.store (i32.add (local.get $arr) (i32.mul (local.get $idx) (i32.const 4))) (local.get $val))
)
```

---

### 6.4 String Representation & UTF-8 Safety
Strings in SynapLang are immutable byte sequences.

#### Memory Layout:
```
Offset:   -4       0                 length              length + 1
Bytes:   [length] [Byte 0] [Byte 1] ... [Byte N] [\0 null] [padding 0..7]
Type:     i32      utf8     utf8         utf8     byte      alignment
```
* **Length Header**: An unsigned 32-bit integer preceding the string pointer (`ptr - 4`) storing the exact UTF-8 byte count.
* **Payload**: Valid UTF-8 encoded text.
* **Null Terminator**: A trailing `\0` byte ensures seamless compatibility with C/WASI APIs.
* **Alignment**: Aligned to 8-byte boundaries for SIMD vector operations.

#### String Slicing:
Substrings are created via zero-copy slices or bounded copies. Because lengths are explicit, `str_len` executes in $O(1)$ time without scanning for null terminators.

---

### 6.5 Multi-Threaded Wasm & Atomics Roadmap
To support parallel agent swarms and multi-threaded computation:
1. **Shared Memory**: Declare memory with the `shared` attribute:
   ```wasm
   (memory (export "memory") 16 256 shared)
   ```
2. **Atomic Instructions**: Emit WebAssembly threads proposal instructions (`i32.atomic.rmw.add`, `i32.atomic.load`, `i32.atomic.store`).
3. **Synchronization Primitives**: Implement `Mutex` and `AtomicFlag` in `std::sync` using `memory.atomic.wait32` and `memory.atomic.notify`.

---

## 7. Standard Library Specification (`synap-std`)

The standard library is structured into four core modules:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Synap Standard Library                          │
├───────────────────┬───────────────────┬──────────────────┬─────────────┤
│ std::core         │ std::collections  │ std::io          │ std::wasi   │
├───────────────────┼───────────────────┼──────────────────┼─────────────┤
│ • Math (sqrt, pow)│ • Vector<T>       │ • print, println │ • fd_read   │
│ • Bitwise ops     │ • HashMap<K, V>   │ • format         │ • fd_write  │
│ • Option, Result  │ • Queue<T>        │ • parse_int      │ • clock_get │
│ • Panic & Assert  │ • RingBuffer<T>   │ • parse_float    │ • random_get│
└───────────────────┴───────────────────┴──────────────────┴─────────────┘
```

### 7.1 `std::core`
* **Math Primitives**:
  - `(fn abs (x: i32) -> i32)`
  - `(fn abs_f64 (x: f64) -> f64)`
  - `(fn min (a: i32 b: i32) -> i32)`
  - `(fn max (a: i32 b: i32) -> i32)`
  - `(fn sqrt (x: f64) -> f64)` (maps directly to Wasm instruction `f64.sqrt`)
  - `(fn clamp (val: f64 low: f64 high: f64) -> f64)`
* **Assertions & Traps**:
  - `(fn assert (cond: bool msg: string) -> void)`: Traps with `msg` if `cond` is false.
  - `(fn panic! (msg: string) -> void)`: Unconditionally triggers a WebAssembly trap.

### 7.2 `std::collections`
* **`Vector<T>` (Dynamic Resizable Array)**:
  - `(fn vec_new<T> (capacity: i32) -> Vector<T>)`
  - `(fn vec_push<T> (v: Vector<T> item: T) -> void)` (automatically doubles capacity when full)
  - `(fn vec_pop<T> (v: Vector<T>) -> Option<T>)`
  - `(fn vec_get<T> (v: Vector<T> idx: i32) -> T)`
  - `(fn vec_len<T> (v: Vector<T>) -> i32)`
* **`HashMap<K, V>`**:
  - Robin Hood hashing or linear probing on 64-bit FNV-1a hashes.

### 7.3 `std::io`
* **Host Interop & Formatting**:
  - `(fn print (s: string) -> void)`
  - `(fn println (s: string) -> void)`
  - `(fn print_int (n: i32) -> void)`
  - `(fn print_float (f: f64) -> void)`
  - `(fn int_to_string (n: i32) -> string)`
  - `(fn string_to_int (s: string) -> Result<i32 string>)`

### 7.4 `std::wasi`
* Standard WASI Preview 1 / Preview 2 system calls for standalone execution:
  - `(fn clock_time_now () -> f64)`: High-resolution monotonic clock timestamp.
  - `(fn get_random_bytes (len: i32) -> Array<i32>)`: Cryptographically secure random bytes via `random_get`.
  - `(fn file_read_all (path: string) -> Result<string string>)`
  - `(fn file_write_all (path: string data: string) -> Result<bool string>)`

---

## 8. Concrete SynapLang Code Examples for New Features

### 8.1 Generics and Dynamic Vector
```lisp
(module examples::generics_demo
  (import "std::collections" (Vector vec_new vec_push vec_get vec_len))
  (import "std::io" (println print_int))

  (fn main () -> i32
    ;; Instantiate generic vector of integers
    (let nums: Vector<i32> (vec_new<i32> 4))
    (vec_push nums 10)
    (vec_push nums 20)
    (vec_push nums 30)

    (let i: i32 0)
    (while (< i (vec_len nums))
      (print_int (vec_get nums i))
      (println "")
      (set i (+ i 1)))
    0)
)
```

### 8.2 Option, Result, and Pattern Matching
```lisp
(module examples::pattern_matching_demo
  (import "std::core" (Option Some None Result Ok Err))
  (import "std::io" (println))

  (enum Shape
    (Circle [radius: f64])
    (Rectangle [width: f64] [height: f64])
    Point)

  (fn calculate_area (s: Shape) -> f64
    (match s
      ((Circle r)
        (* 3.14159265 (* r r)))
      ((Rectangle w h)
        (* w h))
      (Point
        0.0)))

  (fn safe_divide (numerator: f64 denominator: f64) -> Result<f64 string>
    (if (== denominator 0.0)
      (Err "Division by zero error")
      (Ok (/ numerator denominator))))

  (fn main () -> i32
    (let my_shape: Shape (Circle 5.0))
    (let area: f64 (calculate_area my_shape))

    (let div_res: Result<f64 string> (safe_divide 10.0 2.0))
    (match div_res
      ((Ok val) (println "Division succeeded"))
      ((Err msg) (println msg)))
    0)
)
```

### 8.3 Higher-Order Functions and Closures
```lisp
(module examples::functional_pipeline
  (import "std::core" (Array arr_new arr_set arr_get arr_len))
  (import "std::io" (println print_int))

  ;; Higher-order map function
  (fn map_i32 (arr: Array<i32> transform: (fn-type [i32] -> i32)) -> Array<i32>
    (let len: i32 (arr_len arr))
    (let result: Array<i32> (arr_new<i32> len))
    (let i: i32 0)
    (while (< i len)
      (let item: i32 (arr_get arr i))
      (arr_set result i (call transform item))
      (set i (+ i 1)))
    result)

  (fn square (x: i32) -> i32
    (* x x))

  (fn main () -> i32
    (let input: Array<i32> (array 1 2 3 4 5))
    (let squared: Array<i32> (map_i32 input square))

    (let i: i32 0)
    (while (< i (arr_len squared))
      (print_int (arr_get squared i))
      (println "")
      (set i (+ i 1)))
    0)
)
```

---

## 9. Backward Compatibility & Migration Strategy
* **Grammar Compatibility**: Existing SynapLang v0.1.0 programs (`examples/*.ail`) remain 100% syntactically valid under this specification.
* **Monomorphic Arrays**: The type alias `arr_i32` is retained as a built-in alias for `Array<i32>`.
* **Struct Access Syntax**: Both `(struct_get s field)` and `(. s field)` continue to be supported interchangeably.
* **Deprecation Policy**: Any breaking change to type checking or JSON diagnostic formats will require a minor version increment and an automated AST migration tool (`synap-migrate`).
