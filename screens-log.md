# emulator UI test log

devices: List of devices attached emulator-5554	offline  

## gradle
Note: Some input files use or override a deprecated API.
Note: Recompile with -Xlint:deprecation for details.

## mock desktop
[mock] FIDEXE desktop API on 0.0.0.0:47811 (demo@fidexe.app / demo-pass-123, code 685688)
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
+ echo '- время (UTC): 2026-11-28 08:26'
+ echo '- коммит: 4698ff1127baa0ded4a20f49e54bf101fb83c20c'
++ '[' 1 -eq 0 ']'
++ echo 'есть провалы'
+ echo '- итог: есть провалы'
+ echo
+ cat /tmp/checks.txt
+ echo
+ echo '## Скриншоты в папке'
+ echo
+ ls -1 docs/android
+ sed 's/^/- /'
+ echo '== the laptop is far away: internet relay =='
== the laptop is far away: internet relay ==
+ adb logcat -d -s FIDEXE
++ grep -c relay: /tmp/app-relay-before.log
+ note 'интернет-канал перед отключением Wi-Fi: 4 строк лога'
+ echo 'интернет-канал перед отключением Wi-Fi: 4 строк лога'
интернет-канал перед отключением Wi-Fi: 4 строк лога
+ echo '- интернет-канал перед отключением Wi-Fi: 4 строк лога'
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
+ relay_lock=
+ attempt=1
+ '[' 1 -le 3 ']'
+ '[' -z '' ']'
+ python3 tools/android_ui.py tap-text 'Заблокировать ноутбук'
tap-text Заблокировать ноутбук ok
+ waited=0
+ '[' 0 -lt 45 ']'
+ sleep 3
+ waited=3
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ relay_lock=yes
+ break
+ attempt=2
+ '[' 2 -le 3 ']'
+ '[' -z yes ']'
+ take_shot relay.png
+ python3 tools/android_ui.py shot docs/android/relay.png
saved docs/android/relay.png 229108 bytes
+ note 'screenshot: relay.png'
+ echo 'screenshot: relay.png'
screenshot: relay.png
+ echo '- screenshot: relay.png'
+ adb logcat -d -s FIDEXE
+ python3 tools/android_ui.py dump
+ '[' -n yes ']'
+ note 'блокировка через интернет (публичный брокер, E2E-шифрование) — дошла'
+ echo 'блокировка через интернет (публичный брокер, E2E-шифрование) — дошла'
блокировка через интернет (публичный брокер, E2E-шифрование) — дошла
+ echo '- блокировка через интернет (публичный брокер, E2E-шифрование) — дошла'
+ grep -q 'через интернет' /tmp/ui-relay.txt
+ note 'пульт сам переключился на интернет-канал'
+ echo 'пульт сам переключился на интернет-канал'
пульт сам переключился на интернет-канал
+ echo '- пульт сам переключился на интернет-канал'
+ cp /tmp/relay.log docs/android/relay-host.txt
+ cp /tmp/app-relay.log docs/android/app-relay.txt
+ cp /tmp/app-relay-before.log docs/android/app-relay-before.txt
+ cp /tmp/ui-relay.txt docs/android/ui-relay.txt
+ grep -q 'Интернет-канал: готов' /tmp/ui-relay.txt
+ note 'пульт показывает готовый интернет-канал'
+ echo 'пульт показывает готовый интернет-канал'
пульт показывает готовый интернет-канал
+ echo '- пульт показывает готовый интернет-канал'
+ grep -q 'Интернет-канал: ' /tmp/ui-relay.txt
++ grep -o 'Интернет-канал: [^<]*' /tmp/ui-relay.txt
++ head -1
+ note 'состояние канала на экране: Интернет-канал: готов (broker.hivemq.com:8883)'\'''
+ echo 'состояние канала на экране: Интернет-канал: готов (broker.hivemq.com:8883)'\'''
состояние канала на экране: Интернет-канал: готов (broker.hivemq.com:8883)'
+ echo '- состояние канала на экране: Интернет-канал: готов (broker.hivemq.com:8883)'\'''
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
TextView       (99, 594, 981, 652) clickable=False text='Интернет-канал: готов (broker.hivemq.com:8883)'
TextView       (99, 763, 479, 804) clickable=False text='Экран сегодня'
TextView       (99, 815, 479, 886) clickable=False text='4 ч 24 мин'
TextView       (601, 763, 981, 804) clickable=False text='Сейчас в фокусе'
TextView       (601, 815, 981, 886) clickable=False text='chrome'
TextView       (99, 991, 479, 1032) clickable=False text='Буфер обмена'
TextView       (99, 1043, 479, 1114) clickable=False text='42 записей'
TextView       (601, 991, 981, 1032) clickable=False text='Трекинг'
TextView       (601, 1043, 981, 1114) clickable=False text='Активен'
TextView       (55, 1208, 1025, 1472) clickable=True text='Заблокировать ноутбук'
TextView       (55, 1500, 523, 1638) clickable=True text='Спящий режим'
TextView       (557, 1500, 1025, 1638) clickable=True text='Пауза трекинга'
TextView       (55, 1660, 523, 1798) clickable=True text='Камера ноутбука'
TextView       (557, 1660, 1025, 1798) clickable=True text='Приложения'
TextView       (55, 1837, 1025, 1881) clickable=False text='Интернет-связь готова: broker.hivemq.com:8883'
TextView       (55, 1925, 1025, 2007) clickable=False text='Команда выполняется сразу после нажатия. Ноутбук и телефон должны быть в одной Wi-Fi сети.'

## logcat (app)
