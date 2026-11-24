import pytest
from src.runner import Runner, OutOfFuelError, SynapRuntimeError

@pytest.fixture
def runner():
    return Runner()

def test_infinite_loop_trapped_by_fuel(runner):
    """Verify that infinite loops are halted safely by the WebAssembly fuel meter."""
    infinite_loop_code = """
    (module
      (fn main () -> i32
        (let x: i32 0)
        (while true
          (set x (+ x 1))
        )
        x
      )
    )
    """
    with pytest.raises(OutOfFuelError) as excinfo:
        # Give limited fuel: 10,000 units
        runner.execute_function(infinite_loop_code, "main", fuel=10000)

    err = excinfo.value.to_dict()
    assert err["error_type"] == "OutOfFuel"
    assert "fuel limit (10000) exhausted" in err["message"]
    assert "suggested_fix" in err

def test_custom_fuel_sufficiency(runner):
    """Verify that legitimate calculations succeed when sufficient fuel is supplied."""
    code = """
    (module
      (fn count_to (target: i32) -> i32
        (let i: i32 0)
        (while (< i target)
          (set i (+ i 1))
        )
        i
      )
      (fn main () -> i32
        (call count_to 100)
      )
    )
    """
    res = runner.execute_function(code, "main", fuel=50000)
    assert res == 100

def test_division_by_zero_trap(runner):
    """Verify that integer division by zero emits structured SynapRuntimeError."""
    code = """
    (module
      (fn div_zero () -> i32
        (/ 100 0)
      )
      (fn main () -> i32
        (call div_zero)
      )
    )
    """
    with pytest.raises(SynapRuntimeError) as excinfo:
        runner.execute_function(code, "main")

    err = excinfo.value.to_dict()
    assert err["error_type"] == "DivisionByZero"
    assert "Division by zero" in err["message"]
