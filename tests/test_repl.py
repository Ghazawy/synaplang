import io
import sys
import pytest
from src.repl import SynapRepl

def test_repl_eval_basic_expression(capsys):
    repl = SynapRepl()
    repl.eval_input("(+ 100 200)")
    captured = capsys.readouterr()
    assert "300" in captured.out

def test_repl_define_and_call_function(capsys):
    repl = SynapRepl()
    repl.eval_input("(fn double (n: i32) -> i32 (* n 2))")
    captured = capsys.readouterr()
    assert "Defined function" in captured.out and "double" in captured.out

    repl.eval_input("(call double 21)")
    captured2 = capsys.readouterr()
    assert "42" in captured2.out

def test_repl_struct_definition_and_access(capsys):
    repl = SynapRepl()
    repl.eval_input("(struct Point [x: i32] [y: i32])")
    captured = capsys.readouterr()
    assert "Defined struct" in captured.out and "Point" in captured.out

    repl.eval_input("(do (let p: Point (struct_new Point 12 34)) (struct_get p y))")
    captured2 = capsys.readouterr()
    assert "34" in captured2.out

def test_repl_wat_command(capsys):
    repl = SynapRepl()
    repl.eval_input("(+ 1 1)")
    repl.eval_input(":wat")
    captured = capsys.readouterr()
    assert "(module" in captured.out
