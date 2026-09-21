package org.cgutman.usbip.config;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

public class TabletAreaView extends View {
    public enum AspectRatio {
        RATIO_16_9("16:9", 16f / 9f),
        RATIO_4_3("4:3", 4f / 3f),
        RATIO_FULL("Fullscreen", 0f);

        public final String title;
        public final float ratio;

        AspectRatio(String title, float ratio) {
            this.title = title;
            this.ratio = ratio;
        }
    }

    public enum AreaScale {
        SCALE_100("100% (Full)", 100),
        SCALE_80("80%", 80),
        SCALE_65("65% (Recommended)", 65),
        SCALE_50("50% (Medium)", 50),
        SCALE_35("35% (Small)", 35);

        public final String title;
        public final int percent;

        AreaScale(String title, int percent) {
            this.title = title;
            this.percent = percent;
        }
    }

    public enum AreaPosition {
        CENTER("Center"),
        RIGHT_BOTTOM("Bottom right"),
        LEFT_BOTTOM("Bottom left"),
        RIGHT_CENTER("Right center");

        public final String title;

        AreaPosition(String title) {
            this.title = title;
        }
    }

    private AspectRatio currentRatio = AspectRatio.RATIO_16_9;
    private AreaScale currentScale = AreaScale.SCALE_100;
    private AreaPosition currentPosition = AreaPosition.CENTER;
    private boolean isAimOnly = false;

    private final RectF activeRect = new RectF();
    private boolean isPenActive = false;

    private final Paint bgPaint = new Paint();
    private final Paint activeAreaPaint = new Paint();
    private final Paint borderPaint = new Paint();
    private final Paint textPaint = new Paint();
    private final Paint subTextPaint = new Paint();
    private final Paint touchPaint = new Paint();

    private float lastTouchX = -1;
    private float lastTouchY = -1;

    public TabletAreaView(Context context) {
        super(context);
        init();
    }

    public TabletAreaView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public TabletAreaView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    private void init() {
        bgPaint.setColor(Color.parseColor("#000000")); // Pure AMOLED black
        bgPaint.setStyle(Paint.Style.FILL);

        activeAreaPaint.setColor(Color.parseColor("#181818"));
        activeAreaPaint.setStyle(Paint.Style.FILL);

        borderPaint.setColor(Color.parseColor("#00E5FF"));
        borderPaint.setStyle(Paint.Style.STROKE);
        borderPaint.setStrokeWidth(4f);
        borderPaint.setAntiAlias(true);

        textPaint.setColor(Color.parseColor("#80FFFFFF"));
        textPaint.setTextSize(32f);
        textPaint.setTextAlign(Paint.Align.CENTER);
        textPaint.setAntiAlias(true);

        subTextPaint.setColor(Color.parseColor("#FFD54F"));
        subTextPaint.setTextSize(24f);
        subTextPaint.setTextAlign(Paint.Align.CENTER);
        subTextPaint.setAntiAlias(true);

        touchPaint.setColor(Color.parseColor("#8000E5FF"));
        touchPaint.setStyle(Paint.Style.FILL);
        touchPaint.setAntiAlias(true);

        loadPreferences();
    }

    private void loadPreferences() {
        SharedPreferences prefs = getContext().getSharedPreferences("tablet_prefs", Context.MODE_PRIVATE);
        int ratioIdx = prefs.getInt("aspect_ratio", 0);
        if (ratioIdx >= 0 && ratioIdx < AspectRatio.values().length) {
            currentRatio = AspectRatio.values()[ratioIdx];
        }

        int scaleIdx = prefs.getInt("area_scale", 0);
        if (scaleIdx >= 0 && scaleIdx < AreaScale.values().length) {
            currentScale = AreaScale.values()[scaleIdx];
        }

        int posIdx = prefs.getInt("area_position", 0);
        if (posIdx >= 0 && posIdx < AreaPosition.values().length) {
            currentPosition = AreaPosition.values()[posIdx];
        }

        isAimOnly = prefs.getBoolean("aim_only", false);
    }

    public AspectRatio getAspectRatio() {
        return currentRatio;
    }

    public void setAspectRatio(AspectRatio ratio) {
        this.currentRatio = ratio;
        getContext().getSharedPreferences("tablet_prefs", Context.MODE_PRIVATE)
                .edit().putInt("aspect_ratio", ratio.ordinal()).apply();
        updateActiveRect(getWidth(), getHeight());
        invalidate();
    }

    public AreaScale getAreaScale() {
        return currentScale;
    }

    public void setAreaScale(AreaScale scale) {
        this.currentScale = scale;
        getContext().getSharedPreferences("tablet_prefs", Context.MODE_PRIVATE)
                .edit().putInt("area_scale", scale.ordinal()).apply();
        updateActiveRect(getWidth(), getHeight());
        invalidate();
    }

    public AreaPosition getAreaPosition() {
        return currentPosition;
    }

    public void setAreaPosition(AreaPosition position) {
        this.currentPosition = position;
        getContext().getSharedPreferences("tablet_prefs", Context.MODE_PRIVATE)
                .edit().putInt("area_position", position.ordinal()).apply();
        updateActiveRect(getWidth(), getHeight());
        invalidate();
    }

    public boolean isAimOnly() {
        return isAimOnly;
    }

    public void setAimOnly(boolean aimOnly) {
        this.isAimOnly = aimOnly;
        getContext().getSharedPreferences("tablet_prefs", Context.MODE_PRIVATE)
                .edit().putBoolean("aim_only", aimOnly).apply();
        invalidate();
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        updateActiveRect(w, h);
    }

    private void updateActiveRect(int w, int h) {
        if (w <= 0 || h <= 0) return;

        float targetRatio;
        if (currentRatio == AspectRatio.RATIO_FULL || currentRatio.ratio <= 0) {
            targetRatio = (float) w / (float) h;
        } else {
            targetRatio = currentRatio.ratio;
        }

        float maxW, maxH;
        float viewRatio = (float) w / (float) h;
        if (viewRatio > targetRatio) {
            maxH = h;
            maxW = h * targetRatio;
        } else {
            maxW = w;
            maxH = w / targetRatio;
        }

        float rectW = maxW * (currentScale.percent / 100f);
        float rectH = maxH * (currentScale.percent / 100f);

        float left;
        float top;

        switch (currentPosition) {
            case RIGHT_BOTTOM:
                left = w - rectW - 48f;
                top = h - rectH - 48f;
                break;
            case LEFT_BOTTOM:
                left = 48f;
                top = h - rectH - 48f;
                break;
            case RIGHT_CENTER:
                left = w - rectW - 48f;
                top = (h - rectH) / 2f;
                break;
            case CENTER:
            default:
                left = (w - rectW) / 2f;
                top = (h - rectH) / 2f;
                break;
        }

        // Clamp inside view bounds
        left = Math.max(0, Math.min(w - rectW, left));
        top = Math.max(0, Math.min(h - rectH, top));

        activeRect.set(left, top, left + rectW, top + rectH);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        canvas.drawRect(0, 0, getWidth(), getHeight(), bgPaint);

        canvas.drawRoundRect(activeRect, 20f, 20f, activeAreaPaint);
        canvas.drawRoundRect(activeRect, 20f, 20f, borderPaint);

        String label = currentRatio.title + " • " + currentScale.percent + "%";
        canvas.drawText(label, activeRect.centerX(), activeRect.centerY(), textPaint);

        if (isAimOnly) {
            canvas.drawText("aim only", activeRect.centerX(), activeRect.centerY() + 38f, subTextPaint);
        }

        if (isPenActive && lastTouchX >= 0 && lastTouchY >= 0) {
            canvas.drawCircle(lastTouchX, lastTouchY, 32f, touchPaint);
        }
    }

    private boolean isSupportedTool(int toolType) {
        return toolType == MotionEvent.TOOL_TYPE_STYLUS
                || toolType == MotionEvent.TOOL_TYPE_FINGER
                || toolType == MotionEvent.TOOL_TYPE_UNKNOWN;
    }

    private void sendPosition(float touchX, float touchY, float rawPressure, boolean buttonPrimary, boolean buttonSecondary) {
        float relX = (touchX - activeRect.left) / activeRect.width();
        float relY = (touchY - activeRect.top) / activeRect.height();

        int normX = Math.round(relX * 2400f);
        int normY = Math.round(relY * 1080f);
        normX = Math.max(0, Math.min(2400, normX));
        normY = Math.max(0, Math.min(1080, normY));

        int pressure;
        if (isAimOnly) {
            pressure = 0; // Hover / Zero pressure: aim without mouse clicking
        } else {
            pressure = Math.round(rawPressure * 4095);
            if (pressure <= 0) {
                pressure = 2048;
            } else {
                pressure = Math.min(4095, Math.max(0, pressure));
            }
        }

        Intent broadcast = new Intent("position");
        broadcast.putExtra("x", normX);
        broadcast.putExtra("y", normY);
        broadcast.putExtra("pressure", pressure);
        broadcast.putExtra("buttonPrimary", buttonPrimary);
        broadcast.putExtra("buttonSecondary", buttonSecondary);
        getContext().sendBroadcast(broadcast);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (!isSupportedTool(event.getToolType(0))) {
            return super.onTouchEvent(event);
        }

        int action = event.getActionMasked();
        boolean buttonPrimary = event.isButtonPressed(MotionEvent.BUTTON_STYLUS_PRIMARY);
        boolean buttonSecondary = event.isButtonPressed(MotionEvent.BUTTON_STYLUS_SECONDARY);

        if (action == MotionEvent.ACTION_DOWN || action == MotionEvent.ACTION_MOVE) {
            float touchX = event.getX();
            float touchY = event.getY();

            if (activeRect.contains(touchX, touchY)) {
                lastTouchX = touchX;
                lastTouchY = touchY;
                isPenActive = true;
                invalidate();

                // Process historical batch points for high 360Hz touch sampling rate
                int historySize = event.getHistorySize();
                for (int i = 0; i < historySize; i++) {
                    float hX = event.getHistoricalX(i);
                    float hY = event.getHistoricalY(i);
                    if (activeRect.contains(hX, hY)) {
                        sendPosition(hX, hY, event.getHistoricalPressure(i), buttonPrimary, buttonSecondary);
                    }
                }

                sendPosition(touchX, touchY, event.getPressure(), buttonPrimary, buttonSecondary);
                return true;
            } else {
                if (isPenActive) {
                    handleOutOfRange();
                }
                return true;
            }
        } else if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) {
            if (isPenActive) {
                handleOutOfRange();
            }
            return true;
        }

        return super.onTouchEvent(event);
    }

    @Override
    public boolean onGenericMotionEvent(MotionEvent event) {
        if (!isSupportedTool(event.getToolType(0))) {
            return super.onGenericMotionEvent(event);
        }

        int action = event.getActionMasked();
        float touchX = event.getX();
        float touchY = event.getY();

        if (action == MotionEvent.ACTION_HOVER_MOVE) {
            if (activeRect.contains(touchX, touchY)) {
                lastTouchX = touchX;
                lastTouchY = touchY;
                isPenActive = true;
                invalidate();

                sendPosition(touchX, touchY, 0f,
                        event.isButtonPressed(MotionEvent.BUTTON_STYLUS_PRIMARY),
                        event.isButtonPressed(MotionEvent.BUTTON_STYLUS_SECONDARY));
                return true;
            } else if (isPenActive) {
                handleOutOfRange();
                return true;
            }
        } else if (action == MotionEvent.ACTION_HOVER_EXIT) {
            if (isPenActive) {
                handleOutOfRange();
                return true;
            }
        }

        return super.onGenericMotionEvent(event);
    }

    private void handleOutOfRange() {
        isPenActive = false;
        lastTouchX = -1;
        lastTouchY = -1;
        invalidate();
        Intent broadcast = new Intent("penOutOfRange");
        getContext().sendBroadcast(broadcast);
    }
}
