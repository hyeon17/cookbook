// ============================================================
// 필요한 라이브러리 불러오기
// ============================================================

import { GoogleGenAI } from '@google/genai';
// Google Gemini API를 JS에서 쓸 수 있게 해주는 공식 SDK

import * as fs from 'fs';
// fs : 파일 읽기/쓰기 등 파일 시스템 관련 기능 (Node.js 내장)

import * as https from 'https';
// https : 인터넷에서 파일 다운로드할 때 사용 (Node.js 내장)

import * as path from 'path';
// path : 파일 경로 처리 (Node.js 내장)

import 'dotenv/config';
// dotenv : .env 파일에서 환경변수를 읽어옴
// import "dotenv/config" 한 줄로 자동 로드됨
// Python의 load_dotenv()와 동일한 역할

// ============================================================
// 유틸리티 함수
// ============================================================

// 인터넷에서 이미지를 다운로드하는 함수
function downloadImage(url, dest) {
	return new Promise((resolve, reject) => {
		// Promise : 비동기 작업을 다루는 JS 방식
		// resolve : 성공했을 때 호출, reject : 실패했을 때 호출

		const file = fs.createWriteStream(dest);
		// 저장할 파일 스트림 생성

		https
			.get(url, (response) => {
				response.pipe(file);
				// 다운로드 데이터를 파일에 직접 씀

				file.on('finish', () => {
					file.close();
					resolve();
					// 다운로드 완료
				});
			})
			.on('error', reject);
		// 오류 발생 시 reject 호출
	});
}

// 지정한 시간(ms)만큼 기다리는 함수
function sleep(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
	// Python의 time.sleep()과 동일한 역할
	// JS에서는 await sleep(3000) 형태로 사용 (3초 대기)
}

// 오류 발생 시 자동 재시도하는 함수
async function callWithRetry(fn, retries = 5) {
	// async : 이 함수 안에서 await를 쓸 수 있게 해주는 키워드
	// fn      : 실행할 함수
	// retries : 최대 재시도 횟수 (기본값 5)

	for (let i = 0; i < retries; i++) {
		try {
			return await fn();
			// 함수 실행 성공 시 결과 반환
		} catch (e) {
			if (i === retries - 1) throw e;
			// 마지막 시도에서도 실패하면 에러를 그대로 던짐 (포기)

			const wait = 20 * (i + 1);
			// 1번째 실패 → 20초, 2번째 → 40초, 3번째 → 60초...
			// Python 버전과 동일한 지수 백오프 전략

			console.log(`\n  [재시도 ${i + 1}/${retries}, ${wait}초 대기...] ${String(e).slice(0, 60)}`);
			await sleep(wait * 1000);
			// JS의 sleep은 밀리초 단위라서 *1000 필요 (Python은 초 단위)
		}
	}
}

// ============================================================
// 메인 함수
// ============================================================

async function main() {
	// JS에서 await를 최상위에서 쓰려면 async 함수 안에 감싸야 함

	// Gemini 클라이언트 초기화
	const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY });
	// process.env : Node.js에서 환경변수를 읽는 방법
	// Python의 os.environ.get()과 동일한 역할

	const MODEL = 'gemini-2.5-flash';
	// 사용할 모델 (Python 버전과 동일)

	// ============================================================
	// 1단계: 이미지 이해
	// ============================================================

	console.log('='.repeat(50));
	console.log('1. 이미지 이해');
	console.log('='.repeat(50));

	// 샘플 이미지 다운로드
	const imgUrl = 'https://storage.googleapis.com/generativeai-downloads/images/scones.jpg';
	await downloadImage(imgUrl, 'sample.jpg');
	// await : 비동기 작업이 완료될 때까지 기다림
	// Python의 일반 함수 호출과 동일한 효과

	// 이미지 파일을 base64로 인코딩
	const imageData = fs.readFileSync('sample.jpg');
	// readFileSync : 파일을 동기적으로 읽음
	const base64Image = imageData.toString('base64');
	// JS에서는 이미지를 base64 문자열로 변환해서 API에 전달
	// Python은 PIL 이미지 객체를 직접 넘길 수 있지만
	// JS는 base64 인코딩된 문자열로 넘겨야 함

	const imageResponse = await callWithRetry(() =>
		ai.models.generateContent({
			model: MODEL,
			contents: [
				{
					parts: [
						{ text: '이 이미지에 뭐가 있어? 한국어로 설명해줘' },
						{
							inlineData: {
								mimeType: 'image/jpeg',
								data: base64Image,
								// mimeType : 파일 형식 명시 (jpeg, png, gif 등)
								// data     : base64로 인코딩된 이미지 데이터
							},
						},
					],
				},
			],
		}),
	);

	console.log(imageResponse.text);
	// .text : Gemini 응답에서 텍스트만 추출 (Python과 동일)

	await sleep(3000);
	// 3초 대기 (rate limit 방지)

	// ============================================================
	// 2단계: 멀티턴 채팅 + 스트리밍
	// ============================================================

	console.log('\n' + '='.repeat(50));
	console.log('2. 멀티턴 채팅 + 스트리밍');
	console.log('='.repeat(50));

	const chat = ai.chats.create({ model: MODEL });
	// 채팅 세션 생성
	// Python의 client.chats.create()와 동일
	// 이전 대화 기록을 내부적으로 유지함 (멀티턴)

	const questions = [
		'방금 본 스콘 이미지에서 영감을 받아서, 스콘 만드는 법을 간단히 알려줘',
		'거기에 초콜릿 칩을 추가하면 어떻게 달라져?',
		'칼로리는 대략 얼마야?',
	];

	for (const q of questions) {
		// for...of : 배열을 순서대로 순회 (Python의 for q in questions와 동일)

		console.log(`\n사용자: ${q}`);
		process.stdout.write('Gemini: ');
		// process.stdout.write : 줄바꿈 없이 출력
		// Python의 print("Gemini: ", end="", flush=True)와 동일

		await callWithRetry(async () => {
			const stream = await chat.sendMessageStream({ message: q });
			// sendMessageStream : 응답을 스트리밍으로 받음
			// Python의 chat.send_message_stream()과 동일

			for await (const chunk of stream) {
				// for await...of : 비동기 스트림을 순서대로 처리
				// Python의 for chunk in chat.send_message_stream()과 동일
				process.stdout.write(chunk.text);
				// 청크(조각)를 받을 때마다 즉시 출력 → 실시간 스트리밍 효과
			}
		});

		console.log();
		// 줄바꿈 (Python의 print()와 동일)

		await sleep(5000);
		// 다음 질문 전 5초 대기
	}

	console.log('\n✓ 완료');
}

// 메인 함수 실행
main().catch(console.error);
// .catch(console.error) : 예상치 못한 에러 발생 시 콘솔에 출력
