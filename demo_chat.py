# ============================================================
# 필요한 라이브러리 불러오기 (import)
# ============================================================

import os, time
# os     : 운영체제 기능 사용 (환경변수 읽기 등)
# time   : 시간 관련 기능 (sleep으로 대기)

from dotenv import load_dotenv
# dotenv : .env 파일에 저장된 변수를 읽어오는 라이브러리
# 예) .env 파일에 GOOGLE_API_KEY=abc123 이렇게 저장해두면
#     파이썬 코드에서 os.environ.get("GOOGLE_API_KEY") 로 읽을 수 있게 해줌

from google import genai
from google.genai import types
# google-genai : Google Gemini API를 파이썬에서 쓸 수 있게 해주는 공식 라이브러리
# types        : API 요청 설정값(설정 객체)을 만들 때 사용

from google.genai.errors import ServerError, ClientError
# 오류 타입 불러오기
# ServerError : 서버 문제 (503 - 서버 과부하 등)
# ClientError : 클라이언트 문제 (429 - 요청 너무 많음, 401 - 인증 실패 등)

import urllib.request
# 인터넷에서 파일(이미지 등)을 다운로드할 때 사용하는 라이브러리


# ============================================================
# 재시도 함수 (오류가 나면 자동으로 다시 시도)
# ============================================================

def call_with_retry(fn, *args, retries=5, **kwargs):
    # fn      : 실행할 함수 (예: client.models.generate_content)
    # *args   : 함수에 넘길 위치 인자들
    # retries : 최대 몇 번 재시도할지 (기본값 5번)
    # **kwargs: 함수에 넘길 키워드 인자들

    for i in range(retries):
        # 최대 retries번 반복 시도
        try:
            return fn(*args, **kwargs)
            # 함수 실행에 성공하면 바로 결과 반환하고 종료

        except (ServerError, ClientError) as e:
            # 서버 오류 또는 클라이언트 오류가 발생했을 때만 재시도
            # 다른 종류의 오류는 재시도 없이 바로 에러 발생

            if i == retries - 1:
                raise
                # 마지막 시도에서도 실패하면 에러를 그대로 올려보냄 (포기)

            wait = 20 * (i + 1)
            # 대기 시간 계산: 1번째 실패 → 20초, 2번째 → 40초, 3번째 → 60초...
            # 점점 오래 기다리는 이유: 서버가 바쁠 때 짧은 간격으로 계속 요청하면
            # 오히려 더 오래 막힐 수 있어서 (지수 백오프 전략)

            print(f"\n  [재시도 {i+1}/{retries}, {wait}초 대기...] {str(e)[:60]}")
            time.sleep(wait)
            # 지정한 시간만큼 기다린 후 다시 시도


# ============================================================
# Gemini 클라이언트 초기화
# ============================================================

load_dotenv()
# .env 파일을 읽어서 환경변수로 등록
# 이 줄이 없으면 os.environ.get("GOOGLE_API_KEY")가 None을 반환함

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
# Gemini API에 연결하는 클라이언트 객체 생성
# api_key : .env 파일에서 읽어온 API 키를 넘겨줌
# 이 client 객체로 이후 모든 API 요청을 보냄

MODEL = "gemini-2.5-flash"
# 사용할 Gemini 모델 이름
# gemini-2.5-flash : 빠르고 가벼운 모델 (무료 티어에서 사용 가능)
# 더 강력한 모델: gemini-2.5-pro (더 똑똑하지만 느리고 비쌈)


# ============================================================
# 1단계: 이미지 이해
# ============================================================

print("=" * 50)
print("1. 이미지 이해")
print("=" * 50)

# 인터넷에서 샘플 이미지 다운로드
img_url = "https://storage.googleapis.com/generativeai-downloads/images/scones.jpg"
urllib.request.urlretrieve(img_url, "sample.jpg")
# urlretrieve(url, 저장파일명) : url의 파일을 로컬에 sample.jpg로 저장
# 이 이미지는 Google이 공식 예제용으로 제공하는 스콘 사진

import PIL.Image
img = PIL.Image.open("sample.jpg")
# PIL(Pillow 라이브러리)로 이미지 파일을 열어서 img 변수에 저장
# Gemini API는 PIL 이미지 객체를 직접 받을 수 있음

response = call_with_retry(
    client.models.generate_content,  # 실행할 함수
    model=MODEL,                      # 사용할 모델
    contents=["이 이미지에 뭐가 있어? 한국어로 설명해줘", img]
    # contents에 텍스트와 이미지를 함께 넣음 → 멀티모달(multimodal) 요청
    # 텍스트만 넣으면 일반 텍스트 요청, 이미지를 함께 넣으면 이미지 이해 요청
)
print(response.text)
# response.text : Gemini가 생성한 텍스트 응답


time.sleep(3)
# API 요청 사이에 3초 대기
# 이유: 무료 티어는 분당 요청 횟수에 제한이 있어서
#       너무 빠르게 연속 요청하면 429 오류(요청 초과)가 발생할 수 있음


# ============================================================
# 2단계: 멀티턴 채팅 + 스트리밍
# ============================================================

print("\n" + "=" * 50)
print("2. 멀티턴 채팅 + 스트리밍")
print("=" * 50)

chat = client.chats.create(model=MODEL)
# 채팅 세션 생성
# 일반 generate_content와 달리, chat 객체는 대화 기록을 내부적으로 유지함
# 즉, 이전에 한 말을 기억하고 이어서 대화할 수 있음 (멀티턴)

questions = [
    "방금 본 스콘 이미지에서 영감을 받아서, 스콘 만드는 법을 간단히 알려줘",
    "거기에 초콜릿 칩을 추가하면 어떻게 달라져?",
    "칼로리는 대략 얼마야?",
]
# 순서대로 보낼 질문 목록
# 2번째, 3번째 질문은 앞 대화를 전제로 함
# chat 객체가 대화 기록을 유지하기 때문에 "거기에", "칼로리는" 처럼 맥락 있는 질문이 가능


for q in questions:
    # 각 질문을 순서대로 처리

    print(f"\n사용자: {q}")
    print("Gemini: ", end="", flush=True)
    # end=""  : print 후 줄바꿈 없이 이어서 출력 (스트리밍 효과를 위해)
    # flush=True : 버퍼를 즉시 비워서 글자가 바로 화면에 나타나게 함

    for attempt in range(5):
        # 오류 시 최대 5번 재시도
        try:
            for chunk in chat.send_message_stream(q):
                # send_message_stream : 응답을 한 번에 받지 않고 조각(chunk) 단위로 받음
                # 이 덕분에 ChatGPT처럼 글자가 실시간으로 하나씩 출력되는 효과가 남
                # (일반 send_message는 응답 전체가 완성될 때까지 기다렸다가 한 번에 출력)
                print(chunk.text, end="", flush=True)
                # chunk.text : 현재 조각의 텍스트
                # end="", flush=True : 줄바꿈 없이 이어서 즉시 출력
            break
            # 성공하면 재시도 루프 탈출

        except (ServerError, ClientError) as e:
            if attempt == 4:
                raise
            wait = 20 * (attempt + 1)
            print(f"\n  [재시도 {attempt+1}/5, {wait}초 대기...]")
            time.sleep(wait)

    print()
    # 한 질문-답변이 끝나면 줄바꿈

    time.sleep(5)
    # 다음 질문 전에 5초 대기 (API rate limit 방지)


print("\n✓ 완료")
