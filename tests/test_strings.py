import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_string_literal_and_len(runner):
    """Test 1: String literal definition and length inspection."""
    code = """
    (fn get_greeting_len () -> i32
      (let msg: string "Welcome to SynapLang!")
      (str_len msg))
    """
    assert runner.execute_function(code, "get_greeting_len") == 21

def test_print_and_println(runner):
    """Test 2: Host printing functions print and println."""
    code = """
    (fn greet () -> i32
      (print "AI ")
      (println "Agent")
      1)
    """
    runner.execute_function(code, "greet", capture_stdout=True)
    assert runner.captured_output == ["AI ", "Agent\n"]

def test_print_numeric_types(runner):
    """Test 3: Host printing functions for i32 and f64."""
    code = """
    (fn print_numbers () -> i32
      (print_i32 42)
      (print_f64 3.14159)
      0)
    """
    runner.execute_function(code, "print_numbers", capture_stdout=True)
    assert len(runner.captured_output) == 2
    assert "42" in runner.captured_output[0]
    assert "3.14" in runner.captured_output[1]

def test_str_concat(runner):
    """Test 4: Dynamic string concatenation in linear memory."""
    code = """
    (fn join_words () -> i32
      (let part1: string "Neural ")
      (let part2: string "Execution")
      (let combined: string (str_concat part1 part2))
      (println combined)
      (str_len combined))
    """
    res = runner.execute_function(code, "join_words", capture_stdout=True)
    assert res == len("Neural Execution")
    assert runner.captured_output == ["Neural Execution\n"]

def test_string_formatting_loop(runner):
    """Test 5: Iterating and printing strings in a loop."""
    code = """
    (fn count_logs (n: i32) -> i32
      (let i: i32 1)
      (while (<= i n)
        (print "Step: ")
        (print_i32 i)
        (set i (+ i 1)))
      n)
    """
    runner.execute_function(code, "count_logs", 3, capture_stdout=True)
    expected = [
        "Step: ", "1\n",
        "Step: ", "2\n",
        "Step: ", "3\n"
    ]
    assert runner.captured_output == expected

def test_string_type_safety_json_diagnostic(runner):
    """Test 6: Type safety verification for strings emitting structured JSON."""
    invalid_code = """
    (fn bad_print () -> i32
      (println 12345))
    """
    diag = runner.check_source(invalid_code)
    assert diag["status"] == "error"
    assert diag["error_type"] == "TypeMismatch"
    assert diag["context"]["expected_type"] == "string"
    assert diag["context"]["found_type"] == "i32"
    assert "suggested_fix" in diag
