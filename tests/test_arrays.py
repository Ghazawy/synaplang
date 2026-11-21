import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_array_alloc_and_length(runner):
    """Test 1: Dynamic allocation with arr_new and checking length with arr_len."""
    code = """
    (fn make_ten_arr () -> i32
      (let a: arr_i32 (arr_new 10))
      (arr_len a))
    """
    assert runner.execute_function(code, "make_ten_arr") == 10

def test_array_get_and_set(runner):
    """Test 2: Setting elements and retrieving them with arr_set and arr_get."""
    code = """
    (fn set_and_get () -> i32
      (let a: arr_i32 (arr_new 5))
      (arr_set a 0 100)
      (arr_set a 1 200)
      (arr_set a 4 500)
      (+ (+ (arr_get a 0) (arr_get a 1)) (arr_get a 4)))
    """
    assert runner.execute_function(code, "set_and_get") == 800

def test_array_literal(runner):
    """Test 3: Static array literal initialization (array e1 e2 e3 ...)."""
    code = """
    (fn test_lit () -> i32
      (let nums: arr_i32 (array 7 14 21 28))
      (+ (arr_get nums 1) (arr_get nums 3)))
    """
    assert runner.execute_function(code, "test_lit") == 14 + 28

def test_array_sum_loop(runner):
    """Test 4: Iterating over an array with while loop and computing sum."""
    code = """
    (fn sum_array (arr: arr_i32) -> i32
      (let total: i32 0)
      (let i: i32 0)
      (let len: i32 (arr_len arr))
      (while (< i len)
        (set total (+ total (arr_get arr i)))
        (set i (+ i 1)))
      total)

    (fn run_test () -> i32
      (let data: arr_i32 (array 10 20 30 40 50))
      (call sum_array data))
    """
    assert runner.execute_function(code, "run_test") == 150

def test_array_max_finder(runner):
    """Test 5: Finding the maximum element in an array with while and if."""
    code = """
    (fn find_max (arr: arr_i32) -> i32
      (let max_val: i32 (arr_get arr 0))
      (let i: i32 1)
      (let len: i32 (arr_len arr))
      (while (< i len)
        (let current: i32 (arr_get arr i))
        (if (> current max_val)
          (set max_val current))
        (set i (+ i 1)))
      max_val)

    (fn run_max () -> i32
      (let data: arr_i32 (array 45 12 89 23 99 34 67))
      (call find_max data))
    """
    assert runner.execute_function(code, "run_max") == 99

def test_array_type_safety_json_diagnostic(runner):
    """Test 6 (Verification): Strict type checking on arrays emitting machine JSON."""
    invalid_code = """
    (fn bad_array () -> i32
      (let not_arr: i32 42)
      (arr_get not_arr 0))
    """
    diag = runner.check_source(invalid_code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "TypeMismatch"
    assert diag["context"]["expected_type"] == "arr_i32"
    assert diag["context"]["found_type"] == "i32"
    assert "suggested_fix" in diag
