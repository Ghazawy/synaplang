import re
from typing import Any, Tuple, Optional, List, Union
from src.ail_ast import (
    ASTNode, Module, Function, StructDef, StructField, Param, Expr,
    Literal, VarRef, Let, Set, BinaryOp, UnaryOp, If, While, Block,
    Call, Return, ArrNew, ArrGet, ArrSet, ArrLen, ArrLit,
    StructNew, StructGet, StructSet, PrintStr, PrintlnStr, PrintI32, PrintF64,
    StrLen, StrConcat, Type
)
from src.parser import Parser
from src.type_checker import TypeChecker, TypeErrorException

def ast_to_s_expr(node: ASTNode, indent: int = 0) -> str:
    """Format any AST node into canonical S-expression syntax."""
    sp = "  " * indent

    if isinstance(node, Module):
        lines = ["(module"]
        for s in getattr(node, "structs", []):
            lines.append(ast_to_s_expr(s, indent + 1))
        for fn in getattr(node, "functions", []):
            lines.append(ast_to_s_expr(fn, indent + 1))
        lines.append(")")
        return "\n".join(lines)

    if isinstance(node, StructDef):
        fields_str = " ".join(f"[{f.name}: {f.type_name}]" for f in node.fields)
        return f"{sp}(struct {node.name} {fields_str})"

    if isinstance(node, Function):
        params_str = " ".join(f"({p.name}: {p.type_name})" for p in node.params)
        ret_str = f" -> {node.return_type}" if node.return_type != Type.VOID else ""
        lines = [f"{sp}(fn {node.name} ({params_str}){ret_str}"]
        for b in node.body:
            lines.append(ast_to_s_expr(b, indent + 1))
        lines.append(f"{sp})")
        return "\n".join(lines)

    if isinstance(node, Literal):
        if node.type_name == Type.STRING:
            # Escape string
            escaped = str(node.value).replace('"', '\\"').replace('\n', '\\n')
            return f'"{escaped}"'
        elif node.type_name == Type.BOOL:
            return "true" if node.value else "false"
        elif node.type_name == Type.F64:
            return str(float(node.value))
        else:
            return str(int(node.value))

    if isinstance(node, VarRef):
        return node.name

    if isinstance(node, Let):
        val_str = ast_to_s_expr(node.value, indent)
        return f"{sp}(let {node.name}: {node.type_name} {val_str})"

    if isinstance(node, Set):
        val_str = ast_to_s_expr(node.value, indent)
        return f"{sp}(set {node.name} {val_str})"

    if isinstance(node, BinaryOp):
        l_str = ast_to_s_expr(node.left, indent)
        r_str = ast_to_s_expr(node.right, indent)
        return f"({node.op} {l_str} {r_str})"

    if isinstance(node, UnaryOp):
        inner = ast_to_s_expr(node.expr, indent)
        return f"({node.op} {inner})"

    if isinstance(node, If):
        cond = ast_to_s_expr(node.cond, indent)
        then_b = ast_to_s_expr(node.then_branch, indent + 1)
        if node.else_branch:
            else_b = ast_to_s_expr(node.else_branch, indent + 1)
            return f"{sp}(if {cond}\n{then_b}\n{else_b}\n{sp})"
        return f"{sp}(if {cond}\n{then_b}\n{sp})"

    if isinstance(node, While):
        cond = ast_to_s_expr(node.cond, indent)
        lines = [f"{sp}(while {cond}"]
        for b in node.body:
            lines.append(ast_to_s_expr(b, indent + 1))
        lines.append(f"{sp})")
        return "\n".join(lines)

    if isinstance(node, Block):
        lines = [f"{sp}(do"]
        for b in node.exprs:
            lines.append(ast_to_s_expr(b, indent + 1))
        lines.append(f"{sp})")
        return "\n".join(lines)

    if isinstance(node, Call):
        args_str = " ".join(ast_to_s_expr(a, indent) for a in node.args)
        if args_str:
            return f"{sp}(call {node.fn_name} {args_str})"
        return f"{sp}(call {node.fn_name})"

    if isinstance(node, Return):
        inner = ast_to_s_expr(node.expr, indent)
        return f"{sp}(return {inner})"

    if isinstance(node, ArrNew):
        sz = ast_to_s_expr(node.size, indent)
        return f"(arr_new {sz})"

    if isinstance(node, ArrGet):
        arr = ast_to_s_expr(node.arr, indent)
        idx = ast_to_s_expr(node.index, indent)
        return f"(arr_get {arr} {idx})"

    if isinstance(node, ArrSet):
        arr = ast_to_s_expr(node.arr, indent)
        idx = ast_to_s_expr(node.index, indent)
        val = ast_to_s_expr(node.value, indent)
        return f"{sp}(arr_set {arr} {idx} {val})"

    if isinstance(node, ArrLen):
        arr = ast_to_s_expr(node.arr, indent)
        return f"(arr_len {arr})"

    if isinstance(node, ArrLit):
        elems = " ".join(ast_to_s_expr(e, indent) for e in node.elements)
        return f"(array {elems})"

    if isinstance(node, StructNew):
        args = " ".join(ast_to_s_expr(a, indent) for a in node.args)
        return f"(struct_new {node.struct_name} {args})"

    if isinstance(node, StructGet):
        t = ast_to_s_expr(node.target, indent)
        return f"(struct_get {t} {node.field_name})"

    if isinstance(node, StructSet):
        t = ast_to_s_expr(node.target, indent)
        v = ast_to_s_expr(node.value, indent)
        return f"{sp}(struct_set {t} {node.field_name} {v})"

    if isinstance(node, PrintStr):
        return f"{sp}(print {ast_to_s_expr(node.expr, indent)})"

    if isinstance(node, PrintlnStr):
        return f"{sp}(println {ast_to_s_expr(node.expr, indent)})"

    if isinstance(node, PrintI32):
        return f"{sp}(print_i32 {ast_to_s_expr(node.expr, indent)})"

    if isinstance(node, PrintF64):
        return f"{sp}(print_f64 {ast_to_s_expr(node.expr, indent)})"

    if isinstance(node, StrLen):
        return f"(str_len {ast_to_s_expr(node.expr, indent)})"

    if isinstance(node, StrConcat):
        l = ast_to_s_expr(node.left, indent)
        r = ast_to_s_expr(node.right, indent)
        return f"(str_concat {l} {r})"

    return str(node)

class ASTPatcher:
    def __init__(self):
        self.parser = Parser()
        self.type_checker = TypeChecker()

    def resolve_path(self, module: Module, path: str) -> Tuple[Any, Union[str, int], Any]:
        """
        Navigates an AST path and returns:
        (parent_object, key_or_index_in_parent, target_node)
        """
        path = path.strip()
        segments = []

        # Handle symbolic paths like @fn:main.body[0] or @struct:Point.fields[1]
        if path.startswith("@"):
            match = re.match(r"^@(fn|struct):([a-zA-Z0-9_]+)(\..*)?$", path)
            if not match:
                raise ValueError(f"Invalid symbolic AST path format: '{path}'")
            kind, name, rest = match.groups()
            rest = rest or ""

            if kind == "fn":
                found = None
                for i, fn in enumerate(module.functions):
                    if fn.name == name:
                        segments.append("functions")
                        segments.append(i)
                        found = fn
                        break
                if not found:
                    raise KeyError(f"Function '{name}' not found in module")
            elif kind == "struct":
                found = None
                for i, st in enumerate(getattr(module, "structs", [])):
                    if st.name == name:
                        segments.append("structs")
                        segments.append(i)
                        found = st
                        break
                if not found:
                    raise KeyError(f"Struct '{name}' not found in module")

            # Parse remainder like .body[0].then
            parts = [p for p in rest.split(".") if p]
            for part in parts:
                idx_match = re.match(r"^([a-zA-Z0-9_]+)\[(\d+)\]$", part)
                if idx_match:
                    prop, idx = idx_match.groups()
                    segments.append(prop)
                    segments.append(int(idx))
                else:
                    segments.append(part)
        else:
            # Handle dot/bracket path like functions[0].body[1]
            parts = path.replace("[", ".[").split(".")
            for part in parts:
                if not part:
                    continue
                if part.startswith("[") and part.endswith("]"):
                    segments.append(int(part[1:-1]))
                else:
                    segments.append(part)

        # Traverse AST
        curr = module
        parent = None
        last_accessor = None

        for seg in segments:
            parent = curr
            last_accessor = seg
            if isinstance(curr, list):
                if not isinstance(seg, int) or seg >= len(curr):
                    raise IndexError(f"List index out of range: {seg} (len={len(curr)})")
                curr = curr[seg]
            elif isinstance(curr, (dict, object)):
                if isinstance(seg, int):
                    raise TypeError(f"Cannot index object with integer: {seg}")
                if hasattr(curr, seg):
                    curr = getattr(curr, seg)
                elif isinstance(curr, dict) and seg in curr:
                    curr = curr[seg]
                else:
                    raise AttributeError(f"Object {type(curr).__name__} has no attribute '{seg}'")
            else:
                raise TypeError(f"Cannot navigate into {type(curr).__name__}")

        return parent, last_accessor, curr

    def patch(self, source_code: str, path: str, replacement_code: str) -> str:
        """
        Applies a replacement S-expression at the targeted AST path and returns
        the formatted source code.
        """
        module = self.parser.parse(source_code)
        parent, accessor, target = self.resolve_path(module, path)

        # Parse replacement code
        # Wrap replacement in a dummy function if it's an expression
        parsed_replacement = None
        wrap_src = f"(module (fn __dummy () {replacement_code}))"
        try:
            dummy_mod = self.parser.parse(wrap_src)
            parsed_replacement = dummy_mod.functions[0].body[0]
        except Exception:
            # Try parsing as a function or struct definition
            wrap_top = f"(module {replacement_code})"
            dummy_top = self.parser.parse(wrap_top)
            if dummy_top.functions:
                parsed_replacement = dummy_top.functions[0]
            elif getattr(dummy_top, "structs", []):
                parsed_replacement = dummy_top.structs[0]
            else:
                raise ValueError(f"Could not parse replacement snippet: {replacement_code}")

        # Perform replacement
        if isinstance(parent, list):
            parent[accessor] = parsed_replacement
        elif hasattr(parent, str(accessor)):
            setattr(parent, str(accessor), parsed_replacement)
        elif isinstance(parent, dict):
            parent[accessor] = parsed_replacement
        else:
            raise TypeError(f"Cannot apply patch to parent of type {type(parent).__name__}")

        # Check types on patched module
        self.type_checker.check(module)

        # Return regenerated S-expression source
        return ast_to_s_expr(module)

_default_patcher = ASTPatcher()

def patch(source_code: str, path: str, replacement_code: str) -> str:
    """Convenience function to patch source code via default ASTPatcher."""
    return _default_patcher.patch(source_code, path, replacement_code)

