# herdr Agent Sidebar

[herdr](https://herdr.dev)용 컴팩트 Agent 사이드바 — 에이전트별 로고 아이콘, 워크스페이스 그룹당 프로젝트 헤더 하나, 상태 표시(애니메이션 선택).

[English](README.md)

## 요구사항

- herdr 0.8.0 이상
- `python3` (표준 라이브러리만 사용)
- macOS 또는 Linux

## 설치

1. 플러그인 설치. build 단계에서 번들 아이콘 폰트를 사용자 폰트 폴더(macOS `~/Library/Fonts`, Linux `~/.local/share/fonts`)에 복사한다.

   ```sh
   herdr plugin install speardragon/herdr-agent-sidebar
   ```

2. [`layout.toml`](layout.toml)을 `~/.config/herdr/config.toml`에 붙여넣는다. 기존 `[ui]` / `[ui.sidebar.*]` 테이블은 먼저 주석 처리 — 같은 테이블을 두 번 정의하면 TOML 오류.

3. 터미널 폰트 폴백에 아이콘 폰트 추가. WezTerm 예시:

   ```lua
   config.font = wezterm.font_with_fallback({
     'JetBrains Mono', -- 평소 쓰는 폰트
     'Herdr Agent Icons Bounce',
     'Herdr Agent Icons Max',
   })
   ```

4. 적용: `herdr server reload-config` 후 터미널 재시작(새 폰트 인식).

## 왜 플러그인이 필요한가

레이아웃이 쓰는 `$agents_group`, `$agents_logo`, `$agents_mark`, `$agents_group_end`, `$agents_tab_*`는 herdr 내장 토큰이 아니라 커스텀 메타데이터 토큰이라 herdr 문서에 없다. 이 플러그인이 `herdr agent list` / `workspace list` / `tab list`로 값을 계산해 관련 이벤트마다 `herdr pane report-metadata`로 채운다. 플러그인이 없으면 토큰이 비어 행이 숨겨진다.

## 액션

| 액션 | 동작 |
|---|---|
| `sync` | 모든 토큰 즉시 재계산 |
| `animations-on` / `animations-off` / `animations-toggle` | `working` 스피너, `blocked` 물음표 바운스 (기본 꺼짐) |
| `animations-status` | 애니메이션 활성·실행 여부 출력 |

런타임 상태(락·애니메이션 플래그·로그)는 플러그인 체크아웃이 아니라 `HERDR_PLUGIN_STATE_DIR`에 둔다.

## 지원 로고

claude, codex, opencode, pi, grok, agy. 그 외 에이전트는 `◇`. `sync.py`의 `logos` 테이블에 에이전트 id→글리프를 추가하면 확장된다.

## 크레딧

아이콘 폰트는 [hhdebb/herdr-radar](https://github.com/hhdebb/herdr-radar)(MIT, [qintmb/herdr-icon-agent-ui](https://github.com/qintmb/herdr-icon-agent-ui) 포크)에서 가져왔다. `Herdr Agent Icons Bounce`는 Max 폰트에 `?` 프레임 4개(U+E1D0–U+E1D3)를 추가한 파생본. [`fonts/LICENSE`](fonts/LICENSE), [`fonts/THIRD_PARTY_NOTICES.md`](fonts/THIRD_PARTY_NOTICES.md) 참고. 로고는 각 제품을 식별할 뿐 제휴·보증을 뜻하지 않는다.
