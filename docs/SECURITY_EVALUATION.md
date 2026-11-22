# SynapLang Security Evaluation & Sandbox Isolation Architecture

**Document Identifier**: SYNAP-SEC-2026-01  
**Classification**: Authoritative Security Whitepaper & Sandbox Specification  
**Author(s)**: Lead Security Expert & WebAssembly Runtime Specialist  
**Target Audience**: Security Engineers, Compiler Architects, Agent Platform Developers  
**Target Milestone**: v0.2.0 – v1.0.0  
**Date**: November 2026  

---

## 1. Executive Security Summary & Posture

SynapLang is an AI-native programming language designed to execute code synthesized dynamically by Large Language Models (LLMs) and autonomous agent frameworks (e.g. LangChain, CrewAI, AutoGen, Google Antigravity).

Executing LLM-generated code presents fundamental security challenges distinct from traditional human-authored software:
* Models are vulnerable to **indirect prompt injection**, prompt manipulation, and hallucinated logic.
* Generated code cannot be assumed benign; it may contain intentional or accidental infinite loops, out-of-bounds memory accesses, unbounded memory allocations, or host crash triggers.
* Multi-agent execution environments require strict **multi-tenant isolation** to prevent state leakage, noisy-neighbor CPU starvation, and memory disclosure across turns.

### High-Level Security Posture Assessment:
SynapLang's architectural choice to compile directly to **WebAssembly (Wasm32)** provides an exceptional security foundation. In WebAssembly:
1. **Control Flow Integrity (CFI)** is enforced at the hardware/JIT level: code is immutable, call targets are statically verified, and arbitrary code injection into instruction memory is impossible.
2. **Call Stack Isolation**: The program execution stack (return pointers, local variables, frame pointers) is maintained by the host runtime (Wasmtime) in separate memory completely inaccessible to guest pointers.
3. **No Default OS Access**: Unlike Python, C, or Node.js, WebAssembly modules have zero access to the host operating system, filesystem, network sockets, or environment variables unless explicitly imported.

However, an exhaustive audit of the current SynapLang runtime (`v0.1.0`) identified **five critical security vulnerabilities** in instruction metering, memory bounds checking, host-guest memory interfaces, and linear memory allocation. This evaluation details the complete threat model, provides formal analysis of these vulnerabilities, and specifies the production hardening requirements.

---

## 2. Threat Model for AI Agent Execution

```
                             ATTACK SURFACE ARCHITECTURE
                             
  [ Untrusted User Input ] 
             │
             ▼
  [ LLM Inference Engine ]  ──► (Prompt-to-Code Injection / Hallucinated Syntax)
             │
             ▼
  [ Synap Source (.ail) ]
             │
      ┌──────┴──────────────────────────────────────┐
      │ ATTACK VECTOR 1: Compiler Denial of Service │
      │ - Deeply nested parentheses (Parser DoS)   │
      │ - Recursive macro / cyclic definitions      │
      └──────┬──────────────────────────────────────┘
             ▼
     [ Synap Compiler ] 
             │
      ┌──────┴──────────────────────────────────────┐
      │ ATTACK VECTOR 2: Memory & Sandbox Escape    │
      │ - Monotonic heap exhaustion (OOM DoS)       │
      │ - Unchecked linear memory corruption        │
      │ - Host ctypes buffer over-read / disclosure │
      └──────┬──────────────────────────────────────┘
             ▼
    [ Wasmtime Runtime ]
             │
      ┌──────┴──────────────────────────────────────┐
      │ ATTACK VECTOR 3: CPU & Resource Starvation  │
      │ - Infinite loops / unbounded recursion      │
      │ - Host thread lockup                        │
      └─────────────────────────────────────────────┘
```

### 2.1 Threat Actors & Scenarios
1. **Adversarial Prompt Injector**: An external user who supplies malicious inputs to an autonomous agent (e.g., in a customer-support or data-analysis agent) designed to trigger arbitrary code execution, host DoS, or data exfiltration.
2. **Malicious Tool Synthesizer**: An agent instructed to generate tool code that attempts to break out of the execution sandbox to access host credentials, network services, or cloud metadata endpoints (`169.254.169.254`).
3. **Multi-Tenant Cross-Contaminator**: In shared agent clusters, an attacker executing code in tenant $A$ attempting to read residual heap memory or state left behind by tenant $B$.

### 2.2 Attack Vectors & Impact Analysis

| Vector | Description | Target Subsystem | Impact |
| :--- | :--- | :--- | :--- |
| **V-1: CPU Starvation** | Unbounded loops `(while true ...)` or infinite recursion. | Wasmtime Runtime | Locks host worker thread, blocking task queue. |
| **V-2: Heap Tampering** | Out-of-bounds `arr_set` overwriting adjacent heap objects. | Linear Memory | Silently corrupts data structures and string metadata. |
| **V-3: Host Over-Read / DoS** | Mutating string length headers or slicing raw ctypes pointers. | Host Interface (`host_print_str`) | Host memory disclosure, 450MB+ RAM exhaustion via ctypes list allocation, segfault. |
| **V-4: Host Unicode Crash** | Passing non-UTF8 bytes from guest memory into host print. | Host Interface | Host `UnicodeDecodeError` uncaught exception. |
| **V-5: RAM Exhaustion** | Monotonically allocating memory up to host limits. | Memory Subsystem | Out-of-Memory (OOM) killer terminating host container. |
| **V-6: Parser Exhaustion**| Feeding $10^5$ nested opening parentheses. | Lark Parser | Python `RecursionError` / C stack exhaustion crashing compiler process. |

---

## 3. Sandbox Isolation Architecture

To establish an impenetrable sandbox boundary, the SynapLang execution driver (`src/runner.py`) and WebAssembly codegen (`src/codegen_wasm.py`) must enforce four deterministic isolation layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      SANDBOX ISOLATION LAYERS                          │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Capability Tokens & Role-Based API Permissions                │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Host-Guest Boundary Validation (Bounds checks & UTF-8 guards) │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 2: Instruction Fuel Metering & Epoch Execution Timeouts          │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 1: Hardware-Enforced Linear Memory Caps (max_pages boundary)     │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Layer 1: Linear Memory Page Capping (`max_pages`)
In WebAssembly, linear memory is allocated in discrete **64 KiB pages**. 
* **Vulnerability in v0.1.0**: `src/codegen_wasm.py` generates `(memory (export "memory") 16)`. Because no maximum page bound is declared, the guest instance can invoke `memory.grow` up to 65,536 pages (4 GiB), exhausting physical host memory.
* **Production Specification**:
  Every compiled module MUST declare an explicit maximum page limit:
  ```wasm
  ;; Initial: 16 pages (1 MiB), Maximum: 256 pages (16 MiB)
  (memory (export "memory") 16 256)
  ```
  Attempting to grow beyond `256` pages returns `-1`, preventing unbounded host RAM consumption.

### 3.2 Layer 2: Instruction Fuel Metering
Fuel metering assigns a discrete computation budget to each WebAssembly instruction executed:
* Simple arithmetic (`i32.add`, `f64.mul`) consumes 1 fuel unit.
* Memory loads/stores consume 2–3 fuel units.
* Indirect calls and branches consume 3–5 fuel units.

#### Wasmtime Engine Configuration (`src/runner.py`):
```python
from wasmtime import Config, Engine, Store

config = Config()
config.consume_fuel = True
engine = Engine(config)

# In execute_function():
store = Store(engine)
# Allocate 1,000,000 instruction fuel units per agent turn
store.set_fuel(1_000_000)
```

#### Deterministic Termination:
If guest code enters an infinite loop `(while true 0)`, the fuel counter monotonically decrements to zero. Upon exhaustion, Wasmtime immediately traps with:
```
wasm trap: all fuel consumed by WebAssembly
```
This guarantees **zero CPU hang** and bounded execution time regardless of code complexity.

### 3.3 Layer 3: Epoch-Based Deadlines & Wall-Clock Timeouts
While fuel metering bounds the number of instructions, it does not account for wall-clock delays caused by host function calls or asynchronous I/O. SynapLang implements dual-layer protection using **Epoch Interruption**:

```python
config.epoch_interruption = True

# Store configuration
store.set_epoch_deadline(1) # Interrupt when engine epoch advances by 1
```

A lightweight background monitor thread or timer advances the engine epoch every $N$ milliseconds (e.g. 500ms):
```python
engine.increment_epoch()
```
If guest execution has not completed before the epoch ticks, Wasmtime instantly halts JIT execution with:
```
wasm trap: interrupt
```

---

## 4. Linear Memory Safety Guarantees & Vulnerability Analysis

### 4.1 Detailed Audit of Identified Vulnerabilities

#### SEC-01: CPU Starvation via Infinite Loops
* **Location**: `src/runner.py:23-28`
* **Severity**: High (CVSS: 7.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H`)
* **Root Cause**: `Engine()` instantiated with default configuration; no fuel or epoch limits.
* **Impact**: Host worker freezes indefinitely on unverified loops, denying service to all other agent tasks.

#### SEC-02: Host Memory Disclosure & DoS via Unchecked ctypes Pointer Slicing
* **Location**: `src/runner.py:41-44`
* **Severity**: High (CVSS: 7.7 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N`)
* **Code Trace**:
  ```python
  def host_print_str(caller, ptr: int, length: int):
      mem = caller.get("memory")
      data = mem.data_ptr(caller)  # ctypes.POINTER(c_ubyte)
      text = bytes(data[ptr : ptr + length]).decode("utf-8")
  ```
* **Root Cause**: 
  1. `data` is a raw C pointer. Slicing `data[ptr : ptr + length]` does not perform bounds checking against `mem.data_len(caller)`.
  2. Slicing a `ctypes.POINTER(c_ubyte)` via `data[ptr : ptr + length]` causes CPython to instantiate a Python `list` containing `length` individual Python `int` objects. For large slices (e.g. 16 MiB), this instantiates over 16 million `int` objects, consuming 450+ MiB of host RAM and stalling the host runner thread.
* **Impact**: If `ptr + length` exceeds guest linear memory, the Python process reads arbitrary host heap memory located after the Wasm memory mapping (leaking sensitive host secrets or causing `SIGSEGV`/`STATUS_ACCESS_VIOLATION`). Additionally, allocating massive Python integer lists for legitimate or hostile large string prints triggers host memory exhaustion and thread stall.

#### SEC-03: Arbitrary Linear Memory Corruption via Unchecked Array Indexing
* **Location**: `src/codegen_wasm.py:474-504`
* **Severity**: High (CVSS: 7.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:H/A:L`)
* **Root Cause**: `ArrGet` and `ArrSet` emit raw `i32.load` and `i32.store` at `arr + idx * 4` without verifying that `idx < length` or `idx >= 0`.
* **Impact**: Guest code can read and write arbitrary offsets in linear memory. An attacker can overwrite struct fields, alter string length headers, or corrupt memory allocator state.

#### SEC-04: Host Crash via Unhandled Unicode Decoding Error
* **Location**: `src/runner.py:44, 53`
* **Severity**: Medium (CVSS: 5.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L`)
* **Root Cause**: Invoking `.decode("utf-8")` without an exception handler or error replacement strategy.
* **Impact**: If corrupted memory or binary bytes are passed to `println`, Python raises `UnicodeDecodeError`, terminating the host runner process.

#### SEC-05: Unbounded Monotonic Linear Memory Growth
* **Location**: `src/codegen_wasm.py:122, 139-211`
* **Severity**: Medium (CVSS: 5.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L`)
* **Root Cause**: Monotonic bump allocator without deallocation; `(memory 16)` without upper bound; fixed 8-page growth in `_alloc_arr`; missing growth check in `_str_concat`.
* **Impact**: Persistent agent execution steadily consumes memory until hitting process limits.

---

### 4.2 Remediation Specifications & Hardened Implementations

#### 1. Software Bounds Checking in WAT (`src/codegen_wasm.py`)
All array operations must be redirected through verified WebAssembly functions. Note that in valid WebAssembly Text (WAT) format, folded `if` control instructions require an explicit `(then ...)` wrapper block:

```wasm
;; ========================================================
;; Hardened Array Getter with Hardware-Level Trap Checks
;; ========================================================
(func $_arr_get_safe (param $arr i32) (param $idx i32) (result i32)
  ;; Guard check: Reject null pointers or guard page accesses
  (if (i32.lt_u (local.get $arr) (i32.const 1024))
    (then
      (unreachable)
    )
  )
  ;; Length check: Load stored length from (arr - 4)
  ;; Perform unsigned comparison: catches negative numbers AND values >= len
  (if (i32.ge_u (local.get $idx) (i32.load (i32.sub (local.get $arr) (i32.const 4))))
    (then
      (unreachable) ;; Deterministic Wasm Trap: out-of-bounds access
    )
  )
  ;; Validated read
  (i32.load (i32.add (local.get $arr) (i32.mul (local.get $idx) (i32.const 4))))
)

;; ========================================================
;; Hardened Array Setter with Hardware-Level Trap Checks
;; ========================================================
(func $_arr_set_safe (param $arr i32) (param $idx i32) (param $val i32)
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

#### 2. Dynamic Memory Growth & Integer Overflow Defense in Allocators (`_alloc_arr` and `_str_concat`)
In addition to calculating page growth dynamically, the allocator MUST guard against integer overflow and signed wrap-around attacks when allocating arrays:

```wasm
;; ========================================================
;; Hardened Array Allocator with Integer Overflow Checks
;; ========================================================
(func $_alloc_arr (param $size i32) (result i32)
  (local $needed i32)
  (local $pages_needed i32)
  (local $grow_res i32)
  (local $arr_ptr i32)

  ;; 1. Check that size is strictly positive (reject 0 or negative numbers)
  (if (i32.le_s (local.get $size) (i32.const 0))
    (then
      (unreachable) ;; Trap: invalid or negative array allocation size
    )
  )

  ;; 2. Prevent integer overflow on (size * 4 + 4)
  ;; Maximum 32-bit elements without wrapping: (0x7FFFFFF0 - 4) / 4 = 536,870,907
  (if (i32.gt_u (local.get $size) (i32.const 536870907))
    (then
      (unreachable) ;; Trap: integer multiplication overflow in allocation
    )
  )

  ;; 3. Safely calculate needed bytes: 4 bytes header + (size * 4) payload
  (local.set $needed
    (i32.add (i32.const 4) (i32.mul (local.get $size) (i32.const 4))))

  ;; 4. Calculate needed pages dynamically: needed_pages = (needed + 65535) / 65536
  (local.set $pages_needed 
    (i32.div_u 
      (i32.add (local.get $needed) (i32.const 65535)) 
      (i32.const 65536)))

  ;; 5. Check if current memory capacity is exceeded
  (if (i32.gt_u 
        (i32.add (global.get $heap_ptr) (local.get $needed)) 
        (i32.mul (memory.size) (i32.const 65536)))
    (then
      (block
        ;; Attempt memory growth
        (local.set $grow_res (memory.grow (local.get $pages_needed)))
        ;; Check for allocation failure (-1)
        (if (i32.eq (local.get $grow_res) (i32.const -1))
          (then
            (unreachable) ;; Trap immediately on Out-of-Memory
          )
        )
      )
    )
  )

  ;; 6. Store array length at heap_ptr
  (i32.store (global.get $heap_ptr) (local.get $size))
  ;; Base pointer returned is heap_ptr + 4
  (local.set $arr_ptr (i32.add (global.get $heap_ptr) (i32.const 4)))
  ;; Advance global heap pointer
  (global.set $heap_ptr (i32.add (global.get $heap_ptr) (local.get $needed)))
  (local.get $arr_ptr)
)
```

#### 3. Secure Host Memory Bridge & Zero-Copy DoS Mitigation (`src/runner.py`)
In Python, slicing a `ctypes.POINTER(c_ubyte)` via `data[ptr : ptr + length]` generates a Python `list` of `length` individual `int` objects. For a 16 MiB slice, this instantiates 16.7 million `int` objects occupying 450+ MiB of host RAM, triggering severe CPU stalling and host memory exhaustion.

The production host runner MUST use `ctypes.string_at` or `memoryview` for zero-allocation C buffer reading, alongside strict boundary enforcement:

```python
import ctypes
import sys
import wasmtime

def host_print_str(caller, ptr: int, length: int):
    # 1. Retrieve linear memory instance and length
    mem = caller.get("memory")
    if mem is None:
        raise RuntimeError("Memory export 'memory' not found in WebAssembly module")
    
    total_len = mem.data_len(caller)

    # 2. Strict boundary enforcement
    if ptr < 0 or length < 0:
        raise ValueError(f"Negative memory pointer or length: ptr={ptr}, len={length}")
    if ptr + length > total_len:
        raise IndexError(
            f"Host memory boundary violation: access [{ptr}:{ptr+length}] exceeds memory size ({total_len})"
        )

    # 3. Safe C-buffer copy via ctypes.string_at (or memoryview)
    # Prevents allocating massive Python integer lists on large slices
    data = mem.data_ptr(caller)
    base_addr = ctypes.addressof(data.contents) if hasattr(data, "contents") else ctypes.cast(data, ctypes.c_void_p).value
    raw_bytes = ctypes.string_at(base_addr + ptr, length)

    # 4. Resilient UTF-8 decoding (prevents host process termination)
    text = raw_bytes.decode("utf-8", errors="replace")

    # 5. Output recording
    self.captured_output.append(text)
    if not self.capture_stdout:
        sys.stdout.write(text)
        sys.stdout.flush()
```

#### 4. Wasmtime Exception Hierarchy & Host Runner Hardening
A common flaw in WebAssembly host runner implementations is assuming all runtime failures inherit from `wasmtime.WasmtimeError`. In the Python `wasmtime` SDK:
* **`wasmtime.Trap` inherits directly from `Exception`**, NOT from `wasmtime.WasmtimeError`.
* Catching only `except wasmtime.WasmtimeError:` causes runtime traps (such as instruction fuel exhaustion, epoch interruption, and `unreachable` array bounds traps) to **escape uncaught**, fatally crashing the host agent runner thread.

The host execution runner MUST explicitly handle both `wasmtime.Trap` and `wasmtime.WasmtimeError`:

```python
def run_safely(store: wasmtime.Store, func, *args):
    """
    Executes a WebAssembly function within strict host containment boundaries.
    Catches (wasmtime.Trap, wasmtime.WasmtimeError, Exception) to guarantee
    zero host crashes from untrusted guest execution.
    """
    try:
        return {"status": "ok", "value": func(store, *args)}
    except wasmtime.Trap as trap:
        # Traps include fuel exhaustion, epoch timeout, and unreachable instructions
        logger.warning("WebAssembly execution trapped deterministically: %s", trap)
        return {
            "status": "trapped",
            "trap_type": type(trap).__name__,
            "message": str(trap),
        }
    except wasmtime.WasmtimeError as wasm_err:
        # Compilation, instantiation, or linking errors
        logger.error("WebAssembly runtime/link error: %s", wasm_err)
        return {
            "status": "wasm_error",
            "message": str(wasm_err),
        }
    except Exception as ex:
        # Catch unexpected host exceptions
        logger.error("Unexpected host error during execution: %s", ex)
        return {
            "status": "host_error",
            "message": str(ex),
        }
```

---

## 5. Autonomous Agent Vulnerability Mitigations

Beyond runtime and memory safety, executing agent-synthesized code requires proactive defense mechanisms at the AST and parser levels.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   AGENT DEFENSE-IN-DEPTH PIPELINE                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. AST Validation Pass (Static Safety & Complexity Checks)             │
│    - Maximum nesting depth verification (depth <= 128)                 │
│    - Identifier length validation & character whitelisting             │
│    - Array allocation upper bound check (size <= 1,000,000)            │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Capability-Based Host Token Authorizer                              │
│    - Execution context carries cryptographic token with permitted APIs │
│    - Unprivileged agents cannot invoke I/O or WASI file operations     │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Isolated Turn-Lifecycle Sandboxing                                  │
│    - Fresh Store & Memory instantiated per turn                        │
│    - Scrubbing of transient memory buffers to prevent cross-talk       │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Pre-Execution AST Validation & Parser Recursion Defense (V-6 Mitigation)
A critical denial-of-service vector against language compiler frontends is pathological recursion: an adversarial prompt injects thousands of unclosed opening parentheses `((((...` or deeply nested S-expressions. In Python, this triggers an uncaught `RecursionError` or native C-stack exhaustion before AST construction can complete.

SynapLang implements a three-tier defense against parser exhaustion:
1. **Lexer / Pre-Parse Token Nesting Depth Counter**:
   During initial tokenization or via a custom Lark lexer callback, a lightweight integer counter tracks the current parenthetical nesting level:
   ```python
   MAX_PARSER_NESTING_DEPTH = 128

   def validate_nesting_depth(source: str):
       depth = 0
       for line_no, line in enumerate(source.splitlines(), start=1):
           for col_no, ch in enumerate(line, start=1):
               if ch == "(":
                   depth += 1
                   if depth > MAX_PARSER_NESTING_DEPTH:
                       raise CompilerDiagnosticError({
                           "error": "ParserNestingLimitExceeded",
                           "message": f"Parenthetical nesting depth {depth} exceeds safety maximum ({MAX_PARSER_NESTING_DEPTH})",
                           "location": {"line": line_no, "column": col_no},
                           "suggested_fix": "Refactor deeply nested expressions into intermediate let bindings or functions"
                       })
               elif ch == ")":
                   depth = max(0, depth - 1)
   ```
   This check runs in $O(N)$ linear time and aborts with a structured JSON diagnostic *before* invoking any recursive parser rules or allocating parser stack frames.

2. **Host Python Stack Limit Configuration & Iterative AST Traversal**:
   - The compiler runner explicitly configures the host recursion limit via `sys.setrecursionlimit(5000)` with a protective safety margin.
   - The `ASTBuilder` and `TypeChecker` use iterative worklist/stack algorithms rather than unbounded recursive calls for expression trees, guaranteeing immunity to host stack overflow.

3. **GBNF Grammar Depth Bounding**:
   In local inference engines (`llama.cpp`, Ollama), the production GBNF grammar sets an explicit recursive depth ceiling, preventing models from sampling pathological nesting loops at the logit level.

* **Static Array Size Caps**: Array literal or allocation expressions with static sizes $> 10^6$ elements are rejected at compile time (`ExcessiveAllocationSize`).
* **Prohibited Identifier Filter**: Keywords and internal runtime symbols (`$heap_ptr`, `_alloc_arr`, `memory`) cannot be declared as user variables or function names.

### 5.2 Capability-Based Host API Permissions
In production agent architectures, different agents hold different privilege tiers:
* **Pure Math/Logic Agent**: Zero host imports permitted; pure in-memory calculation.
* **Data Processing Agent**: Read-only access to specific memory buffers; no filesystem access.
* **System Integration Agent**: Explicit capability token authorizing WASI `fd_read` / `fd_write` on pre-opened directory descriptors.

```python
class CapabilityToken:
    can_print: bool = True
    can_read_files: bool = False
    can_write_files: bool = False
    allowed_file_paths: List[str] = []
    max_memory_pages: int = 256
    instruction_fuel_quota: int = 1_000_000
    timeout_ms: int = 1000
```
During module instantiation, the `Linker` checks the active `CapabilityToken` and only binds the specific host functions authorized for that agent.

---

## 6. Security Hardening Checklist & Implementation Roadmap

```
┌────────────────────────────────────────────────────────────────────────┐
│                     SECURITY HARDENING ROADMAP                         │
├──────────────┬──────────────────────────────────────────┬──────────────┤
│ Milestone    │ Security Deliverable                     │ Target CVSS  │
├──────────────┼──────────────────────────────────────────┼──────────────┤
│ **v0.2.0**   │ • Software Bounds Checking in WAT        │ Mitigate     │
│ (Hardening)  │ • Host Pointer Validation in runner.py   │ SEC-01..04   │
│              │ • Fuel Metering (1M fuel default)        │ High -> None │
│              │ • Resilient UTF-8 decode ("replace")     │              │
├──────────────┼──────────────────────────────────────────┼──────────────┤
│ **v0.3.0**   │ • Epoch-based Execution Timeouts (500ms) │ Mitigate     │
│ (Isolation)  │ • Max memory pages capped at 256 (16MB)  │ SEC-05       │
│              │ • Dynamic page calculation in _alloc_arr │ Med -> None  │
│              │ • Memory growth check in _str_concat     │              │
├──────────────┼──────────────────────────────────────────┼──────────────┤
│ **v0.5.0**   │ • Pre-execution AST Safety Pass          │ Agent Safety │
│ (Enterprise) │ • Capability-based Host API Tokens       │ Defense-in-  │
│              │ • Multi-tenant memory scrubbing per turn │ Depth        │
├──────────────┼──────────────────────────────────────────┼──────────────┤
│ **v1.0.0**   │ • Rust native compiler & runtime core    │ Memory-Safe  │
│ (Production) │ • Formal verification of Wasm allocators │ Toolchain    │
│              │ • Independent third-party audit          │ Production   │
└──────────────┴──────────────────────────────────────────┴──────────────┘
```

### Verification Criteria for Security Fixes:
1. **Infinite Loop Test**: `(fn f () -> i32 (while true 0) 0)` MUST terminate with `wasm trap: all fuel consumed` within $< 100\text{ ms}$.
2. **Bounds Violation Test**: `(arr_set a 100 42)` on an array of length 4 MUST trap with `wasm trap: unreachable executed`.
3. **Host Boundary Test**: Passing `ptr=9999999` to `println` MUST raise a structured boundary error without triggering host segmentation faults or disclosing host memory.
4. **UTF-8 Resilience Test**: Non-UTF8 byte sequences passed to `print` MUST be safely replaced with the Unicode replacement character `\uFFFD` without crashing the host runner.
5. **Integer Overflow Defense Test**: Invocations of `(arr_new -5)` or `(arr_new 600000000)` MUST trigger deterministic WebAssembly traps via `unreachable`, preventing negative or wrapped allocations.
6. **Zero-Copy Host Slicing & Exception Isolation Test**: Reading string memory in `host_print_str` MUST execute via `ctypes.string_at` or `memoryview` with zero Python integer list allocations, and `run_safely()` MUST catch `(wasmtime.Trap, wasmtime.WasmtimeError, Exception)` ensuring zero unhandled host runner crashes.
7. **Parser Recursion Depth Test**: An S-expression string nested deeper than 128 levels MUST trigger `ParserNestingLimitExceeded` during pre-parse validation without exhausting Python C-stack limits.
