package app.fidexe.remote;

import android.content.Context;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import java.net.InetAddress;

/** Finds the FIDEXE desktop on the local network using mDNS (NSD). */
final class Discovery {

    interface Listener {
        void onFound(String name, String address);

        void onFinished();

        void onError(String message);
    }

    private final NsdManager manager;
    private final Listener listener;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private NsdManager.DiscoveryListener discoveryListener;
    private final Runnable timeout = new Runnable() {
        @Override
        public void run() {
            stop();
            listener.onFinished();
        }
    };
    private boolean found;

    Discovery(Context context, Listener listener) {
        this.manager = (NsdManager) context.getSystemService(Context.NSD_SERVICE);
        this.listener = listener;
    }

    void start(long timeoutMs) {
        found = false;
        discoveryListener = new NsdManager.DiscoveryListener() {
            @Override
            public void onDiscoveryStarted(String serviceType) {
            }

            @Override
            public void onServiceFound(NsdServiceInfo info) {
                if (!info.getServiceType().startsWith(Api.SERVICE_TYPE)) {
                    return;
                }
                resolve(info);
            }

            @Override
            public void onServiceLost(NsdServiceInfo info) {
            }

            @Override
            public void onDiscoveryStopped(String serviceType) {
            }

            @Override
            public void onStartDiscoveryFailed(String serviceType, int errorCode) {
                listener.onError("Поиск в Wi-Fi недоступен. Введите адрес вручную");
            }

            @Override
            public void onStopDiscoveryFailed(String serviceType, int errorCode) {
            }
        };
        try {
            manager.discoverServices(Api.SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener);
            handler.postDelayed(timeout, timeoutMs);
        } catch (Exception exc) {
            listener.onError("Поиск в Wi-Fi недоступен. Введите адрес вручную");
        }
    }

    private void resolve(NsdServiceInfo info) {
        try {
            manager.resolveService(info, new NsdManager.ResolveListener() {
                @Override
                public void onResolveFailed(NsdServiceInfo serviceInfo, int errorCode) {
                }

                @Override
                public void onServiceResolved(NsdServiceInfo serviceInfo) {
                    String ip = addressOf(serviceInfo);
                    if (ip == null) {
                        return;
                    }
                    String name = serviceInfo.getServiceName();
                    if (name != null && name.startsWith("FIDEXE-")) {
                        name = name.substring("FIDEXE-".length());
                    }
                    found = true;
                    String address = ip + ":" + serviceInfo.getPort();
                    handler.post(() -> listener.onFound(name, address));
                }
            });
        } catch (Exception ignored) {
            // resolution can fail when a service disappears mid-flight
        }
    }

    private static String addressOf(NsdServiceInfo info) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                InetAddress[] addresses = info.getHostAddresses();
                if (addresses != null && addresses.length > 0) {
                    return addresses[0].getHostAddress();
                }
            }
        } catch (Exception ignored) {
        }
        InetAddress host = info.getHost();
        return host == null ? null : host.getHostAddress();
    }

    void stop() {
        handler.removeCallbacks(timeout);
        if (discoveryListener != null) {
            try {
                manager.stopServiceDiscovery(discoveryListener);
            } catch (Exception ignored) {
            }
            discoveryListener = null;
        }
        if (!found) {
            handler.post(listener::onFinished);
        }
    }
}
