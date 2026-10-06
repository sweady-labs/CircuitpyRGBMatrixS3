"""ulab.numpy stand-in, see __init__.py."""
import numpy as _np

# names that exist in ulab.numpy on the device (dir(np) on CircuitPython 10.0.3)
_SAME = [
    "all", "any", "arange", "arctan2", "argmax", "argmin", "argsort", "around", "asarray", "ceil",
    "clip", "compress", "concatenate", "convolve", "cos", "cosh", "cross", "degrees", "delete", "diag", "diff",
    "dot", "e", "empty", "equal", "exp", "expm1", "eye", "flip", "floor", "full", "inf", "int16", "int8",
    "interp", "isfinite", "isinf", "left_shift", "linspace", "log", "log10", "log2", "logspace", "max",
    "maximum", "mean", "median", "min", "minimum", "nan", "ndarray", "nonzero", "not_equal", "ones", "pi",
    "polyfit", "polyval", "radians", "right_shift", "roll", "sin", "sinc", "sinh", "size", "sort", "sqrt",
    "std", "sum", "tan", "tanh", "trace", "uint16", "uint8", "vectorize", "where", "zeros",
    "bitwise_and", "bitwise_or", "bitwise_xor",
]
for _name in _SAME:
    globals()[_name] = getattr(_np, _name)

float = _np.float32
bool = _np.bool_
acos, acosh, asin, asinh, atan, atanh = _np.arccos, _np.arccosh, _np.arcsin, _np.arcsinh, _np.arctan, _np.arctanh
trapz = _np.trapezoid
frombuffer = _np.frombuffer


def array(obj, dtype=None):
    if dtype is None:
        dtype = obj.dtype if isinstance(obj, _np.ndarray) else _np.float32
    if dtype in (_np.uint8, _np.int8, _np.uint16, _np.int16):
        values = _np.asarray(obj)
        info = _np.iinfo(dtype)
        # the device refuses values that do not fit (no wrap around); clip before converting
        if values.size and (values.min() < info.min or values.max() > info.max + 0.999999):
            raise OverflowError("value must fit in %d byte(s)" % _np.dtype(dtype).itemsize)
    return _np.array(obj, dtype=dtype)


def zeros(shape, dtype=_np.float32):
    return _np.zeros(shape, dtype=dtype)


def ones(shape, dtype=_np.float32):
    return _np.ones(shape, dtype=dtype)


def full(shape, fill_value, dtype=_np.float32):
    return _np.full(shape, fill_value, dtype=dtype)


def empty(shape, dtype=_np.float32):
    return _np.empty(shape, dtype=dtype)


def linspace(start, stop, num=50, endpoint=True, dtype=_np.float32):
    return _np.linspace(start, stop, num, endpoint=endpoint).astype(dtype)


def arange(*args, dtype=None):
    result = _np.arange(*args)
    return result.astype(dtype or (_np.int16 if result.dtype.kind == "i" else _np.float32))
