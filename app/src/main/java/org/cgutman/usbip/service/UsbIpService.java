package org.cgutman.usbip.service;

import java.io.IOException;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import org.cgutman.usbip.config.UsbIpConfig;
import org.cgutman.usbip.server.UsbDeviceInfo;
import org.cgutman.usbip.server.UsbIpServer;
import org.cgutman.usbip.server.UsbRequestHandler;
import org.cgutman.usbip.server.protocol.ProtoDefs;
import org.cgutman.usbip.server.protocol.UsbIpDevice;
import org.cgutman.usbip.server.protocol.UsbIpInterface;
import org.cgutman.usbip.server.protocol.dev.UsbIpDevicePacket;
import org.cgutman.usbip.server.protocol.dev.UsbIpSubmitUrb;
import org.cgutman.usbip.server.protocol.dev.UsbIpSubmitUrbReply;
import org.cgutman.usbip.server.protocol.dev.UsbIpUnlinkUrb;
import org.cgutman.usbip.server.protocol.dev.UsbIpUnlinkUrbReply;
import org.cgutman.usbip.usb.MockDeviceConnection;
import org.cgutman.usbip.usb.UsbControlHelper;
import org.cgutman.usbip.usb.XferUtils;
import org.cgutman.usbipserverforandroid.R;

import android.annotation.SuppressLint;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbConstants;
import android.net.wifi.WifiManager;
import android.net.wifi.WifiManager.WifiLock;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.PowerManager.WakeLock;
import android.util.SparseArray;

import androidx.annotation.RequiresApi;
import androidx.core.app.NotificationCompat;

public class UsbIpService extends Service implements UsbRequestHandler {
    private BroadcastReceiver broadcastReceiver;
    private BroadcastReceiver maxSizeBroadcastReceiver;

    public static boolean isConnected = false;

    private boolean broadcastReceiverRegistered = false;
    private boolean maxSizeBroadcastReceiverRegistered = false;
    private SparseArray<AttachedDeviceContext> connections;
    private HashMap<Socket, AttachedDeviceContext> socketMap;
    private UsbDeviceInfo deviceInfo;
    private UsbIpServer server;
    private WakeLock cpuWakeLock;
    private WifiLock highPerfWifiLock;
    private WifiLock lowLatencyWifiLock;

    private int maxX = 0;
    private int maxY = 0;

    private static final boolean DEBUG = false;

    private static final int NOTIFICATION_ID = 100;

    private final static String CHANNEL_ID = "serviceInfo";

    private void updateNotification() {
        Intent intent = new Intent(this, UsbIpConfig.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);

        int intentFlags = 0;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            intentFlags |= PendingIntent.FLAG_IMMUTABLE;
        }

        PendingIntent pendIntent = PendingIntent.getActivity(this, 0, intent, intentFlags);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(getApplicationContext(), CHANNEL_ID)
                .setSmallIcon(R.drawable.notification_icon)
                .setOngoing(true)
                .setSilent(true)
                .setTicker("USB/IP Server Running")
                .setContentTitle("USB/IP Server Running")
                .setAutoCancel(false)
                .setContentIntent(pendIntent)
                .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE);

        deviceInfo = constructTabletDeviceInfo();

        builder.setContentText(String.format("MaxX: %d, MaxY: %d", maxX, maxY));

        startForeground(NOTIFICATION_ID, builder.build());
    }

    @RequiresApi(api = Build.VERSION_CODES.TIRAMISU)
    @SuppressLint({"UseSparseArrays", "UnspecifiedRegisterReceiverFlag"})
    @Override
    public void onCreate() {
        super.onCreate();

        connections = new SparseArray<>();
        socketMap = new HashMap<>();

        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);

        cpuWakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "USBIPServerForAndroid:Service");
        cpuWakeLock.acquire();

        highPerfWifiLock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "USBIPServerForAndroid:Service:HP");
        highPerfWifiLock.acquire();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            lowLatencyWifiLock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_LOW_LATENCY, "USBIPServerForAndroid:Service:LL");
            lowLatencyWifiLock.acquire();
        }

        server = new UsbIpServer();
        server.start(this);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(CHANNEL_ID, "Service Info", NotificationManager.IMPORTANCE_DEFAULT);
            NotificationManager notificationManager = getSystemService(NotificationManager.class);
            notificationManager.createNotificationChannel(channel);
        }

        updateNotification();

        broadcastReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String action = intent.getAction();
                if (action.equalsIgnoreCase("maxSize")) {
                    maxX = intent.getIntExtra("maxX", 0);
                    maxY = intent.getIntExtra("maxY", 0);
                    updateNotification();
                    return;
                }

                AttachedDeviceContext attached = connections.get(0);
                if (attached == null || attached.devConn == null) {
                    return;
                }

                if (action.equalsIgnoreCase("penOutOfRange")) {
                    attached.devConn.tabletData.penInRange = false;
                } else if (action.equalsIgnoreCase("position")) {
                    attached.devConn.tabletData.penInRange = true;
                    attached.devConn.tabletData.x = intent.getIntExtra("x", 0);
                    attached.devConn.tabletData.y = intent.getIntExtra("y", 0);
                    attached.devConn.tabletData.pressure = intent.getIntExtra("pressure", 0);
                    attached.devConn.tabletData.buttonPrimaryPressed = intent.getBooleanExtra("buttonPrimary", false);
                    attached.devConn.tabletData.buttonSecondaryPressed = intent.getBooleanExtra("buttonSecondary", false);
                }
            }
        };

        maxSizeBroadcastReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String action = intent.getAction();
                if (action.equalsIgnoreCase("maxSize")) {
                    maxX = intent.getIntExtra("maxX", 0);
                    maxY = intent.getIntExtra("maxY", 0);
                    updateNotification();
                }
            }
        };

        IntentFilter intentFilter = new IntentFilter();
        // set the custom action
        intentFilter.addAction("maxSize");
        // register the receiver
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(maxSizeBroadcastReceiver, intentFilter, RECEIVER_EXPORTED); // for some reason it has to be exported
        } else {
            registerReceiver(maxSizeBroadcastReceiver, intentFilter);
        }
        maxSizeBroadcastReceiverRegistered = true;
    }

    public void onDestroy() {
        super.onDestroy();

        server.stop();

        if (lowLatencyWifiLock != null) {
            lowLatencyWifiLock.release();
        }
        highPerfWifiLock.release();
        cpuWakeLock.release();

        if (broadcastReceiverRegistered) {
            unregisterReceiver(broadcastReceiver);
            broadcastReceiverRegistered = false;
        }
        if (maxSizeBroadcastReceiverRegistered) {
            unregisterReceiver(maxSizeBroadcastReceiver);
            maxSizeBroadcastReceiverRegistered = false;
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        // Not currently bindable
        return null;
    }

    // Here we're going to enumerate interfaces and endpoints
    // to eliminate possible speeds until we've narrowed it
    // down to only 1 which is our speed real speed. In a typical
    // USB driver, the host controller knows the real speed but
    // we need to derive it without HCI help.
    private final static int FLAG_POSSIBLE_SPEED_LOW = 0x01;
    private final static int FLAG_POSSIBLE_SPEED_FULL = 0x02;
    private final static int FLAG_POSSIBLE_SPEED_HIGH = 0x04;
    private final static int FLAG_POSSIBLE_SPEED_SUPER = 0x08;

    private UsbDeviceInfo constructTabletDeviceInfo() {
        UsbDeviceInfo info = new UsbDeviceInfo();
        UsbIpDevice ipDev = new UsbIpDevice();

        ipDev.path = "/sys/devices/pci0000:00/0000:00:01.2/usb1/1-1";
        ipDev.busnum = 1;
        ipDev.devnum = 1;
        ipDev.busid = "1-1";

        ipDev.idVendor = 5824;
        ipDev.idProduct = 1500;
        ipDev.bcdDevice = 0;

        ipDev.bDeviceClass = 0;
        ipDev.bDeviceSubClass = 0;
        ipDev.bDeviceProtocol = 0;

        ipDev.bConfigurationValue = 1;
        ipDev.bNumConfigurations = 1;

        ipDev.bNumInterfaces = 1;

        info.dev = ipDev;
        info.interfaces = new UsbIpInterface[ipDev.bNumInterfaces];

        for (int i = 0; i < ipDev.bNumInterfaces; i++) {
            info.interfaces[i] = new UsbIpInterface();

            info.interfaces[i].bInterfaceClass = (byte) 0xFF; // vendor specific
            info.interfaces[i].bInterfaceSubClass = 0;
            info.interfaces[i].bInterfaceProtocol = 0;
        }

        ipDev.speed = FLAG_POSSIBLE_SPEED_FULL;

        return info;
    }

    @Override
    public List<UsbDeviceInfo> getDevices() {
        List<UsbDeviceInfo> devices = new ArrayList<>();
        devices.add(deviceInfo);

        return devices;
    }

    private static void sendReply(Socket s, UsbIpSubmitUrbReply reply, int status) {
        reply.status = status;
        try {
            // We need to synchronize to avoid writing on top of ourselves
            synchronized (s) {
                s.getOutputStream().write(reply.serialize());
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private static void sendReply(Socket s, UsbIpUnlinkUrbReply reply, int status) {
        reply.status = status;
        try {
            // We need to synchronize to avoid writing on top of ourselves
            synchronized (s) {
                s.getOutputStream().write(reply.serialize());
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // FIXME: This dispatching could use some refactoring so we don't have to pass
    // a million parameters to this guy
    private void dispatchRequest(final AttachedDeviceContext context, final Socket s,
                                 final ByteBuffer buff, final UsbIpSubmitUrb msg) {
        context.requestPool.submit(new Runnable() {
            @Override
            public void run() {
                UsbIpSubmitUrbReply reply = new UsbIpSubmitUrbReply(msg.seqNum,
                        msg.devId, msg.direction, msg.ep);

                if (msg.direction == UsbIpDevicePacket.USBIP_DIR_IN) {
                    // We need to store our buffer in the URB reply
                    reply.inData = buff.array();
                }

                // TODO
                int endpointType = UsbConstants.USB_ENDPOINT_XFER_BULK;

                if (endpointType == UsbConstants.USB_ENDPOINT_XFER_BULK) {
                    if (DEBUG) {
                        System.out.printf("Bulk transfer - %d bytes %s\n",
                                buff.array().length, msg.direction == UsbIpDevicePacket.USBIP_DIR_IN ? "in" : "out");
                    }

                    int res;
                    do {
                        res = XferUtils.doBulkTransfer(context.devConn, buff.array(), 1000);

                        if (context.requestPool.isShutdown()) {
                            // Bail if the queue is being torn down
                            return;
                        }

                        if (!context.activeMessages.contains(msg)) {
                            // Somebody cancelled the URB, return without responding
                            return;
                        }
                    } while (res == -110); // ETIMEDOUT

                    if (DEBUG) {
                        System.out.printf("Bulk transfer complete with %d bytes (wanted %d)\n",
                                res, msg.transferBufferLength);
                    }

                    if (!context.activeMessages.remove(msg)) {
                        // Somebody cancelled the URB, return without responding
                        return;
                    }

                    if (res < 0) {
                        reply.status = res;
                    } else {
                        reply.actualLength = res;
                        reply.status = ProtoDefs.ST_OK;
                    }

                    sendReply(s, reply, reply.status);
                }
//				else if (selectedEndpoint.getType() == UsbConstants.USB_ENDPOINT_XFER_INT) {
//					if (DEBUG) {
//						System.out.printf("Interrupt transfer - %d bytes %s on EP %d\n",
//								msg.transferBufferLength, msg.direction == UsbIpDevicePacket.USBIP_DIR_IN ? "in" : "out",
//										selectedEndpoint.getEndpointNumber());
//					}
//
//					int res;
//					do {
//						res = XferUtils.doInterruptTransfer(context.devConn, selectedEndpoint, buff.array(), 1000);
//
//						if (context.requestPool.isShutdown()) {
//							// Bail if the queue is being torn down
//							return;
//						}
//
//						if (!context.activeMessages.contains(msg)) {
//							// Somebody cancelled the URB, return without responding
//							return;
//						}
//					} while (res == -110); // ETIMEDOUT
//
//					if (DEBUG) {
//						System.out.printf("Interrupt transfer complete with %d bytes (wanted %d)\n",
//								res, msg.transferBufferLength);
//					}
//
//					if (!context.activeMessages.remove(msg)) {
//						// Somebody cancelled the URB, return without responding
//						return;
//					}
//
//					if (res < 0) {
//						reply.status = res;
//					}
//					else {
//						reply.actualLength = res;
//						reply.status = ProtoDefs.ST_OK;
//					}
//
//					sendReply(s, reply, reply.status);
//				}
                else {
                    // unsupported endpoint
                    context.activeMessages.remove(msg);
                    server.killClient(s);
                }
            }
        });
    }

    @Override
    public void submitUrbRequest(Socket s, UsbIpSubmitUrb msg) {
        UsbIpSubmitUrbReply reply = new UsbIpSubmitUrbReply(msg.seqNum,
                msg.devId, msg.direction, msg.ep);

        AttachedDeviceContext context = connections.get(0);
        if (context == null) {
            // This should never happen, but kill the connection if it does
            server.killClient(s);
            return;
        }

        MockDeviceConnection devConn = context.devConn;

        // Control endpoint is handled with a special case
        if (msg.ep == 0) {
            // This is little endian
            ByteBuffer bb = ByteBuffer.wrap(msg.setup).order(ByteOrder.LITTLE_ENDIAN);

            byte requestType = bb.get();
            byte request = bb.get();
            short value = bb.getShort();
            short index = bb.getShort();
            short length = bb.getShort();

            System.out.printf("URB Request: %x %x %x %x %x\n",
                    requestType, request, value, index, length);

            if (length != 0) {
                reply.inData = new byte[length];
            }

            // This message is now active
            context.activeMessages.add(msg);

            int res;

            // We have to handle certain control requests (SET_CONFIGURATION/SET_INTERFACE) by calling
            // Android APIs rather than just submitting the URB directly to the device
            if (!UsbControlHelper.handleInternalControlTransfer(context, requestType, request, value, index)) {
                do {
                    res = XferUtils.doControlTransfer(devConn, requestType, request, value, index,
                            (requestType & 0x80) != 0 ? reply.inData : msg.outData, length, 1000);

                    if (context.requestPool.isShutdown()) {
                        // Bail if the queue is being torn down
                        return;
                    }

                    if (!context.activeMessages.contains(msg)) {
                        // Somebody cancelled the URB, return without responding
                        return;
                    }
                } while (res == -110); // ETIMEDOUT
            } else {
                // Handled the request internally
                res = 0;
            }

            if (!context.activeMessages.remove(msg)) {
                // Somebody cancelled the URB, return without responding
                return;
            }

            if (res < 0) {
                reply.status = res;
            } else {
                reply.actualLength = res;
                reply.status = ProtoDefs.ST_OK;
            }

            sendReply(s, reply, reply.status);
        } else {
            ByteBuffer buff;
            if (msg.direction == UsbIpDevicePacket.USBIP_DIR_IN) {
                // The buffer is allocated by us
                buff = ByteBuffer.allocate(msg.transferBufferLength);
            } else {
                // The buffer came in with the request
                buff = ByteBuffer.wrap(msg.outData);
            }

            // This message is now active
            context.activeMessages.add(msg);

            // Dispatch this request asynchronously
            dispatchRequest(context, s, buff, msg);
        }
    }

    @Override
    public UsbDeviceInfo getDeviceByBusId(String busId) {
        return deviceInfo;
    }

    @Override
    public boolean attachToDevice(Socket s, String busId) {
        if (connections.size() > 0) {
            // Already attached
            return false;
        }

        MockDeviceConnection devConn = new MockDeviceConnection();

        // Create a context for this attachment
        AttachedDeviceContext context = new AttachedDeviceContext();
        context.devConn = devConn;

        // Count all endpoints on all interfaces
        int endpointCount = 1;

        // Use a thread pool with a thread per endpoint
        context.requestPool = new ThreadPoolExecutor(endpointCount, endpointCount,
                Long.MAX_VALUE, TimeUnit.DAYS,
                new LinkedBlockingQueue<>(), new ThreadPoolExecutor.DiscardPolicy());

        // Create the active message set
        context.activeMessages = new HashSet<>();

        connections.put(0, context);
        socketMap.put(s, context);

        if (!broadcastReceiverRegistered) {
            IntentFilter intentFilter = new IntentFilter();
            // set the custom action
            intentFilter.addAction("position"); //Action is just a string used to identify the receiver as there can be many in your app so it helps deciding which receiver should receive the intent.
            intentFilter.addAction("penOutOfRange");
            intentFilter.addAction("maxSize");
            // register the receiver
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                registerReceiver(broadcastReceiver, intentFilter, RECEIVER_EXPORTED); // for some reason it has to be exported
            } else {
                registerReceiver(broadcastReceiver, intentFilter);
            }
            broadcastReceiverRegistered = true;
        }

        isConnected = true;
        updateNotification();
        sendBroadcast(new Intent("connectionState").putExtra("connected", true));
        return true;
    }

    private void cleanupDetachedDevice() {
        // todo make connection not a list
        AttachedDeviceContext context = connections.get(0);
        if (context == null) {
            return;
        }

        // Clear the this attachment's context
        connections.clear();

        // Signal queue death
        context.requestPool.shutdownNow();

        // Release our claim to the interfaces
//		for (int i = 0; i < context.device.getInterfaceCount(); i++) {
//			context.devConn.releaseInterface(context.device.getInterface(i));
//		}

        // Close the connection
//		context.devConn.close();

        // Wait for the queue to die
        try {
            context.requestPool.awaitTermination(Long.MAX_VALUE, TimeUnit.DAYS);
        } catch (InterruptedException e) {
        }

        if (broadcastReceiverRegistered) {
            unregisterReceiver(broadcastReceiver);
            broadcastReceiverRegistered = false;
        }

        isConnected = false;
        updateNotification();
        sendBroadcast(new Intent("connectionState").putExtra("connected", false));
    }

    @Override
    public void detachFromDevice(Socket s, String busId) {
//		UsbDevice dev = getDevice(busId);
//		if (dev == null) {
//			return;
//		}
//
        cleanupDetachedDevice();
    }

    @Override
    public void cleanupSocket(Socket s) {
        AttachedDeviceContext context = socketMap.remove(s);
        if (context == null) {
            return;
        }

        cleanupDetachedDevice();
    }

    @Override
    public void abortUrbRequest(Socket s, UsbIpUnlinkUrb msg) {
        AttachedDeviceContext context = socketMap.get(s);
        if (context == null) {
            return;
        }

        UsbIpUnlinkUrbReply reply = new UsbIpUnlinkUrbReply(msg.seqNum, msg.devId, msg.direction, msg.ep);

        boolean found = false;
        synchronized (context.activeMessages) {
            for (UsbIpSubmitUrb urbMsg : context.activeMessages) {
                if (msg.seqNumToUnlink == urbMsg.seqNum) {
                    context.activeMessages.remove(urbMsg);
                    found = true;
                    break;
                }
            }
        }

        System.out.println("Removed URB? " + (found ? "yes" : "no"));
        sendReply(s, reply,
                found ? UsbIpSubmitUrb.USBIP_STATUS_URB_ABORTED :
                        -22); // EINVAL
    }

}
