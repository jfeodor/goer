gør
===

Gør [ˈgɶɐ̯], does stuff for you!

Usage
-----

Write a `Goerfile.py`, similarly to how you would write a `Makefile`, for
example:

```python
import goer

headers = goer.glob("src/*.h")
sources = goer.glob("src/program.c")

obj = goer.shell(
    "gcc -c src/program.c -o build/program.o",
    targets=["build/program.o"]
)

program = goer.shell(
    "gcc build/program.o -o build/program",
    target="build/program",
    depends_on=[obj],
)
```

followed by the command:

    goer program
