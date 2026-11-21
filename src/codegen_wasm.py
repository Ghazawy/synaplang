import struct
from typing import List, Dict, Set as PySet
from src.ail_ast import (
    Module, Function, Param, Expr, Literal, VarRef, Let, Set,
    BinaryOp, UnaryOp, If, While, Block, Call, Return,
    ArrNew, ArrGet, ArrSet, ArrLen, ArrLit,
    PrintStr, PrintlnStr, PrintI32, PrintF64, StrLen, StrConcat,
    Type
)

def wasm_type(t: str) -> str:
    if t in (Type.I32, Type.BOOL, Type.ARR_I32, Type.STRING):
        return "i32"
    if t == Type.F64:
        return "f64"
    return "i32"

class WasmCodegen:
    def __init__(self):
        self.label_counter = 0
        self.string_literals: Dict[str, int] = {}

    def _next_label(self, prefix: str = "label") -> str:
        self.label_counter += 1
        return f"${prefix}_{self.label_counter}"

    def _collect_strings(self, module: Module) -> Dict[str, int]:
        strings: Dict[str, int] = {}
        curr_offset = 64

        def walk(e: Expr):
            nonlocal curr_offset
            if isinstance(e, Literal) and e.type_name == Type.STRING:
                val = str(e.value)
                if val not in strings:
                    # data format: 4 bytes length, then UTF-8 bytes, then null terminator
                    data_ptr = curr_offset + 4
                    strings[val] = data_ptr
                    encoded = val.encode("utf-8")
                    total_bytes = 4 + len(encoded) + 1
                    # align to 8 bytes
                    aligned_bytes = (total_bytes + 7) & ~7
                    curr_offset += aligned_bytes
            elif isinstance(e, Let) and e.value:
                walk(e.value)
            elif isinstance(e, Set) and e.value:
                walk(e.value)
            elif isinstance(e, BinaryOp):
                walk(e.left)
                walk(e.right)
            elif isinstance(e, UnaryOp):
                walk(e.expr)
            elif isinstance(e, If):
                walk(e.cond)
                walk(e.then_branch)
                if e.else_branch:
                    walk(e.else_branch)
            elif isinstance(e, While):
                walk(e.cond)
                for b in e.body:
                    walk(b)
            elif isinstance(e, Block):
                for b in e.exprs:
                    walk(b)
            elif isinstance(e, Call):
                for a in e.args:
                    walk(a)
            elif isinstance(e, Return) and e.expr:
                walk(e.expr)
            elif isinstance(e, ArrNew):
                walk(e.size)
            elif isinstance(e, ArrGet):
                walk(e.arr)
                walk(e.index)
            elif isinstance(e, ArrSet):
                walk(e.arr)
                walk(e.index)
                walk(e.value)
            elif isinstance(e, ArrLen):
                walk(e.arr)
            elif isinstance(e, ArrLit):
                for el in e.elements:
                    walk(el)
            elif isinstance(e, (PrintStr, PrintlnStr, PrintI32, PrintF64, StrLen)):
                walk(e.expr)
            elif isinstance(e, StrConcat):
                walk(e.left)
                walk(e.right)

        for fn in module.functions:
            for expr in fn.body:
                walk(expr)

        return strings, max(1024, curr_offset)

    def generate(self, module: Module) -> str:
        self.label_counter = 0
        self.string_literals, initial_heap = self._collect_strings(module)

        lines = [
            "(module",
            "  ;; Host function imports for printing",
            "  (import \"env\" \"print_str\" (func $print_str (param i32 i32)))",
            "  (import \"env\" \"println_str\" (func $println_str (param i32 i32)))",
            "  (import \"env\" \"print_i32\" (func $print_i32 (param i32)))",
            "  (import \"env\" \"print_f64\" (func $print_f64 (param f64)))",
            "",
            "  (memory (export \"memory\") 2)",
            f"  (global $heap_ptr (mut i32) (i32.const {initial_heap}))",
            ""
        ]

        # Generate static data segments for string literals
        for text, data_ptr in self.string_literals.items():
            encoded = text.encode("utf-8")
            base_offset = data_ptr - 4
            header_bytes = struct.pack("<I", len(encoded))
            full_bytes = header_bytes + encoded + b"\x00"
            hex_str = "".join(f"\\{b:02x}" for b in full_bytes)
            lines.append(f'  (data (i32.const {base_offset}) "{hex_str}")')

        lines.extend([
            "",
            "  ;; Linear memory allocator for dynamic arrays & strings",
            "  (func $_alloc_arr (param $size i32) (result i32)",
            "    (local $base i32)",
            "    (local $needed i32)",
            "    (local.set $base (global.get $heap_ptr))",
            "    (i32.store (local.get $base) (local.get $size))",
            "    (local.set $needed (i32.add (i32.const 4) (i32.mul (local.get $size) (i32.const 4))))",
            "    (local.set $needed (i32.and (i32.add (local.get $needed) (i32.const 7)) (i32.const -8)))",
            "    (global.set $heap_ptr (i32.add (global.get $heap_ptr) (local.get $needed)))",
            "    (i32.add (local.get $base) (i32.const 4))",
            "  )",
            "",
            "  ;; Dynamic string concatenation helper",
            "  (func $_str_concat (param $s1 i32) (param $s2 i32) (result i32)",
            "    (local $len1 i32)",
            "    (local $len2 i32)",
            "    (local $total_len i32)",
            "    (local $new_str i32)",
            "    (local $needed i32)",
            "    (local $i i32)",
            "    (local.set $len1 (i32.load (i32.sub (local.get $s1) (i32.const 4))))",
            "    (local.set $len2 (i32.load (i32.sub (local.get $s2) (i32.const 4))))",
            "    (local.set $total_len (i32.add (local.get $len1) (local.get $len2)))",
            "    (local.set $new_str (global.get $heap_ptr))",
            "    (i32.store (local.get $new_str) (local.get $total_len))",
            "    (local.set $needed (i32.add (i32.const 5) (local.get $total_len)))",
            "    (local.set $needed (i32.and (i32.add (local.get $needed) (i32.const 7)) (i32.const -8)))",
            "    (global.set $heap_ptr (i32.add (global.get $heap_ptr) (local.get $needed)))",
            "    (local.set $new_str (i32.add (local.get $new_str) (i32.const 4)))",
            "    (local.set $i (i32.const 0))",
            "    (block $break_c1",
            "      (loop $loop_c1",
            "        (br_if $break_c1 (i32.ge_s (local.get $i) (local.get $len1)))",
            "        (i32.store8",
            "          (i32.add (local.get $new_str) (local.get $i))",
            "          (i32.load8_u (i32.add (local.get $s1) (local.get $i)))",
            "        )",
            "        (local.set $i (i32.add (local.get $i) (i32.const 1)))",
            "        (br $loop_c1)",
            "      )",
            "    )",
            "    (local.set $i (i32.const 0))",
            "    (block $break_c2",
            "      (loop $loop_c2",
            "        (br_if $break_c2 (i32.ge_s (local.get $i) (local.get $len2)))",
            "        (i32.store8",
            "          (i32.add (i32.add (local.get $new_str) (local.get $len1)) (local.get $i))",
            "          (i32.load8_u (i32.add (local.get $s2) (local.get $i)))",
            "        )",
            "        (local.set $i (i32.add (local.get $i) (i32.const 1)))",
            "        (br $loop_c2)",
            "      )",
            "    )",
            "    (i32.store8 (i32.add (local.get $new_str) (local.get $total_len)) (i32.const 0))",
            "    (local.get $new_str)",
            "  )",
            ""
        ])

        for fn in module.functions:
            lines.append(self._generate_function(fn))

        lines.append(")")
        return "\n".join(lines)

    def _collect_locals(self, exprs: List[Expr], param_names: PySet[str]) -> Dict[str, str]:
        locals_dict: Dict[str, str] = {}
        has_arr_lit = False

        def walk(e: Expr):
            nonlocal has_arr_lit
            if isinstance(e, ArrLit):
                has_arr_lit = True
                for el in e.elements:
                    walk(el)
            elif isinstance(e, ArrNew):
                walk(e.size)
            elif isinstance(e, ArrGet):
                walk(e.arr)
                walk(e.index)
            elif isinstance(e, ArrSet):
                walk(e.arr)
                walk(e.index)
                walk(e.value)
            elif isinstance(e, ArrLen):
                walk(e.arr)
            elif isinstance(e, Let):
                if e.name not in param_names:
                    locals_dict[e.name] = wasm_type(e.type_name)
                if e.value:
                    walk(e.value)
            elif isinstance(e, Set):
                if e.value:
                    walk(e.value)
            elif isinstance(e, BinaryOp):
                walk(e.left)
                walk(e.right)
            elif isinstance(e, UnaryOp):
                walk(e.expr)
            elif isinstance(e, If):
                walk(e.cond)
                walk(e.then_branch)
                if e.else_branch:
                    walk(e.else_branch)
            elif isinstance(e, While):
                walk(e.cond)
                for b in e.body:
                    walk(b)
            elif isinstance(e, Block):
                for b in e.exprs:
                    walk(b)
            elif isinstance(e, Call):
                for a in e.args:
                    walk(a)
            elif isinstance(e, Return) and e.expr:
                walk(e.expr)
            elif isinstance(e, (PrintStr, PrintlnStr, PrintI32, PrintF64, StrLen)):
                walk(e.expr)
            elif isinstance(e, StrConcat):
                walk(e.left)
                walk(e.right)

        for e in exprs:
            walk(e)

        if has_arr_lit:
            locals_dict["__arr_tmp"] = "i32"

        return locals_dict

    def _generate_function(self, fn: Function) -> str:
        param_names = {p.name for p in fn.params}
        locals_dict = self._collect_locals(fn.body, param_names)

        fn_parts = [f'  (func ${fn.name} (export "{fn.name}")']
        
        for p in fn.params:
            fn_parts.append(f' (param ${p.name} {wasm_type(p.type_name)})')
            
        if fn.return_type != Type.VOID:
            fn_parts.append(f' (result {wasm_type(fn.return_type)})')

        fn_parts.append("\n")

        for name, t in locals_dict.items():
            fn_parts.append(f'    (local ${name} {t})\n')

        num_exprs = len(fn.body)
        for i, expr in enumerate(fn.body):
            is_last = (i == num_exprs - 1)
            code = self._generate_expr(expr, indent=4)
            
            expr_type = getattr(expr, "inferred_type", None)
            if not is_last and expr_type and expr_type != Type.VOID and not isinstance(expr, (Let, Set, While, ArrSet, PrintStr, PrintlnStr, PrintI32, PrintF64)):
                code = f"    (drop\n  {code}\n    )"
            fn_parts.append(f"{code}\n")

        fn_parts.append("  )")
        return "".join(fn_parts)

    def _generate_expr(self, expr: Expr, indent: int = 4) -> str:
        sp = " " * indent
        if isinstance(expr, Literal):
            if expr.type_name in (Type.I32, Type.ARR_I32):
                return f"{sp}(i32.const {int(expr.value)})"
            elif expr.type_name == Type.F64:
                val = float(expr.value)
                return f"{sp}(f64.const {val})"
            elif expr.type_name == Type.BOOL:
                val = 1 if expr.value else 0
                return f"{sp}(i32.const {val})"
            elif expr.type_name == Type.STRING:
                val = str(expr.value)
                data_ptr = self.string_literals.get(val, 64)
                return f"{sp}(i32.const {data_ptr})"

        if isinstance(expr, VarRef):
            return f"{sp}(local.get ${expr.name})"

        if isinstance(expr, Let):
            val_code = self._generate_expr(expr.value, indent + 2)
            return f"{sp}(local.set ${expr.name}\n{val_code}\n{sp})"

        if isinstance(expr, Set):
            val_code = self._generate_expr(expr.value, indent + 2)
            return f"{sp}(local.set ${expr.name}\n{val_code}\n{sp})"

        if isinstance(expr, BinaryOp):
            left_code = self._generate_expr(expr.left, indent + 2)
            right_code = self._generate_expr(expr.right, indent + 2)
            t = getattr(expr.left, "inferred_type", Type.I32)
            prefix = "f64" if t == Type.F64 else "i32"

            op_map = {
                "+": f"{prefix}.add",
                "-": f"{prefix}.sub",
                "*": f"{prefix}.mul",
                "/": f"{prefix}.div_s" if prefix == "i32" else "f64.div",
                "%": "i32.rem_s",
                "==": f"{prefix}.eq",
                "!=": f"{prefix}.ne",
                "<": f"{prefix}.lt_s" if prefix == "i32" else "f64.lt",
                "<=": f"{prefix}.le_s" if prefix == "i32" else "f64.le",
                ">": f"{prefix}.gt_s" if prefix == "i32" else "f64.gt",
                ">=": f"{prefix}.ge_s" if prefix == "i32" else "f64.ge",
                "and": "i32.and",
                "or": "i32.or",
            }
            instr = op_map.get(expr.op, f"{prefix}.add")
            return f"{sp}({instr}\n{left_code}\n{right_code}\n{sp})"

        if isinstance(expr, UnaryOp):
            inner_code = self._generate_expr(expr.expr, indent + 2)
            if expr.op == "not":
                return f"{sp}(i32.eqz\n{inner_code}\n{sp})"
            if expr.op == "neg":
                t = getattr(expr.expr, "inferred_type", Type.I32)
                if t == Type.F64:
                    return f"{sp}(f64.neg\n{inner_code}\n{sp})"
                else:
                    return f"{sp}(i32.sub\n{sp}  (i32.const 0)\n{inner_code}\n{sp})"

        if isinstance(expr, If):
            cond_code = self._generate_expr(expr.cond, indent + 2)
            then_code = self._generate_expr(expr.then_branch, indent + 4)
            res_type = getattr(expr, "inferred_type", Type.VOID)
            res_str = f" (result {wasm_type(res_type)})" if res_type != Type.VOID else ""

            if expr.else_branch:
                else_code = self._generate_expr(expr.else_branch, indent + 4)
                return (
                    f"{sp}(if{res_str}\n"
                    f"{cond_code}\n"
                    f"{sp}  (then\n{then_code}\n{sp}  )\n"
                    f"{sp}  (else\n{else_code}\n{sp}  )\n"
                    f"{sp})"
                )
            else:
                return (
                    f"{sp}(if\n"
                    f"{cond_code}\n"
                    f"{sp}  (then\n{then_code}\n{sp}  )\n"
                    f"{sp})"
                )

        if isinstance(expr, While):
            break_lbl = self._next_label("break")
            loop_lbl = self._next_label("loop")
            cond_code = self._generate_expr(expr.cond, indent + 4)
            body_lines = [self._generate_expr(b, indent + 4) for b in expr.body]
            body_str = "\n".join(body_lines)

            return (
                f"{sp}(block {break_lbl}\n"
                f"{sp}  (loop {loop_lbl}\n"
                f"{sp}    (br_if {break_lbl}\n"
                f"{sp}      (i32.eqz\n{cond_code}\n{sp}      )\n"
                f"{sp}    )\n"
                f"{body_str}\n"
                f"{sp}    (br {loop_lbl})\n"
                f"{sp}  )\n"
                f"{sp})"
            )

        if isinstance(expr, Block):
            lines = [self._generate_expr(b, indent + 2) for b in expr.exprs]
            joined = "\n".join(lines)
            return f"{sp}(block\n{joined}\n{sp})"

        if isinstance(expr, Call):
            args_code = [self._generate_expr(a, indent + 2) for a in expr.args]
            args_str = "\n".join(args_code)
            if args_str:
                return f"{sp}(call ${expr.fn_name}\n{args_str}\n{sp})"
            else:
                return f"{sp}(call ${expr.fn_name})"

        if isinstance(expr, Return):
            val_code = self._generate_expr(expr.expr, indent + 2)
            return f"{sp}(return\n{val_code}\n{sp})"

        if isinstance(expr, ArrNew):
            size_code = self._generate_expr(expr.size, indent + 2)
            return f"{sp}(call $_alloc_arr\n{size_code}\n{sp})"

        if isinstance(expr, ArrLen):
            arr_code = self._generate_expr(expr.arr, indent + 4)
            return (
                f"{sp}(i32.load\n"
                f"{sp}  (i32.sub\n"
                f"{arr_code}\n"
                f"{sp}    (i32.const 4)\n"
                f"{sp}  )\n"
                f"{sp})"
            )

        if isinstance(expr, ArrGet):
            arr_code = self._generate_expr(expr.arr, indent + 4)
            idx_code = self._generate_expr(expr.index, indent + 6)
            return (
                f"{sp}(i32.load\n"
                f"{sp}  (i32.add\n"
                f"{arr_code}\n"
                f"{sp}    (i32.mul\n"
                f"{idx_code}\n"
                f"{sp}      (i32.const 4)\n"
                f"{sp}    )\n"
                f"{sp}  )\n"
                f"{sp})"
            )

        if isinstance(expr, ArrSet):
            arr_code = self._generate_expr(expr.arr, indent + 4)
            idx_code = self._generate_expr(expr.index, indent + 6)
            val_code = self._generate_expr(expr.value, indent + 2)
            return (
                f"{sp}(i32.store\n"
                f"{sp}  (i32.add\n"
                f"{arr_code}\n"
                f"{sp}    (i32.mul\n"
                f"{idx_code}\n"
                f"{sp}      (i32.const 4)\n"
                f"{sp}    )\n"
                f"{sp}  )\n"
                f"{val_code}\n"
                f"{sp})"
            )

        if isinstance(expr, ArrLit):
            n = len(expr.elements)
            lines = [
                f"{sp}(block (result i32)",
                f"{sp}  (local.set $__arr_tmp (call $_alloc_arr (i32.const {n})))"
            ]
            for i, el in enumerate(expr.elements):
                el_code = self._generate_expr(el, indent + 4)
                offset = i * 4
                lines.append(
                    f"{sp}  (i32.store (i32.add (local.get $__arr_tmp) (i32.const {offset}))\n"
                    f"{el_code}\n"
                    f"{sp}  )"
                )
            lines.append(f"{sp}  (local.get $__arr_tmp)")
            lines.append(f"{sp})")
            return "\n".join(lines)

        if isinstance(expr, PrintStr):
            str_code = self._generate_expr(expr.expr, indent + 4)
            return (
                f"{sp}(call $print_str\n"
                f"{str_code}\n"
                f"{sp}  (i32.load (i32.sub\n{str_code}\n{sp}    (i32.const 4)))\n"
                f"{sp})"
            )

        if isinstance(expr, PrintlnStr):
            str_code = self._generate_expr(expr.expr, indent + 4)
            return (
                f"{sp}(call $println_str\n"
                f"{str_code}\n"
                f"{sp}  (i32.load (i32.sub\n{str_code}\n{sp}    (i32.const 4)))\n"
                f"{sp})"
            )

        if isinstance(expr, PrintI32):
            val_code = self._generate_expr(expr.expr, indent + 2)
            return f"{sp}(call $print_i32\n{val_code}\n{sp})"

        if isinstance(expr, PrintF64):
            val_code = self._generate_expr(expr.expr, indent + 2)
            return f"{sp}(call $print_f64\n{val_code}\n{sp})"

        if isinstance(expr, StrLen):
            str_code = self._generate_expr(expr.expr, indent + 4)
            return (
                f"{sp}(i32.load\n"
                f"{sp}  (i32.sub\n"
                f"{str_code}\n"
                f"{sp}    (i32.const 4)\n"
                f"{sp}  )\n"
                f"{sp})"
            )

        if isinstance(expr, StrConcat):
            left_code = self._generate_expr(expr.left, indent + 2)
            right_code = self._generate_expr(expr.right, indent + 2)
            return (
                f"{sp}(call $_str_concat\n"
                f"{left_code}\n"
                f"{right_code}\n"
                f"{sp})"
            )

        return f"{sp};; unknown expr"
