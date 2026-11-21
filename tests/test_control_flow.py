import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_if_else_branches(runner):
    code = """
    (fn max_val (a: i32 b: i32) -> i32
      (if (> a b)
        a
        b))
    """
    assert runner.execute_function(code, "max_val", 10, 20) == 20
    assert runner.execute_function(code, "max_val", 50, 5) == 50

def test_while_loop_accumulator(runner):
    code = """
    (fn count_sum (n: i32) -> i32
      (let total: i32 0)
      (let i: i32 1)
      (while (<= i n)
        (set total (+ total i))
        (set i (+ i 1)))
      total)
    """
    assert runner.execute_function(code, "count_sum", 10) == 55
    assert runner.execute_function(code, "count_sum", 100) == 5050

def test_recursive_fibonacci(runner):
    code = """
    (fn fib (n: i32) -> i32
      (if (<= n 1)
        n
        (+ (call fib (- n 1))
           (call fib (- n 2)))))
    """
    assert runner.execute_function(code, "fib", 0) == 0
    assert runner.execute_function(code, "fib", 1) == 1
    assert runner.execute_function(code, "fib", 6) == 8
    assert runner.execute_function(code, "fib", 10) == 55

def test_recursive_factorial(runner):
    code = """
    (fn fact (n: i32) -> i32
      (if (<= n 1)
        1
        (* n (call fact (- n 1)))))
    """
    assert runner.execute_function(code, "fact", 1) == 1
    assert runner.execute_function(code, "fact", 5) == 120
    assert runner.execute_function(code, "fact", 6) == 720

def test_inter_function_calls(runner):
    code = """
    (fn square (x: i32) -> i32
      (* x x))

    (fn sum_of_squares (a: i32 b: i32) -> i32
      (+ (call square a)
         (call square b)))
    """
    assert runner.execute_function(code, "sum_of_squares", 3, 4) == 25
