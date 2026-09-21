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
            broadcastSize.putExtra("maxX", 2400);
            broadcastSize.putExtra("maxY", 1080);
            sendBroadcast(broadcastSize);
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

        setContentView(R.layout.activity_usbip_config);

        tabletAreaView = findViewById(R.id.tabletAreaView);
        btnSettings = findViewById(R.id.btnSettings);
        overlayDisconnected = findViewById(R.id.overlayDisconnected);

        if (btnSettings != null && tabletAreaView != null) {
            updateButtonLabel();
            btnSettings.setOnClickListener(v -> showMainMenu());
        }

        connectionReceiver = new android.content.BroadcastReceiver() {
            @Override
            public void onReceive(android.content.Context context, Intent intent) {
                boolean connected = intent.getBooleanExtra("connected", false);
                if (overlayDisconnected != null) {
                    overlayDisconnected.setVisibility(connected ? android.view.View.GONE : android.view.View.VISIBLE);
                }
            }
        };
        android.content.IntentFilter filter = new android.content.IntentFilter("connectionState");
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(connectionReceiver, filter, 4); // RECEIVER_NOT_EXPORTED = 4
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
        String aimPrefix = tabletAreaView.isAimOnly() ? "⚡ " : "";
        btnSettings.setText("⚙ " + aimPrefix + tabletAreaView.getAspectRatio().title + " (" + tabletAreaView.getAreaScale().percent + "%)");
    }

    private void showMainMenu() {
        String aimOption = tabletAreaView.isAimOnly() ? "Aim" : "Click mode";
        String[] menuItems = new String[]{
                "Aspect Ratio: " + tabletAreaView.getAspectRatio().title,
                "Zone size: " + tabletAreaView.getAreaScale().title,
                "Pozition: " + tabletAreaView.getAreaPosition().title,
                aimOption
        };

        new AlertDialog.Builder(this)
                .setTitle("Settings")
                .setItems(menuItems, (dialog, which) -> {
                    switch (which) {
                        case 0:
                            showRatioDialog();
                            break;
                        case 1:
                            showScaleDialog();
                            break;
                        case 2:
                            showPositionDialog();
                            break;
                        case 3:
                            tabletAreaView.setAimOnly(!tabletAreaView.isAimOnly());
                            updateButtonLabel();
                            break;
                    }
                })
                .setNegativeButton("Close", null)
                .show();
    }

    private void showRatioDialog() {
        TabletAreaView.AspectRatio[] options = TabletAreaView.AspectRatio.values();
        String[] titles = new String[options.length];
        int selected = 0;
        for (int i = 0; i < options.length; i++) {
            titles[i] = options[i].title;
            if (options[i] == tabletAreaView.getAspectRatio()) {
                selected = i;
            }
        }

        new AlertDialog.Builder(this)
                .setTitle("Aspect ratio")
                .setSingleChoiceItems(titles, selected, (dialog, which) -> {
                    tabletAreaView.setAspectRatio(options[which]);
                    updateButtonLabel();
                    dialog.dismiss();
                })
                .setNegativeButton("Back", (dialog, which) -> showMainMenu())
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
}
