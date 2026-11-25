from dataclasses import dataclass, field
from typing import List, Optional, Any, Union

class Type:
    I32 = "i32"
    F64 = "f64"
    BOOL = "bool"
    VOID = "void"
    ARR_I32 = "arr_i32"
    ARR_F64 = "arr_f64"
    ARR_BOOL = "arr_bool"
    ARR_STRING = "arr_string"
    STRING = "string"
    UNKNOWN = "unknown"

    @classmethod
    def is_array(cls, s: str) -> bool:
        if not s:
            return False
        return s in (cls.ARR_I32, cls.ARR_F64, cls.ARR_BOOL, cls.ARR_STRING) or s.startswith("arr_") or (s.startswith("[") and s.endswith("]"))

    @classmethod
    def elem_type(cls, s: str) -> str:
        if s in (cls.ARR_I32, "i32[]", "[i32]"):
            return cls.I32
        if s in (cls.ARR_F64, "f64[]", "[f64]"):
            return cls.F64
        if s in (cls.ARR_BOOL, "bool[]", "[bool]"):
            return cls.BOOL
        if s in (cls.ARR_STRING, "string[]", "[string]"):
            return cls.STRING
        if s.startswith("arr_"):
            return s[4:]
        if s.startswith("[") and s.endswith("]"):
            return s[1:-1]
        return cls.I32

    @classmethod
    def array_of(cls, elem_t: str) -> str:
        if elem_t == cls.I32:
            return cls.ARR_I32
        if elem_t == cls.F64:
            return cls.ARR_F64
        if elem_t == cls.BOOL:
            return cls.ARR_BOOL
        if elem_t == cls.STRING:
            return cls.ARR_STRING
        return f"[{elem_t}]"

    @classmethod
    def from_str(cls, s: str) -> str:
        s = s.strip()
        if s in ("i32", "int"):
            return cls.I32
        if s in ("f64", "float"):
            return cls.F64
        if s in ("bool", "boolean"):
            return cls.BOOL
        if s in ("void", "nil", "none"):
            return cls.VOID
        if s in ("arr_i32", "array", "i32[]", "int[]", "arr", "[i32]"):
            return cls.ARR_I32
        if s in ("arr_f64", "f64[]", "float[]", "[f64]"):
            return cls.ARR_F64
        if s in ("arr_bool", "bool[]", "[bool]"):
            return cls.ARR_BOOL
        if s in ("arr_string", "string[]", "[string]"):
            return cls.ARR_STRING
        if s in ("string", "str"):
            return cls.STRING
        if s.startswith("[") and s.endswith("]"):
            return s
        if s.isidentifier():
            return s
        raise ValueError(f"Unknown type: {s}")

@dataclass
class SourceLocation:
    line: int = 1
    column: int = 1

@dataclass
class ASTNode:
    loc: SourceLocation = field(default_factory=SourceLocation)
    label: Optional[str] = None

@dataclass
class Expr(ASTNode):
    inferred_type: Optional[str] = None

@dataclass
class Literal(Expr):
    value: Union[int, float, bool, str] = 0
    type_name: str = Type.I32

@dataclass
class VarRef(Expr):
    name: str = ""

@dataclass
class Let(Expr):
    name: str = ""
    type_name: str = Type.I32
    value: Optional[Expr] = None

@dataclass
class Set(Expr):
    name: str = ""
    value: Optional[Expr] = None

@dataclass
class BinaryOp(Expr):
    op: str = "+"
    left: Optional[Expr] = None
    right: Optional[Expr] = None

@dataclass
class UnaryOp(Expr):
    op: str = "not"
    expr: Optional[Expr] = None

@dataclass
class If(Expr):
    cond: Optional[Expr] = None
    then_branch: Optional[Expr] = None
    else_branch: Optional[Expr] = None

@dataclass
class While(Expr):
    cond: Optional[Expr] = None
    body: List[Expr] = field(default_factory=list)

@dataclass
class Block(Expr):
    exprs: List[Expr] = field(default_factory=list)

@dataclass
class Call(Expr):
    fn_name: str = ""
    args: List[Expr] = field(default_factory=list)

@dataclass
class Return(Expr):
    expr: Optional[Expr] = None

@dataclass
class WithArena(Expr):
    body: List[Expr] = field(default_factory=list)

@dataclass
class HeapPtr(Expr):
    pass

@dataclass
class LabelExpr(Expr):
    name: str = ""
    expr: Optional[Expr] = None

@dataclass
class ResultOk(Expr):
    value: Optional[Expr] = None

@dataclass
class ResultErr(Expr):
    code: Optional[Expr] = None

@dataclass
class ResultIsOk(Expr):
    expr: Optional[Expr] = None

@dataclass
class ResultIsErr(Expr):
    expr: Optional[Expr] = None

@dataclass
class ResultUnwrap(Expr):
    expr: Optional[Expr] = None

@dataclass
class ArrNew(Expr):
    size: Optional[Expr] = None
    elem_type: str = Type.I32

@dataclass
class ArrGet(Expr):
    arr: Optional[Expr] = None
    index: Optional[Expr] = None

@dataclass
class ArrSet(Expr):
    arr: Optional[Expr] = None
    index: Optional[Expr] = None
    value: Optional[Expr] = None

@dataclass
class ArrLen(Expr):
    arr: Optional[Expr] = None

@dataclass
class ArrLit(Expr):
    elements: List[Expr] = field(default_factory=list)

@dataclass
class PrintStr(Expr):
    expr: Optional[Expr] = None

@dataclass
class PrintlnStr(Expr):
    expr: Optional[Expr] = None

@dataclass
class PrintI32(Expr):
    expr: Optional[Expr] = None

@dataclass
class PrintF64(Expr):
    expr: Optional[Expr] = None

@dataclass
class StrLen(Expr):
    expr: Optional[Expr] = None

@dataclass
class StrConcat(Expr):
    left: Optional[Expr] = None
    right: Optional[Expr] = None

@dataclass
class StructField(ASTNode):
    name: str = ""
    type_name: str = Type.I32

@dataclass
class StructDef(ASTNode):
    name: str = ""
    fields: List[StructField] = field(default_factory=list)

@dataclass
class StructNew(Expr):
    struct_name: str = ""
    args: List[Expr] = field(default_factory=list)

@dataclass
class StructGet(Expr):
    target: Optional[Expr] = None
    field_name: str = ""

@dataclass
class StructSet(Expr):
    target: Optional[Expr] = None
    field_name: str = ""
    value: Optional[Expr] = None

@dataclass
class Param(ASTNode):
    name: str = ""
    type_name: str = Type.I32

@dataclass
class Function(ASTNode):
    name: str = ""
    params: List[Param] = field(default_factory=list)
    return_type: str = Type.VOID
    body: List[Expr] = field(default_factory=list)

@dataclass
class Module(ASTNode):
    functions: List[Function] = field(default_factory=list)
    structs: List[StructDef] = field(default_factory=list)
