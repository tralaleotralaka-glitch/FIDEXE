#!/usr/bin/env bash
# Drives the FIDEXE Remote APK on the CI emulator: fills the address, logs in
# with the real 6-digit code from the mock desktop and takes the screenshots.
# Runs inside the android-emulator-runner action (adb is already connected).
set -uo pipefail
# keep the whole run in one file so CI can publish it when something fails
exec > >(tee -a /tmp/flow.log) 2>&1
set -x

OUT=docs/android
mkdir -p "$OUT"
CHECKS=/tmp/checks.txt
: > "$CHECKS"

STATUS=0
note() {
    echo "$*"
    echo "- $*" >> "$CHECKS"
}

step_failed() {
    echo "STEP FAILED: $1"
    echo "- FAIL: $1" >> "$CHECKS"
    STATUS=1
}

take_shot() {
    python3 tools/android_ui.py shot "$OUT/$1" || step_failed "shot $1"
    note "screenshot: $1"
}

open_app() {
    adb install -r android/app/build/outputs/apk/release/app-release.apk || step_failed "install"
    adb shell am start -n app.fidexe.remote/.MainActivity || step_failed "start"
    sleep 6
}

echo "== connect screen =="
open_app
take_shot connect.png
python3 tools/android_ui.py dump > /tmp/ui-connect.txt 2>&1 || true

echo "== laptop address =="
python3 tools/android_ui.py tap-edit 0 || step_failed "tap host"
python3 tools/android_ui.py type "10.0.2.2:47811"
python3 tools/android_ui.py hide-keyboard

echo "== pairing code from the mock desktop =="
CODE=$(curl -s --max-time 10 http://127.0.0.1:47811/api/demo/code \
    | python3 -c "import json,sys;print(json.load(sys.stdin)['code'])" 2>/dev/null)
echo "code=$CODE"
if [ -z "${CODE:-}" ]; then
    step_failed "fetch pairing code"
    CODE=000000
fi

python3 tools/android_ui.py tap-edit 1 || step_failed "tap code field"
python3 tools/android_ui.py type "$CODE"
python3 tools/android_ui.py hide-keyboard
take_shot filled.png

echo "== log in with the code =="
python3 tools/android_ui.py tap-text "Войти по коду" || step_failed "tap login"
sleep 10
take_shot control.png
python3 tools/android_ui.py dump > /tmp/ui-control.txt 2>&1 || true

echo "== the phone remembers the laptop after a restart =="
adb shell am force-stop app.fidexe.remote
sleep 1
adb shell am start -n app.fidexe.remote/.MainActivity || step_failed "restart app"
sleep 7
python3 tools/android_ui.py dump > /tmp/ui-relaunch.txt 2>&1 || true
if grep -q "Заблокировать ноутбук" /tmp/ui-relaunch.txt && grep -q "На связи" /tmp/ui-relaunch.txt; then
    note "телефон остался подключён после перезапуска приложения"
else
    step_failed "the app forgot the laptop after a restart"
    head -n 40 /tmp/ui-relaunch.txt || true
fi
take_shot remember.png

echo "== reconnecting when the laptop address changes =="
python3 tools/android_ui.py tap-exact "Найти заново" || step_failed "tap reconnect"
sleep 8
python3 tools/android_ui.py dump > /tmp/ui-reconnect.txt 2>&1 || true
if grep -q "Заблокировать ноутбук" /tmp/ui-reconnect.txt; then
    note "пульт жив после «Найти заново»"
else
    step_failed "reconnect left the app on an empty screen"
    head -n 40 /tmp/ui-reconnect.txt || true
fi

echo "== running apps on the laptop =="
python3 tools/android_ui.py tap-text "Приложения" || step_failed "open apps"
sleep 3
take_shot apps.png
python3 tools/android_ui.py tap-exact "Закрыть" || step_failed "close an app"
sleep 3
take_shot apps-closed.png
adb shell input keyevent 4   # back to the control panel
sleep 2

echo "== laptop camera =="
python3 tools/android_ui.py tap-text "Камера ноутбука" || step_failed "open camera"
sleep 4
take_shot camera.png
python3 tools/android_ui.py tap-exact "Стоп" || step_failed "stop camera"
sleep 2

echo "== lock the laptop =="
python3 tools/android_ui.py tap-text "Заблокировать ноутбук" || step_failed "tap lock"
sleep 5
take_shot locked.png

echo "== mock desktop state =="
cat /tmp/mock.log || true
curl -s --max-time 10 http://127.0.0.1:47811/api/state || true
echo
if grep -q "phone paired with code" /tmp/mock.log; then
    note "вход по коду принят API ноутбука"
else
    step_failed "desktop never accepted the code"
fi
if grep -q "CLOSE APP" /tmp/mock.log; then
    note "программа закрыта с телефона"
else
    step_failed "no close-app request reached the desktop"
fi
FRAMES=$(curl -s --max-time 10 http://127.0.0.1:47811/api/state \
    | python3 -c "import json,sys;print(json.load(sys.stdin).get('camera_frames',0))" 2>/dev/null || echo 0)
if [ "${FRAMES:-0}" -gt 0 ]; then
    note "кадров камеры получено: $FRAMES"
else
    step_failed "the phone never fetched a camera frame"
fi
if grep -q "LOCK COMMAND RECEIVED" /tmp/mock.log; then
    note "команда блокировки дошла до ноутбука"
else
    step_failed "lock command not received"
fi

{
    echo "# Android UI check — CI report"
    echo
    echo "Собрано автоматически: эмулятор Android, настоящий APK, мок-ноутбук."
    echo
    echo "- время (UTC): $(date -u '+%Y-%m-%d %H:%M')"
    echo "- коммит: ${GITHUB_SHA:-local}"
    echo "- итог: $([ "$STATUS" -eq 0 ] && echo 'всё зелёное' || echo 'есть провалы')"
    echo
    cat "$CHECKS"
    echo
    echo "## Скриншоты в папке"
    echo
    ls -1 "$OUT" | sed 's/^/- /'
} > "$OUT/CI-STATUS.md"

echo "== the laptop is far away: internet relay =="
pkill -f mock_remote.py || true
sleep 2
note "локальная сеть отключена: мок-ноутбук остановлен"
curl -s --max-time 3 http://127.0.0.1:47811/api/ping > /dev/null 2>&1 \
    && step_failed "mock laptop is still running" \
    || note "локальный адрес 47811 больше не отвечает"
python3 tools/android_ui.py tap-text "Заблокировать ноутбук" || step_failed "tap lock through the relay"
sleep 18
take_shot relay.png
if grep -q "LOCK COMMAND RECEIVED OVER THE INTERNET" /tmp/relay.log 2>/dev/null; then
    note "блокировка через интернет (публичный брокер, E2E-шифрование) — дошла"
else
    step_failed "блокировка через интернет не дошла"
    tail -n 25 /tmp/relay.log 2>/dev/null || true
fi
python3 tools/android_ui.py dump > /tmp/ui-relay.txt 2>&1 || true
if grep -q "через интернет" /tmp/ui-relay.txt; then
    note "пульт сам переключился на интернет-канал"
fi

echo "STATUS=$STATUS"
exit "$STATUS"
