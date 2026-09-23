import socket
import struct

def get_exported_devices(host, port=3240):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((host, port))
        
        # OP_REQ_DEVLIST = 0x8005
        # version = 0x0111
        req = struct.pack('>HHII', 0x0111, 0x8005, 0, 0) # Wait, it's 8 bytes without the last 0?
        # Actually: version (2), cmd (2), status (4)
        req = struct.pack('>HHI', 0x0111, 0x8005, 0)
        s.sendall(req)
        
        # Read header
        res = s.recv(8)
        if len(res) < 8:
            return []
            
        version, cmd, status = struct.unpack('>HHI', res)
        if cmd != 0x0005:
            return []
            
        # Read n_devices
        res = s.recv(4)
        if len(res) < 4:
            return []
        n_devices = struct.unpack('>I', res)[0]
        
        devices = []
        for _ in range(n_devices):
            # Read device info: path(256), busid(32), busnum(4), devnum(4), speed(4), idVendor(2), idProduct(2), bcdDevice(2), bDeviceClass(1), bDeviceSubClass(1), bDeviceProtocol(1), bConfigurationValue(1), bNumConfigurations(1), bNumInterfaces(1)
            # Total size: 256 + 32 + 4 + 4 + 4 + 2 + 2 + 2 + 1 + 1 + 1 + 1 + 1 + 1 = 312 bytes
            dev_data = b''
            while len(dev_data) < 312:
                dev_data += s.recv(312 - len(dev_data))
                
            path = dev_data[0:256].decode('utf-8').strip('\x00')
            busid = dev_data[256:288].decode('utf-8').strip('\x00')
            busnum, devnum, speed, vid, pid = struct.unpack('>IIIHH', dev_data[288:304])
            
            devices.append({
                'busid': busid,
                'vid': vid,
                'pid': pid
            })
            
            # Read interfaces (bNumInterfaces)
            num_interfaces = dev_data[311]
            # Each interface is 4 bytes (bInterfaceClass, bInterfaceSubClass, bInterfaceProtocol, padding)
            if num_interfaces > 0:
                ifaces_data = b''
                while len(ifaces_data) < num_interfaces * 4:
                    ifaces_data += s.recv(num_interfaces * 4 - len(ifaces_data))
                    
        s.close()
        return devices
    except Exception as e:
        print(f"Error fetching devlist: {e}")
        return []

if __name__ == '__main__':
    # Test on local network if possible
    print(get_exported_devices('127.0.0.1'))
