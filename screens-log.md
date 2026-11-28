# emulator UI test log

devices: List of devices attached emulator-5554	offline  

## gradle
Note: Some input files use or override a deprecated API.
Note: Recompile with -Xlint:deprecation for details.

## mock desktop
[mock] FIDEXE desktop API on 0.0.0.0:47811 (demo@fidexe.app / demo-pass-123, code 374105)
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
+ '[' 42 -lt 45 ']'
+ sleep 3
+ waited=45
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 45 -lt 45 ']'
+ attempt=3
+ '[' 3 -le 3 ']'
+ '[' -z '' ']'
+ python3 tools/android_ui.py tap-text 'Заблокировать ноутбук'
tap-text Заблокировать ноутбук NOT FOUND
+ step_failed 'tap lock through the relay'
+ echo 'STEP FAILED: tap lock through the relay'
STEP FAILED: tap lock through the relay
+ echo '- FAIL: tap lock through the relay'
+ STATUS=1
+ waited=0
+ '[' 0 -lt 45 ']'
+ sleep 3
+ waited=3
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 3 -lt 45 ']'
+ sleep 3
+ waited=6
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 6 -lt 45 ']'
+ sleep 3
+ waited=9
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 9 -lt 45 ']'
+ sleep 3
+ waited=12
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 12 -lt 45 ']'
+ sleep 3
+ waited=15
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 15 -lt 45 ']'
+ sleep 3
+ waited=18
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 18 -lt 45 ']'
+ sleep 3
+ waited=21
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 21 -lt 45 ']'
+ sleep 3
+ waited=24
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 24 -lt 45 ']'
+ sleep 3
+ waited=27
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 27 -lt 45 ']'
+ sleep 3
+ waited=30
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 30 -lt 45 ']'
+ sleep 3
+ waited=33
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 33 -lt 45 ']'
+ sleep 3
+ waited=36
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 36 -lt 45 ']'
+ sleep 3
+ waited=39
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 39 -lt 45 ']'
+ sleep 3
+ waited=42
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 42 -lt 45 ']'
+ sleep 3
+ waited=45
+ grep -q 'LOCK COMMAND RECEIVED OVER THE INTERNET' /tmp/relay.log
+ '[' 45 -lt 45 ']'
+ attempt=4
+ '[' 4 -le 3 ']'
+ take_shot relay.png
+ python3 tools/android_ui.py shot docs/android/relay.png
saved docs/android/relay.png 192999 bytes
+ note 'screenshot: relay.png'
+ echo 'screenshot: relay.png'
screenshot: relay.png
+ echo '- screenshot: relay.png'
+ adb logcat -d -s FIDEXE
+ python3 tools/android_ui.py dump
+ '[' -n '' ']'
+ step_failed 'блокировка через интернет не дошла'
+ echo 'STEP FAILED: блокировка через интернет не дошла'
STEP FAILED: блокировка через интернет не дошла
+ echo '- FAIL: блокировка через интернет не дошла'
+ STATUS=1
+ tail -n 15 /tmp/relay.log
[relay] 08:19:07 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:19:17 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:19:27 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:19:38 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:19:48 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:19:58 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:20:08 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:20:18 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:20:29 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:20:39 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:20:49 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:20:59 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:21:10 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:21:20 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
[relay] 08:21:30 broker test.mosquitto.org:8883 failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)
+ grep -q 'через интернет' /tmp/ui-relay.txt
+ cp /tmp/relay.log docs/android/relay-host.txt
+ cp /tmp/app-relay.log docs/android/app-relay.txt
+ cp /tmp/app-relay-before.log docs/android/app-relay-before.txt
+ cp /tmp/ui-relay.txt docs/android/ui-relay.txt
+ grep -q 'Интернет-канал: готов' /tmp/ui-relay.txt
+ grep -q 'Интернет-канал: ' /tmp/ui-relay.txt
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
