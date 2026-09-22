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
        final android.app.Dialog dialog = new android.app.Dialog(this);
        dialog.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);
        dialog.setContentView(org.cgutman.usbipserverforandroid.R.layout.dialog_settings_modern);
        dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        
        // Make the dialog wider like a bottom sheet or modern dialog
        android.view.WindowManager.LayoutParams lp = new android.view.WindowManager.LayoutParams();
        lp.copyFrom(dialog.getWindow().getAttributes());
        lp.width = (int)(getResources().getDisplayMetrics().widthPixels * 0.9);
        dialog.getWindow().setAttributes(lp);

        android.widget.TextView tvZone = dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.tv_zone_size_val);
        tvZone.setText(tabletAreaView.getAreaScale().title);
        
        android.widget.TextView tvPos = dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.tv_position_val);
        tvPos.setText(tabletAreaView.getAreaPosition().title);

        dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.btn_zone_size).setOnClickListener(v -> {
            dialog.dismiss();
            showScaleDialog();
        });

        dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.btn_position).setOnClickListener(v -> {
            dialog.dismiss();
            showPositionDialog();
        });

        dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.btn_about).setOnClickListener(v -> {
            dialog.dismiss();
            Intent browserIntent = new Intent(Intent.ACTION_VIEW, android.net.Uri.parse("https://github.com/swzxu/tabletizer"));
            startActivity(browserIntent);
        });

        dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.btn_close).setOnClickListener(v -> dialog.dismiss());

        dialog.show();
    }

    private void showScaleDialog() {
        TabletAreaView.AreaScale[] options = TabletAreaView.AreaScale.values();
        
        final android.app.Dialog dialog = new android.app.Dialog(this);
        dialog.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);
        dialog.setContentView(org.cgutman.usbipserverforandroid.R.layout.dialog_list_modern);
        dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        
        android.view.WindowManager.LayoutParams lp = new android.view.WindowManager.LayoutParams();
        lp.copyFrom(dialog.getWindow().getAttributes());
        lp.width = (int)(getResources().getDisplayMetrics().widthPixels * 0.9);
        dialog.getWindow().setAttributes(lp);

        android.widget.TextView tvTitle = dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.tv_dialog_title);
        tvTitle.setText("Working zone size");

        android.widget.LinearLayout container = dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.ll_options_container);
        
        for (final TabletAreaView.AreaScale option : options) {
            android.widget.TextView tv = new android.widget.TextView(this);
            tv.setText(option.title);
            tv.setTextSize(16);
            if (option == tabletAreaView.getAreaScale()) {
                tv.setTextColor(android.graphics.Color.parseColor("#4ADE80")); // Green for selected
                tv.setTypeface(null, android.graphics.Typeface.BOLD);
            } else {
                tv.setTextColor(android.graphics.Color.WHITE);
            }
            tv.setPadding(0, 30, 0, 30);
            
            // Add ripple effect
            android.util.TypedValue outValue = new android.util.TypedValue();
            getTheme().resolveAttribute(android.R.attr.selectableItemBackground, outValue, true);
            tv.setBackgroundResource(outValue.resourceId);
            tv.setClickable(true);
            tv.setFocusable(true);
            
            tv.setOnClickListener(v -> {
                tabletAreaView.setAreaScale(option);
                updateButtonLabel();
                dialog.dismiss();
            });
            container.addView(tv);
        }

        dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.btn_back).setOnClickListener(v -> {
            dialog.dismiss();
            showMainMenu();
        });

        dialog.show();
    }

    private void showPositionDialog() {
        TabletAreaView.AreaPosition[] options = TabletAreaView.AreaPosition.values();
        
        final android.app.Dialog dialog = new android.app.Dialog(this);
        dialog.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);
        dialog.setContentView(org.cgutman.usbipserverforandroid.R.layout.dialog_list_modern);
        dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        
        android.view.WindowManager.LayoutParams lp = new android.view.WindowManager.LayoutParams();
        lp.copyFrom(dialog.getWindow().getAttributes());
        lp.width = (int)(getResources().getDisplayMetrics().widthPixels * 0.9);
        dialog.getWindow().setAttributes(lp);

        android.widget.TextView tvTitle = dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.tv_dialog_title);
        tvTitle.setText("Position");

        android.widget.LinearLayout container = dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.ll_options_container);
        
        for (final TabletAreaView.AreaPosition option : options) {
            android.widget.TextView tv = new android.widget.TextView(this);
            tv.setText(option.title);
            tv.setTextSize(16);
            if (option == tabletAreaView.getAreaPosition()) {
                tv.setTextColor(android.graphics.Color.parseColor("#4ADE80")); // Green for selected
                tv.setTypeface(null, android.graphics.Typeface.BOLD);
            } else {
                tv.setTextColor(android.graphics.Color.WHITE);
            }
            tv.setPadding(0, 30, 0, 30);
            
            android.util.TypedValue outValue = new android.util.TypedValue();
            getTheme().resolveAttribute(android.R.attr.selectableItemBackground, outValue, true);
            tv.setBackgroundResource(outValue.resourceId);
            tv.setClickable(true);
            tv.setFocusable(true);
            
            tv.setOnClickListener(v -> {
                tabletAreaView.setAreaPosition(option);
                dialog.dismiss();
            });
            container.addView(tv);
        }

        dialog.findViewById(org.cgutman.usbipserverforandroid.R.id.btn_back).setOnClickListener(v -> {
            dialog.dismiss();
            showMainMenu();
        });

        dialog.show();
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
