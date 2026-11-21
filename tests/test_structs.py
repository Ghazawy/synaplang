import pytest
from src.runner import Runner
from src.parser import Parser
from src.type_checker import TypeChecker, TypeErrorException

@pytest.fixture
def runner():
    return Runner()

def test_basic_struct_instantiation_and_get(runner):
    code = """
    (module
      (struct Point [x: i32] [y: i32])
      (fn main () -> i32
        (let p: Point (struct_new Point 15 25))
        (+ (struct_get p x) (struct_get p y))
      )
    )
    """
    assert runner.execute_function(code, "main") == 40

def test_struct_mutation_set(runner):
    code = """
    (module
      (struct Point [x: i32] [y: i32])
      (fn main () -> i32
        (let p: Point (struct_new Point 10 20))
        (struct_set p x 100)
        (struct_set p y 200)
        (+ (struct_get p x) (struct_get p y))
      )
    )
    """
    assert runner.execute_function(code, "main") == 300

def test_struct_mixed_types_with_f64(runner):
    code = """
    (module
      (struct Player [id: i32] [score: f64])
      (fn main () -> f64
        (let pl: Player (struct_new Player 7 99.5))
        (struct_set pl score (+ (struct_get pl score) 0.5))
        (struct_get pl score)
      )
    )
    """
    assert pytest.approx(runner.execute_function(code, "main")) == 100.0

def test_struct_as_function_argument(runner):
    code = """
    (module
      (struct Vector2D [x: i32] [y: i32])
      (fn dot_product (v1: Vector2D v2: Vector2D) -> i32
        (+ (* (struct_get v1 x) (struct_get v2 x))
           (* (struct_get v1 y) (struct_get v2 y)))
      )
      (fn main () -> i32
        (let a: Vector2D (struct_new Vector2D 3 4))
        (let b: Vector2D (struct_new Vector2D 2 5))
        (call dot_product a b)
      )
    )
    """
    # 3*2 + 4*5 = 6 + 20 = 26
    assert runner.execute_function(code, "main") == 26

def test_nested_structs(runner):
    code = """
    (module
      (struct Point [x: i32] [y: i32])
      (struct Rect [top_left: Point] [bottom_right: Point])
      (fn area (r: Rect) -> i32
        (let p1: Point (struct_get r top_left))
        (let p2: Point (struct_get r bottom_right))
        (let width: i32 (- (struct_get p2 x) (struct_get p1 x)))
        (let height: i32 (- (struct_get p2 y) (struct_get p1 y)))
        (* width height)
      )
      (fn main () -> i32
        (let p1: Point (struct_new Point 0 0))
        (let p2: Point (struct_new Point 10 5))
        (let r: Rect (struct_new Rect p1 p2))
        (call area r)
      )
    )
    """
    assert runner.execute_function(code, "main") == 50

def test_struct_type_checker_diagnostics():
    parser = Parser()
    type_checker = TypeChecker()

    # 1. Unknown field
    bad_field_code = """
    (module
      (struct Point [x: i32] [y: i32])
      (fn main () -> i32
        (let p: Point (struct_new Point 1 2))
        (struct_get p z)
      )
    )
    """
    mod1 = parser.parse(bad_field_code)
    with pytest.raises(TypeErrorException) as excinfo:
        type_checker.check(mod1)
    err = excinfo.value.to_dict()
    assert err["error_type"] == "UnknownField"
    assert "Available fields for 'Point' are: x, y" in err["suggested_fix"]

    # 2. Field type mismatch on struct_new
    bad_type_code = """
    (module
      (struct Point [x: i32] [y: i32])
      (fn main () -> i32
        (let p: Point (struct_new Point 1 2.5))
        (struct_get p x)
      )
    )
    """
    mod2 = parser.parse(bad_type_code)
    with pytest.raises(TypeErrorException) as excinfo2:
        type_checker.check(mod2)
    err2 = excinfo2.value.to_dict()
    assert err2["error_type"] == "FieldTypeMismatch"
    assert err2["context"]["expected_type"] == "i32"
    assert err2["context"]["found_type"] == "f64"
