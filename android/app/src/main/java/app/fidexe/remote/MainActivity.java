package app.fidexe.remote;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * FIDEXE Remote: connects to the FIDEXE desktop app over the local Wi-Fi and
 * locks the computer with one tap.
 */
public class MainActivity extends Activity {

    private static final int BG = 0xFF0E1017;
    private static final int CARD = 0xFF171B27;
    private static final int CARD_ALT = 0xFF1E2333;
    private static final int BORDER = 0xFF242B3D;
    private static final int ACCENT = 0xFF7B6CFF;
    private static final int ACCENT_DARK = 0xFF5B4BE0;
    private static final int ACCENT_SOFT = 0xFF272350;
    private static final int MINT = 0xFF2EE6A8;
    private static final int MINT_SOFT = 0xFF12352C;
    private static final int WARN = 0xFFFFB84D;
    private static final int WARN_SOFT = 0xFF3A2C15;
    private static final int DANGER = 0xFFFF5D7A;
    private static final int TEXT = 0xFFECEEF7;
    private static final int MUTED = 0xFF8B93AB;
    private static final int FAINT = 0xFF5A6175;

    private static final long POLL_MS = 5000L;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    private SharedPreferences prefs;
    private LinearLayout container;
    private ScrollView scroll;

    private String host = "";
    private String token = "";
    private String email = "";
    private String laptopName = "Ноутбук";
    private boolean paused;

    // connect screen
    private Discovery discovery;
    private LinearLayout foundBox;
    private EditText hostField;
    private EditText codeField;
    private TextView codeButton;
    private EditText emailField;
    private EditText passwordField;
    private TextView errorLabel;
    private TextView connectButton;
    private TextView discoverButton;

    // control screen
    private TextView laptopLabel;
    private TextView statusLine;
    private TextView addressLine;
    private TextView timeValue;
    private TextView focusValue;
    private TextView clipsValue;
    private TextView trackingValue;
    private TextView logLine;
    private TextView pauseButton;
    private TextView lockButton;

    private Runnable pollTask;

    // camera screen
    private ImageView cameraView;
    private TextView cameraStatus;
    private Runnable cameraTask;
    private boolean cameraFetching;
    private boolean cameraStopped;

    // apps screen
    private LinearLayout appsList;
    private TextView appsStatus;

    private String screen = "connect";

    // ------------------------------------------------------------------ setup
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("fidexe_remote", Context.MODE_PRIVATE);

        Window window = getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(BG);
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(BG);
        scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setPadding(dp(20), dp(22), dp(20), dp(28));
        scroll.addView(container, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);

        String savedHost = prefs.getString("host", "");
        String savedToken = prefs.getString("token", "");
        email = prefs.getString("email", "");
        laptopName = prefs.getString("laptop", "Ноутбук");
        if (!savedHost.isEmpty() && !savedToken.isEmpty()) {
            host = savedHost;
            token = savedToken;
            showControlScreen();
        } else {
            host = savedHost;
            showConnectScreen();
        }
    }

    @Override
    public void onBackPressed() {
        if ("camera".equals(screen) || "apps".equals(screen)) {
            showControlScreen();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onPause() {
        stopCamera();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        stopCamera();
        stopPolling();
        if (discovery != null) {
            discovery.stop();
        }
        io.shutdownNow();
        super.onDestroy();
    }

    // ------------------------------------------------------- connect screen
    private void showConnectScreen() {
        screen = "connect";
        stopCamera();
        stopPolling();
        container.removeAllViews();
        addBrandHeader();
        container.addView(text("Блокировка ноутбука\nс телефона", TEXT, 24, true), lpm(-1, -2, 18));
        container.addView(text("Введите 6 цифр из настроек FIDEXE на ноутбуке — и пульт откроется.",
                MUTED, 13, false), lpm(-1, -2, 6));

        // ---- laptop card
        LinearLayout laptopCard = card();
        laptopCard.addView(sectionTitle("Ноутбук"));
        foundBox = new LinearLayout(this);
        foundBox.setOrientation(LinearLayout.VERTICAL);
        laptopCard.addView(foundBox, lpm(-1, -2, 8));

        discoverButton = button("Найти ноутбук в Wi-Fi", false);
        discoverButton.setOnClickListener(v -> startDiscovery());
        laptopCard.addView(discoverButton, lpm(-1, dp(48), 10));

        laptopCard.addView(text("или укажите адрес вручную", FAINT, 11, false), lpm(-1, -2, 14));
        hostField = field("192.168.1.10:47811", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        hostField.setText(prefs.getString("host", ""));
        laptopCard.addView(hostField, lpm(-1, dp(48), 6));
        container.addView(laptopCard, lpm(-1, -2, 18));

        // ---- pairing code card
        LinearLayout codeCard = card();
        codeCard.addView(sectionTitle("Код с ноутбука"));
        codeCard.addView(text("FIDEXE на ноутбуке → Настройки → «Телефон». "
                + "Шесть цифр меняются каждую минуту.", MUTED, 12, false), lpm(-1, -2, 6));
        codeField = field("000 000", InputType.TYPE_CLASS_NUMBER);
        codeField.setTextSize(TypedValue.COMPLEX_UNIT_SP, 24);
        codeField.setLetterSpacing(0.28f);
        codeField.setGravity(Gravity.CENTER);
        codeCard.addView(codeField, lpm(-1, dp(62), 12));
        codeButton = button("Войти по коду", true);
        codeButton.setOnClickListener(v -> doConnectWithCode());
        codeCard.addView(codeButton, lpm(-1, dp(52), 10));
        container.addView(codeCard, lpm(-1, -2, 14));

        // ---- account card (fallback)
        LinearLayout accountCard = card();
        accountCard.addView(sectionTitle("Или по почте и паролю"));
        accountCard.addView(text("Тот же аккаунт, что на ноутбуке — если код под рукой не оказалось.",
                MUTED, 12, false), lpm(-1, -2, 6));
        emailField = field("you@mail.ru", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        emailField.setText(email);
        accountCard.addView(emailField, lpm(-1, dp(48), 12));
        passwordField = field("Пароль", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        accountCard.addView(passwordField, lpm(-1, dp(48), 10));
        connectButton = button("Войти с паролем", false);
        connectButton.setOnClickListener(v -> doConnect());
        accountCard.addView(connectButton, lpm(-1, dp(48), 12));
        accountCard.addView(text("Пароль не передаётся на ноутбук: телефон доказывает его знание HMAC-подписью.",
                FAINT, 11, false), lpm(-1, -2, 10));
        container.addView(accountCard, lpm(-1, -2, 14));

        errorLabel = text("", DANGER, 12, false);
        errorLabel.setVisibility(View.GONE);
        container.addView(errorLabel, lpm(-1, -2, 12));

        container.addView(text("Работает только в локальной сети: данные идут напрямую с телефона "
                + "на ноутбук, интернет не нужен.", FAINT, 11, false), lpm(-1, -2, 16));
        container.addView(text("FIDEXE Remote 2.1.0", FAINT, 11, false), lpm(-1, -2, 8));
    }

    private void startDiscovery() {
        if (discovery != null) {
            discovery.stop();
            discovery = null;
        }
        foundBox.removeAllViews();
        foundBox.addView(text("Ищу ноутбук в этой сети…", MUTED, 12, false));
        discoverButton.setEnabled(false);
        discovery = new Discovery(this, new Discovery.Listener() {
            @Override
            public void onFound(String name, String address) {
                foundBox.removeAllViews();
                foundBox.addView(foundRow(name, address));
                hostField.setText(address);
            }

            @Override
            public void onFinished() {
                discoverButton.setEnabled(true);
                if (foundBox.getChildCount() == 0) {
                    foundBox.addView(text("Ноутбук не найден. Проверьте, что FIDEXE запущен и вы вошли "
                            + "в аккаунт по почте, а устройства в одной Wi-Fi сети.", MUTED, 12, false));
                }
            }

            @Override
            public void onError(String message) {
                discoverButton.setEnabled(true);
                foundBox.removeAllViews();
                foundBox.addView(text(message, MUTED, 12, false));
            }
        });
        discovery.start(6000);
    }

    private View foundRow(String name, String address) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setBackground(roundedStroke(CARD_ALT, 12, BORDER));
        row.setPadding(dp(12), dp(10), dp(12), dp(10));
        row.setClickable(true);

        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.ic_monitor);
        icon.setColorFilter(ACCENT);
        LinearLayout.LayoutParams iconParams = new LinearLayout.LayoutParams(dp(20), dp(20));
        iconParams.rightMargin = dp(10);
        row.addView(icon, iconParams);

        LinearLayout texts = new LinearLayout(this);
        texts.setOrientation(LinearLayout.VERTICAL);
        texts.addView(text(name == null || name.isEmpty() ? "Ноутбук" : name, TEXT, 13, true));
        texts.addView(text(address, MUTED, 11, false));
        row.addView(texts, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        row.setOnClickListener(v -> {
            hostField.setText(address);
            Toast.makeText(this, "Ноутбук выбран", Toast.LENGTH_SHORT).show();
        });
        return row;
    }

    private void doConnectWithCode() {
        String raw = hostField.getText().toString().trim();
        final String code = codeField.getText().toString().replaceAll("[^0-9]", "");
        if (raw.isEmpty()) {
            showError("Найдите ноутбук в Wi-Fi или введите адрес");
            return;
        }
        if (!raw.contains(":")) {
            raw = raw + ":" + Api.DEFAULT_PORT;
        }
        if (code.length() != 6) {
            showError("Код с ноутбука — ровно 6 цифр");
            return;
        }
        final String target = raw;
        hideKeyboard();
        setConnectBusy(true);
        showError("");
        io.execute(() -> {
            try {
                String device = (Build.MANUFACTURER + " " + Build.MODEL).trim();
                JSONObject auth = Api.pair(target, code, device);
                final String newToken = auth.getString("token");
                final String name = auth.optString("host", "Ноутбук");
                final String mail = auth.optString("account", email);
                ui.post(() -> {
                    setConnectBusy(false);
                    onConnected(target, newToken, name, mail);
                });
            } catch (Exception exc) {
                ui.post(() -> {
                    setConnectBusy(false);
                    showError(describe(exc));
                });
            }
        });
    }

    private void onConnected(String target, String newToken, String name, String mail) {
        host = target;
        token = newToken;
        email = mail;
        laptopName = name;
        prefs.edit()
                .putString("host", host)
                .putString("token", token)
                .putString("email", email)
                .putString("laptop", laptopName)
                .apply();
        showControlScreen();
    }

    private void doConnect() {
        String raw = hostField.getText().toString().trim();
        final String mail = emailField.getText().toString().trim();
        final String password = passwordField.getText().toString();
        if (raw.isEmpty()) {
            showError("Найдите ноутбук в Wi-Fi или введите адрес");
            return;
        }
        if (!raw.contains(":")) {
            raw = raw + ":" + Api.DEFAULT_PORT;
        }
        if (mail.isEmpty() || password.isEmpty()) {
            showError("Введите почту и пароль");
            return;
        }
        final String target = raw;
        hideKeyboard();
        setConnectBusy(true);
        showError("");
        io.execute(() -> {
            try {
                JSONObject info = Api.info(target);
                JSONObject challenge = Api.challenge(target, mail);
                String salt = challenge.getString("salt");
                int iterations = challenge.optInt("iterations", 240000);
                String challengeValue = challenge.getString("challenge");
                byte[] hash = Api.pbkdf2(password, Api.unhex(salt), iterations);
                String proof = Api.hmacHex(hash, challengeValue);
                String device = (Build.MANUFACTURER + " " + Build.MODEL).trim();
                JSONObject auth = Api.proof(target, mail, challengeValue, proof, device);
                final String newToken = auth.getString("token");
                final String name = info.optString("host", "Ноутбук");
                ui.post(() -> {
                    setConnectBusy(false);
                    onConnected(target, newToken, name, mail);
                });
            } catch (Exception exc) {
                ui.post(() -> {
                    setConnectBusy(false);
                    showError(describe(exc));
                });
            }
        });
    }

    // -------------------------------------------------------- control screen
    private void showControlScreen() {
        screen = "control";
        stopCamera();
        container.removeAllViews();
        addBrandHeader();

        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);

        LinearLayout names = new LinearLayout(this);
        names.setOrientation(LinearLayout.VERTICAL);
        laptopLabel = text(laptopName, TEXT, 20, true);
        names.addView(laptopLabel);
        addressLine = text(host, FAINT, 11, false);
        names.addView(addressLine);
        head.addView(names, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        TextView disconnect = text("Отключиться", ACCENT, 12, true);
        disconnect.setPadding(dp(10), dp(8), dp(4), dp(8));
        disconnect.setOnClickListener(v -> disconnectLaptop());
        head.addView(disconnect);
        container.addView(head, lpm(-1, -2, 16));

        // status
        LinearLayout statusCard = card();
        LinearLayout statusRow = new LinearLayout(this);
        statusRow.setOrientation(LinearLayout.HORIZONTAL);
        statusRow.setGravity(Gravity.CENTER_VERTICAL);
        statusLine = text("●  Проверяю связь…", MUTED, 13, true);
        statusRow.addView(statusLine, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        statusCard.addView(statusRow);
        container.addView(statusCard, lpm(-1, -2, 12));

        // stats grid
        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams half = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        half.rightMargin = dp(6);
        LinearLayout.LayoutParams halfLeft = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        halfLeft.leftMargin = dp(6);
        timeValue = statCard(row1, "Экран сегодня", "—", half);
        focusValue = statCard(row1, "Сейчас в фокусе", "—", halfLeft);
        container.addView(row1, lpm(-1, -2, 10));

        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams half2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        half2.rightMargin = dp(6);
        LinearLayout.LayoutParams half2l = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        half2l.leftMargin = dp(6);
        clipsValue = statCard(row2, "Буфер обмена", "—", half2);
        trackingValue = statCard(row2, "Трекинг", "—", half2l);
        container.addView(row2, lpm(-1, -2, 8));

        // main action
        lockButton = text("Заблокировать ноутбук", 0xFFFFFFFF, 17, true);
        lockButton.setGravity(Gravity.CENTER);
        lockButton.setCompoundDrawablesWithIntrinsicBounds(R.drawable.ic_lock, 0, 0, 0);
        lockButton.setCompoundDrawablePadding(dp(10));
        lockButton.setBackground(pressable(gradientRounded(ACCENT, ACCENT_DARK, 26)));
        lockButton.setClickable(true);
        lockButton.setOnClickListener(v -> {
            v.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
            runCommand("lock", "Блокирую ноутбук…");
        });
        container.addView(lockButton, lpm(-1, dp(96), 18));

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setGravity(Gravity.CENTER_VERTICAL);

        TextView sleep = actionButton("Спящий режим");
        sleep.setOnClickListener(v -> runCommand("sleep", "Отправляю ноутбук в сон…"));
        LinearLayout.LayoutParams sleepParams = new LinearLayout.LayoutParams(0, dp(50), 1f);
        sleepParams.rightMargin = dp(6);
        actions.addView(sleep, sleepParams);

        pauseButton = actionButton("Пауза трекинга");
        pauseButton.setOnClickListener(v -> runCommand(paused ? "resume" : "pause",
                paused ? "Включаю трекинг…" : "Ставлю трекинг на паузу…"));
        LinearLayout.LayoutParams pauseParams = new LinearLayout.LayoutParams(0, dp(50), 1f);
        pauseParams.leftMargin = dp(6);
        actions.addView(pauseButton, pauseParams);
        container.addView(actions, lpm(-1, -2, 10));

        LinearLayout extras = new LinearLayout(this);
        extras.setOrientation(LinearLayout.HORIZONTAL);
        extras.setGravity(Gravity.CENTER_VERTICAL);

        TextView cameraButton = actionButton("Камера ноутбука");
        cameraButton.setOnClickListener(v -> showCameraScreen());
        LinearLayout.LayoutParams cameraParams = new LinearLayout.LayoutParams(0, dp(50), 1f);
        cameraParams.rightMargin = dp(6);
        extras.addView(cameraButton, cameraParams);

        TextView appsButton = actionButton("Приложения");
        appsButton.setOnClickListener(v -> showAppsScreen());
        LinearLayout.LayoutParams appsParams = new LinearLayout.LayoutParams(0, dp(50), 1f);
        appsParams.leftMargin = dp(6);
        extras.addView(appsButton, appsParams);
        container.addView(extras, lpm(-1, -2, 8));

        logLine = text("", MUTED, 12, false);
        container.addView(logLine, lpm(-1, -2, 14));

        container.addView(text("Команда выполняется сразу после нажатия. Ноутбук и телефон должны "
                + "быть в одной Wi-Fi сети.", FAINT, 11, false), lpm(-1, -2, 16));

        startPolling();
    }

    private TextView statCard(LinearLayout parent, String caption, String value, LinearLayout.LayoutParams params) {
        LinearLayout card = card();
        card.addView(text(caption, MUTED, 11, false));
        TextView valueView = text(value, TEXT, 19, true);
        valueView.setMaxLines(2);
        card.addView(valueView, lpm(-1, -2, 4));
        parent.addView(card, params);
        return valueView;
    }

    // ------------------------------------------------------------- polling
    private void startPolling() {
        stopPolling();
        pollTask = new Runnable() {
            @Override
            public void run() {
                final String currentHost = host;
                final String currentToken = token;
                if (currentHost.isEmpty() || currentToken.isEmpty()) {
                    return;
                }
                io.execute(() -> {
                    try {
                        JSONObject status = Api.status(currentHost, currentToken);
                        ui.post(() -> applyStatus(status));
                    } catch (Exception exc) {
                        ui.post(() -> {
                            if (statusLine != null) {
                                statusLine.setText("●  Нет связи");
                                statusLine.setTextColor(DANGER);
                            }
                            if (isAuthError(exc)) {
                                disconnectLaptop();
                                showConnectScreen();
                                showError("Сессия истекла — войдите заново");
                                return;
                            }
                        });
                    }
                    ui.postDelayed(pollTask, POLL_MS);
                });
            }
        };
        ui.post(pollTask);
    }

    private void stopPolling() {
        if (pollTask != null) {
            ui.removeCallbacks(pollTask);
            pollTask = null;
        }
    }

    private void applyStatus(JSONObject status) {
        if (statusLine == null) {
            return;
        }
        laptopName = status.optString("host", laptopName);
        laptopLabel.setText(laptopName);
        statusLine.setText("●  На связи");
        statusLine.setTextColor(MINT);
        timeValue.setText(Api.humanDuration(status.optLong("today_seconds", 0)));

        String app = status.optString("current_app", "");
        String title = status.optString("current_title", "");
        if (app.isEmpty()) {
            focusValue.setText("—");
        } else {
            focusValue.setText(app.replace(".exe", ""));
            focusValue.setTextColor(TEXT);
        }
        if (!title.isEmpty()) {
            addressLine.setText(title.length() > 46 ? title.substring(0, 46) + "…" : title);
        } else {
            addressLine.setText(host);
        }
        clipsValue.setText(status.optInt("clip_count", 0) + " записей");
        paused = status.optBoolean("paused", false);
        trackingValue.setText(paused ? "Пауза" : "Активен");
        trackingValue.setTextColor(paused ? WARN : MINT);
        pauseButton.setText(paused ? "Включить трекинг" : "Пауза трекинга");
    }

    // -------------------------------------------------------- camera screen
    private View screenHeader(String title, String action, Runnable onAction) {
        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);

        TextView back = text("‹  Назад", ACCENT, 13, true);
        back.setPadding(dp(4), dp(8), dp(10), dp(8));
        back.setClickable(true);
        back.setOnClickListener(v -> {
            v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);
            showControlScreen();
        });
        head.addView(back);

        TextView label = text(title, TEXT, 16, true);
        LinearLayout.LayoutParams labelParams = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        labelParams.leftMargin = dp(8);
        head.addView(label, labelParams);

        if (action != null) {
            TextView button = text(action, ACCENT, 12, true);
            button.setPadding(dp(10), dp(8), dp(4), dp(8));
            button.setClickable(true);
            button.setOnClickListener(v -> onAction.run());
            head.addView(button);
        }
        return head;
    }

    private void showCameraScreen() {
        screen = "camera";
        stopPolling();
        stopCamera();
        container.removeAllViews();
        addBrandHeader();
        container.addView(screenHeader("Камера ноутбука", "Стоп", this::showControlScreen), lpm(-1, -2, 12));

        cameraStatus = text("Включаю камеру на ноутбуке…", MUTED, 12, false);
        container.addView(cameraStatus, lpm(-1, -2, 8));

        FrameLayout frame = new FrameLayout(this);
        frame.setBackground(rounded(0xFF05060A, 18));
        cameraView = new ImageView(this);
        cameraView.setAdjustViewBounds(true);
        cameraView.setScaleType(ImageView.ScaleType.FIT_CENTER);
        cameraView.setMinimumHeight(dp(240));
        frame.addView(cameraView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        container.addView(frame, lpm(-1, -2, 10));

        container.addView(text("Кадры идут напрямую с ноутбука по Wi-Fi. Индикатор камеры на ноутбуке "
                + "горит, пока идёт просмотр; после «Стоп» камера гаснет через несколько секунд.",
                FAINT, 11, false), lpm(-1, -2, 12));

        startCamera();
    }

    private void startCamera() {
        cameraStopped = false;
        cameraTask = new Runnable() {
            @Override
            public void run() {
                if (cameraStopped || cameraView == null || cameraFetching) {
                    return;
                }
                final String currentHost = host;
                final String currentToken = token;
                cameraFetching = true;
                io.execute(() -> {
                    try {
                        byte[] jpeg = Api.frame(currentHost, currentToken);
                        final Bitmap bitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length);
                        ui.post(() -> {
                            cameraFetching = false;
                            if (cameraStopped) {
                                return;
                            }
                            if (bitmap == null) {
                                if (cameraStatus != null) {
                                    cameraStatus.setText("Не удалось декодировать кадр");
                                }
                            } else {
                                if (cameraView != null) {
                                    cameraView.setImageBitmap(bitmap);
                                }
                                if (cameraStatus != null) {
                                    cameraStatus.setText("●  Смотрю камеру · " + bitmap.getWidth()
                                            + "×" + bitmap.getHeight());
                                    cameraStatus.setTextColor(MINT);
                                }
                            }
                            ui.postDelayed(cameraTask, 400);
                        });
                    } catch (Exception exc) {
                        ui.post(() -> {
                            cameraFetching = false;
                            if (cameraStopped) {
                                return;
                            }
                            if (cameraStatus != null) {
                                cameraStatus.setText(describe(exc));
                                cameraStatus.setTextColor(DANGER);
                            }
                            if (isAuthError(exc)) {
                                stopCamera();
                                showConnectScreen();
                                showError("Сессия истекла — войдите заново");
                                return;
                            }
                            ui.postDelayed(cameraTask, 2000);
                        });
                    }
                });
            }
        };
        ui.post(cameraTask);
    }

    private void stopCamera() {
        cameraStopped = true;
        cameraFetching = false;
        if (cameraTask != null) {
            ui.removeCallbacks(cameraTask);
            cameraTask = null;
        }
        cameraView = null;
        cameraStatus = null;
    }

    // ---------------------------------------------------------- apps screen
    private void showAppsScreen() {
        screen = "apps";
        stopPolling();
        stopCamera();
        container.removeAllViews();
        addBrandHeader();
        container.addView(screenHeader("Приложения", "Обновить", this::loadApps), lpm(-1, -2, 12));

        appsStatus = text("Смотрю, что открыто на ноутбуке…", MUTED, 12, false);
        container.addView(appsStatus, lpm(-1, -2, 8));

        appsList = new LinearLayout(this);
        appsList.setOrientation(LinearLayout.VERTICAL);
        container.addView(appsList, lpm(-1, -2, 6));

        container.addView(text("Закрытие работает как крестик в окне: программа получит запрос "
                + "и сможет предложить сохранить файл. Системные процессы Windows закрыть нельзя.",
                FAINT, 11, false), lpm(-1, -2, 14));

        loadApps();
    }

    private void loadApps() {
        if (appsStatus == null || appsList == null) {
            return;
        }
        appsStatus.setText("Обновляю список…");
        appsStatus.setTextColor(MUTED);
        final String currentHost = host;
        final String currentToken = token;
        io.execute(() -> {
            try {
                JSONObject response = Api.apps(currentHost, currentToken);
                ui.post(() -> renderApps(response));
            } catch (Exception exc) {
                ui.post(() -> {
                    if (appsStatus != null) {
                        appsStatus.setText(describe(exc));
                        appsStatus.setTextColor(DANGER);
                    }
                    if (isAuthError(exc)) {
                        showConnectScreen();
                        showError("Сессия истекла — войдите заново");
                    }
                });
            }
        });
    }

    private void renderApps(JSONObject response) {
        if (appsList == null || appsStatus == null) {
            return;
        }
        appsList.removeAllViews();
        JSONArray apps = response.optJSONArray("apps");
        boolean supported = response.optBoolean("supported", true);
        if (apps == null || apps.length() == 0) {
            appsStatus.setText("На ноутбуке нет открытых приложений с окнами");
            appsStatus.setTextColor(MUTED);
            return;
        }
        appsStatus.setText(supported
                ? apps.length() + " приложений открыто · нажмите «Закрыть», чтобы убрать"
                : "Список открыт, но закрывать приложения может только Windows-версия");
        appsStatus.setTextColor(MUTED);
        for (int index = 0; index < apps.length(); index++) {
            JSONObject app = apps.optJSONObject(index);
            if (app == null) {
                continue;
            }
            appsList.addView(appRow(app, supported), lpm(-1, -2, 8));
        }
    }

    private View appRow(JSONObject app, boolean canClose) {
        final int pid = app.optInt("pid", 0);
        String name = app.optString("app", "приложение");
        String title = app.optString("title", "");
        boolean active = app.optBoolean("active", false);

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setBackground(roundedStroke(CARD, 14, active ? ACCENT : BORDER));
        row.setPadding(dp(14), dp(12), dp(12), dp(12));

        LinearLayout texts = new LinearLayout(this);
        texts.setOrientation(LinearLayout.VERTICAL);
        TextView nameView = text(name, TEXT, 14, true);
        texts.addView(nameView);
        if (!title.isEmpty()) {
            TextView titleView = text(title, MUTED, 11, false);
            titleView.setMaxLines(2);
            titleView.setEllipsize(android.text.TextUtils.TruncateAt.END);
            texts.addView(titleView, lpm(-1, -2, 3));
        }
        texts.addView(text(active ? "●  активное окно" : "pid " + pid, active ? MINT : FAINT, 10, false),
                lpm(-1, -2, 4));
        LinearLayout.LayoutParams textsParams = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        textsParams.rightMargin = dp(10);
        row.addView(texts, textsParams);

        TextView close = text("Закрыть", canClose ? DANGER : FAINT, 12, true);
        close.setGravity(Gravity.CENTER);
        close.setPadding(dp(12), dp(9), dp(12), dp(9));
        close.setBackground(roundedStroke(CARD_ALT, 10, BORDER));
        close.setClickable(canClose);
        close.setOnClickListener(v -> {
            v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);
            close.setText("Закрываю…");
            close.setTextColor(MUTED);
            final String currentHost = host;
            final String currentToken = token;
            io.execute(() -> {
                try {
                    Api.closeApp(currentHost, currentToken, pid);
                    ui.post(() -> {
                        Toast.makeText(this, "Закрыто: " + name, Toast.LENGTH_SHORT).show();
                        loadApps();
                    });
                } catch (Exception exc) {
                    ui.post(() -> {
                        close.setText("Закрыть");
                        close.setTextColor(DANGER);
                        Toast.makeText(this, describe(exc), Toast.LENGTH_LONG).show();
                    });
                }
            });
        });
        row.addView(close);

        LinearLayout wrapper = new LinearLayout(this);
        wrapper.setOrientation(LinearLayout.VERTICAL);
        wrapper.addView(row);
        return wrapper;
    }

    // ------------------------------------------------------------- actions
    private void runCommand(final String cmd, final String message) {
        log(message);
        final String currentHost = host;
        final String currentToken = token;
        io.execute(() -> {
            try {
                boolean ok = Api.command(currentHost, currentToken, cmd);
                ui.post(() -> {
                    log(ok ? message.replace("…", " — готово") : "Ноутбук не подтвердил команду");
                    if (lockButton != null) {
                        lockButton.postDelayed(this::refreshOnce, 1200);
                    }
                });
            } catch (Exception exc) {
                ui.post(() -> {
                    log(describe(exc));
                    if (isAuthError(exc)) {
                        disconnectLaptop();
                        showConnectScreen();
                        showError("Сессия истекла — войдите заново");
                    }
                });
            }
        });
    }

    private void refreshOnce() {
        final String currentHost = host;
        final String currentToken = token;
        if (currentHost.isEmpty() || currentToken.isEmpty() || statusLine == null) {
            return;
        }
        io.execute(() -> {
            try {
                JSONObject status = Api.status(currentHost, currentToken);
                ui.post(() -> applyStatus(status));
            } catch (Exception ignored) {
            }
        });
    }

    private void log(String message) {
        if (logLine != null) {
            logLine.setText(message);
        }
    }

    private void disconnectLaptop() {
        stopPolling();
        token = "";
        prefs.edit().remove("token").apply();
        if (statusLine != null) {
            statusLine.setText("●  Отключено");
            statusLine.setTextColor(MUTED);
        }
        showConnectScreen();
    }

    // --------------------------------------------------------------- helpers
    private void addBrandHeader() {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);

        TextView logo = text("F", 0xFFFFFFFF, 16, true);
        logo.setGravity(Gravity.CENTER);
        logo.setBackground(rounded(ACCENT, 10));
        row.addView(logo, new LinearLayout.LayoutParams(dp(32), dp(32)));

        TextView name = text("FIDEXE", TEXT, 18, true);
        name.setLetterSpacing(0.14f);
        LinearLayout.LayoutParams nameParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        nameParams.leftMargin = dp(10);
        row.addView(name, nameParams);

        TextView badge = text("REMOTE", ACCENT, 10, true);
        badge.setGravity(Gravity.CENTER);
        badge.setBackground(rounded(ACCENT_SOFT, 8));
        badge.setPadding(dp(8), dp(3), dp(8), dp(3));
        LinearLayout.LayoutParams badgeParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        badgeParams.leftMargin = dp(8);
        row.addView(badge, badgeParams);

        row.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));

        TextView help = text("?", MUTED, 14, true);
        help.setGravity(Gravity.CENTER);
        help.setBackground(roundedStroke(CARD_ALT, 16, BORDER));
        help.setClickable(true);
        help.setOnClickListener(v -> showHelp());
        row.addView(help, new LinearLayout.LayoutParams(dp(32), dp(32)));

        container.addView(row);
    }

    private void showHelp() {
        AlertDialog.Builder builder = new AlertDialog.Builder(
                this, android.R.style.Theme_Material_Dialog_Alert);
        builder.setTitle("Как это работает");
        builder.setMessage("1. Запустите FIDEXE на ноутбуке и войдите по почте — сервер для телефона "
                + "стартует сам.\n\n"
                + "2. Телефон и ноутбук должны быть в одной Wi-Fi сети.\n\n"
                + "3. На телефоне нажмите «Найти ноутбук в Wi-Fi» или введите адрес "
                + "вида 192.168.1.10:47811.\n\n"
                + "4. На ноутбуке: Настройки → «Телефон» — там шесть цифр, "
                + "они меняются каждую минуту.\n\n"
                + "5. Введите эти цифры на телефоне и нажмите «Войти по коду» — откроется пульт. "
                + "Можно войти и почтой с паролем того же аккаунта.\n\n"
                + "6. Кнопка «Заблокировать ноутбук» сразу блокирует экран компьютера.\n\n"
                + "Код живёт минуту и работает только в вашей Wi-Fi сети; сервер не выходит в интернет.");
        builder.setPositiveButton("Понятно", null);
        builder.show();
    }

    private void showError(String message) {
        if (errorLabel == null) {
            if (!message.isEmpty()) {
                Toast.makeText(this, message, Toast.LENGTH_LONG).show();
            }
            return;
        }
        if (message.isEmpty()) {
            errorLabel.setVisibility(View.GONE);
        } else {
            errorLabel.setText(message);
            errorLabel.setVisibility(View.VISIBLE);
        }
    }

    private void setConnectBusy(boolean busy) {
        connectButton.setEnabled(!busy);
        connectButton.setText(busy ? "Подключаюсь…" : "Войти с паролем");
        if (codeButton != null) {
            codeButton.setEnabled(!busy);
            codeButton.setText(busy ? "Подключаюсь…" : "Войти по коду");
            codeButton.setAlpha(busy ? 0.6f : 1f);
        }
        connectButton.setAlpha(busy ? 0.6f : 1f);
    }

    private void hideKeyboard() {
        View focus = getCurrentFocus();
        if (focus != null) {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                imm.hideSoftInputFromWindow(focus.getWindowToken(), 0);
            }
        }
    }

    private static boolean isAuthError(Exception exc) {
        String message = describe(exc).toLowerCase();
        return message.contains("сессия") || message.contains("авторизация");
    }

    private static String describe(Exception exc) {
        String message = exc.getMessage();
        if (message == null || message.isEmpty()) {
            return "Не удалось выполнить запрос";
        }
        return message;
    }

    // ------------------------------------------------------------ view utils
    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private TextView text(String value, int color, float sizeSp, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextColor(color);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp);
        view.setLineSpacing(dp(2), 1f);
        if (bold) {
            view.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        }
        return view;
    }

    private TextView sectionTitle(String value) {
        TextView view = text(value, TEXT, 13, true);
        view.setLetterSpacing(0.02f);
        return view;
    }

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(roundedStroke(CARD, 18, BORDER));
        card.setPadding(dp(16), dp(14), dp(16), dp(16));
        return card;
    }

    private EditText field(String hint, int inputType) {
        EditText field = new EditText(this);
        field.setHint(hint);
        field.setHintTextColor(FAINT);
        field.setTextColor(TEXT);
        field.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        field.setInputType(inputType);
        field.setSingleLine(true);
        field.setBackground(roundedStroke(CARD_ALT, 12, BORDER));
        field.setPadding(dp(14), dp(12), dp(14), dp(12));
        return field;
    }

    private TextView button(String caption, boolean primary) {
        TextView view = text(caption, primary ? 0xFFFFFFFF : TEXT, 14, true);
        view.setGravity(Gravity.CENTER);
        view.setClickable(true);
        if (primary) {
            view.setBackground(pressable(gradientRounded(ACCENT, ACCENT_DARK, 16)));
        } else {
            view.setBackground(pressable(roundedStroke(CARD_ALT, 12, BORDER)));
        }
        return view;
    }

    private TextView actionButton(String caption) {
        TextView view = text(caption, TEXT, 13, true);
        view.setGravity(Gravity.CENTER);
        view.setClickable(true);
        view.setBackground(pressable(roundedStroke(CARD_ALT, 14, BORDER)));
        return view;
    }

    private GradientDrawable rounded(int color, int radiusDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radiusDp));
        return drawable;
    }

    private GradientDrawable roundedStroke(int color, int radiusDp, int strokeColor) {
        GradientDrawable drawable = rounded(color, radiusDp);
        drawable.setStroke(dp(1), strokeColor);
        return drawable;
    }

    private GradientDrawable gradientRounded(int from, int to, int radiusDp) {
        GradientDrawable drawable = new GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT, new int[]{from, to});
        drawable.setCornerRadius(dp(radiusDp));
        return drawable;
    }

    private Drawable pressable(Drawable normal) {
        StateListDrawable states = new StateListDrawable();
        Drawable pressed = normal.getConstantState() != null
                ? normal.getConstantState().newDrawable().mutate()
                : normal;
        pressed.setAlpha(190);
        states.addState(new int[]{android.R.attr.state_pressed}, pressed);
        states.addState(new int[]{}, normal);
        return states;
    }

    private LinearLayout.LayoutParams lpm(int widthDp, int heightPx, int topMarginDp) {
        int width = widthDp < 0 ? widthDp : dp(widthDp);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(width, heightPx);
        params.topMargin = dp(topMarginDp);
        return params;
    }
}
