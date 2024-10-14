import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import requests, lxml, os, time, requests, json, sys, random, re
from wordcloud import WordCloud, ImageColorGenerator
from base64 import b64encode
from datetime import datetime, timedelta
import os
import dc_api
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from collections import Counter
import asyncio

 #
def sendTelegramMsg(APIKey, chatID, text):
    r = requests.get("https://api.telegram.org/bot"
                     + APIKey + "/sendMessage?chat_id="
                     + chatID + "&text="
                     + text + "&parse_mode=Markdown")
    return r


TelAPI = "telegram_bot_api_key"  # 텔레그램 봇키
TelChan = "channel"  # 채널 주소

def remove_singleletter_words(s):
    return ' '.join([w for w in s.split() if len(w) != 1])


def deEmojify(text):
    regrex_pattern = re.compile(pattern="["
                                        u"\U0001F600-\U0001F64F"  # emoticons
                                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                        "]+", flags=re.UNICODE)
    return regrex_pattern.sub(r'', text)


# 제목하나당 중복키워드 제거 람다 (ex:'foo foo foo bar'->'foo bar')
rmduplicate = lambda x: ' '.join(list(set(x.split(' '))))

taskdone = False
trial = 0

# 탐색 날짜 범위 (ex. days=1 : 1일 이내, 0:측정 시작순간 이후)
# 설정 날짜의 딱 자정으로 설정됩니다 (ex. 8.18 1:45AM -> 8.18 00:00AM)
drange = 1
fontpath = 'font.otf'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'}

# 갤러리ID
gid = 'electricguitar'

# 갤러리 링크
link = 'https://gall.dcinside.com/board/lists/?id=' + gid

# 예외카운트 (공지때문에)
pass_cnt = 6

ystday = (datetime.now() - timedelta(days=drange)).replace(hour=0, minute=0, second=0, microsecond=0)
tday = (datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)

print(ystday, '이후의 게시글을 수집합니다.')

taskdone = False
trial = 0

tdata_ai = ''

while not taskdone and trial < 10:
    try:

        # 마이너, 정식갤러리 판별
        r = requests.get('https://gall.dcinside.com/board/lists/?id=' + gid, headers=headers).text
        print('갤러리 형식:', end=' ')

        # 마이너 갤러리일 경우
        if 'location.replace' in r:
            link = link.replace('board/', 'mgallery/board/')
            print('마이너')
        else:
            print('정식')

        i = 0
        tdata = ' '
        ndata = ''
        fin = False
        r = None
        postcount = 0

        while not fin:
            time.sleep(1)

            i += 1
            reqtrial = 0
            print('페이지 읽는 중... [{}번째...]'.format(i))  # , end='\r')
            titleok = False

            while not titleok:
                r = requests.get(link + '&page=' + str(i) + '&list_num=100', headers=headers).text
                bs = BeautifulSoup(r, 'lxml')

                posts = bs.find_all('tr', class_='ub-content us-post')

                for p in posts:
                    # td, class = gall_tit ub-word에서 보플(voice_tit)대응으로 ub-word 지움
                    title = p.find('td', class_='gall_tit')

                    # 공지 제외 (볼드태그 찾을때 str 처리 해줘야 찾기가능)
                    if not '<b>' in str(title):
                        titleok = True
                        title_ai_tmp = title.a.text.strip()
                        title = rmduplicate(title.a.text.strip())
                        subject = p.find('td', class_='gall_subject').text.strip()

                        # AI용 정보 수집 (추천수, 작성날짜)
                        upvote = p.find('td', class_='gall_recommend').text.strip()
                        date = datetime.strptime(p.find('td', class_='gall_date').get('title'), "%Y-%m-%d %H:%M:%S")

                        print(subject, '|', date, '|', title, '|', date)

                        if (subject == '일반'):
                            subject = ''
                        else:
                            subject = '[' + subject + ']'

                        # 초 단위까지는 안 가도록 함
                        if date >= ystday:

                            if date >= tday:
                                print('기간 앞섬:', date)
                            else:
                                postcount += 1
                                tdata += title + ' '  # 제목 값

                                tdata_ai += date.strftime(
                                    "%Y-%m-%d %H:%M") + '|' + subject + title_ai_tmp + '|' + upvote + '\n'  # 생성형 AI를 위한 시간,(분야)제목,개추수 수집
                        else:

                            if pass_cnt <= 0:
                                print('기간 초과:', date)
                                fin = True
                                date = ystday
                                break
                            else:
                                pass_cnt -= 1  # 일정개수는 무시하고 계속 조회해보도록 함 (공지 내린걸로 정지되면 곤란하므로)

                if not titleok:

                    if reqtrial > 10:
                        print('크롤링 실패 횟수가 10회를 넘었습니다. 스크립트를 종료 후 다시 시작합니다.')
                        # 최근조회일을 어제로 변경
                        open('lastupd.txt', 'w').write((datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))
                        sys.exit()

                    print('게시글 크롤링 실패. 10초 후 다시 시도해 봅니다.')
                    # i -= 1
                    time.sleep(10)
                    reqtrial += 1

        print()

        # 예외 단어 목록
        rmkeys = []

        print('불필요한 키워드 제거중...')
        for d in rmkeys:
            tdata = tdata.replace(' ' + d + ' ', ' ')

        tdata = tdata.replace('&gt;', ' ')
        tdata = tdata.replace('&lt;', ' ')
        tdata = tdata.replace('!', ' ')
        tdata = tdata.replace('.', ' ')
        tdata = tdata.replace('?', ' ')

        # 단어 길이가 1인 단어 제거
        tdata = remove_singleletter_words(tdata)

        print('워드클라우드 생성 중... [1/2]')
        wc_title = WordCloud(font_path=fontpath, width=1200, height=1000, background_color='white',
                             collocations=False).generate(tdata)
        
        print('이미지 저장 중...')
        wc_title.to_file('title.png')

        hk = sorted(wc_title.words_.items(), key=(lambda x: x[1]), reverse=True)
        # 현재 키워드에서 제외 키워드는 지워버리기
        keys = [i[0] for i in hk]
        print(1, keys)

        for s in rmkeys:
            if s in keys: keys.remove(s)

        # 현재 키워드 목록 저장
        pkeys = ''
        for s in hk: pkeys += s[0] + '\n'

        open('./keyword/' + ai_today_name, 'w').write(pkeys)

        print(keys)
        print('저장 완료')
        taskdone = True
    except Exception as e:
        print('뭔가 문제가 있습니다. 다시 해보겠습니다.')
        print('오류 메시지:', str(e))
        print('시도 횟수:', str(trial))
        # exit() # 에러 발생시 스크립트 종료 (디버그용)
        sendTelegramMsg(TelAPI, TelChan, "*WC Status Report*\n워드클라우드 생성 중 문제 발생.\n" + str(e) + "\n시도 횟수:" + str(trial))
        trial += 1
        time.sleep(5)

    # ============================AI 시작============================
    print('AI 작업 시작...')
    result_ai = ''
    print('글 시작')

    import anthropic

    client = anthropic.Anthropic(
        api_key="api_key",
    )

    final = ''

    try:
        # AI 작업
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=8192,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "너는 일렉트릭기타 마이너 갤러리(일마갤)을 하는 디시인사이드 커뮤니티 유저야. 귀찮고 어렵고 때려치고 싶은 일상에서 스트레스 풀려고 일마갤 글 보는 게 일과야. 오늘도 어김없이 일마갤에 들어왔어.\n\n오늘 일마갤에 올라온 글들이야:\n\n<daily_posts>\n"+tdata_ai+"\n</daily_posts>\n\n이 글들을 읽고 재미있게 요약해서 글을 써. 다음 지침을 꼭 따라야 해:\n\n1. 디시 말투를 완벽하게 사용해. 비속어나 디시 은어도 섞어 써서 재미를 더해 너무 많이는 말고.\n2. 글 내용이나 글 제목, 댓글 내용에 기호가 있으면 안 돼. 최대한 한글로만 작성해. ##, **, -- 등의 기호는 쓰지 마.\n3. 1234 등의 목차도 사용하지 마.\n4. 글 제목도 디시스타일로 지어. 제목은 <title> 태그 안에 써.\n5. 요약한 내용은 <summary> 태그 안에 써.\n6. 정보는 시간, 제목, 추천수로 주어질거야\n7. 시간 경과에 따른 떡밥 변화가 잘 나왔으면 좋겠어\n8. 이 요약을 일마갤에 업로드 할 예정이라 줄바꿈은<br> 로 처리해야해\n9. 일마갤은 닉네임 언급이 금지라 절대 내용에 직접적인 닉네임을 쓰면안돼\n자, 이제 시작해. 일마갤 유저답게 글 써봐."
                        }                                                                                                                                   
                    ]
                }
            ]
        )
        final = message.content[0].text
        print('AI일붕이 작업 완료, 결과:')
        print(final)

        open("./ai/" + ai_today_name, 'w').write(final)
        print('결과 끝')
    except Exception as e:
        print('AI 작업 실패')
        print('오류 메시지:', str(e))
        final = ''
    # ============================AI 끝============================
    result_ai = final
    page_source = open('orgpage.txt', 'r').read()
    page_source = page_source.replace('[gallid]', gid)
    page_source = page_source.replace('[ai]', result_ai)
    page_source = page_source.replace('[posts]', str(postcount))
    page_source = page_source.replace('[posts2]', str(round(postcount / 144, 2)))

    open('page.txt', 'w').write(page_source)

    taskdone = True
    print('작업이 모두 성공하였습니다.')

print('업로드 스크립트 끝.')

# ============================글쓰기 시작============================

try:
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By

    id = 'id'  # 디시 ID
    pw = 'password'  # 디시 PW
    url = 'https://www.dcinside.com/'
    gall = 'https://gall.dcinside.com/mgallery/board/write/?id=' + gid
    title = '일마갤 오늘의 키워드 < ' + str(ystday.month) + '/' + str(ystday.day) + ' >'
    content = open('page.txt', 'r').read()

    # 리눅스를 위한 가상 디스플레이 드라이버 로드
    from pyvirtualdisplay import Display

    display = Display(visible=0, size=(800, 800))
    display.start()
    print('디스플레이 드라이버 로드...')

    # 크롬 환경 변수
    print('환경 변수 설정...')
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=800x600')
    options.add_argument("disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # 크롬 드라이버 로드
    print('chromedriver 로드...')
    # 웹드라이버 불러오기 - Windows의 경우 웹드라이버를 받은 후 같은 디렉토리에 넣은 후
    service = Service(executable_path='/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(3)

    # 디시인사이드 로그인 페이지 로드
    print('dcinside 로그인 작업 중...')
    driver.get(url)

    # 아이디
    driver.find_element(By.NAME, 'user_id').send_keys(id)
    # 패스워드
    driver.find_element(By.NAME, 'pw').send_keys(pw)
    # 로그인
    driver.find_element(By.ID, 'login_ok').send_keys(Keys.ENTER)

    # 글을 쓰고자 하는 갤러리로 이동
    print('갤러리 글쓰기 페이지 접속...')
    driver.get(gall)
    time.sleep(3)

    # 제목 입력
    print('글 제목 입력중...')
    driver.find_element(By.NAME, 'subject').send_keys(title)
    driver.execute_script("window.scrollTo(0, 100)")
    time.sleep(1)

    # 이미지 업로드 버튼 선택
    print('이미지 업로드 팝업 표시...')
    driver.find_element(By.XPATH, "//a[@class='tx-text' and @title='사진']").click()
    currentHandle = driver.current_window_handle
    time.sleep(0.5)

    print('창 포커스 전환...')
    for handle in driver.window_handles:
        if currentHandle != handle:
            driver.switch_to.window(handle)
            break

    print('파일 추가...')
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(os.getcwd() + "/title.png")
    time.sleep(7)

    print('이미지 업로드 적용...')
    driver.find_element(By.XPATH, "//button[@class='btn_apply']").click()

    driver.switch_to.window(currentHandle)
    # 이미지 업로드 끝

    # HTML으로 쓰기 방식 변경
    print('HTML 글쓰기 방식 변경...')
    driver.find_element(By.XPATH, "//a[@id='chk_html']").click()
    time.sleep(1)

    # 글쓰기 폼으로 진입
    print('글쓰기 폼으로 프레임 전환...')
    driver.switch_to.frame(driver.find_element(By.XPATH, "//iframe[@name='tx_canvas_wysiwyg']"))

    # 본문 입력
    print('본문 입력중...')
    content = deEmojify(content)  # 이모지 제거
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL, 'a')
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
    driver.find_element(By.TAG_NAME, "body").send_keys(content)

    driver.switch_to.default_content()

    # 글쓰기 저장
    print('저장 후 전송중...')

    # HTML으로 쓰기 방식 변경
    print('HTML 글쓰기 방식 (다시) 변경...')
    driver.find_element(By.XPATH, "//a[@id='chk_html']").click()
    time.sleep(1)

    time.sleep(3)
    driver.find_element(By.XPATH, "//button[@class='btn_blue btn_svc write']").click()
    # 저장 딜레이
    time.sleep(2)
    # 웹페이지 닫기
    print('작업 마무리중...')
    driver.quit()
    display.stop()

    sendTelegramMsg(TelAPI, TelChan, "*WC Status Report*\nimage post 하였습니다.\n" + "\n제목:" + '[@]오늘의 갤러리 워드클라우드 (' + str(
        ystday.month) + '월 ' + str(ystday.day) + '일~)')

except Exception as e:
    print('브라우저 글쓰기 작업 실패')
    print('오류 메시지:', str(e))
    sendTelegramMsg(TelAPI, TelChan, "*WC Status Report*\n브라우저 글쓰기 작업 중 문제 발생.\n" + str(e))
    exit()
