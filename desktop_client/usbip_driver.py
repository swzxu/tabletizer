import ctypes
from ctypes import wintypes
import random
import string

cfgmgr32 = ctypes.windll.cfgmgr32
kernel32 = ctypes.windll.kernel32
kernel32.DeviceIoControl.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]

CR_SUCCESS = 0
CM_GET_DEVICE_INTERFACE_LIST_PRESENT = 0x00000000

FILE_DEVICE_UNKNOWN = 0x00000022
METHOD_BUFFERED = 0
FILE_READ_DATA = 0x0001
FILE_WRITE_DATA = 0x0002

def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method

PLUGIN_HARDWARE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x800, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA)
PLUGOUT_HARDWARE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x801, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA)
GET_IMPORTED_DEVICES = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x802, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA)

class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_byte * 8)]
GUID_DEVINTERFACE_USBIP_VHCI = GUID(0xB4030C06, 0xDC5F, 0x4FCC, (ctypes.c_byte * 8)(0x87, 0xEB, 0xE5, 0x51, 0x5A, 0x09, 0x35, 0xC0))

# Fixed sizes according to MSVC tail padding reuse!
class PLUGIN_HARDWARE_STRUCT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("size", wintypes.ULONG),          # 4
        ("port", ctypes.c_int),            # 4
        ("busid", ctypes.c_char * 32),     # 32
        ("service", ctypes.c_char * 32),   # 32
        ("host", ctypes.c_char * 1025),    # 1025
        ("pad1", ctypes.c_char * 3),       # 3 (padding to 1100)
        ("serial", ctypes.c_char * 16),    # 16
        ("wsk_events", ctypes.c_bool),     # 1
        ("_padding", ctypes.c_char * 3)    # 3 (Total 1120)
    ]

class IMPORTED_DEVICE_LOCATION(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("port", ctypes.c_int),
        ("busid", ctypes.c_char * 32),
        ("service", ctypes.c_char * 32),
        ("host", ctypes.c_char * 1025),
        ("_padding", ctypes.c_char * 3) # padded to 1096
    ]

class IMPORTED_DEVICE_PROPERTIES(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("devid", wintypes.UINT),
        ("speed", ctypes.c_int),
        ("vendor", wintypes.WORD),
        ("product", wintypes.WORD),
        ("serial", ctypes.c_char * 16),
        ("iserial", ctypes.c_ubyte),
        ("wsk_events", ctypes.c_bool),
        ("_padding", ctypes.c_char * 2)
    ]

class IMPORTED_DEVICE(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("loc", IMPORTED_DEVICE_LOCATION),
        ("prop", IMPORTED_DEVICE_PROPERTIES)
    ]

class GET_IMPORTED_DEVICES_STRUCT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("size", wintypes.ULONG),
        ("devices", IMPORTED_DEVICE * 1)
    ]

class PLUGOUT_HARDWARE_STRUCT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("size", wintypes.ULONG), ("port", ctypes.c_int)]

def get_device_path():
    cch = wintypes.ULONG()
    if cfgmgr32.CM_Get_Device_Interface_List_SizeW(ctypes.byref(cch), ctypes.byref(GUID_DEVINTERFACE_USBIP_VHCI), None, CM_GET_DEVICE_INTERFACE_LIST_PRESENT) != CR_SUCCESS:
        return None
    buf = ctypes.create_unicode_buffer(cch.value)
    if cfgmgr32.CM_Get_Device_Interface_ListW(ctypes.byref(GUID_DEVINTERFACE_USBIP_VHCI), None, buf, cch.value, CM_GET_DEVICE_INTERFACE_LIST_PRESENT) != CR_SUCCESS:
        return None
    return buf.value if buf.value else None

class UsbIpDriver:
    def __init__(self):
        self.handle = None
        
    def open(self):
        path = get_device_path()
        if not path:
            return False
        self.handle = kernel32.CreateFileW(path, 0x80000000 | 0x40000000, 3, None, 3, 0x80, None)
        return self.handle != -1
        
    def close(self):
        if self.handle and self.handle != -1:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def get_imported_devices(self):
        if not self.handle or self.handle == -1: return []
        
        in_len = 4 + ctypes.sizeof(IMPORTED_DEVICE)
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)
        
        r = ctypes.cast(buf, ctypes.POINTER(GET_IMPORTED_DEVICES_STRUCT)).contents
        r.size = in_len
        
        bytes_returned = wintypes.DWORD()
        if kernel32.DeviceIoControl(self.handle, GET_IMPORTED_DEVICES, buf, in_len, buf, buf_size, ctypes.byref(bytes_returned), None):
            if bytes_returned.value > 4:
                num_devices = (bytes_returned.value - 4) // ctypes.sizeof(IMPORTED_DEVICE)
                devices = []
                class DEVICE_ARRAY(ctypes.Structure):
                    _pack_ = 1
                    _fields_ = [("size", wintypes.ULONG), ("devices", IMPORTED_DEVICE * num_devices)]
                res = ctypes.cast(buf, ctypes.POINTER(DEVICE_ARRAY)).contents
                for i in range(num_devices):
                    devices.append(res.devices[i].loc.port)
                return devices
        return []

    def attach(self, host, service="3240", busid="1-1"):
        if not self.handle or self.handle == -1: return 0
        serial = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
        r = PLUGIN_HARDWARE_STRUCT()
        r.size = 1120
        r.port = 0
        r.busid = busid.encode('utf-8')
        r.service = service.encode('utf-8')
        r.host = host.encode('utf-8')
        r.serial = serial.encode('utf-8')
        r.wsk_events = True
        
        outlen = 8 # offsetof(port)=4 + sizeof(port)=4
        bytes_returned = wintypes.DWORD()
        
        if kernel32.DeviceIoControl(self.handle, PLUGIN_HARDWARE, ctypes.byref(r), 1120, ctypes.byref(r), outlen, ctypes.byref(bytes_returned), None):
            return r.port
        return 0

    def detach(self, port):
        if not self.handle or self.handle == -1: return False
        r = PLUGOUT_HARDWARE_STRUCT()
        r.size = ctypes.sizeof(r)
        r.port = port
        bytes_returned = wintypes.DWORD()
        return bool(kernel32.DeviceIoControl(self.handle, PLUGOUT_HARDWARE, ctypes.byref(r), ctypes.sizeof(r), None, 0, ctypes.byref(bytes_returned), None))
