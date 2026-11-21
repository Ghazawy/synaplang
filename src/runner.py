from typing import Any, Dict, List, Optional
from wasmtime import Engine, Store, Module as WasmModule, Instance
from src.parser import Parser
from src.type_checker import TypeChecker, TypeErrorException
from src.codegen_wasm import WasmCodegen

class Runner:
    def __init__(self):
        self.parser = Parser()
        self.type_checker = TypeChecker()
        self.codegen = WasmCodegen()
        self.engine = Engine()

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

    def execute_function(self, source_code: str, fn_name: str, *args) -> Any:
        wat = self.compile_to_wat(source_code)
        store = Store(self.engine)
        wasm_module = WasmModule(self.engine, wat)
        instance = Instance(store, wasm_module, [])
        exports = instance.exports(store)
        if fn_name not in exports:
            raise ValueError(f"Function '{fn_name}' not found in compiled WebAssembly exports")
        func = exports[fn_name]
        return func(store, *args)
