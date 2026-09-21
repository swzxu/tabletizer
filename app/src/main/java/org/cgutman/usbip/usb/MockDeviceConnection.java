package org.cgutman.usbip.usb;

import android.hardware.usb.UsbConfiguration;
import android.hardware.usb.UsbInterface;

import org.cgutman.usbip.service.TabletData;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

class Result {
    public final boolean handled;
    public final int length;

    public Result(boolean handled, int length) {
        this.handled = handled;
        this.length = length;
    }
}

public class MockDeviceConnection {
    public final TabletData tabletData = new TabletData();

    private final ByteBuffer descriptor;
    private final ByteBuffer configuration;
    private final ByteBuffer initialReport;

    public MockDeviceConnection() {
        descriptor = ByteBuffer.allocate(UsbDeviceDescriptor.DESCRIPTOR_SIZE);
        descriptor.order(ByteOrder.LITTLE_ENDIAN);
        descriptor.put((byte) UsbDeviceDescriptor.DESCRIPTOR_SIZE)
                .put((byte) 1) // descriptor type
                .putShort((short) 0x0110) // bcdUSB
                .put((byte) 0) // device class
                .put((byte) 0) // device sub class
                .put((byte) 0) // device protocol
                .put((byte) 8) // max packet size
                .putShort((short) 5824) // vendor id
                .putShort((short) 1500) // product id
                .putShort((short) 0) // bcd device
                .put((byte) 0) // iManufacturer
                .put((byte) 0) // iProduct
                .put((byte) 0) // iSerialNumber
                .put((byte) 1); // num configurations

        configuration = ByteBuffer.allocate(0x22);
        configuration.order(ByteOrder.LITTLE_ENDIAN);
        // configuration
        configuration.put((byte) 9) // bLength
                .put((byte) 2) // bDescriptorType
                .putShort((short) 0x22) // wTotalLength
                .put((byte) 1) // bNumInterfaces
                .put((byte) 1) // bConfigurationValue
                .put((byte) 0) // iConfiguration 0 is empty string
                .put((byte) 0x80) // bmAttributes
                .put((byte) 0x32); // bMaxPower

        // interface
        configuration.put((byte) 9) // bLength=9
                .put((byte) 4) // bDescriptorType
                .put((byte) 0) // bInterfaceNumber
                .put((byte) 0) // bAlternateSetting=0,
                .put((byte) 1) // bNumEndpoints=1,
                .put((byte) 0xFF) // bInterfaceClass=3,
                .put((byte) 0) // bInterfaceSubClass=1,
                .put((byte) 0) // bInterfaceProtocol=2, 2 is mouse, 0 is None
                .put((byte) 0); // iInterface=0)

        // description (hid class)
        configuration.put((byte) 9) // bLength
                .put((byte) 0x21) // bDescriptorType
                .putShort((short) 0) // bcdHID mouse, keyboard is also 1...
                .put((byte) 0) // bCountryCode
                .put((byte) 1) // bNumDescriptors
                .put((byte) 0x22) // bDescriptprType2
                .putShort((short) 0x34); // wDescriptionLength

        // endpoint
        configuration.put((byte) 7) // bLength
                .put((byte) 5) // bDescriptorType
                .put((byte) 0x81) // bEndpointAddress
                .put((byte) 3) // bmAttributes
                .putShort((short) 12) // wMaxPacketSize
                .put((byte) 1); // bInterval 1 ms


        initialReport = ByteBuffer.allocate(52);
        initialReport.order(ByteOrder.LITTLE_ENDIAN);
        // maybe we don't have to change this at all... I think it's only important for HID devices, we can just send raw data
        initialReport.put((byte) 0x05).put((byte) 0x0D)   // Usage Page (Digitizer)
                .put((byte) 0x09).put((byte) 0x00)        // Usage (Undefined)
                .put((byte) 0xa1).put((byte) 0x01)        // Collection (Application)
                .put((byte) 0x09).put((byte) 0x01)        // Usage (Pointer)
                .put((byte) 0xa1).put((byte) 0x00)        // Collection (Physical)
                .put((byte) 0x05).put((byte) 0x09)        // Usage Page (Button)
                .put((byte) 0x19).put((byte) 0x01)        // Usage Minimum (1)
                .put((byte) 0x29).put((byte) 0x03)        // Usage Maximum (3)
                .put((byte) 0x15).put((byte) 0x00)        // Logical Minimum (0)
                .put((byte) 0x25).put((byte) 0x01)        // Logical Maximum (1)
                .put((byte) 0x95).put((byte) 0x03)        // Report Count (3)
                .put((byte) 0x75).put((byte) 0x01)        // Report Size (1)
                .put((byte) 0x81).put((byte) 0x02)        // Input (Data, Variable, Absolute)
                .put((byte) 0x95).put((byte) 0x01)        // Report Count (1)
                .put((byte) 0x75).put((byte) 0x05)        // Report Size (5)
                .put((byte) 0x81).put((byte) 0x01)        // Input (Constant)
                .put((byte) 0x05).put((byte) 0x01)        // Usage Page (Generic Desktop)
                .put((byte) 0x09).put((byte) 0x30)        // Usage (X)
                .put((byte) 0x09).put((byte) 0x31)        // Usage (Y)
                .put((byte) 0x09).put((byte) 0x38)        // Usage (Wheel)
                .put((byte) 0x15).put((byte) 0x81)        // Logical Minimum (-0x7f)
                .put((byte) 0x25).put((byte) 0x7f)        // Logical Maximum (0x7f)
                .put((byte) 0x75).put((byte) 0x08)        // Report Size (8)
                .put((byte) 0x95).put((byte) 0x03)        // Report Count (3)
                .put((byte) 0x81).put((byte) 0x06)        // Input (Data, Variable, Relative)
                .put((byte) 0xc0)                         // End Collection
                .put((byte) 0xc0);                        // End Collection
    }

    public void close() {
    }

    public boolean setInterface(UsbInterface intf) {
        throw new RuntimeException("Stub!");
    }

    public boolean setConfiguration(UsbConfiguration configuration) {
        throw new RuntimeException("Stub!");
    }

    public int controlTransfer(int requestType, int request, int value, int index, byte[] buffer, int length, int timeout) {
        Result res = new Result(false, 0);

        if (requestType == 0x80) // Host Request
        {
            if (request == 0x06) // Get Descriptor
                res = handleGetDescriptor(request, value, index, buffer, length);
            else if (request == 0x00) { // Get STATUS
                buffer[0] = 1;
                buffer[1] = 0;
                res = new Result(true, 2);
            }
        } else if (requestType == 0x81) {
            if (request == 0x06) { // Get Descriptor
                // send initial report
                if (value == 0x2200) {
                    initialReport.rewind();
                    int copyLen = Math.min(length, initialReport.remaining());
                    initialReport.get(buffer, 0, copyLen);
                    res = new Result(true, copyLen);
                }
            }
        } else if (requestType == 0x21) { // Host Request
            if (request == 0xa) { // Set Idle
                res = new Result(true, 0);
            }
        }
        return res.length;
    }

    public int bulkTransfer(byte[] buffer, int length, int timeout) {
        if (length == 12) {
            ByteBuffer input = ByteBuffer.allocate(length);
            input.order(ByteOrder.LITTLE_ENDIAN);
            input.put((byte) 1); // to comply with other parser
            byte penByte = (byte) ((tabletData.penInRange ? 0x20 : 0) |
                    (tabletData.buttonPrimaryPressed ? 2 : 0)
                    | (tabletData.buttonSecondaryPressed ? 4 : 0));
            input.put(penByte);
            input.putShort((short) tabletData.x); // X
            input.putShort((short) tabletData.y); // Y
            input.putShort((short) tabletData.pressure); // pressure
            input.putShort((short) tabletData.tiltX); // tiltX
            input.putShort((short) tabletData.tiltY); // tiltY

            input.rewind();
            int copyLen = Math.min(length, input.remaining());
            input.get(buffer, 0, copyLen);
            return copyLen;
        }
        return 0;
    }

    private Result handleGetDescriptor(int request, int value, int index, byte[] buffer, int length) {
        if (value == 0x100) { // Device
            descriptor.rewind(); // this resets position to 0, needed for .get to work
            int copyLen = Math.min(length, descriptor.remaining());
            descriptor.get(buffer, 0, copyLen); // copy it over
            return new Result(true, copyLen);
        } else if (value == 0x200) { // Configuration
            configuration.rewind(); // this resets position to 0, needed for .get to work
            int copyLen = Math.min(length, configuration.remaining());
            configuration.get(buffer, 0, copyLen); // copy it over
            return new Result(true, copyLen);
        }
        return new Result(false, 0);
    }
}
