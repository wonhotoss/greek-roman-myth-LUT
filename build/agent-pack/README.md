# agent-pack — 음성 에이전트에 얹는 방법

이 폴더는 `tools/render_agent.py` 가 만든 산출물이다. 직접 고치지 말고 `data/` 를 고쳐 다시 만든다.

## my-talking-claw 에 붙이기

`my-talking-claw` 의 에이전트 게이트웨이는 질문을 `claude -p` 로 넘긴다.
이 폴더를 그 프로세스의 작업 디렉터리로 주면 `CLAUDE.md` 가 자동으로 읽힌다.

```sh
cd build/agent-pack
claude -p "제우스는 누구야?"
```

작업 디렉터리를 바꿀 수 없으면 지침을 직접 얹는다.

```sh
claude -p --append-system-prompt "$(cat build/agent-pack/CLAUDE.md)" "제우스는 누구야?"
```

## 들어 있는 것

- `CLAUDE.md` — 에이전트 지침. 어떻게 답할지
- `집필-지침.md` — 문장·이름·수위·톤 규칙. `data/` 를 쓸 때와 같은 기준
- `knowledge/` — 지식 299인물 / 263사건 / 85장소 / 33묶음서사

## 화면용과 다른 점

화면(`build/myth.html`)에는 `민감도`와 `내부 메모`를 그리지 않는다. 아이가 보는 것이다.
에이전트에게는 준다. **무엇을 말하지 않을지 알아야 하기 때문이다.**
