import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_type_mismatch_in_binary_op(runner):
    code = """
    (fn invalid () -> i32
      (+ 10 3.14))
    """
    diag = runner.check_source(code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "TypeMismatch"
    assert diag["context"]["expected_type"] == "i32"
    assert diag["context"]["found_type"] == "f64"
    assert "suggested_fix" in diag

def test_type_mismatch_in_let_assignment(runner):
    code = """
    (fn invalid () -> i32
      (let x: i32 3.14)
      x)
    """
    diag = runner.check_source(code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "TypeMismatch"
    assert diag["context"]["expected_type"] == "i32"
    assert diag["context"]["found_type"] == "f64"

def test_undefined_variable(runner):
    code = """
    (fn invalid () -> i32
      (+ x 10))
    """
    diag = runner.check_source(code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "UndefinedVariable"
    assert "suggested_fix" in diag

def test_undefined_function(runner):
    code = """
    (fn invalid () -> i32
      (call nonexistent_function 42))
    """
    diag = runner.check_source(code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "UndefinedFunction"

def test_arity_mismatch(runner):
    code = """
    (fn add (a: i32 b: i32) -> i32
      (+ a b))

    (fn caller () -> i32
      (call add 10))
    """
    diag = runner.check_source(code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "ArityMismatch"

def test_return_type_mismatch(runner):
    code = """
    (fn invalid () -> i32
      3.14)
    """
    diag = runner.check_source(code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "ReturnTypeMismatch"
    assert diag["context"]["expected_type"] == "i32"
    assert diag["context"]["found_type"] == "f64"
