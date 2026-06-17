import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  BookOpen,
  ClipboardList,
  DoorOpen,
  Home,
  KeyRound,
  LogOut,
  Mic,
  Power,
  Radio,
  RefreshCcw,
  Send,
  ShieldCheck,
  Trash2,
  UserPlus
} from "lucide-react";
import { api, audioUrlFromBase64, TurnResponse, User } from "./api/client";
import { recordWav } from "./api/wav";
import "./styles/app.css";

type HistoryItem = { id: string; role: string; content: string; source: string; created_at: string };
type Invite = {
  id: string;
  code: string;
  max_uses: number;
  used_count: number;
  is_active: boolean;
  expires_at: string;
  available?: boolean;
};

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [entered, setEntered] = useState(Boolean(localStorage.getItem("token")));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api<User>("/api/v1/auth/me", {}, token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("token");
        setToken(null);
      });
  }, [token]);

  function onAuth(nextToken: string, nextUser: User) {
    localStorage.setItem("token", nextToken);
    setToken(nextToken);
    setUser(nextUser);
    setError("");
  }

  if (!entered && (!token || !user)) {
    return <Landing onEnter={() => setEntered(true)} />;
  }

  if (!token || !user) {
    return (
      <AuthView
        mode={mode}
        setMode={setMode}
        error={error}
        setError={setError}
        onAuth={onAuth}
      />
    );
  }

  return (
    <Dashboard
      token={token}
      user={user}
      logout={() => {
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
      }}
    />
  );
}

function Landing({ onEnter }: { onEnter: () => void }) {
  return (
    <main className="landing-shell">
      <nav className="landing-nav">
        <strong>Spare-Time Companion</strong>
        <button onClick={onEnter}><DoorOpen size={17} /> 团队入口</button>
      </nav>
      <section className="landing-hero">
        <div className="landing-copy">
          <span className="eyebrow"><ShieldCheck size={16} /> Private demo</span>
          <h1>一台安静的桌面陪伴设备，背后是一套云端语音 Agent。</h1>
          <p>
            用于课程展示的受限访问 demo。语音识别、对话决策、语音合成和长期记忆都在服务端完成；
            Web 页面只是虚拟客户端和调试后台。
          </p>
          <div className="landing-actions">
            <button className="primary" onClick={onEnter}>进入登录</button>
            <span>需要团队邀请码或管理员账号</span>
          </div>
        </div>
        <div className="landing-device">
          <div className="device-preview">
            <div className="face large happy">
              <span className="eye" />
              <span className="eye" />
              <span className="mouth" />
            </div>
          </div>
          <div className="feature-strip">
            <span><Mic size={15} /> 语音输入</span>
            <span><Activity size={15} /> Agent 决策</span>
            <span><BookOpen size={15} /> 习惯记忆</span>
          </div>
        </div>
      </section>
    </main>
  );
}

function AuthView({
  mode,
  setMode,
  error,
  setError,
  onAuth
}: {
  mode: "login" | "register";
  setMode: (mode: "login" | "register") => void;
  error: string;
  setError: (value: string) => void;
  onAuth: (token: string, user: User) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [invite, setInvite] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const path = mode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
      const body =
        mode === "login"
          ? { email, password }
          : { email, password, display_name: displayName, invite_code: invite };
      const result = await api<{ access_token: string; user: User }>(path, {
        method: "POST",
        body: JSON.stringify(body)
      });
      onAuth(result.access_token, result.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-visual">
        <div className="device-preview">
          <div className="face large">
            <span className="eye" />
            <span className="eye" />
            <span className="mouth" />
          </div>
        </div>
        <h1>Spare-Time Companion</h1>
        <p>受限访问的云端语音陪伴 demo 控制台</p>
      </section>
      <form className="auth-panel" onSubmit={submit}>
        <div className="tabs">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            <KeyRound size={16} /> 登录
          </button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
            <UserPlus size={16} /> 注册
          </button>
        </div>
        <label>邮箱<input autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>密码<input autoComplete={mode === "login" ? "current-password" : "new-password"} type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {mode === "register" && (
          <>
            <label>昵称<input autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
            <label>邀请码<input autoComplete="off" value={invite} onChange={(event) => setInvite(event.target.value)} /></label>
          </>
        )}
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "处理中" : "进入 demo"}</button>
      </form>
    </main>
  );
}

function Dashboard({ token, user, logout }: { token: string; user: User; logout: () => void }) {
  const [text, setText] = useState("我有点累，不知道现在该做什么。");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turn, setTurn] = useState<TurnResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [agentRuns, setAgentRuns] = useState<Record<string, unknown>[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [inviteTtlHours, setInviteTtlHours] = useState(72);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const audioRef = useRef<HTMLAudioElement>(null);

  const expression = turn?.expression ?? (busy ? "thinking" : "idle");
  const statusText = busy || turn?.action || "待机";

  async function refresh() {
    const [nextHistory, nextRuns] = await Promise.all([
      api<HistoryItem[]>("/api/v1/companion/history", {}, token),
      api<Record<string, unknown>[]>("/api/v1/companion/agent-runs", {}, token)
    ]);
    setHistory(nextHistory);
    setAgentRuns(nextRuns);
    if (user.role === "admin") {
      setInvites(await api<Invite[]>("/api/v1/auth/invites", {}, token));
    }
  }

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  async function applyTurn(next: TurnResponse) {
    setTurn(next);
    setConversationId(next.conversation_id);
    if (next.audio_base64) {
      const url = audioUrlFromBase64(next.audio_base64, next.audio_mime_type);
      if (audioRef.current) {
        audioRef.current.src = url;
        await audioRef.current.play().catch(() => undefined);
      }
    }
    await refresh();
  }

  async function sendText(trigger = "text") {
    setBusy(trigger === "button" ? "按键触发" : "思考中");
    setError("");
    try {
      const next = await api<TurnResponse>(
        trigger === "button" ? "/api/v1/companion/turn/trigger" : "/api/v1/companion/turn/text",
        {
          method: "POST",
          body: JSON.stringify({
            text,
            conversation_id: conversationId,
            trigger,
            desktop_state: desktopState()
          })
        },
        token
      );
      await applyTurn(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  async function sendVoice() {
    setBusy("录音中");
    setError("");
    try {
      const wav = await recordWav(4);
      setBusy("上传语音");
      const form = new FormData();
      form.append("file", wav, "speech.wav");
      if (conversationId) form.append("conversation_id", conversationId);
      form.append("desktop_state_json", JSON.stringify(desktopState()));
      const next = await api<TurnResponse>("/api/v1/companion/turn/audio", { method: "POST", body: form }, token);
      await applyTurn(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  async function feedback(kind: string) {
    if (!turn?.conversation_id) return;
    await api(
      "/api/v1/companion/feedback",
      {
        method: "POST",
        body: JSON.stringify({
          conversation_id: turn.conversation_id,
          message_id: turn.debug.assistant_message_id,
          kind,
          note: kind === "negative" ? "这次回应不合适" : undefined
        })
      },
      token
    );
    await refresh();
  }

  async function createInvite() {
    await api(
      "/api/v1/auth/invites",
      { method: "POST", body: JSON.stringify({ max_uses: 20, ttl_hours: inviteTtlHours }) },
      token
    );
    await refresh();
  }

  async function resetDemo() {
    setBusy("清空记录");
    setError("");
    try {
      await api("/api/v1/companion/demo/reset", { method: "POST", body: JSON.stringify({}) }, token);
      setConversationId(null);
      setTurn(null);
      setText("我有点累，不知道现在该做什么。");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  async function seedBedroomDemo() {
    setBusy("写入卧室习惯");
    setError("");
    try {
      const result = await api<{ conversation_id: string; prompt: string; seeded: Record<string, unknown> }>(
        "/api/v1/companion/demo/sample",
        { method: "POST", body: JSON.stringify({}) },
        token
      );
      setConversationId(result.conversation_id);
      setTurn(null);
      setText(result.prompt);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  const recentHistory = useMemo(() => history.slice(0, 8), [history]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <strong>Spare-Time Companion</strong>
          <span>{user.display_name} · {user.role}</span>
        </div>
        <button className="icon-button" onClick={logout} title="退出"><LogOut size={18} /></button>
      </header>

      <section className="workspace">
        <div className="device-column">
          <div className={`device ${expression}`}>
            <div className="screen">
              <div className="status-row"><Radio size={16} /> {statusText}</div>
              <Face expression={expression} />
            </div>
            <div className="hardware">
              <button title="模拟物理按钮" onClick={() => sendText("button")} disabled={!!busy}>
                <Power size={22} />
              </button>
              <button title="重新生成" onClick={() => feedback("regenerate")} disabled={!turn}>
                <RefreshCcw size={22} />
              </button>
            </div>
          </div>
          <audio ref={audioRef} controls />
        </div>

        <div className="control-column">
          <section className="panel demo-tools">
            <div className="panel-title"><Home size={18} /> Demo 场景</div>
            <div className="button-row">
              <button onClick={seedBedroomDemo} disabled={!!busy}><BookOpen size={17} /> 写入卧室习惯</button>
              <button className="danger" onClick={resetDemo} disabled={!!busy}><Trash2 size={17} /> 重置记录</button>
            </div>
            <p>示例会写入“卧室床头柜、睡前阅读、低刺激放松”等习惯，然后把输入框改成当前时间相关的问题。</p>
          </section>

          <section className="panel composer">
            <div className="panel-title"><Activity size={18} /> 实时对话</div>
            <textarea value={text} onChange={(event) => setText(event.target.value)} />
            <div className="button-row">
              <button className="primary" onClick={() => sendText()} disabled={!!busy}><Send size={17} /> 发送文本</button>
              <button onClick={sendVoice} disabled={!!busy}><Mic size={17} /> 录音 4 秒</button>
            </div>
            {error && <div className="error">{error}</div>}
          </section>

          <section className="panel response">
            <div className="panel-title"><ClipboardList size={18} /> 本轮响应</div>
            <div className="response-grid">
              <span>转写</span><p>{turn?.transcript ?? "暂无"}</p>
              <span>播报</span><p>{turn?.speech_text ?? "暂无"}</p>
              <span>动作</span><p>{turn?.action ?? "idle"} · {turn?.expression ?? "idle"}</p>
            </div>
            <div className="button-row compact">
              <button onClick={() => feedback("positive")} disabled={!turn}>满意</button>
              <button onClick={() => feedback("negative")} disabled={!turn}>不合适</button>
              <button onClick={() => feedback("dismiss")} disabled={!turn}>忽略</button>
            </div>
          </section>
        </div>

        <aside className="side-column">
          <section className="panel">
            <div className="panel-title">历史</div>
            <div className="log-list">
              {recentHistory.map((item) => (
                <article key={item.id} className={item.role}>
                  <strong>{item.role}</strong>
                  <p>{item.content}</p>
                </article>
              ))}
            </div>
          </section>
          <section className="panel">
            <div className="panel-title">Agent 摘要</div>
            <div className="run-list">
              {agentRuns.slice(0, 5).map((item) => (
                <pre key={String(item.id)}>{JSON.stringify(item, null, 2)}</pre>
              ))}
            </div>
          </section>
          {user.role === "admin" && (
            <section className="panel">
              <div className="panel-title">邀请码</div>
              <div className="inline-form">
                <input
                  type="number"
                  min={1}
                  max={720}
                  value={inviteTtlHours}
                  onChange={(event) => setInviteTtlHours(Number(event.target.value))}
                  title="有效期小时数"
                />
                <button onClick={createInvite}>生成</button>
              </div>
              <div className="invite-list">
                {invites.map((invite) => (
                  <span key={invite.id}>
                    {invite.code} {invite.used_count}/{invite.max_uses} · 到期 {new Date(invite.expires_at).toLocaleString()}
                  </span>
                ))}
              </div>
            </section>
          )}
        </aside>
      </section>
    </main>
  );
}

function desktopState() {
  return {
    presence: "at_desk",
    active_app: "demo-web-client",
    idle_minutes: 12,
    is_playing_audio: false,
    local_time: new Date().toISOString()
  };
}

function Face({ expression }: { expression: string }) {
  return (
    <div className={`face ${expression}`}>
      <span className="eye" />
      <span className="eye" />
      <span className="mouth" />
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
