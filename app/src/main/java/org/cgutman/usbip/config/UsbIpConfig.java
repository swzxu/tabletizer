package org.cgutman.usbip.config;

import org.cgutman.usbip.service.UsbIpService;
import org.cgutman.usbipserverforandroid.R;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Point;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;

import androidx.activity.ComponentActivity;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.core.content.ContextCompat;

public class UsbIpConfig extends ComponentActivity {
    private final Point screenSize = new Point();
    private boolean screenSizeSet = false;
    private TabletAreaView tabletAreaView;
    private Button btnSettings;

    private ActivityResultLauncher<String> requestPermissionLauncher =
            registerForActivityResult(new ActivityResultContracts.RequestPermission(), isGranted -> {
                startService(new Intent(UsbIpConfig.this, UsbIpService.class));
            });

    private void sendScreenSize() {
        if (screenSize.x > 0 && screenSize.y > 0) {
            Intent broadcastSize = new Intent("maxSize");
            broadcastSize.putExtra("maxX", screenSize.x);
            broadcastSize.putExtra("maxY", screenSize.y);
            sendBroadcast(broadcastSize);
            
            if (tabletAreaView != null) {
                tabletAreaView.setScreenSize(screenSize.x, screenSize.y);
            }
            
            screenSizeSet = true;
        }
    }

    private View overlayDisconnected;
    private android.content.BroadcastReceiver connectionReceiver;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        // Keep screen awake for long beatmaps
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        // Force maximum refresh rate for lower latency
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
            android.view.Display.Mode[] modes = getWindowManager().getDefaultDisplay().getSupportedModes();
            android.view.Display.Mode bestMode = null;
            float maxHz = 0f;
            for (android.view.Display.Mode mode : modes) {
                if (mode.getRefreshRate() > maxHz) {
                    maxHz = mode.getRefreshRate();
                    bestMode = mode;
                }
            }
            if (bestMode != null) {
                WindowManager.LayoutParams lp = getWindow().getAttributes();
                lp.preferredDisplayModeId = bestMode.getModeId();
                getWindow().setAttributes(lp);
            }
        }
        setContentView(R.layout.activity_usbip_config);

        tabletAreaView = findViewById(R.id.tabletAreaView);
        btnSettings = findViewById(R.id.btnSettings);
        overlayDisconnected = findViewById(R.id.overlayDisconnected);
        
        android.widget.TextView tvIpAddress = findViewById(R.id.tvIpAddress);
        if (tvIpAddress != null) {
            tvIpAddress.setText("Wi-Fi IP: " + getLocalIpAddress());
        }

        if (btnSettings != null && tabletAreaView != null) {
            updateButtonLabel();
            btnSettings.setOnClickListener(v -> showMainMenu());
        }

        connectionReceiver = new android.content.BroadcastReceiver() {
            @Override
            public void onReceive(android.content.Context context, Intent intent) {
                boolean connected = intent.getBooleanExtra("connected", false);
                runOnUiThread(() -> {
                    if (overlayDisconnected != null) {
                        overlayDisconnected.setVisibility(connected ? android.view.View.GONE : android.view.View.VISIBLE);
                    }
                });
            }
        };
        android.content.IntentFilter filter = new android.content.IntentFilter("connectionState");
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(connectionReceiver, filter, 2); // RECEIVER_EXPORTED = 2
        } else {
            registerReceiver(connectionReceiver, filter);
        }

        if (ContextCompat.checkSelfPermission(UsbIpConfig.this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            startService(new Intent(UsbIpConfig.this, UsbIpService.class));
        } else {
            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS);
        }

        this.getWindowManager().getDefaultDisplay().getRealSize(screenSize);
        sendScreenSize();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (overlayDisconnected != null) {
            overlayDisconnected.setVisibility(UsbIpService.isConnected ? android.view.View.GONE : android.view.View.VISIBLE);
        }
    }


    private void updateButtonLabel() {
        if (btnSettings == null || tabletAreaView == null) return;
        btnSettings.setText("Settings: (" + tabletAreaView.getAreaScale().percent + "%)");
    }

    private void showMainMenu() {
        String[] menuItems = new String[]{
                "Zone size: " + tabletAreaView.getAreaScale().title,
                "Position: " + tabletAreaView.getAreaPosition().title,
                "About"
        };

        new AlertDialog.Builder(this)
                .setTitle("Settings")
                .setItems(menuItems, (dialog, which) -> {
                    switch (which) {
                        case 0:
                            showScaleDialog();
                            break;
                        case 1:
                            showPositionDialog();
                            break;
                        case 2:
                            Intent browserIntent = new Intent(Intent.ACTION_VIEW, android.net.Uri.parse("https://github.com/swzxu/tabletizer"));
                            startActivity(browserIntent);
                            break;
                    }
                })
                .setNegativeButton("Close", null)
                .show();
    }

    private void showScaleDialog() {
        TabletAreaView.AreaScale[] options = TabletAreaView.AreaScale.values();
        String[] titles = new String[options.length];
        int selected = 0;
        for (int i = 0; i < options.length; i++) {
            titles[i] = options[i].title;
            if (options[i] == tabletAreaView.getAreaScale()) {
                selected = i;
            }
        }

        new AlertDialog.Builder(this)
                .setTitle("Working zone size")
                .setSingleChoiceItems(titles, selected, (dialog, which) -> {
                    tabletAreaView.setAreaScale(options[which]);
                    updateButtonLabel();
                    dialog.dismiss();
                })
                .setNegativeButton("Back", (dialog, which) -> showMainMenu())
                .show();
    }

    private void showPositionDialog() {
        TabletAreaView.AreaPosition[] options = TabletAreaView.AreaPosition.values();
        String[] titles = new String[options.length];
        int selected = 0;
        for (int i = 0; i < options.length; i++) {
            titles[i] = options[i].title;
            if (options[i] == tabletAreaView.getAreaPosition()) {
                selected = i;
            }
        }

        new AlertDialog.Builder(this)
                .setTitle("Working zone position")
                .setSingleChoiceItems(titles, selected, (dialog, which) -> {
                    tabletAreaView.setAreaPosition(options[which]);
                    updateButtonLabel();
                    dialog.dismiss();
                })
                .setNegativeButton("Back", (dialog, which) -> showMainMenu())
                .show();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            this.getWindowManager().getDefaultDisplay().getRealSize(screenSize);
            sendScreenSize();
        }
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        this.getWindowManager().getDefaultDisplay().getRealSize(screenSize);
        sendScreenSize();
    }

    @Override
    protected void onDestroy() {
        stopService(new Intent(UsbIpConfig.this, UsbIpService.class));
        if (connectionReceiver != null) {
            unregisterReceiver(connectionReceiver);
        }
        super.onDestroy();
    }

    private String getLocalIpAddress() {
        try {
            java.util.Enumeration<java.net.NetworkInterface> en = java.net.NetworkInterface.getNetworkInterfaces();
            while (en.hasMoreElements()) {
                java.net.NetworkInterface intf = en.nextElement();
                java.util.Enumeration<java.net.InetAddress> enumIpAddr = intf.getInetAddresses();
                while (enumIpAddr.hasMoreElements()) {
                    java.net.InetAddress inetAddress = enumIpAddr.nextElement();
                    if (!inetAddress.isLoopbackAddress() && inetAddress instanceof java.net.Inet4Address) {
                        return inetAddress.getHostAddress();
                    }
                }
            }
        } catch (Exception ex) {
            ex.printStackTrace();
        }
        return "Not connected to Wi-Fi";
    }
}
