# emulator UI test log

devices: List of devices attached emulator-5554	offline  

## mock desktop
[mock] FIDEXE desktop API on 0.0.0.0:47811 (demo@fidexe.app / demo-pass-123, code 589793)
[mock] "GET /api/info HTTP/1.1" 200 -
[mock] "GET /api/demo/code HTTP/1.1" 200 -
[mock] phone paired with code: unknown Android SDK built for x86_64
[mock] "POST /api/pair HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/apps HTTP/1.1" 200 -
[mock] CLOSE APP: chrome.exe 101
[mock] "POST /api/apps/close HTTP/1.1" 200 -
[mock] "GET /api/apps HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] LOCK COMMAND RECEIVED
[mock] "POST /api/command HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/state HTTP/1.1" 200 -
[mock] "GET /api/state HTTP/1.1" 200 -

## flow log
[mock] phone paired with code: unknown Android SDK built for x86_64
[mock] "POST /api/pair HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/apps HTTP/1.1" 200 -
[mock] CLOSE APP: chrome.exe 101
[mock] "POST /api/apps/close HTTP/1.1" 200 -
[mock] "GET /api/apps HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/camera/frame HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] LOCK COMMAND RECEIVED
[mock] "POST /api/command HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
+ curl -s --max-time 10 http://127.0.0.1:47811/api/state
{"locked": 1, "commands": ["close_app", "lock"], "closed": [{"pid": 101, "app": "chrome.exe"}], "camera_frames": 15}+ echo

+ grep -q 'phone paired with code' /tmp/mock.log
+ note 'вход по коду принят API ноутбука'
+ echo 'вход по коду принят API ноутбука'
вход по коду принят API ноутбука
+ echo '- вход по коду принят API ноутбука'
+ grep -q 'CLOSE APP' /tmp/mock.log
+ note 'программа закрыта с телефона'
+ echo 'программа закрыта с телефона'
программа закрыта с телефона
+ echo '- программа закрыта с телефона'
++ curl -s --max-time 10 http://127.0.0.1:47811/api/state
++ python3 -c 'import json,sys;print(json.load(sys.stdin).get('\''camera_frames'\'',0))'
+ FRAMES=15
+ '[' 15 -gt 0 ']'
+ note 'кадров камеры получено: 15'
+ echo 'кадров камеры получено: 15'
кадров камеры получено: 15
+ echo '- кадров камеры получено: 15'
+ grep -q 'LOCK COMMAND RECEIVED' /tmp/mock.log
+ note 'команда блокировки дошла до ноутбука'
+ echo 'команда блокировки дошла до ноутбука'
команда блокировки дошла до ноутбука
+ echo '- команда блокировки дошла до ноутбука'
+ echo '# Android UI check — CI report'
+ echo
+ echo 'Собрано автоматически: эмулятор Android, настоящий APK, мок-ноутбук.'
+ echo
++ date -u '+%Y-%m-%d %H:%M'
+ echo '- время (UTC): 2026-11-28 07:58'
+ echo '- коммит: 2d1054bec4a93794e0cc5dc6a9d1445861491b48'
++ '[' 0 -eq 0 ']'
++ echo 'всё зелёное'
+ echo '- итог: всё зелёное'
+ echo
+ cat /tmp/checks.txt
+ echo
+ echo '## Скриншоты в папке'
+ echo
+ ls -1 docs/android
+ sed 's/^/- /'
+ echo '== the laptop is far away: internet relay =='
== the laptop is far away: internet relay ==
+ pkill -f mock_remote.py
+ sleep 2
+ note 'локальная сеть отключена: мок-ноутбук остановлен'
+ echo 'локальная сеть отключена: мок-ноутбук остановлен'
локальная сеть отключена: мок-ноутбук остановлен
+ echo '- локальная сеть отключена: мок-ноутбук остановлен'
+ curl -s --max-time 3 http://127.0.0.1:47811/api/ping
+ note 'локальный адрес 47811 больше не отвечает'
+ echo 'локальный адрес 47811 больше не отвечает'
локальный адрес 47811 больше не отвечает
+ echo '- локальный адрес 47811 больше не отвечает'
+ python3 tools/android_ui.py tap-text 'Заблокировать ноутбук'
tap-text Заблокировать ноутбук ok
+ sleep 18
+ take_shot relay.png
+ python3 tools/android_ui.py shot docs/android/relay.png
saved docs/android/relay.png 232197 bytes
+ note 'screenshot: relay.png'
+ echo 'screenshot: relay.png'
screenshot: relay.png
+ echo '- screenshot: relay.png'
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ step_failed 'блокировка через интернет не дошла'
+ echo 'STEP FAILED: блокировка через интернет не дошла'
STEP FAILED: блокировка через интернет не дошла
+ echo '- FAIL: блокировка через интернет не дошла'
+ STATUS=1
+ tail -n 25 /tmp/relay.log
[relay] 07:55:38 starting, link=ci-rel… brokers=[('broker.hivemq.com', 8883)]
[relay] 07:55:39 READY on broker.hivemq.com:8883
+ python3 tools/android_ui.py dump
+ grep -q 'через интернет' /tmp/ui-relay.txt
+ echo STATUS=1
STATUS=1
+ exit 1

## connect screen dump
TextView       (55, 197, 143, 285) clickable=False text='F'
TextView       (171, 207, 373, 274) clickable=False text='FIDEXE'
TextView       (395, 214, 545, 268) clickable=False text='REMOTE'
TextView       (937, 197, 1025, 285) clickable=True text='?'
TextView       (55, 335, 1025, 506) clickable=False text='Блокировка ноутбука\nс телефона'
TextView       (55, 523, 1025, 619) clickable=False text='Введите 6 цифр из настроек FIDEXE на ноутбуке — и пульт откроется.'
TextView       (99, 708, 981, 756) clickable=False text='Ноутбук'
TextView       (99, 806, 981, 938) clickable=True text='Найти ноутбук в Wi-Fi'
TextView       (99, 977, 981, 1018) clickable=False text='или укажите адрес вручную'
EditText       (99, 1035, 981, 1167) clickable=True text='192.168.1.10:47811'
TextView       (99, 1289, 981, 1337) clickable=False text='Код с ноутбука'
TextView       (99, 1354, 981, 1445) clickable=False text='FIDEXE на ноутбуке → «Настройки» → крупные 6 цифр внизу страницы. Они меняются каждую минуту.'
EditText       (99, 1478, 981, 1649) clickable=True text='000 000'
TextView       (99, 1677, 981, 1820) clickable=True text='Войти по коду'
TextView       (99, 1942, 981, 1990) clickable=False text='Или по почте и паролю'
TextView       (99, 2007, 981, 2072) clickable=False text='Тот же аккаунт, что на ноутбуке — если код под рукой не оказалось.'
EditText       (0, 0, 0, 0) clickable=True text='you@mail.ru'

## control screen dump
TextView       (55, 197, 143, 285) clickable=False text='F'
TextView       (171, 207, 373, 274) clickable=False text='FIDEXE'
TextView       (395, 214, 545, 268) clickable=False text='REMOTE'
TextView       (937, 197, 1025, 285) clickable=True text='?'
TextView       (55, 329, 777, 403) clickable=False text='DESKTOP-DEMO'
TextView       (55, 403, 777, 444) clickable=False text='GitHub — FIDEXE (mock)'
TextView       (777, 342, 1025, 430) clickable=True text='Отключиться'
TextView       (99, 530, 739, 579) clickable=False text='●  На связи · Wi-Fi'
TextView       (739, 516, 981, 594) clickable=True text='Найти заново'
TextView       (99, 705, 479, 746) clickable=False text='Экран сегодня'
TextView       (99, 757, 479, 828) clickable=False text='4 ч 24 мин'
TextView       (601, 705, 981, 746) clickable=False text='Сейчас в фокусе'
TextView       (601, 757, 981, 828) clickable=False text='chrome'
TextView       (99, 933, 479, 974) clickable=False text='Буфер обмена'
TextView       (99, 985, 479, 1056) clickable=False text='42 записей'
TextView       (601, 933, 981, 974) clickable=False text='Трекинг'
TextView       (601, 985, 981, 1056) clickable=False text='Активен'
TextView       (55, 1150, 1025, 1414) clickable=True text='Заблокировать ноутбук'
TextView       (55, 1442, 523, 1580) clickable=True text='Спящий режим'
TextView       (557, 1442, 1025, 1580) clickable=True text='Пауза трекинга'
TextView       (55, 1602, 523, 1740) clickable=True text='Камера ноутбука'
TextView       (557, 1602, 1025, 1740) clickable=True text='Приложения'
TextView       (55, 1779, 1025, 1823) clickable=False text='Интернет-связь готова: broker.hivemq.com:8883'
TextView       (55, 1867, 1025, 1949) clickable=False text='Команда выполняется сразу после нажатия. Ноутбук и телефон должны быть в одной Wi-Fi сети.'

## logcat (app)
