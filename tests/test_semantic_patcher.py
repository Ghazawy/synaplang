import pytest
from src.runner import Runner
from src.patcher import patch, patch_multi

@pytest.fixture
def runner():
    return Runner()

def test_semantic_label_patch(runner):
    code = """
    (fn compute (x: i32) -> i32
      (let a (* x 2))
      (label "mutate_here" (+ a 5)))
    """
    assert runner.execute_function(code, "compute", 10) == 25
    
    # Surgical patch targeted specifically at the semantic label #mutate_here
    patched = patch(code, "@fn:compute#mutate_here", "(+ a 50)")
    assert runner.execute_function(patched, "compute", 10) == 70

def test_multi_patch_transaction(runner):
    code = """
    (fn process (x: i32) -> i32
      (let a (+ x 1))
      (let b (+ a 2))
      (+ a b))
    """
    # 10 + 1 = 11, b = 11 + 2 = 13, sum = 24
    assert runner.execute_function(code, "process", 10) == 24
    
    # Apply two parallel patches simultaneously
    patches = [
        ("@fn:process.body[0].value", "(+ x 10)"),
        ("@fn:process.body[1].value", "(+ a 20)")
    ]
    patched = patch_multi(code, patches)
    # x=10 -> a=20 -> b=40 -> sum=60
    assert runner.execute_function(patched, "process", 10) == 60
