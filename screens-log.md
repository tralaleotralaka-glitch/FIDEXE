# emulator UI test log

devices: List of devices attached emulator-5554	offline  

## mock desktop
[mock] FIDEXE desktop API on 0.0.0.0:47811 (demo@fidexe.app / demo-pass-123, code 680371)
[mock] "GET /api/info HTTP/1.1" 200 -
[mock] "GET /api/demo/code HTTP/1.1" 200 -
[mock] phone paired with code: unknown Android SDK built for x86_64
[mock] "POST /api/pair HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
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
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] LOCK COMMAND RECEIVED
[mock] "POST /api/command HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/state HTTP/1.1" 200 -
[mock] "GET /api/state HTTP/1.1" 200 -

## flow log
== laptop address ==
+ python3 tools/android_ui.py tap-edit 0
tap-edit 0 ok
+ python3 tools/android_ui.py type 10.0.2.2:47811
+ python3 tools/android_ui.py hide-keyboard
+ echo '== pairing code from the mock desktop =='
== pairing code from the mock desktop ==
++ curl -s --max-time 10 http://127.0.0.1:47811/api/demo/code
++ python3 -c 'import json,sys;print(json.load(sys.stdin)['\''code'\''])'
+ CODE=141413
+ echo code=141413
code=141413
+ '[' -z 141413 ']'
+ python3 tools/android_ui.py tap-edit 1
tap-edit 1 ok
+ python3 tools/android_ui.py type 141413
+ python3 tools/android_ui.py hide-keyboard
+ take_shot filled.png
+ python3 tools/android_ui.py shot docs/android/filled.png
saved docs/android/filled.png 190889 bytes
+ echo '== log in with the code =='
== log in with the code ==
+ python3 tools/android_ui.py tap-text 'Войти по коду'
tap-text Войти по коду ok
+ sleep 10
+ take_shot control.png
+ python3 tools/android_ui.py shot docs/android/control.png
saved docs/android/control.png 210013 bytes
+ python3 tools/android_ui.py dump
+ echo '== running apps on the laptop =='
== running apps on the laptop ==
+ python3 tools/android_ui.py tap-text Приложения
tap-text Приложения ok
+ sleep 3
+ take_shot apps.png
+ python3 tools/android_ui.py shot docs/android/apps.png
saved docs/android/apps.png 154366 bytes
+ python3 tools/android_ui.py tap-text Закрыть
tap-text Закрыть ok
+ sleep 3
+ take_shot apps-closed.png
+ python3 tools/android_ui.py shot docs/android/apps-closed.png
saved docs/android/apps-closed.png 154366 bytes
+ adb shell input keyevent 4
+ sleep 2
+ echo '== laptop camera =='
== laptop camera ==
+ python3 tools/android_ui.py tap-text 'Камера ноутбука'
tap-text Камера ноутбука ok
+ sleep 4
+ take_shot camera.png
+ python3 tools/android_ui.py shot docs/android/camera.png
saved docs/android/camera.png 97250 bytes
+ python3 tools/android_ui.py tap-text Стоп
tap-text Стоп ok
+ sleep 2
+ echo '== lock the laptop =='
== lock the laptop ==
+ python3 tools/android_ui.py tap-text 'Заблокировать ноутбук'
tap-text Заблокировать ноутбук ok
+ sleep 5
+ take_shot locked.png
+ python3 tools/android_ui.py shot docs/android/locked.png
saved docs/android/locked.png 215129 bytes
+ echo '== mock desktop state =='
== mock desktop state ==
+ cat /tmp/mock.log
[mock] FIDEXE desktop API on 0.0.0.0:47811 (demo@fidexe.app / demo-pass-123, code 680371)
[mock] "GET /api/info HTTP/1.1" 200 -
[mock] "GET /api/demo/code HTTP/1.1" 200 -
[mock] phone paired with code: unknown Android SDK built for x86_64
[mock] "POST /api/pair HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
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
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] LOCK COMMAND RECEIVED
[mock] "POST /api/command HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
[mock] "GET /api/status HTTP/1.1" 200 -
+ curl -s --max-time 10 http://127.0.0.1:47811/api/state
{"locked": 1, "commands": ["lock"], "closed": [], "camera_frames": 14}+ echo

+ grep -q 'phone paired with code' /tmp/mock.log
+ echo 'RESULT: code login accepted by the desktop API'
RESULT: code login accepted by the desktop API
+ grep -q 'CLOSE APP' /tmp/mock.log
+ step_failed 'no close-app request reached the desktop'
+ echo 'STEP FAILED: no close-app request reached the desktop'
STEP FAILED: no close-app request reached the desktop
+ STATUS=1
++ curl -s --max-time 10 http://127.0.0.1:47811/api/state
++ python3 -c 'import json,sys;print(json.load(sys.stdin).get('\''camera_frames'\'',0))'
+ FRAMES=14
+ '[' 14 -gt 0 ']'
+ echo 'RESULT: camera frames served: 14'
RESULT: camera frames served: 14
+ grep -q 'LOCK COMMAND RECEIVED' /tmp/mock.log
+ echo 'RESULT: lock command received'
RESULT: lock command received
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
TextView       (99, 1354, 981, 1445) clickable=False text='FIDEXE на ноутбуке → Настройки → «Телефон и блокировка». Шесть цифр меняются каждую минуту.'
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
TextView       (99, 516, 981, 565) clickable=False text='●  На связи'
TextView       (99, 676, 479, 717) clickable=False text='Экран сегодня'
TextView       (99, 728, 479, 799) clickable=False text='4 ч 24 мин'
TextView       (601, 676, 981, 717) clickable=False text='Сейчас в фокусе'
TextView       (601, 728, 981, 799) clickable=False text='chrome'
TextView       (99, 904, 479, 945) clickable=False text='Буфер обмена'
TextView       (99, 956, 479, 1027) clickable=False text='42 записей'
TextView       (601, 904, 981, 945) clickable=False text='Трекинг'
TextView       (601, 956, 981, 1027) clickable=False text='Активен'
TextView       (55, 1121, 1025, 1385) clickable=True text='Заблокировать ноутбук'
TextView       (55, 1413, 523, 1551) clickable=True text='Спящий режим'
TextView       (557, 1413, 1025, 1551) clickable=True text='Пауза трекинга'
TextView       (55, 1573, 523, 1711) clickable=True text='Камера ноутбука'
TextView       (557, 1573, 1025, 1711) clickable=True text='Приложения'
TextView       (55, 1838, 1025, 1920) clickable=False text='Команда выполняется сразу после нажатия. Ноутбук и телефон должны быть в одной Wi-Fi сети.'

## logcat (app)
