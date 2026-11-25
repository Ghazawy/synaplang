import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_result_ok_and_unwrap(runner):
    code = """
    (fn main () -> i32
      (let r (ok 42))
      (if (is_ok r)
        (unwrap r)
        -1))
    """
    assert runner.execute_function(code, "main") == 42

def test_result_err_and_check(runner):
    code = """
    (fn main () -> i32
      (let r (err 404))
      (if (is_err r)
        99
        0))
    """
    assert runner.execute_function(code, "main") == 99

def test_safe_division_with_result(runner):
    code = """
    (fn safe_div (a: i32 b: i32) -> i32
      (let r (if (== b 0)
               (err 1)
               (ok (/ a b))))
      (if (is_ok r)
        (unwrap r)
        -999))
        
    (fn main () -> i32
      (+ (safe_div 100 5) (safe_div 50 0)))
    """
    # 20 + (-999) = -979
    assert runner.execute_function(code, "main") == -979
