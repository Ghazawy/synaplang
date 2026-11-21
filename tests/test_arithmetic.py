import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_integer_addition_subtraction(runner):
    code = """
    (fn calc (a: i32 b: i32) -> i32
      (- (+ a b) 5))
    """
    res = runner.execute_function(code, "calc", 10, 20)
    assert res == 25

def test_integer_multiplication_division(runner):
    code = """
    (fn calc (x: i32 y: i32) -> i32
      (/ (* x y) 4))
    """
    res = runner.execute_function(code, "calc", 8, 3)
    assert res == 6

def test_integer_modulo(runner):
    code = """
    (fn calc (x: i32 y: i32) -> i32
      (% x y))
    """
    assert runner.execute_function(code, "calc", 17, 5) == 2
    assert runner.execute_function(code, "calc", 20, 4) == 0

def test_float_arithmetic(runner):
    code = """
    (fn float_math (a: f64 b: f64) -> f64
      (* (+ a b) 2.0))
    """
    res = runner.execute_function(code, "float_math", 1.5, 3.5)
    assert abs(res - 10.0) < 1e-6

def test_nested_arithmetic_precedence(runner):
    # Tests that S-expressions strictly preserve unambiguous tree evaluation:
    # (+ (* 2 3) (/ 10 2)) => (6 + 5) => 11
    code = """
    (fn eval_expr () -> i32
      (+ (* 2 3) (/ 10 2)))
    """
    assert runner.execute_function(code, "eval_expr") == 11

def test_unary_negation(runner):
    code = """
    (fn negate_val (x: i32) -> i32
      (neg x))
    """
    assert runner.execute_function(code, "negate_val", 42) == -42
