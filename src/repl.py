import sys
import json
from typing import List
from src.runner import Runner
from src.type_checker import TypeErrorException

BANNER = """\
\033[1;36m============================================================\033[0m
\033[1;32m   SynapLang v0.3.0 - AI-Native Interactive REPL\033[0m
   Direct S-Expression Evaluation -> WebAssembly (Wasmtime)
   Type \033[1;33m:help\033[0m for commands, \033[1;33m:quit\033[0m or Ctrl+D to exit.
\033[1;36m============================================================\033[0m"""

HELP_TEXT = """\
Available REPL Commands:
  :help         - Show this help reference
  :reset        - Clear all session functions and structs
  :wat          - Print the compiled WebAssembly Text (WAT) of the last snippet
  :env          - Show all currently defined structs and functions
  :quit / :exit - Exit the REPL

S-Expression Usage Examples:
  synap> (+ 40 2)
  => 42

  synap> (println "Hello AI!")
  Hello AI!

  synap> (fn square (n: i32) -> i32 (* n n))
  Defined function: square

  synap> (call square 9)
  => 81

  synap> (struct Point [x: i32] [y: i32])
  Defined struct: Point

  synap> (let p: Point (struct_new Point 3 4))
  synap> (+ (struct_get p x) (struct_get p y))
  => 7
"""

class SynapRepl:
    def __init__(self):
        self.runner = Runner()
        self.definitions: List[str] = []
        self.last_wat: str = ""

    def reset(self):
        self.definitions.clear()
        self.last_wat = ""
        print("\033[1;33m[REPL session reset]\033[0m")

    def _is_balanced(self, text: str) -> bool:
        depth = 0
        in_string = False
        escape = False
        for ch in text:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
        return depth <= 0

    def eval_input(self, text: str):
        text = text.strip()
        if not text:
            return

        # Handle REPL meta commands
        if text.startswith(":"):
            cmd = text[1:].strip().lower()
            if cmd in ("quit", "exit", "q"):
                print("Goodbye!")
                sys.exit(0)
            elif cmd in ("help", "h"):
                print(HELP_TEXT)
                return
            elif cmd == "reset":
                self.reset()
                return
            elif cmd == "wat":
                if self.last_wat:
                    print(self.last_wat)
                else:
                    print("No code compiled yet.")
                return
            elif cmd == "env":
                if not self.definitions:
                    print("No definitions in current session.")
                else:
                    for d in self.definitions:
                        print(d)
                return
            else:
                print(f"Unknown command: {text}. Type :help for commands.")
                return

        # Check if it's a top-level definition (fn or struct)
        clean = text.lstrip(" \t\r\n(")
        is_fn = clean.startswith("fn ")
        is_struct = clean.startswith("struct ")

        if is_fn or is_struct:
            # Validate and compile definition
            module_code = "(module\n" + "\n".join(self.definitions) + "\n" + text + "\n)"
            diag = self.runner.check_source(module_code)
            if diag.get("status") != "ok":
                self._print_error(diag)
                return
            self.definitions.append(text)
            name = text.split()[1].rstrip(")]")
            kind = "function" if is_fn else "struct"
            print(f"\033[1;32mDefined {kind}:\033[0m {name}")
            return

        # Otherwise it's an expression to evaluate
        # Infer return type or wrap in a temporary runner function
        # Try returning i32, then f64, then bool, or void
        eval_module = None
        eval_fn_name = "__repl_eval"

        # Check with void, i32, f64, string, bool
        candidate_types = ["i32", "f64", "bool", "string", "void"]
        matched_module = None

        for ret_t in candidate_types:
            if ret_t == "void":
                candidate = (
                    "(module\n"
                    + "\n".join(self.definitions)
                    + f"\n  (fn {eval_fn_name} ()\n    {text}\n  )\n)"
                )
            else:
                candidate = (
                    "(module\n"
                    + "\n".join(self.definitions)
                    + f"\n  (fn {eval_fn_name} () -> {ret_t}\n    {text}\n  )\n)"
                )
            diag = self.runner.check_source(candidate)
            if diag.get("status") == "ok":
                matched_module = candidate
                break

        if not matched_module:
            # Emit error from the most relevant check (i32)
            diag = self.runner.check_source(
                "(module\n" + "\n".join(self.definitions) + f"\n  (fn {eval_fn_name} () -> i32\n    {text}\n  )\n)"
            )
            self._print_error(diag)
            return

        try:
            self.last_wat = self.runner.compile_to_wat(matched_module)
            result = self.runner.execute_function(matched_module, eval_fn_name)
            if result is not None:
                print(f"\033[1;35m=>\033[0m {result}")
        except Exception as e:
            print(f"\033[1;31mRuntime Error:\033[0m {e}")

    def _print_error(self, diag: dict):
        print("\033[1;31mCompiler Diagnostic:\033[0m")
        print(json.dumps(diag, indent=2))

    def run(self):
        print(BANNER)
        buffer = []
        while True:
            try:
                prompt = "synap> " if not buffer else "...    "
                line = input(prompt)
                buffer.append(line)
                combined = "\n".join(buffer)
                if self._is_balanced(combined):
                    full_text = combined.strip()
                    buffer.clear()
                    if full_text:
                        self.eval_input(full_text)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting SynapLang REPL.")
                break

def start_repl():
    SynapRepl().run()
