import pytest
from src.patcher import ASTPatcher, ast_to_s_expr
from src.parser import Parser
from src.runner import Runner
from src.type_checker import TypeErrorException

@pytest.fixture
def patcher():
    return ASTPatcher()

def test_ast_path_patch_function_body(patcher):
    """Test surgical replacement of an expression in a function body."""
    original = """
    (module
      (fn main () -> i32
        (let x: i32 10)
        (+ x 5)
      )
    )
    """
    # Replace the return expression (+ x 5) at index 1 with (* x 10)
    patched = patcher.patch(original, "@fn:main.body[1]", "(* x 10)")
    
    # Verify execution of patched code
    runner = Runner()
    res = runner.execute_function(patched, "main")
    assert res == 100

def test_ast_path_patch_nested_condition(patcher):
    """Test surgical patch of an inner branch in an if-expression."""
    code = """
    (module
      (fn test_cond (flag: bool) -> i32
        (if flag
          111
          222
        )
      )
      (fn main () -> i32
        (call test_cond false)
      )
    )
    """
    # Patch else_branch to 999
    patched = patcher.patch(code, "@fn:test_cond.body[0].else_branch", "999")
    runner = Runner()
    res = runner.execute_function(patched, "main")
    assert res == 999

def test_patch_catches_type_errors(patcher):
    """Verify that if a patch introduces an invalid type, it raises TypeErrorException."""
    code = """
    (module
      (fn main () -> i32
        (let x: i32 10)
        x
      )
    )
    """
    # Try replacing x with a string "hello" in an i32 function
    with pytest.raises(TypeErrorException) as excinfo:
        patcher.patch(code, "@fn:main.body[1]", '"hello"')
    
    err = excinfo.value.to_dict()
    assert "TypeMismatch" in err["error_type"]

def test_ast_to_s_expr_roundtrip(patcher):
    """Verify that ast_to_s_expr formats code that parses and executes identically."""
    code = """
    (module
      (struct Point [x: i32] [y: i32])
      (fn main () -> i32
        (let p: Point (struct_new Point 40 2))
        (+ (struct_get p x) (struct_get p y))
      )
    )
    """
    parser = Parser()
    mod = parser.parse(code)
    formatted = ast_to_s_expr(mod)
    
    runner = Runner()
    res = runner.execute_function(formatted, "main")
    assert res == 42
