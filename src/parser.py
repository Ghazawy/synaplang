import os
from lark import Lark, Transformer, v_args, Token, Tree
from src.ail_ast import (
    Module, Function, Param, Expr, Literal, VarRef, Let, Set,
    BinaryOp, UnaryOp, If, While, Block, Call, Return,
    ArrNew, ArrGet, ArrSet, ArrLen, ArrLit,
    StructDef, StructField, StructNew, StructGet, StructSet,
    PrintStr, PrintlnStr, PrintI32, PrintF64, StrLen, StrConcat,
    Type, SourceLocation
)

def _get_loc(meta) -> SourceLocation:
    if hasattr(meta, 'line') and hasattr(meta, 'column'):
        return SourceLocation(line=meta.line, column=meta.column)
    return SourceLocation(line=1, column=1)

@v_args(meta=True)
class ASTBuilder(Transformer):
    def start(self, meta, children):
        return children[0]

    def type_i32(self, meta, children):
        return Type.I32

    def type_f64(self, meta, children):
        return Type.F64

    def type_bool(self, meta, children):
        return Type.BOOL

    def type_arr_i32(self, meta, children):
        return Type.ARR_I32

    def type_string(self, meta, children):
        return Type.STRING

    def type_custom(self, meta, children):
        return str(children[0])

    def param(self, meta, children):
        name = str(children[0])
        type_name = str(children[1])
        return Param(loc=_get_loc(meta), name=name, type_name=type_name)

    def param_list(self, meta, children):
        return [c for c in children if isinstance(c, Param)]

    def return_type(self, meta, children):
        return str(children[0])

    def int_lit(self, meta, children):
        return Literal(loc=_get_loc(meta), value=int(children[0]), type_name=Type.I32)

    def float_lit(self, meta, children):
        return Literal(loc=_get_loc(meta), value=float(children[0]), type_name=Type.F64)

    def bool_true(self, meta, children):
        return Literal(loc=_get_loc(meta), value=True, type_name=Type.BOOL)

    def bool_false(self, meta, children):
        return Literal(loc=_get_loc(meta), value=False, type_name=Type.BOOL)

    def string_lit(self, meta, children):
        raw = str(children[0])
        # strip surrounding quotes and decode escape characters
        inner = raw[1:-1]
        try:
            val = inner.encode('utf-8').decode('unicode_escape')
        except Exception:
            val = inner
        return Literal(loc=_get_loc(meta), value=val, type_name=Type.STRING)

    def var_ref(self, meta, children):
        return VarRef(loc=_get_loc(meta), name=str(children[0]))

    def let_expr(self, meta, children):
        name = str(children[0])
        type_name = str(children[1])
        expr = children[2]
        return Let(loc=_get_loc(meta), name=name, type_name=type_name, value=expr)

    def set_expr(self, meta, children):
        name = str(children[0])
        expr = children[1]
        return Set(loc=_get_loc(meta), name=name, value=expr)

    def bin_op(self, meta, children):
        return str(children[0])

    def binary_op(self, meta, children):
        op = str(children[0].children[0]) if isinstance(children[0], Tree) else str(children[0])
        left = children[1]
        right = children[2]
        return BinaryOp(loc=_get_loc(meta), op=op, left=left, right=right)

    def unary_op(self, meta, children):
        op = str(children[0])
        expr = children[1]
        return UnaryOp(loc=_get_loc(meta), op=op, expr=expr)

    def if_expr(self, meta, children):
        cond = children[0]
        then_b = children[1]
        else_b = children[2] if len(children) > 2 else None
        return If(loc=_get_loc(meta), cond=cond, then_branch=then_b, else_branch=else_b)

    def while_expr(self, meta, children):
        cond = children[0]
        body = children[1:]
        return While(loc=_get_loc(meta), cond=cond, body=body)

    def block_expr(self, meta, children):
        return Block(loc=_get_loc(meta), exprs=children)

    def call_expr(self, meta, children):
        fn_name = str(children[0])
        args = children[1:]
        return Call(loc=_get_loc(meta), fn_name=fn_name, args=args)

    def return_expr(self, meta, children):
        return Return(loc=_get_loc(meta), expr=children[0])

    def arr_new_expr(self, meta, children):
        return ArrNew(loc=_get_loc(meta), size=children[0])

    def arr_get_expr(self, meta, children):
        return ArrGet(loc=_get_loc(meta), arr=children[0], index=children[1])

    def arr_set_expr(self, meta, children):
        return ArrSet(loc=_get_loc(meta), arr=children[0], index=children[1], value=children[2])

    def arr_len_expr(self, meta, children):
        return ArrLen(loc=_get_loc(meta), arr=children[0])

    def arr_lit_expr(self, meta, children):
        return ArrLit(loc=_get_loc(meta), elements=children)

    def struct_new_expr(self, meta, children):
        struct_name = str(children[0])
        args = children[1:]
        return StructNew(loc=_get_loc(meta), struct_name=struct_name, args=args)

    def struct_get_expr(self, meta, children):
        target = children[0]
        field_name = str(children[1])
        return StructGet(loc=_get_loc(meta), target=target, field_name=field_name)

    def struct_set_expr(self, meta, children):
        target = children[0]
        field_name = str(children[1])
        value = children[2]
        return StructSet(loc=_get_loc(meta), target=target, field_name=field_name, value=value)

    def struct_def(self, meta, children):
        name = str(children[0])
        fields = []
        for c in children[1:]:
            if isinstance(c, list):
                for p in c:
                    if isinstance(p, Param):
                        fields.append(StructField(loc=p.loc, name=p.name, type_name=p.type_name))
            elif isinstance(c, Param):
                fields.append(StructField(loc=c.loc, name=c.name, type_name=c.type_name))
        return StructDef(loc=_get_loc(meta), name=name, fields=fields)

    def print_str_expr(self, meta, children):
        return PrintStr(loc=_get_loc(meta), expr=children[0])

    def println_str_expr(self, meta, children):
        return PrintlnStr(loc=_get_loc(meta), expr=children[0])

    def print_i32_expr(self, meta, children):
        return PrintI32(loc=_get_loc(meta), expr=children[0])

    def print_f64_expr(self, meta, children):
        return PrintF64(loc=_get_loc(meta), expr=children[0])

    def str_len_expr(self, meta, children):
        return StrLen(loc=_get_loc(meta), expr=children[0])

    def str_concat_expr(self, meta, children):
        return StrConcat(loc=_get_loc(meta), left=children[0], right=children[1])

    def fn_def(self, meta, children):
        name = str(children[0])
        idx = 1
        params = children[idx]
        idx += 1
        ret_type = Type.VOID
        if idx < len(children) and isinstance(children[idx], str) and (children[idx] in (Type.I32, Type.F64, Type.BOOL, Type.VOID, Type.ARR_I32, Type.STRING) or children[idx].isidentifier()):
            ret_type = children[idx]
            idx += 1
        body = children[idx:]
        return Function(loc=_get_loc(meta), name=name, params=params, return_type=ret_type, body=body)

    def module(self, meta, children):
        funcs = [c for c in children if isinstance(c, Function)]
        structs = [c for c in children if isinstance(c, StructDef)]
        return Module(loc=_get_loc(meta), functions=funcs, structs=structs)

    def top_level_list(self, meta, children):
        funcs = [c for c in children if isinstance(c, Function)]
        structs = [c for c in children if isinstance(c, StructDef)]
        return Module(loc=_get_loc(meta), functions=funcs, structs=structs)

class Parser:
    def __init__(self, grammar_path: str = None):
        if grammar_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            grammar_path = os.path.join(base_dir, "grammar", "syntax.lark")
        with open(grammar_path, "r", encoding="utf-8") as f:
            grammar = f.read()
        self.lark = Lark(grammar, start="start", parser="lalr", propagate_positions=True)
        self.transformer = ASTBuilder()

    def parse(self, text: str) -> Module:
        tree = self.lark.parse(text)
        return self.transformer.transform(tree)
