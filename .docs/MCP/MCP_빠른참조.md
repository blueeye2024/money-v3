# MCP 서버 빠른 참조 가이드 (Context7 Only)

## 🚀 활성 서버: Context7

현재 **Context7** 서버만 사용 가능합니다.

### ✅ 주요 기능
*   **코드 검색**: "이 기능을 담당하는 코드는 어디에 있어?"
*   **의존성 분석**: "이 변수를 참조하는 파일들을 다 찾아줘"
*   **문서화**: "이 모듈의 기능을 요약해줘"

### 💡 활용 예시
```
"KIS API 인증 토큰 처리 로직을 찾아서 설명해줘"
"db.py의 스키마 구조를 요약해줘"
"트리플 필터 매매 전략이 구현된 코드를 분석해줘"
```

---

## 🚫 비활성화됨
*   Filesystem (대신 기본 도구 사용)
*   Shell (대신 기본 도구 사용)
*   MySQL
*   Memory
*   Fetch
*   Sequential Thinking
*   Brave Search

---

## 📁 주요 파일 위치
*   전역 설정: `~/.config/mcp/config.json`
*   에디터 설정: `~/.cursor/mcp.json`

**업데이트**: 2026-01-06
