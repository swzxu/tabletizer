package org.cgutman.usbip.service;

public class TabletData {
    public boolean penInRange;
    public int x;
    public int y;
    public int pressure;
    public int tiltX;
    public int tiltY;
    public boolean buttonPrimaryPressed;
    public boolean buttonSecondaryPressed;

    public TabletData() {
        penInRange = false;
        x = 0;
        y = 0;
        pressure = 0;
        tiltX = 0;
        tiltY = 0;
        buttonPrimaryPressed = false;
        buttonSecondaryPressed = false;
    }
}
