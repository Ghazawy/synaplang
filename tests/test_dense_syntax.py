import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_dense_for_loop(runner):
    code = """
    (fn main () -> i32
      (let sum: i32 0)
      (for i 1 5
        (set sum (+ sum i)))
      sum)
    """
    assert runner.execute_function(code, "main") == 10

def test_dense_let_type_inference(runner):
    code = """
    (fn main () -> i32
      (:= a 42)
      (let b 58)
      (+ a b))
    """
    assert runner.execute_function(code, "main") == 100

def test_dense_direct_call(runner):
    code = """
    (fn double (x: i32) -> i32
      (* x 2))
    
    (fn main () -> i32
      (double 21))
    """
    assert runner.execute_function(code, "main") == 42

def test_dense_array_shortcuts(runner):
    code = """
    (fn main () -> i32
      (:= arr [10 20 30])
      (@= arr 1 99)
      (+ (@ arr 0) (+ (@ arr 1) (# arr))))
    """
    # 10 + 99 + 3 = 112
    assert runner.execute_function(code, "main") == 112

def test_dense_struct_dot_access(runner):
    code = """
    (struct Point
      (x: i32)
      (y: i32))
      
    (fn main () -> i32
      (:= p (new Point 15 25))
      (+ (. p x) (. p y)))
    """
    assert runner.execute_function(code, "main") == 40
