import sys
import json
from typing import Any, Dict, List, Optional
from wasmtime import Config, Engine, Store, Module as WasmModule, Instance, Linker, FuncType, ValType, Trap, TrapCode
from src.parser import Parser
from src.type_checker import TypeChecker, TypeErrorException
from src.codegen_wasm import WasmCodegen

class SynapRuntimeError(Exception):
    def __init__(self, error_type: str, message: str, suggested_fix: str = ""):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.suggested_fix = suggested_fix

    def to_dict(self) -> dict:
        return {
            "status": "error",
            "error_type": self.error_type,
            "message": self.message,
            "suggested_fix": self.suggested_fix
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

class OutOfFuelError(SynapRuntimeError):
    def __init__(self, fuel_limit: int):
        super().__init__(
            error_type="OutOfFuel",
            message=f"Execution halted: instruction fuel limit ({fuel_limit}) exhausted. Infinite loop or runaway recursion detected.",
            suggested_fix="Ensure loops have valid termination conditions, or increase fuel limit with --fuel."
        )

class MemoryOutOfBoundsError(SynapRuntimeError):
    def __init__(self, details: str = ""):
        super().__init__(
            error_type="MemoryOutOfBounds",
            message=f"Out of bounds linear memory access: {details}".strip(),
            suggested_fix="Verify array/struct indices are within valid allocated boundaries (0 <= index < length)."
        )

class Runner:
    def __init__(self, default_fuel: Optional[int] = 1_000_000):
        self.parser = Parser()
        self.type_checker = TypeChecker()
        self.codegen = WasmCodegen()
        self.default_fuel = default_fuel

        # Configure WebAssembly engine with fuel metering
        config = Config()
        config.consume_fuel = True
        self.engine = Engine(config)
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

    def _setup_store_and_linker(self, fuel: Optional[int], capture_stdout: bool = False):
        store = Store(self.engine)
        actual_fuel = fuel if fuel is not None else self.default_fuel
        if actual_fuel and actual_fuel > 0:
            store.set_fuel(actual_fuel)

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

        return store, linker, actual_fuel

    def _handle_trap(self, trap: Trap, fuel_limit: Optional[int]):
        code = getattr(trap, "trap_code", None)
        if code == TrapCode.OUT_OF_FUEL:
            raise OutOfFuelError(fuel_limit or self.default_fuel or 0)
        elif code == TrapCode.INTEGER_DIVISION_BY_ZERO:
            raise SynapRuntimeError(
                error_type="DivisionByZero",
                message="Division by zero in WebAssembly runtime.",
                suggested_fix="Ensure divisor expression evaluates to non-zero before division."
            )
        elif code in (TrapCode.MEMORY_OUT_OF_BOUNDS, TrapCode.ARRAY_OUT_OF_BOUNDS):
            raise MemoryOutOfBoundsError(str(trap))
        else:
            raise SynapRuntimeError(
                error_type="RuntimeTrap",
                message=f"WebAssembly execution trapped: {trap}",
                suggested_fix="Check array boundaries, type safety, and memory allocations."
            )

    def execute_function(self, source_code: str, fn_name: str, *args, fuel: Optional[int] = None, capture_stdout: bool = False) -> Any:
        wat = self.compile_to_wat(source_code)
        store, linker, actual_fuel = self._setup_store_and_linker(fuel, capture_stdout=capture_stdout)

        wasm_module = WasmModule(self.engine, wat)
        instance = linker.instantiate(store, wasm_module)
        exports = instance.exports(store)
        if fn_name not in exports:
            raise ValueError(f"Function '{fn_name}' not found in compiled WebAssembly exports")
        func = exports[fn_name]

        try:
            return func(store, *args)
        except Trap as t:
            self._handle_trap(t, actual_fuel)

    def prepare_callable(self, source_code: str, fn_name: str, fuel: Optional[int] = None):
        wat = self.compile_to_wat(source_code)
        store, linker, actual_fuel = self._setup_store_and_linker(fuel, capture_stdout=True)

        wasm_module = WasmModule(self.engine, wat)
        instance = linker.instantiate(store, wasm_module)
        exports = instance.exports(store)
        if fn_name not in exports:
            raise ValueError(f"Function '{fn_name}' not found in compiled WebAssembly exports")
        func = exports[fn_name]

        def call_wrapper(*args):
            # replenish fuel for each repeated execution
            if actual_fuel and actual_fuel > 0:
                store.set_fuel(actual_fuel)
            try:
                return func(store, *args)
            except Trap as t:
                self._handle_trap(t, actual_fuel)

        return call_wrapper
