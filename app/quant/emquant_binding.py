import ctypes
from ctypes import Structure, POINTER, c_int, c_char_p, c_void_p, c_uint, c_float, c_double, c_short, c_ushort, c_longlong, c_ulonglong, c_bool, Union, CFUNCTYPE, c_char

# Constants
EQERR_SUCCESS = 0
EQErr = c_int

# Enums
class EQVarType:
    eVT_null = 0
    eVT_char = 1
    eVT_byte = 2
    eVT_bool = 3
    eVT_short = 4
    eVT_ushort = 5
    eVT_int = 6
    eVT_uInt = 7
    eVT_int64 = 8
    eVT_uInt64 = 9
    eVT_float = 10
    eVT_double = 11
    eVT_byteArray = 12
    eVT_asciiString = 13
    eVT_unicodeString = 14

# Structs
class EQCHAR(Structure):
    _fields_ = [
        ("pChar", c_char_p),
        ("nSize", c_uint)
    ]

class EQCHARARRAY(Structure):
    _fields_ = [
        ("pChArray", POINTER(EQCHAR)),
        ("nSize", c_uint)
    ]

class EQVARIENT_UNION(Union):
    _fields_ = [
        ("charValue", ctypes.c_byte),
        ("boolValue", c_bool),
        ("shortValue", c_short),
        ("uShortValue", c_ushort),
        ("intValue", c_int),
        ("uIntValue", c_uint),
        ("int64Value", c_longlong),
        ("uInt64Value", c_ulonglong),
        ("floatValue", c_float),
        ("doubleValue", c_double)
    ]

class EQVARIENT(Structure):
    _fields_ = [
        ("vtype", c_int), # EQVarType
        ("unionValues", EQVARIENT_UNION),
        ("eqchar", EQCHAR)
    ]

class EQVARIENTARRAY(Structure):
    _fields_ = [
        ("pEQVarient", POINTER(EQVARIENT)),
        ("nSize", c_uint)
    ]

class EQDATA(Structure):
    _fields_ = [
        ("codeArray", EQCHARARRAY),
        ("indicatorArray", EQCHARARRAY),
        ("dateArray", EQCHARARRAY),
        ("valueArray", EQVARIENTARRAY)
    ]

class EQLOGININFO(Structure):
    _fields_ = [
        ("userName", c_char * 255),
        ("password", c_char * 255)
    ]

# Callback types
LogCallback = CFUNCTYPE(c_int, c_char_p)

# Helper to extract value from EQVARIENT
def get_eqvarient_value(eq_var):
    vtype = eq_var.vtype
    if vtype == EQVarType.eVT_null:
        return None
    elif vtype == EQVarType.eVT_bool:
        return eq_var.unionValues.boolValue
    elif vtype == EQVarType.eVT_int:
        return eq_var.unionValues.intValue
    elif vtype == EQVarType.eVT_double:
        return eq_var.unionValues.doubleValue
    elif vtype == EQVarType.eVT_float:
        return eq_var.unionValues.floatValue
    elif vtype == EQVarType.eVT_asciiString:
        # pChar is bytes, decode to string
        if eq_var.eqchar.pChar:
            return eq_var.eqchar.pChar.decode('utf-8', errors='ignore')
        return ""
    # Add other types as needed
    return None
