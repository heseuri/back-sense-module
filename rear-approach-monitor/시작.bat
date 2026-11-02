@echo off
echo 후방 감지 모니터 시작 중...

:: 백엔드 (FastAPI)
start "백엔드" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 잠깐 대기 후 프론트엔드 (React)
timeout /t 2 /nobreak > nul
start "프론트엔드" cmd /k "cd /d %~dp0frontend && npm run dev"

:: 잠깐 대기 후 브라우저 열기
timeout /t 4 /nobreak > nul
start http://localhost:5173

echo.
echo 브라우저가 자동으로 열립니다.
echo 폰에서는 http://192.168.219.102:5173 으로 접속하세요.
echo.
echo 종료하려면 열린 터미널 창 두 개를 닫으세요.
