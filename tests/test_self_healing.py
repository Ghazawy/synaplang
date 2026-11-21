import json
import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_automated_agent_self_healing_loop(runner):
    """
    Demonstrates how an AI agent uses the structured JSON compiler diagnostic
    to detect a type bug, understand the context, repair the source code,
    and successfully compile and run on WebAssembly.
    """
    # Step 1: Simulated AI Agent produces code with a deliberate type bug (passing f64 to an i32 addition)
    buggy_code = """
    (fn compute (x: i32) -> i32
      (+ x 10.5))
    """

    # Step 2: Compiler intercepts the code and returns JSON diagnostics
    diagnostic = runner.check_source(buggy_code)
    assert diagnostic["status"] == "error"
    assert diagnostic["error_type"] == "TypeMismatch"
    assert diagnostic["location"]["line"] == 3
    assert diagnostic["context"]["expected_type"] == "i32"
    assert diagnostic["context"]["found_type"] == "f64"
    assert "suggested_fix" in diagnostic

    # Step 3: Automated Agent Repair Action
    # An agent inspects the JSON payload:
    # error: TypeMismatch, expected: i32, found: f64 at line 3.
    # The agent repairs 10.5 -> 10 based on the compiler's diagnostic:
    repaired_code = buggy_code.replace("10.5", "10")

    # Step 4: Re-check the repaired code
    repaired_diag = runner.check_source(repaired_code)
    assert repaired_diag["status"] == "ok"

    # Step 5: Execute repaired code natively in WebAssembly
    result = runner.execute_function(repaired_code, "compute", 40)
    assert result == 50

def test_automated_arity_healing(runner):
    """
    Demonstrates automated healing when an agent accidentally calls a function
    with the wrong number of arguments.
    """
    buggy_code = """
    (fn multiply (a: i32 b: i32) -> i32
      (* a b))

    (fn run_calc () -> i32
      (call multiply 5))
    """

    diagnostic = runner.check_source(buggy_code)
    assert diagnostic["status"] == "error"
    assert diagnostic["error_type"] == "ArityMismatch"
    assert "2 arguments" in diagnostic["context"]["expected_type"]

    # Agent applies repair by providing missing argument
    repaired_code = buggy_code.replace("(call multiply 5)", "(call multiply 5 6)")
    assert runner.check_source(repaired_code)["status"] == "ok"
    assert runner.execute_function(repaired_code, "run_calc") == 30
