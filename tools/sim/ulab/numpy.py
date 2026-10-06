"""ulab.numpy stand-in, see __init__.py."""
import numpy as _np


class _Array(_np.ndarray):
    """numpy array with one ulab rule numpy does not have: with the Python number on the left
    (300 - a, 1000 + a), ulab gives the number its own type (uint8 up to 255, uint16 above) first,
    and uint16 together with int8/int16 becomes float. So 300 - int16_array is float on the device."""

    def _reflected(self, ufunc, other):
        result = ufunc(other, _np.asarray(self))
        if (isinstance(other, int) and not isinstance(other, bool) and self.dtype in (_np.int8, _np.int16)
                and not -128 <= other <= 255):
            result = result.astype(_np.float32)
        if result.dtype == _np.float64:
            result = result.astype(_np.float32)
        return _wrap(result)

    def __radd__(self, other):
        return self._reflected(_np.add, other)

    def __rsub__(self, other):
        return self._reflected(_np.subtract, other)

    def __rmul__(self, other):
        return self._reflected(_np.multiply, other)


def _wrap(value):
    if isinstance(value, _np.ndarray) and not isinstance(value, _Array):
        return value.view(_Array)
    return value


def _wrapped(function):
    return lambda *args, **kwargs: _wrap(function(*args, **kwargs))

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
    _value = getattr(_np, _name)
    globals()[_name] = _wrapped(_value) if callable(_value) and not isinstance(_value, type) else _value

float = _np.float32
bool = _np.bool_
acos, acosh, asin, asinh, atan, atanh = (_wrapped(f) for f in (_np.arccos, _np.arccosh, _np.arcsin, _np.arcsinh,
                                                               _np.arctan, _np.arctanh))
trapz = _np.trapezoid
frombuffer = _wrapped(_np.frombuffer)
ndarray = _np.ndarray


def array(obj, dtype=None):
    if dtype is None:
        dtype = obj.dtype if isinstance(obj, _np.ndarray) else _np.float32
    if dtype in (_np.uint8, _np.int8, _np.uint16, _np.int16):
        values = _np.asarray(obj)
        if values.dtype.kind == "f":
            # ulab rounds half away from zero when it converts floats (0.5 -> 1, -2.7 -> -3);
            # numpy would cut off the fraction
            values = _np.sign(values) * _np.floor(_np.abs(values) + 0.5)
        info = _np.iinfo(dtype)
        # the device refuses values that do not fit (no wrap around); clip before converting
        if values.size and (values.min() < info.min or values.max() > info.max):
            raise OverflowError("value must fit in %d byte(s)" % _np.dtype(dtype).itemsize)
        return _wrap(values.astype(dtype))
    return _wrap(_np.array(obj, dtype=dtype))


def zeros(shape, dtype=_np.float32):
    return _wrap(_np.zeros(shape, dtype=dtype))


def ones(shape, dtype=_np.float32):
    return _wrap(_np.ones(shape, dtype=dtype))


def full(shape, fill_value, dtype=_np.float32):
    return _wrap(_np.full(shape, fill_value, dtype=dtype))


def empty(shape, dtype=_np.float32):
    return _wrap(_np.empty(shape, dtype=dtype))


def linspace(start, stop, num=50, endpoint=True, dtype=_np.float32):
    return _wrap(_np.linspace(start, stop, num, endpoint=endpoint).astype(dtype))


def arange(*args, dtype=None):
    result = _np.arange(*args)
    return _wrap(result.astype(dtype or (_np.int16 if result.dtype.kind == "i" else _np.float32)))
