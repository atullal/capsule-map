package dev.atul.camerabridge;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;

/** Invokes Nebula's exported capture screen. Requires the stock factory app. */
public final class CaptureActivity extends Activity {
    public void onCreate(Bundle saved) {
        super.onCreate(saved);
        Bundle params = new Bundle();
        params.putInt("CameraShootMode", 3);
        params.putInt("CameraExposure", -1);
        params.putString("cmd", "capsule_mapping_capture");
        Intent intent = new Intent();
        intent.setClassName("com.zhixin.factorytest", "com.zhixin.factorytest.activity.devicecontrol.DeviceControlTestActivity");
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        intent.putExtra("fragmentClassName", "com.zhixin.factorytest.activity.devicecontrol.CameraHWShootFragment");
        intent.putExtra("bundle", params);
        startActivity(intent);
        finish();
    }
}
