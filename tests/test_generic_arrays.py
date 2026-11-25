import pytest
from src.runner import Runner
from src.type_checker import TypeErrorException

@pytest.fixture
def runner():
    return Runner()

def test_f64_array_allocation_and_math(runner):
    code = """
    (fn main () -> f64
      (let arr: arr_f64 (arr_new f64 3))
      (@= arr 0 10.5)
      (@= arr 1 20.25)
      (@= arr 2 30.25)
      (+ (@ arr 0) (+ (@ arr 1) (@ arr 2))))
    """
    assert runner.execute_function(code, "main") == pytest.approx(61.0)

def test_f64_array_literal(runner):
    code = """
    (fn main () -> f64
      (let arr: arr_f64 [1.25 2.5 3.25])
      (+ (@ arr 0) (+ (@ arr 1) (@ arr 2))))
    """
    assert runner.execute_function(code, "main") == pytest.approx(7.0)

def test_bool_array(runner):
    code = """
    (fn main () -> i32
      (let flags: arr_bool (arr_new bool 2))
      (@= flags 0 true)
      (@= flags 1 false)
      (if (and (@ flags 0) (not (@ flags 1)))
        1
        0))
    """
    assert runner.execute_function(code, "main") == 1

def test_typechecker_rejects_heterogeneous_array(runner):
    code = """
    (fn main () -> i32
      (let arr: arr_i32 (arr_new i32 2))
      (@= arr 0 3.14)
      0)
    """
    with pytest.raises(TypeErrorException) as excinfo:
        runner.compile_to_wat(code)
    assert "TypeMismatch" in str(excinfo.value.to_dict())

def test_typechecker_rejects_mixed_array_literal(runner):
    code = """
    (fn main () -> i32
      (let arr: arr_i32 [1 2 3.5])
      0)
    """
    with pytest.raises(TypeErrorException) as excinfo:
        runner.compile_to_wat(code)
    assert "TypeMismatch" in str(excinfo.value.to_dict())
