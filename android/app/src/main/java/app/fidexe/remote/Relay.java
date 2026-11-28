package app.fidexe.remote;

import android.content.Context;

import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Internet relay: the phone reaches the laptop from any distance.
 *
 * <p>Both sides dial out to a public MQTT broker over TLS, so no port forwarding,
 * no firewall hole and no fixed IP are needed. The payload is encrypted end to
 * end with AES-256-GCM using the key that was handed over when the phone was
 * paired on the local network — the broker only sees a random topic and
 * ciphertext.
 */
final class Relay {

    static final String ROOT = "fidexe/v2";
    private static final byte[] AAD = "fidexe-relay-v1".getBytes(StandardCharsets.UTF_8);
    private static final long DEFAULT_TIMEOUT = 12_000L;

    private final String linkId;
    private final byte[] key;
    private final List<String[]> brokers = new ArrayList<>();
    private final String topicUp;
    private final String topicDown;
    private final Map<String, JSONObject> answers = new HashMap<>();
    private final Object gate = new Object();

    private MqttAsyncClient client;
    private volatile boolean connected;
    private volatile String lastError = "";
    private String currentBroker = "";

    Relay(JSONObject link) {
        linkId = link == null ? "" : link.optString("id", "");
        String keyHex = link == null ? "" : link.optString("key", "");
        key = unhex(keyHex);
        JSONArray list = link == null ? null : link.optJSONArray("brokers");
        if (list != null) {
            for (int index = 0; index < list.length(); index++) {
                JSONArray pair = list.optJSONArray(index);
                if (pair != null && pair.length() >= 2) {
                    brokers.add(new String[]{pair.optString(0), String.valueOf(pair.optInt(1, 8883))});
                }
            }
        }
        if (brokers.isEmpty()) {
            brokers.add(new String[]{"broker.hivemq.com", "8883"});
            brokers.add(new String[]{"broker.emqx.io", "8883"});
        }
        topicUp = ROOT + "/" + linkId + "/u";
        topicDown = ROOT + "/" + linkId + "/d";
    }

    boolean usable() {
        return linkId.length() >= 8 && key != null && key.length == 32;
    }

    boolean isConnected() {
        return connected && client != null && client.isConnected();
    }

    String brokerName() {
        return currentBroker;
    }

    String lastError() {
        return lastError;
    }

    /** Blocking connect: call it from a worker thread, never from the UI thread. */
    boolean connect(Context context) {
        if (!usable()) {
            lastError = "нет ключа интернет-связи";
            return false;
        }
        if (isConnected()) {
            return true;
        }
        close();
        lastError = "";
        for (String[] broker : brokers) {
            String host = broker[0];
            String port = broker[1];
            try {
                String clientId = "fidexe-" + UUID.randomUUID().toString().substring(0, 8);
                MqttAsyncClient candidate = new MqttAsyncClient(
                        "ssl://" + host + ":" + port, clientId, new MemoryPersistence());
                candidate.setCallback(new MqttCallbackExtended() {
                    @Override
                    public void connectComplete(boolean reconnect, String serverURI) {
                        connected = true;
                    }

                    @Override
                    public void connectionLost(Throwable cause) {
                        connected = false;
                    }

                    @Override
                    public void messageArrived(String topic, MqttMessage message) {
                        onMessage(message);
                    }

                    @Override
                    public void deliveryComplete(IMqttDeliveryToken token) {
                    }
                });
                MqttConnectOptions options = new MqttConnectOptions();
                options.setCleanSession(true);
                options.setAutomaticReconnect(true);
                options.setKeepAliveInterval(45);
                options.setConnectionTimeout(12);
                candidate.connect(options).waitForCompletion(15_000);
                candidate.subscribe(topicDown, 1).waitForCompletion(10_000);
                client = candidate;
                connected = true;
                currentBroker = host + ":" + port;
                return true;
            } catch (Exception exc) {
                lastError = host + ":" + port + " — " + describe(exc);
                connected = false;
                try {
                    if (client != null) {
                        client.close();
                    }
                } catch (Exception ignored) {
                }
                client = null;
            }
        }
        return false;
    }

    void close() {
        connected = false;
        MqttAsyncClient old = client;
        client = null;
        if (old != null) {
            try {
                old.disconnectForcibly(500, 500, false);
                old.close();
            } catch (Exception ignored) {
            }
        }
        synchronized (gate) {
            answers.clear();
        }
    }

    // ------------------------------------------------------------- requests
    /** Sends one encrypted request and waits for the encrypted answer. */
    JSONObject request(String op, JSONObject payload, String token) throws Api.ApiException {
        return request(op, payload, token, DEFAULT_TIMEOUT);
    }

    JSONObject request(String op, JSONObject payload, String token, long timeoutMs)
            throws Api.ApiException {
        if (!isConnected()) {
            throw new Api.ApiException(0, "Ноутбук недоступен через интернет");
        }
        String id = UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        try {
            JSONObject body = new JSONObject();
            body.put("v", 1);
            body.put("id", id);
            body.put("op", op);
            body.put("t", token == null ? "" : token);
            body.put("p", payload == null ? new JSONObject() : payload);
            MqttMessage message = new MqttMessage(encrypt(body.toString()).getBytes(StandardCharsets.US_ASCII));
            message.setQos(1);
            client.publish(topicUp, message);
        } catch (Exception exc) {
            throw new Api.ApiException(0, "Не удалось отправить запрос через интернет: " + describe(exc));
        }
        JSONObject answer = null;
        long deadline = System.currentTimeMillis() + timeoutMs;
        synchronized (gate) {
            while (answer == null) {
                answer = answers.remove(id);
                if (answer != null) {
                    break;
                }
                long left = deadline - System.currentTimeMillis();
                if (left <= 0) {
                    break;
                }
                try {
                    gate.wait(Math.min(left, 500));
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
        if (answer == null) {
            throw new Api.ApiException(0, "Ноутбук не ответил через интернет");
        }
        if (!answer.optBoolean("ok", false)) {
            int code = answer.optInt("c", 400);
            throw new Api.ApiException(code, answer.optString("e", "Ошибка ноутбука"));
        }
        JSONObject data = answer.optJSONObject("p");
        return data == null ? new JSONObject() : data;
    }

    private void onMessage(MqttMessage message) {
        try {
            String text = new String(message.getPayload(), StandardCharsets.US_ASCII);
            JSONObject reply = decrypt(text);
            String id = reply.optString("id", "");
            if (id.isEmpty()) {
                return;
            }
            synchronized (gate) {
                answers.put(id, reply);
                gate.notifyAll();
            }
        } catch (Exception ignored) {
            // wrong key or a foreign message on the topic
        }
    }

    // --------------------------------------------------------------- crypto
    String encrypt(String plain) throws Exception {
        byte[] nonce = new byte[12];
        new SecureRandom().nextBytes(nonce);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, nonce));
        cipher.updateAAD(AAD);
        byte[] sealed = cipher.doFinal(plain.getBytes(StandardCharsets.UTF_8));
        return b64(nonce) + "." + b64(sealed);
    }

    JSONObject decrypt(String message) throws Exception {
        int dot = message.indexOf('.');
        if (dot <= 0) {
            throw new IllegalArgumentException("no separator");
        }
        byte[] nonce = unb64(message.substring(0, dot));
        byte[] sealed = unb64(message.substring(dot + 1));
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, nonce));
        cipher.updateAAD(AAD);
        byte[] plain = cipher.doFinal(sealed);
        return new JSONObject(new String(plain, StandardCharsets.UTF_8));
    }

    private static String b64(byte[] raw) {
        return android.util.Base64.encodeToString(
                raw, android.util.Base64.URL_SAFE | android.util.Base64.NO_WRAP | android.util.Base64.NO_PADDING);
    }

    private static byte[] unb64(String text) {
        int padding = (4 - text.length() % 4) % 4;
        String padded = text + "====".substring(0, padding);
        return android.util.Base64.decode(padded, android.util.Base64.URL_SAFE | android.util.Base64.NO_WRAP);
    }

    static byte[] unhex(String text) {
        if (text == null || text.length() % 2 != 0) {
            return new byte[0];
        }
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            int hi = Character.digit(text.charAt(i * 2), 16);
            int lo = Character.digit(text.charAt(i * 2 + 1), 16);
            if (hi < 0 || lo < 0) {
                return new byte[0];
            }
            out[i] = (byte) ((hi << 4) | lo);
        }
        return out;
    }

    private static String describe(Exception exc) {
        String message = exc.getMessage();
        return message == null || message.isEmpty() ? exc.getClass().getSimpleName() : message;
    }

    private static String describe(Throwable exc) {
        String message = exc.getMessage();
        return message == null || message.isEmpty() ? exc.getClass().getSimpleName() : message;
    }
}
