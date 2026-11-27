package app.fidexe.remote;

import android.content.Context;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Finds the FIDEXE desktop in the local network.
 *
 * <p>Two channels run at once, because neither of them works everywhere:
 * <ul>
 *     <li>mDNS (NSD) — the polite standard, but routers and the Wi-Fi chip's
 *     multicast filter regularly eat the packets;</li>
 *     <li>a plain UDP broadcast to {@code 255.255.255.255:47812} — survives
 *     most access points and does not need any Android system service.</li>
 * </ul>
 * Whichever answers first wins; the first result is reported, then the search
 * stops. A multicast lock is held while searching so mDNS packets are not
 * dropped by the Wi-Fi power saving filter.
 */
final class Discovery {

    interface Listener {
        void onFound(String name, String address);

        void onFinished();

        void onError(String message);
    }

    private final Context context;
    private final NsdManager manager;
    private final Listener listener;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean reported = new AtomicBoolean(false);
    private final AtomicBoolean finished = new AtomicBoolean(false);

    private NsdManager.DiscoveryListener discoveryListener;
    private WifiManager.MulticastLock multicastLock;
    private Thread udpThread;
    private volatile boolean stopped;
    private volatile String lastError;

    private final Runnable timeout = new Runnable() {
        @Override
        public void run() {
            stop();
        }
    };

    Discovery(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.manager = (NsdManager) context.getSystemService(Context.NSD_SERVICE);
        this.listener = listener;
    }

    void start(long timeoutMs) {
        stopped = false;
        reported.set(false);
        finished.set(false);
        lastError = null;
        acquireMulticastLock();
        startNsd();
        startUdp(Math.max(2500, timeoutMs));
        handler.postDelayed(timeout, Math.max(2500, timeoutMs) + 500);
    }

    // ---------------------------------------------------------------- mDNS
    private void startNsd() {
        if (manager == null) {
            lastError = "mDNS недоступен на этом телефоне";
            return;
        }
        discoveryListener = new NsdManager.DiscoveryListener() {
            @Override
            public void onDiscoveryStarted(String serviceType) {
            }

            @Override
            public void onServiceFound(NsdServiceInfo info) {
                if (info.getServiceType() == null || !info.getServiceType().startsWith(Api.SERVICE_TYPE)) {
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
                lastError = "mDNS не запустился (код " + errorCode + ")";
                maybeReportError();
            }

            @Override
            public void onStopDiscoveryFailed(String serviceType, int errorCode) {
            }
        };
        try {
            manager.discoverServices(Api.SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener);
        } catch (Exception exc) {
            lastError = "mDNS не запустился: " + exc.getMessage();
            discoveryListener = null;
            maybeReportError();
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
                    String rawName = serviceInfo.getServiceName();
                    String name = rawName != null && rawName.startsWith("FIDEXE-")
                            ? rawName.substring("FIDEXE-".length())
                            : rawName;
                    found(name, ip + ":" + serviceInfo.getPort());
                }
            });
        } catch (Exception ignored) {
            // resolution can fail when a service disappears mid-flight
        }
    }

    private static String addressOf(NsdServiceInfo info) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                List<InetAddress> addresses = info.getHostAddresses();
                if (addresses != null && !addresses.isEmpty()) {
                    return addresses.get(0).getHostAddress();
                }
            }
        } catch (Exception ignored) {
        }
        InetAddress host = info.getHost();
        return host == null ? null : host.getHostAddress();
    }

    // ----------------------------------------------------------------- UDP
    private void startUdp(long timeoutMs) {
        udpThread = new Thread(() -> {
            DatagramSocket socket = null;
            try {
                socket = new DatagramSocket();
                socket.setBroadcast(true);
                socket.setSoTimeout(400);
                byte[] payload = Api.DISCOVERY_MAGIC.getBytes(StandardCharsets.US_ASCII);
                List<InetAddress> targets = broadcastTargets();
                long deadline = System.currentTimeMillis() + timeoutMs;
                for (int round = 0; round < 8 && !stopped && !reported.get(); round++) {
                    for (InetAddress target : targets) {
                        try {
                            socket.send(new DatagramPacket(payload, payload.length, target, Api.DISCOVERY_PORT));
                        } catch (IOException ignored) {
                        }
                    }
                    long listenUntil = Math.min(deadline, System.currentTimeMillis() + 600);
                    while (!stopped && !reported.get() && System.currentTimeMillis() < listenUntil) {
                        DatagramPacket packet = new DatagramPacket(new byte[2048], 2048);
                        try {
                            socket.receive(packet);
                        } catch (SocketTimeoutException timeout) {
                            continue;
                        } catch (IOException exc) {
                            return;
                        }
                        handleReply(packet);
                    }
                    if (System.currentTimeMillis() >= deadline) {
                        break;
                    }
                }
            } catch (Exception exc) {
                lastError = "UDP-поиск не удался: " + exc.getMessage();
            } finally {
                if (socket != null) {
                    socket.close();
                }
                maybeReportError();
            }
        }, "fidexe-discovery-udp");
        udpThread.setDaemon(true);
        udpThread.start();
    }

    private void handleReply(DatagramPacket packet) {
        try {
            String text = new String(packet.getData(), 0, packet.getLength(), StandardCharsets.UTF_8);
            JSONObject json = new JSONObject(text);
            if (!"FIDEXE".equals(json.optString("app"))) {
                return;
            }
            int port = json.optInt("port", Api.DEFAULT_PORT);
            String ip = packet.getAddress() == null ? "" : packet.getAddress().getHostAddress();
            if (ip.isEmpty()) {
                return;
            }
            if (ip.startsWith("::ffff:")) {
                ip = ip.substring("::ffff:".length());
            }
            found(json.optString("host", ""), ip + ":" + port);
        } catch (Exception ignored) {
            // not our packet
        }
    }

    private static List<InetAddress> broadcastTargets() {
        List<InetAddress> targets = new ArrayList<>();
        try {
            targets.add(InetAddress.getByName("255.255.255.255"));
        } catch (Exception ignored) {
        }
        try {
            for (NetworkInterface card : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!card.isUp() || card.isLoopback()) {
                    continue;
                }
                for (InterfaceAddress address : card.getInterfaceAddresses()) {
                    InetAddress broadcast = address.getBroadcast();
                    if (broadcast != null && !targets.contains(broadcast)) {
                        targets.add(broadcast);
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return targets;
    }

    // -------------------------------------------------------------- helpers
    private void acquireMulticastLock() {
        try {
            WifiManager wifi = (WifiManager) context.getSystemService(Context.WIFI_SERVICE);
            if (wifi == null) {
                return;
            }
            WifiManager.MulticastLock lock = wifi.createMulticastLock("fidexe-discovery");
            lock.setReferenceCounted(false);
            lock.acquire();
            multicastLock = lock;
        } catch (Exception ignored) {
            // some ROMs refuse the lock; the UDP channel still works
        }
    }

    private void releaseMulticastLock() {
        WifiManager.MulticastLock lock = multicastLock;
        multicastLock = null;
        if (lock != null) {
            try {
                if (lock.isHeld()) {
                    lock.release();
                }
            } catch (Exception ignored) {
            }
        }
    }

    private void found(String name, String address) {
        if (stopped || !reported.compareAndSet(false, true)) {
            return;
        }
        final String cleanName = name == null ? "" : name;
        handler.post(() -> listener.onFound(cleanName, address));
        stop();
    }

    private void maybeReportError() {
        String message = lastError;
        if (message == null || reported.get()) {
            return;
        }
        handler.post(() -> {
            if (!reported.get() && !finished.get()) {
                listener.onError("Не удалось искать в Wi-Fi. Введите адрес вручную — например "
                        + "192.168.1.10:47811");
            }
        });
    }

    /** Stops both channels and reports the end of the search exactly once. */
    void stop() {
        stopped = true;
        handler.removeCallbacks(timeout);
        if (discoveryListener != null) {
            try {
                manager.stopServiceDiscovery(discoveryListener);
            } catch (Exception ignored) {
            }
            discoveryListener = null;
        }
        Thread thread = udpThread;
        udpThread = null;
        if (thread != null) {
            thread.interrupt();
        }
        releaseMulticastLock();
        if (finished.compareAndSet(false, true)) {
            handler.post(listener::onFinished);
        }
    }
}
