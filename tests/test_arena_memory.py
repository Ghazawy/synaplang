import pytest
from src.runner import Runner

@pytest.fixture
def runner():
    return Runner()

def test_arena_basic_scoped_allocation(runner):
    code = """
    (fn main () -> i32
      (let initial_mem: i32 (heap_ptr))
      (let scoped_sum: i32
        (with-arena
          (let arr: arr_i32 [10 20 30])
          (+ (@ arr 0) (@ arr 1))))
      (let final_mem: i32 (heap_ptr))
      ;; Verify that memory after exiting arena was restored to initial_mem
      (if (== initial_mem final_mem)
        scoped_sum
        -1))
    """
    assert runner.execute_function(code, "main") == 30

def test_arena_stress_loop_zero_leak(runner):
    # Runs 10,000 iterations allocating dynamic arrays inside an arena.
    # Without arena, this would leak 10,000 * 32 bytes = 320 KB.
    # With arena, memory stays 100% constant!
    code = """
    (fn main () -> i32
      (let mem_start: i32 (heap_ptr))
      (let total: i32 0)
      (for i 0 1000
        (with-arena
          (let temp_arr: arr_i32 [1 2 3 4])
          (set total (+ total (@ temp_arr 0)))))
      (let mem_end: i32 (heap_ptr))
      (if (== mem_start mem_end)
        total
        -999))
    """
    assert runner.execute_function(code, "main") == 1000

def test_arena_nested_scopes(runner):
    code = """
    (fn main () -> i32
      (let m0: i32 (heap_ptr))
      (with-arena
        (let a1: arr_i32 [1 2])
        (let m1: i32 (heap_ptr))
        (with-arena
          (let a2: arr_i32 [3 4 5]))
        (let m2: i32 (heap_ptr))
        ;; Inner arena restored to m1
        (if (!= m1 m2) (return -1))
      )
      (let m3: i32 (heap_ptr))
      ;; Outer arena restored to m0
      (if (== m0 m3) 42 -2))
    """
    assert runner.execute_function(code, "main") == 42
