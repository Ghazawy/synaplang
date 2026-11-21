import json
from typing import Dict, Optional, List, Tuple
from src.ail_ast import (
    Module, Function, Param, Expr, Literal, VarRef, Let, Set,
    BinaryOp, UnaryOp, If, While, Block, Call, Return, Type, ASTNode
)

class TypeErrorException(Exception):
    def __init__(self, error_type: str, message: str, node: ASTNode, expected: str = "", found: str = "", suggested_fix: str = ""):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.node = node
        self.expected = expected
        self.found = found
        self.suggested_fix = suggested_fix

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        return {
            "status": "error",
            "error_type": self.error_type,
            "message": self.message,
            "location": {
                "line": self.node.loc.line,
                "column": self.node.loc.column
            },
            "context": {
                "node": type(self.node).__name__,
                "expected_type": self.expected,
                "found_type": self.found
            },
            "suggested_fix": self.suggested_fix
        }

class TypeChecker:
    def __init__(self):
        # Global function signatures: name -> (List[Param], return_type)
        self.functions: Dict[str, Tuple[List[str], str]] = {}
        # Scoped symbol tables for local variables
        self.scopes: List[Dict[str, str]] = []

    def _push_scope(self):
        self.scopes.append({})

    def _pop_scope(self):
        self.scopes.pop()

    def _declare_var(self, name: str, type_name: str, node: ASTNode):
        if not self.scopes:
            raise TypeErrorException("ScopeError", "No active scope for variable declaration", node)
        current_scope = self.scopes[-1]
        if name in current_scope:
            raise TypeErrorException(
                "RedeclarationError",
                f"Variable '{name}' already declared in current scope",
                node,
                suggested_fix=f"Use (set {name} ...) instead of declaring it again"
            )
        current_scope[name] = type_name

    def _lookup_var(self, name: str, node: ASTNode) -> str:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise TypeErrorException(
            "UndefinedVariable",
            f"Variable '{name}' is not defined",
            node,
            suggested_fix=f"Declare variable with (let {name} <type> <initial_value>) before referencing it"
        )

    def check(self, module: Module) -> dict:
        self.functions.clear()
        self.scopes.clear()

        # Pass 1: Collect function signatures
        for fn in module.functions:
            if fn.name in self.functions:
                raise TypeErrorException(
                    "DuplicateFunction",
                    f"Function '{fn.name}' is already defined",
                    fn,
                    suggested_fix=f"Rename or remove duplicate definition of '{fn.name}'"
                )
            param_types = [p.type_name for p in fn.params]
            self.functions[fn.name] = (param_types, fn.return_type)

        # Pass 2: Type check function bodies
        for fn in module.functions:
            self._check_function(fn)

        return {"status": "ok", "message": "Type check passed successfully"}

    def _check_function(self, fn: Function):
        self._push_scope()
        for p in fn.params:
            self._declare_var(p.name, p.type_name, p)

        last_type = Type.VOID
        for expr in fn.body:
            last_type = self._check_expr(expr, fn.return_type)

        if fn.return_type != Type.VOID and last_type != fn.return_type:
            # Check if there is an explicit return in the body
            has_explicit_return = any(isinstance(e, Return) for e in fn.body)
            if not has_explicit_return:
                raise TypeErrorException(
                    "ReturnTypeMismatch",
                    f"Function '{fn.name}' declared to return '{fn.return_type}', but body evaluates to '{last_type}'",
                    fn,
                    expected=fn.return_type,
                    found=last_type,
                    suggested_fix=f"Ensure the last expression or return statement evaluates to '{fn.return_type}'"
                )

        self._pop_scope()

    def _check_expr(self, expr: Expr, expected_return: str) -> str:
        if isinstance(expr, Literal):
            expr.inferred_type = expr.type_name
            return expr.type_name

        if isinstance(expr, VarRef):
            t = self._lookup_var(expr.name, expr)
            expr.inferred_type = t
            return t

        if isinstance(expr, Let):
            val_type = self._check_expr(expr.value, expected_return)
            if val_type != expr.type_name:
                raise TypeErrorException(
                    "TypeMismatch",
                    f"Cannot assign expression of type '{val_type}' to variable '{expr.name}' of type '{expr.type_name}'",
                    expr,
                    expected=expr.type_name,
                    found=val_type,
                    suggested_fix=f"Ensure value expression evaluates to '{expr.type_name}'"
                )
            self._declare_var(expr.name, expr.type_name, expr)
            expr.inferred_type = expr.type_name
            return expr.type_name

        if isinstance(expr, Set):
            target_type = self._lookup_var(expr.name, expr)
            val_type = self._check_expr(expr.value, expected_return)
            if val_type != target_type:
                raise TypeErrorException(
                    "TypeMismatch",
                    f"Cannot assign expression of type '{val_type}' to variable '{expr.name}' of type '{target_type}'",
                    expr,
                    expected=target_type,
                    found=val_type,
                    suggested_fix=f"Change value expression to evaluate to '{target_type}'"
                )
            expr.inferred_type = target_type
            return target_type

        if isinstance(expr, BinaryOp):
            left_t = self._check_expr(expr.left, expected_return)
            right_t = self._check_expr(expr.right, expected_return)

            if expr.op in ("+", "-", "*", "/", "%"):
                if left_t != right_t:
                    raise TypeErrorException(
                        "TypeMismatch",
                        f"Binary operator '{expr.op}' requires identical operand types, got '{left_t}' and '{right_t}'",
                        expr,
                        expected=left_t,
                        found=right_t,
                        suggested_fix=f"Ensure both operands are of the same arithmetic type ('{left_t}')"
                    )
                if left_t not in (Type.I32, Type.F64):
                    raise TypeErrorException(
                        "InvalidOperatorType",
                        f"Arithmetic operator '{expr.op}' is only valid for i32 or f64, not '{left_t}'",
                        expr,
                        expected="i32 or f64",
                        found=left_t,
                        suggested_fix="Convert operands to i32 or f64"
                    )
                expr.inferred_type = left_t
                return left_t

            if expr.op in ("==", "!=", "<", "<=", ">", ">="):
                if left_t != right_t:
                    raise TypeErrorException(
                        "TypeMismatch",
                        f"Comparison operator '{expr.op}' requires matching operand types, got '{left_t}' and '{right_t}'",
                        expr,
                        expected=left_t,
                        found=right_t,
                        suggested_fix=f"Ensure both operands have identical types before comparison"
                    )
                expr.inferred_type = Type.BOOL
                return Type.BOOL

            if expr.op in ("and", "or"):
                if left_t != Type.BOOL or right_t != Type.BOOL:
                    raise TypeErrorException(
                        "TypeMismatch",
                        f"Logical operator '{expr.op}' requires boolean operands, got '{left_t}' and '{right_t}'",
                        expr,
                        expected=Type.BOOL,
                        found=f"{left_t}, {right_t}",
                        suggested_fix="Ensure both operands evaluate to bool"
                    )
                expr.inferred_type = Type.BOOL
                return Type.BOOL

            raise TypeErrorException("UnknownOperator", f"Unknown binary operator '{expr.op}'", expr)

        if isinstance(expr, UnaryOp):
            t = self._check_expr(expr.expr, expected_return)
            if expr.op == "not":
                if t != Type.BOOL:
                    raise TypeErrorException(
                        "TypeMismatch",
                        f"Unary 'not' requires bool operand, got '{t}'",
                        expr,
                        expected=Type.BOOL,
                        found=t,
                        suggested_fix="Pass a boolean expression to (not ...)"
                    )
                expr.inferred_type = Type.BOOL
                return Type.BOOL
            if expr.op == "neg":
                if t not in (Type.I32, Type.F64):
                    raise TypeErrorException(
                        "TypeMismatch",
                        f"Unary 'neg' requires i32 or f64, got '{t}'",
                        expr,
                        expected="i32 or f64",
                        found=t,
                        suggested_fix="Negate numbers only"
                    )
                expr.inferred_type = t
                return t

        if isinstance(expr, If):
            cond_t = self._check_expr(expr.cond, expected_return)
            if cond_t != Type.BOOL:
                raise TypeErrorException(
                    "TypeMismatch",
                    f"If condition must evaluate to bool, got '{cond_t}'",
                    expr,
                    expected=Type.BOOL,
                    found=cond_t,
                    suggested_fix="Use a comparison operator (such as ==, <, >) to yield a boolean condition"
                )
            then_t = self._check_expr(expr.then_branch, expected_return)
            if expr.else_branch:
                else_t = self._check_expr(expr.else_branch, expected_return)
                if then_t != else_t:
                    raise TypeErrorException(
                        "BranchTypeMismatch",
                        f"Both branches of if expression must have identical types, got '{then_t}' and '{else_t}'",
                        expr,
                        expected=then_t,
                        found=else_t,
                        suggested_fix="Ensure both the then-branch and else-branch evaluate to the same type"
                    )
                expr.inferred_type = then_t
                return then_t
            else:
                expr.inferred_type = Type.VOID
                return Type.VOID

        if isinstance(expr, While):
            cond_t = self._check_expr(expr.cond, expected_return)
            if cond_t != Type.BOOL:
                raise TypeErrorException(
                    "TypeMismatch",
                    f"While loop condition must be bool, got '{cond_t}'",
                    expr,
                    expected=Type.BOOL,
                    found=cond_t,
                    suggested_fix="Ensure while condition evaluates to a boolean"
                )
            for b in expr.body:
                self._check_expr(b, expected_return)
            expr.inferred_type = Type.VOID
            return Type.VOID

        if isinstance(expr, Block):
            last_t = Type.VOID
            for b in expr.exprs:
                last_t = self._check_expr(b, expected_return)
            expr.inferred_type = last_t
            return last_t

        if isinstance(expr, Call):
            if expr.fn_name not in self.functions:
                raise TypeErrorException(
                    "UndefinedFunction",
                    f"Function '{expr.fn_name}' is not defined",
                    expr,
                    suggested_fix=f"Define function (fn {expr.fn_name} ...) before calling it"
                )
            param_types, ret_t = self.functions[expr.fn_name]
            if len(expr.args) != len(param_types):
                raise TypeErrorException(
                    "ArityMismatch",
                    f"Function '{expr.fn_name}' expects {len(param_types)} arguments, but received {len(expr.args)}",
                    expr,
                    expected=f"{len(param_types)} arguments",
                    found=f"{len(expr.args)} arguments",
                    suggested_fix=f"Provide exactly {len(param_types)} arguments: ({', '.join(param_types)})"
                )
            for i, (arg, expected_t) in enumerate(zip(expr.args, param_types)):
                arg_t = self._check_expr(arg, expected_return)
                if arg_t != expected_t:
                    raise TypeErrorException(
                        "ArgumentTypeMismatch",
                        f"Argument {i+1} of '{expr.fn_name}' expects type '{expected_t}', but got '{arg_t}'",
                        arg,
                        expected=expected_t,
                        found=arg_t,
                        suggested_fix=f"Pass an expression evaluating to '{expected_t}' for argument {i+1}"
                    )
            expr.inferred_type = ret_t
            return ret_t

        if isinstance(expr, Return):
            ret_t = self._check_expr(expr.expr, expected_return)
            if ret_t != expected_return:
                raise TypeErrorException(
                    "ReturnTypeMismatch",
                    f"Return statement produces '{ret_t}', but function expects '{expected_return}'",
                    expr,
                    expected=expected_return,
                    found=ret_t,
                    suggested_fix=f"Ensure returned expression evaluates to '{expected_return}'"
                )
            expr.inferred_type = ret_t
            return ret_t

        raise TypeErrorException("UnknownExpression", f"Unknown AST expression node '{type(expr).__name__}'", expr)
