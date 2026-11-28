package app.fidexe.remote;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Thin HTTP client for the FIDEXE desktop LAN API plus the crypto helpers
 * (PBKDF2-SHA256 derivation and HMAC challenge proof).
 */
final class Api {

    static final String SERVICE_TYPE = "_fidexe._tcp.";
    static final int DEFAULT_PORT = 47811;
    /** UDP port the desktop answers "where are you" broadcasts on. */
    static final int DISCOVERY_PORT = 47812;
    static final String DISCOVERY_MAGIC = "FIDEXE?";

    /** Encrypted internet channel; set once the phone has been paired. */
    static volatile Relay relay;
    /** Where the last answer came from: "lan" or "relay". */
    static volatile String lastTransport = "lan";
    private static volatile long lanSkipUntil;

    static class ApiException extends Exception {
        /** HTTP status, or 0 when the laptop could not be reached at all. */
        final int code;

        ApiException(String message) {
            this(0, message);
        }

        ApiException(int code, String message) {
            super(message);
            this.code = code;
        }

        boolean isAuth() {
            return code == 401;
        }
    }

    private Api() {
    }

    // ------------------------------------------------------------------ HTTP
    static JSONObject info(String host) throws ApiException {
        return call(host, "/api/info", "GET", null, null);
    }

    static JSONObject challenge(String host, String email) throws ApiException {
        JSONObject body = new JSONObject();
        try {
            body.put("email", email);
        } catch (JSONException ignored) {
        }
        return call(host, "/api/auth/challenge", "POST", body, null);
    }

    static JSONObject proof(String host, String email, String challenge, String proofHex, String device)
            throws ApiException {
        JSONObject body = new JSONObject();
        try {
            body.put("email", email);
            body.put("challenge", challenge);
            body.put("proof", proofHex);
            body.put("device", device);
        } catch (JSONException ignored) {
        }
        return call(host, "/api/auth/proof", "POST", body, null);
    }

    /** Sign in with the six digits the desktop shows in its settings. */
    static JSONObject pair(String host, String code, String device) throws ApiException {
        JSONObject body = new JSONObject();
        try {
            body.put("code", code);
            body.put("device", device);
        } catch (JSONException ignored) {
        }
        return call(host, "/api/pair", "POST", body, null);
    }

    /** Windows open on the desktop, the active one first. */
    static JSONObject apps(String host, String token) throws ApiException {
        try {
            return viaLan(host, "/api/apps", "GET", null, token);
        } catch (ApiException exc) {
            return relayOrThrow("apps", null, token, exc);
        }
    }

    /** Ask the desktop to close an app the same way a click on X would. */
    static void closeApp(String host, String token, int pid) throws ApiException {
        JSONObject body = new JSONObject();
        try {
            body.put("pid", pid);
        } catch (JSONException ignored) {
        }
        try {
            viaLan(host, "/api/apps/close", "POST", body, token);
            return;
        } catch (ApiException exc) {
            if (exc.code != 0) {
                throw exc;
            }
        }
        relayOrThrow("close", body, token, new ApiException(0, "Ноутбук недоступен"));
    }

    /** One JPEG frame from the laptop webcam. */
    static byte[] frame(String host, String token) throws ApiException {
        try {
            return frameViaLan(host, token);
        } catch (ApiException exc) {
            if (exc.code != 0) {
                throw exc;
            }
        }
        JSONObject payload = new JSONObject();
        try {
            payload.put("frame", true);
        } catch (JSONException ignored) {
        }
        JSONObject answer = relayOrThrow("camera", payload, token, new ApiException(0, "Ноутбук недоступен"));
        String encoded = answer.optString("jpeg", "");
        if (encoded.isEmpty()) {
            throw new ApiException("Ноутбук не прислал кадр");
        }
        try {
            return android.util.Base64.decode(encoded, android.util.Base64.DEFAULT);
        } catch (IllegalArgumentException exc) {
            throw new ApiException("Кадр пришёл повреждённым");
        }
    }

    private static byte[] frameViaLan(String host, String token) throws ApiException {
        HttpURLConnection conn = null;
        try {
            String base = host.startsWith("http://") || host.startsWith("https://")
                    ? host
                    : "http://" + host;
            URL url = new URL(base + "/api/camera/frame");
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(4000);
            conn.setReadTimeout(8000);
            conn.setRequestMethod("GET");
            conn.setRequestProperty("Authorization", "Bearer " + token);
            int code = conn.getResponseCode();
            InputStream stream = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
            if (code >= 400) {
                String text = readAll(stream);
                String message = "Камера недоступна";
                try {
                    message = new JSONObject(text).optString("error", message);
                } catch (JSONException ignored) {
                }
                throw new ApiException(code, message);
            }
            return readBytes(stream);
        } catch (ApiException exc) {
            throw exc;
        } catch (IOException exc) {
            throw new ApiException("Ноутбук не отвечает. Проверьте, что он включён и в той же Wi-Fi сети");
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    static JSONObject status(String host, String token) throws ApiException {
        try {
            return viaLan(host, "/api/status", "GET", null, token);
        } catch (ApiException exc) {
            return relayOrThrow("status", null, token, exc);
        }
    }

    static boolean command(String host, String token, String cmd) throws ApiException {
        JSONObject body = new JSONObject();
        try {
            body.put("cmd", cmd);
        } catch (JSONException ignored) {
        }
        try {
            JSONObject response = viaLan(host, "/api/command", "POST", body, token);
            return response.optBoolean("ok", false);
        } catch (ApiException exc) {
            JSONObject response = relayOrThrow("command", body, token, exc);
            return response.optBoolean("ok", false);
        }
    }

    private static JSONObject call(String host, String path, String method, JSONObject body, String token)
            throws ApiException {
        HttpURLConnection conn = null;
        try {
            String base = host.startsWith("http://") || host.startsWith("https://")
                    ? host
                    : "http://" + host;
            URL url = new URL(base + path);
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(4000);
            conn.setReadTimeout(8000);
            conn.setRequestMethod(method);
            conn.setRequestProperty("Accept", "application/json");
            if (token != null && !token.isEmpty()) {
                conn.setRequestProperty("Authorization", "Bearer " + token);
            }
            if (body != null) {
                byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                conn.setFixedLengthStreamingMode(payload.length);
                OutputStream out = conn.getOutputStream();
                out.write(payload);
                out.flush();
                out.close();
            }
            int code = conn.getResponseCode();
            InputStream stream = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
            String text = readAll(stream);
            JSONObject json;
            try {
                json = text.isEmpty() ? new JSONObject() : new JSONObject(text);
            } catch (JSONException exc) {
                throw new ApiException("Неожиданный ответ ноутбука");
            }
            if (code >= 400) {
                throw new ApiException(code, json.optString("error", "Ошибка " + code));
            }
            return json;
        } catch (ApiException exc) {
            throw exc;
        } catch (IOException exc) {
            throw new ApiException("Ноутбук не отвечает. Проверьте, что он включён, в той же Wi-Fi "
                    + "сети и что Windows разрешает FIDEXE доступ в сети");
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    /** LAN request that remembers a dead network and skips it for a minute. */
    private static JSONObject viaLan(String host, String path, String method, JSONObject body, String token)
            throws ApiException {
        if (System.currentTimeMillis() < lanSkipUntil) {
            throw new ApiException(0, "Ноутбук не в этой Wi-Fi сети");
        }
        try {
            JSONObject result = call(host, path, method, body, token);
            lanSkipUntil = 0;
            lastTransport = "lan";
            return result;
        } catch (ApiException exc) {
            if (exc.code == 0) {
                lanSkipUntil = System.currentTimeMillis() + 60_000;
            }
            throw exc;
        }
    }

    /** Uses the encrypted internet channel; rethrows the LAN error if it is not usable. */
    private static JSONObject relayOrThrow(String op, JSONObject payload, String token, ApiException lanError)
            throws ApiException {
        Relay channel = relay;
        if (channel == null || !channel.usable() || lanError.code != 0) {
            throw lanError;
        }
        JSONObject answer = channel.request(op, payload, token);
        lastTransport = "relay";
        lanSkipUntil = System.currentTimeMillis() + 60_000;
        return answer;
    }

    private static byte[] readBytes(InputStream stream) throws IOException {
        if (stream == null) {
            return new byte[0];
        }
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[8192];
        int read;
        while ((read = stream.read(chunk)) > 0) {
            buffer.write(chunk, 0, read);
        }
        stream.close();
        return buffer.toByteArray();
    }

    private static String readAll(InputStream stream) throws IOException {
        if (stream == null) {
            return "";
        }
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int read;
        while ((read = stream.read(chunk)) > 0) {
            buffer.write(chunk, 0, read);
        }
        stream.close();
        return buffer.toString("UTF-8");
    }

    // -------------------------------------------------------------- crypto
    /** PBKDF2-HMAC-SHA256, 32-byte output (one block), matching the desktop side. */
    static byte[] pbkdf2(String password, byte[] salt, int iterations) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(password.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        byte[] block = new byte[salt.length + 4];
        System.arraycopy(salt, 0, block, 0, salt.length);
        block[salt.length] = 0;
        block[salt.length + 1] = 0;
        block[salt.length + 2] = 0;
        block[salt.length + 3] = 1;
        byte[] u = mac.doFinal(block);
        byte[] result = u.clone();
        for (int round = 1; round < iterations; round++) {
            u = mac.doFinal(u);
            for (int i = 0; i < result.length; i++) {
                result[i] ^= u[i];
            }
        }
        return result;
    }

    static String hmacHex(byte[] key, String message) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
        return hex(mac.doFinal(message.getBytes(StandardCharsets.UTF_8)));
    }

    static String hex(byte[] data) {
        StringBuilder builder = new StringBuilder(data.length * 2);
        for (byte value : data) {
            int unsigned = value & 0xFF;
            if (unsigned < 16) {
                builder.append('0');
            }
            builder.append(Integer.toHexString(unsigned));
        }
        return builder.toString();
    }

    static byte[] unhex(String text) {
        int length = text.length();
        byte[] out = new byte[length / 2];
        for (int i = 0; i < out.length; i++) {
            int hi = Character.digit(text.charAt(i * 2), 16);
            int lo = Character.digit(text.charAt(i * 2 + 1), 16);
            out[i] = (byte) ((hi << 4) | lo);
        }
        return out;
    }

    static String humanDuration(long seconds) {
        long hours = seconds / 3600;
        long minutes = (seconds % 3600) / 60;
        if (hours > 0) {
            return String.format(java.util.Locale.getDefault(), "%d ч %02d мин", hours, minutes);
        }
        if (minutes > 0) {
            return minutes + " мин";
        }
        return seconds + " с";
    }
}
