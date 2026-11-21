import argparse
import sys
import json
import os

# Ensure package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.runner import Runner

def main():
    parser = argparse.ArgumentParser(
        prog="ail",
        description="AI-Native Programming Language (AIL) Toolchain"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: run
    run_parser = subparsers.add_parser("run", help="Compile and execute an AIL source file in Wasmtime")
    run_parser.add_argument("file", help="Path to .ail source file")
    run_parser.add_argument("--fn", default="main", help="Function name to execute (default: main)")
    run_parser.add_argument("args", nargs="*", help="Arguments to pass to the function")

    # Command: compile
    compile_parser = subparsers.add_parser("compile", help="Compile an AIL source file to WebAssembly Text (.wat)")
    compile_parser.add_argument("file", help="Path to .ail source file")
    compile_parser.add_argument("-o", "--output", required=True, help="Output path for .wat file")

    # Command: check
    check_parser = subparsers.add_parser("check", help="Type-check an AIL source file")
    check_parser.add_argument("file", help="Path to .ail source file")
    check_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON diagnostics")

    # Command: export-gbnf
    gbnf_parser = subparsers.add_parser("export-gbnf", help="Export GBNF grammar for llama.cpp / Ollama")
    gbnf_parser.add_argument("-o", "--output", default="grammar/synap.gbnf", help="Output file path (default: grammar/synap.gbnf)")

    # Command: repl
    subparsers.add_parser("repl", help="Start the interactive SynapLang S-Expression REPL")

    args = parser.parse_args()
    runner = Runner()

    if args.command == "repl":
        from src.repl import start_repl
        start_repl()
        sys.exit(0)

    if args.command == "export-gbnf":
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_gbnf = os.path.join(base_dir, "grammar", "synap.gbnf")
        with open(source_gbnf, "r", encoding="utf-8") as f:
            content = f.read()
        out_path = args.output
        if not os.path.isabs(out_path):
            out_path = os.path.join(os.getcwd(), out_path)
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully exported GBNF grammar to '{out_path}'")
        sys.exit(0)

    if not os.path.exists(args.file):
        error_payload = {
            "status": "error",
            "error_type": "FileNotFound",
            "message": f"Source file '{args.file}' not found.",
            "suggested_fix": "Provide a valid path to an existing .ail file."
        }
        if getattr(args, "json", False):
            print(json.dumps(error_payload, indent=2))
        else:
            print(f"Error: {error_payload['message']}", file=sys.stderr)
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    if args.command == "check":
        diag = runner.check_source(source)
        if args.json:
            print(json.dumps(diag, indent=2))
        else:
            if diag.get("status") == "ok":
                print("Type check passed successfully.")
            else:
                print(f"Type check failed: {diag.get('message')}", file=sys.stderr)
                if "suggested_fix" in diag:
                    print(f"Fix: {diag['suggested_fix']}", file=sys.stderr)
        sys.exit(0 if diag.get("status") == "ok" else 1)

    elif args.command == "compile":
        try:
            wat = runner.compile_to_wat(source)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(wat)
            print(f"Successfully compiled '{args.file}' -> '{args.output}'")
            sys.exit(0)
        except Exception as e:
            print(f"Compilation error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "run":
        try:
            parsed_args = []
            for a in args.args:
                try:
                    parsed_args.append(int(a))
                except ValueError:
                    try:
                        parsed_args.append(float(a))
                    except ValueError:
                        parsed_args.append(a)

            result = runner.execute_function(source, args.fn, *parsed_args)
            if result is not None:
                print(result)
            sys.exit(0)
        except Exception as e:
            print(f"Execution error: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
