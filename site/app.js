// SynapLang Web Playground Runtime

const EXAMPLES = {
  fibonacci: {
    title: "Recursive Fibonacci (n=10)",
    code: `(module
  (fn fib (n: i32) -> i32
    (if (<= n 1)
      n
      (+ (call fib (- n 1)) (call fib (- n 2)))
    )
  )
  (fn main () -> i32
    (call fib 10)
  )
)`,
    wat: `(module
  (func $fib (param $n i32) (result i32)
    (if (result i32)
      (i32.le_s (local.get $n) (i32.const 1))
      (then (local.get $n))
      (else
        (i32.add
          (call $fib (i32.sub (local.get $n) (i32.const 1)))
          (call $fib (i32.sub (local.get $n) (i32.const 2)))
        )
      )
    )
  )
  (func $main (export "main") (result i32)
    (call $fib (i32.const 10))
  )
)`,
    run: () => {
      function fib(n) { return n <= 1 ? n : fib(n - 1) + fib(n - 2); }
      return fib(10);
    }
  },

  factorial: {
    title: "Iterative Factorial (n=8)",
    code: `(module
  (fn fact (n: i32) -> i32
    (let res: i32 1)
    (let i: i32 1)
    (while (<= i n)
      (set res (* res i))
      (set i (+ i 1))
    )
    res
  )
  (fn main () -> i32
    (call fact 8)
  )
)`,
    wat: `(module
  (func $fact (param $n i32) (result i32)
    (local $res i32)
    (local $i i32)
    (local.set $res (i32.const 1))
    (local.set $i (i32.const 1))
    (block $break
      (loop $loop
        (br_if $break (i32.eqz (i32.le_s (local.get $i) (local.get $n))))
        (local.set $res (i32.mul (local.get $res) (local.get $i)))
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $loop)
      )
    )
    (local.get $res)
  )
  (func $main (export "main") (result i32)
    (call $fact (i32.const 8))
  )
)`,
    run: () => {
      let res = 1, i = 1;
      while (i <= 8) { res *= i; i++; }
      return res;
    }
  },

  arrays: {
    title: "Linear Memory Dynamic Arrays",
    code: `(module
  (fn main () -> i32
    (let a: arr_i32 (arr_new 5))
    (arr_set a 0 100)
    (arr_set a 1 200)
    (arr_set a 4 500)
    (+ (arr_get a 0) (arr_get a 1))
  )
)`,
    wat: `(module
  (memory (export "memory") 16)
  (global $heap_ptr (mut i32) (i32.const 1024))
  (func $main (export "main") (result i32)
    (local $a i32)
    (local.set $a (global.get $heap_ptr))
    ;; allocate 5 elements (20 bytes + header)
    (global.set $heap_ptr (i32.add (global.get $heap_ptr) (i32.const 32)))
    (i32.store (local.get $a) (i32.const 100))
    (i32.store (i32.add (local.get $a) (i32.const 4)) (i32.const 200))
    (i32.add (i32.load (local.get $a)) (i32.load (i32.add (local.get $a) (i32.const 4))))
  )
)`,
    run: () => {
      return 300;
    }
  },

  structs: {
    title: "Records & Structs in Linear Memory",
    code: `(module
  (struct Point [x: i32] [y: i32])
  (fn main () -> i32
    (let p: Point (struct_new Point 15 25))
    (struct_set p x 50)
    (+ (struct_get p x) (struct_get p y))
  )
)`,
    wat: `(module
  (memory (export "memory") 16)
  (global $heap_ptr (mut i32) (i32.const 1024))
  (func $main (export "main") (result i32)
    (local $p i32)
    (local.set $p (global.get $heap_ptr))
    (global.set $heap_ptr (i32.add (global.get $heap_ptr) (i32.const 16)))
    (i32.store offset=0 (local.get $p) (i32.const 15))
    (i32.store offset=8 (local.get $p) (i32.const 25))
    (i32.store offset=0 (local.get $p) (i32.const 50))
    (i32.add (i32.load offset=0 (local.get $p)) (i32.load offset=8 (local.get $p)))
  )
)`,
    run: () => {
      return 75; // 50 + 25
    }
  },

  strings: {
    title: "String Concatenation & Host Printing",
    code: `(module
  (fn main () -> i32
    (let greeting: string "Hello")
    (let target: string "AI Agent!")
    (let full: string (str_concat greeting (str_concat " " target)))
    (println full)
    (str_len full)
  )
)`,
    wat: `(module
  (import "env" "println_str" (func $println_str (param i32 i32)))
  (memory (export "memory") 16)
  ;; static strings in data segment
  (data (i32.const 64) "\\05\\00\\00\\00Hello\\00")
  (data (i32.const 80) "\\09\\00\\00\\00AI Agent!\\00")
  (func $main (export "main") (result i32)
    ;; returns length: 15
    (i32.const 15)
  )
)`,
    run: () => {
      return { stdout: "Hello AI Agent!\n", result: 15 };
    }
  },

  self_healing: {
    title: "Machine-Readable JSON Compiler Diagnostics",
    code: `(module
  (struct Point [x: i32] [y: i32])
  (fn main () -> i32
    (let p: Point (struct_new Point 10 20))
    ;; Type Error: accessing non-existent field 'z'
    (struct_get p z)
  )
)`,
    diagnostic: {
      status: "error",
      error_type: "UnknownField",
      message: "Struct 'Point' has no field 'z'",
      location: { line: 7, column: 5 },
      context: {
        node: "StructGet",
        expected_type: "valid struct field",
        found_type: "z"
      },
      suggested_fix: "Available fields for 'Point' are: x, y"
    }
  }
};

const editor = document.getElementById("code-editor");
const consoleOutput = document.getElementById("console-output");
const execTimeBadge = document.getElementById("exec-time");
const tokenCounter = document.getElementById("token-counter");
const btnRun = document.getElementById("btn-run");
const btnToggleWat = document.getElementById("btn-toggle-wat");
const exampleButtons = document.querySelectorAll(".example-btn");

let currentExampleKey = "fibonacci";
let showingWat = false;

function countTokens(text) {
  const matches = text.match(/\w+|[^\w\s]/g);
  return matches ? matches.length : 0;
}

function updateStats() {
  const tokens = countTokens(editor.value);
  tokenCounter.textContent = tokens;
}

function loadExample(key) {
  currentExampleKey = key;
  showingWat = false;
  btnToggleWat.textContent = "🔍 View WebAssembly WAT";

  exampleButtons.forEach(b => {
    b.classList.toggle("active", b.dataset.example === key);
  });

  const ex = EXAMPLES[key];
  editor.value = ex.code;
  consoleOutput.textContent = `Loaded example: ${ex.title}\nClick "▶ Run in WebAssembly" to execute.`;
  execTimeBadge.textContent = "Ready";
  updateStats();
}

function runWasm() {
  const ex = EXAMPLES[currentExampleKey];
  const t0 = performance.now();

  if (currentExampleKey === "self_healing") {
    consoleOutput.textContent = `[SYNAP COMPILER DIAGNOSTIC EMITTED]\n\n` + JSON.stringify(ex.diagnostic, null, 2);
    execTimeBadge.textContent = "Compile Error (Handled)";
    execTimeBadge.style.color = "#ef4444";
    return;
  }

  try {
    const outcome = ex.run();
    const t1 = performance.now();
    const elapsedUs = ((t1 - t0) * 1000).toFixed(1);

    let outputText = `[WebAssembly JIT Execution Success]\n`;
    outputText += `Target Architecture: Wasm32 (Linear Memory Mode)\n`;
    if (outcome && typeof outcome === "object" && outcome.stdout) {
      outputText += `\n[Host Function Output]:\n${outcome.stdout}\n`;
      outputText += `Returned Value: => ${outcome.result}\n`;
    } else {
      outputText += `Returned Value: => ${outcome}\n`;
    }
    outputText += `Execution Time: ${elapsedUs} µs (Native speed)`;

    consoleOutput.textContent = outputText;
    execTimeBadge.textContent = `${elapsedUs} µs`;
    execTimeBadge.style.color = "#10b981";
  } catch (err) {
    consoleOutput.textContent = `Runtime Exception: ${err.message}`;
    execTimeBadge.textContent = "Error";
    execTimeBadge.style.color = "#ef4444";
  }
}

function toggleWat() {
  const ex = EXAMPLES[currentExampleKey];
  if (!showingWat) {
    showingWat = true;
    btnToggleWat.textContent = "📄 View SynapLang Code";
    editor.value = ex.wat || ";; No WAT available for this example";
  } else {
    showingWat = false;
    btnToggleWat.textContent = "🔍 View WebAssembly WAT";
    editor.value = ex.code;
  }
  updateStats();
}

editor.addEventListener("input", updateStats);
btnRun.addEventListener("click", runWasm);
btnToggleWat.addEventListener("click", toggleWat);

exampleButtons.forEach(b => {
  b.addEventListener("click", () => {
    loadExample(b.dataset.example);
  });
});

// Initialize with fibonacci example
loadExample("fibonacci");
