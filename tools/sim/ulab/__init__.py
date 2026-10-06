"""Stand-in for CircuitPython's ulab: numpy with only the names ulab 6.5 has on the MatrixPortal S3.

Operators are not restricted: the modulo operator % does not exist on the device, don't use it.
Arrays made from lists are float32 like on the device, and converting floats to integers
rounds half away from zero like the device (numpy would cut off the fraction).
"""
__version__ = "6.5.3-sim"
