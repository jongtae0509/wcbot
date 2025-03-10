import time, os
from datetime import datetime, timedelta

trial = 0
waittime = 5

if not os.path.isfile('lastupd.txt'): open('lastupd.txt', 'w').write(datetime.now().strftime('%Y-%m-%d'))

while (True):
    # 날짜 갱신이 안되어있을시 본격적 작업 시작
    if datetime.strptime(open('lastupd.txt', 'r').read(), '%Y-%m-%d') < datetime.now().replace(hour=0, minute=0,
                                                                                               second=0, microsecond=0):
        print()

        # 날짜 갱신
        open('lastupd.txt', 'w').write(datetime.now().strftime('%Y-%m-%d'))

        # 스크립트 실행
        os.system("lxterminal --command=\"python3 run.py\"")
        print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + ']' + '스크립트 실행... (' + str(waittime) + ')')

    else:
        print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + ']' + '대기중... (' + str(waittime) + ')', end='\r')
    time.sleep(waittime)
