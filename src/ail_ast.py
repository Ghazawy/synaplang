from dataclasses import dataclass, field
from typing import List, Optional, Any, Union

class Type:
    I32 = "i32"
    F64 = "f64"
    BOOL = "bool"
    VOID = "void"
    ARR_I32 = "arr_i32"
    STRING = "string"
    UNKNOWN = "unknown"

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
        if s in ("arr_i32", "array", "i32[]", "int[]", "arr"):
            return cls.ARR_I32
        if s in ("string", "str"):
            return cls.STRING
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
class ArrNew(Expr):
    size: Optional[Expr] = None

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
