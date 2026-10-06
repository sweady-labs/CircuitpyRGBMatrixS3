"""math and random as CircuitPython has them, so the simulator fails where the device would.

install() replaces the modules for everything imported afterwards (the scenes); numpy and
Pillow keep the real ones they imported before.
"""
import math as _math
import random as _random
import sys
import types

MATH = ("acos", "asin", "atan", "atan2", "ceil", "copysign", "cos", "degrees", "e", "exp", "fabs", "floor",
        "fmod", "frexp", "isfinite", "isinf", "isnan", "ldexp", "log", "modf", "pi", "pow", "radians", "sin",
        "sqrt", "tan", "trunc")
RANDOM = ("random", "randint", "randrange", "uniform", "choice", "getrandbits", "seed")


def install():
    # CircuitPython has no time zones: localtime(seconds) works like gmtime
    import time
    time.localtime = time.gmtime
    for name, real, names in (("math", _math, MATH), ("random", _random, RANDOM)):
        module = types.ModuleType(name)
        for attr in names:
            setattr(module, attr, getattr(real, attr))
        sys.modules[name] = module
