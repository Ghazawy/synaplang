import sys
from typing import Any, Dict, List, Optional
from wasmtime import Engine, Store, Module as WasmModule, Instance, Linker, FuncType, ValType
from src.parser import Parser
from src.type_checker import TypeChecker, TypeErrorException
from src.codegen_wasm import WasmCodegen

class Runner:
    def __init__(self):
        self.parser = Parser()
        self.type_checker = TypeChecker()
        self.codegen = WasmCodegen()
        self.engine = Engine()
        self.captured_output: List[str] = []

    def check_source(self, source_code: str) -> dict:
        try:
            ast = self.parser.parse(source_code)
            return self.type_checker.check(ast)
        except TypeErrorException as e:
            return e.to_dict()
        except Exception as e:
            return {
                "status": "error",
                "error_type": "SyntaxError",
                "message": str(e),
                "suggested_fix": "Verify that all S-expressions are properly formed and balanced."
            }

    def compile_to_wat(self, source_code: str) -> str:
        ast = self.parser.parse(source_code)
        self.type_checker.check(ast)
        return self.codegen.generate(ast)

    def execute_function(self, source_code: str, fn_name: str, *args, capture_stdout: bool = False) -> Any:
        wat = self.compile_to_wat(source_code)
        store = Store(self.engine)
        linker = Linker(self.engine)
        self.captured_output.clear()

        def host_print_str(caller, ptr: int, length: int):
            mem = caller.get("memory")
            data = mem.data_ptr(caller)
            text = bytes(data[ptr : ptr + length]).decode("utf-8")
            self.captured_output.append(text)
            if not capture_stdout:
                sys.stdout.write(text)
                sys.stdout.flush()

        def host_println_str(caller, ptr: int, length: int):
            mem = caller.get("memory")
            data = mem.data_ptr(caller)
            text = bytes(data[ptr : ptr + length]).decode("utf-8") + "\n"
            self.captured_output.append(text)
            if not capture_stdout:
                sys.stdout.write(text)
                sys.stdout.flush()

        def host_print_i32(val: int):
            text = f"{val}\n"
            self.captured_output.append(text)
            if not capture_stdout:
                sys.stdout.write(text)
                sys.stdout.flush()

        def host_print_f64(val: float):
            text = f"{val}\n"
            self.captured_output.append(text)
            if not capture_stdout:
                sys.stdout.write(text)
                sys.stdout.flush()

        linker.define_func("env", "print_str", FuncType([ValType.i32(), ValType.i32()], []), host_print_str, access_caller=True)
        linker.define_func("env", "println_str", FuncType([ValType.i32(), ValType.i32()], []), host_println_str, access_caller=True)
        linker.define_func("env", "print_i32", FuncType([ValType.i32()], []), host_print_i32)
        linker.define_func("env", "print_f64", FuncType([ValType.f64()], []), host_print_f64)

        wasm_module = WasmModule(self.engine, wat)
        instance = linker.instantiate(store, wasm_module)
        exports = instance.exports(store)
        if fn_name not in exports:
            raise ValueError(f"Function '{fn_name}' not found in compiled WebAssembly exports")
        func = exports[fn_name]
        return func(store, *args)

    def prepare_callable(self, source_code: str, fn_name: str):
        wat = self.compile_to_wat(source_code)
        store = Store(self.engine)
        linker = Linker(self.engine)
        linker.define_func("env", "print_str", FuncType([ValType.i32(), ValType.i32()], []), lambda c, p, l: None, access_caller=True)
        linker.define_func("env", "println_str", FuncType([ValType.i32(), ValType.i32()], []), lambda c, p, l: None, access_caller=True)
        linker.define_func("env", "print_i32", FuncType([ValType.i32()], []), lambda v: None)
        linker.define_func("env", "print_f64", FuncType([ValType.f64()], []), lambda v: None)
        wasm_module = WasmModule(self.engine, wat)
        instance = linker.instantiate(store, wasm_module)
        exports = instance.exports(store)
        if fn_name not in exports:
            raise ValueError(f"Function '{fn_name}' not found in compiled WebAssembly exports")
        func = exports[fn_name]
        return lambda *args: func(store, *args)
