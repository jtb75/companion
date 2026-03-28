import { useState, useEffect, useRef } from "react";

// ── Palette ──────────────────────────────────────────────────────────────────
const C = {
  cream: "#FAF7F2",
  warmWhite: "#FFFEF9",
  softBlue: "#E8F0FA",
  blue: "#2C5F8A",
  blueMid: "#3D7AB5",
  blueLight: "#6FA3D0",
  teal: "#2A7A6F",
  tealLight: "#E6F4F2",
  amber: "#D4832A",
  amberLight: "#FDF3E7",
  rose: "#C0444A",
  roseLight: "#FDECEA",
  sage: "#4A7C59",
  sageLight: "#EAF2EC",
  text: "#1A1A2E",
  textMid: "#4A4A6A",
  textSoft: "#8A8AAA",
  border: "#E2DDD6",
  shadow: "rgba(44,95,138,0.12)",
};

// ── Arlo Avatar ───────────────────────────────────────────────────────────────
function ArloAvatar({ size = 56, speaking = false, color = C.blue }) {
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      {speaking && (
        <div style={{
          position: "absolute", inset: -6,
          borderRadius: "50%",
          background: `${color}22`,
          animation: "pulse 1.4s ease-in-out infinite",
        }} />
      )}
      <div style={{
        width: size, height: size,
        borderRadius: "50%",
        background: `linear-gradient(135deg, ${color} 0%, ${C.blueMid} 100%)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: `0 4px 16px ${C.shadow}`,
        fontSize: size * 0.42,
      }}>
        🌟
      </div>
    </div>
  );
}

// ── Arlo Speech Bubble ────────────────────────────────────────────────────────
function ArloBubble({ text, speaking = true, small = false }) {
  const [shown, setShown] = useState("");
  const [done, setDone] = useState(false);
  const idx = useRef(0);

  useEffect(() => {
    setShown(""); setDone(false); idx.current = 0;
    if (!text) return;
    const timer = setInterval(() => {
      idx.current += 2;
      setShown(text.slice(0, idx.current));
      if (idx.current >= text.length) { setDone(true); clearInterval(timer); }
    }, 18);
    return () => clearInterval(timer);
  }, [text]);

  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 4 }}>
      <ArloAvatar size={small ? 40 : 48} speaking={!done && speaking} />
      <div style={{
        background: C.warmWhite,
        border: `1.5px solid ${C.border}`,
        borderRadius: "4px 18px 18px 18px",
        padding: small ? "10px 14px" : "14px 18px",
        maxWidth: "100%",
        boxShadow: `0 2px 8px ${C.shadow}`,
        flex: 1,
      }}>
        <p style={{
          margin: 0,
          fontSize: small ? 15 : 17,
          lineHeight: 1.55,
          color: C.text,
          fontFamily: "'Georgia', serif",
          fontWeight: 400,
        }}>
          {shown}
          {!done && <span style={{ opacity: 0.4, animation: "blink 0.8s step-end infinite" }}>|</span>}
        </p>
      </div>
    </div>
  );
}

// ── Big Button ────────────────────────────────────────────────────────────────
function BigBtn({ label, sub, emoji, onClick, color = C.blue, light = false, active = false }) {
  const [hover, setHover] = useState(false);
  const bg = active ? color : light ? (hover ? C.softBlue : C.warmWhite) : (hover ? C.blueMid : color);
  const fg = active || !light ? "#fff" : C.blue;
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: "100%", padding: sub ? "14px 18px" : "16px 20px",
        background: bg,
        border: `2px solid ${active || !light ? "transparent" : C.border}`,
        borderRadius: 16, cursor: "pointer",
        textAlign: "left", display: "flex", alignItems: "center", gap: 14,
        transition: "all 0.18s ease",
        transform: hover ? "translateY(-1px)" : "none",
        boxShadow: hover ? `0 6px 20px ${C.shadow}` : `0 2px 8px ${C.shadow}`,
      }}>
      {emoji && <span style={{ fontSize: 26 }}>{emoji}</span>}
      <div>
        <div style={{ fontSize: 16, fontWeight: 700, color: fg, letterSpacing: 0.2 }}>{label}</div>
        {sub && <div style={{ fontSize: 13, color: active || !light ? "rgba(255,255,255,0.8)" : C.textSoft, marginTop: 2 }}>{sub}</div>}
      </div>
    </button>
  );
}

// ── Primary CTA ───────────────────────────────────────────────────────────────
function PrimaryBtn({ label, onClick, disabled = false }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick} disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: "100%", padding: "18px",
        background: disabled ? C.border : hover ? C.blueMid : C.blue,
        color: disabled ? C.textSoft : "#fff",
        border: "none", borderRadius: 18, cursor: disabled ? "default" : "pointer",
        fontSize: 17, fontWeight: 700, letterSpacing: 0.3,
        transition: "all 0.18s ease",
        transform: !disabled && hover ? "translateY(-1px)" : "none",
        boxShadow: disabled ? "none" : `0 4px 16px ${C.shadow}`,
      }}>{label}</button>
  );
}

// ── Text Input ────────────────────────────────────────────────────────────────
function TextIn({ placeholder, value, onChange }) {
  return (
    <input
      type="text" placeholder={placeholder} value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        width: "100%", padding: "16px 18px",
        fontSize: 18, fontFamily: "'Georgia', serif",
        background: C.warmWhite, border: `2px solid ${C.border}`,
        borderRadius: 16, outline: "none", color: C.text,
        boxSizing: "border-box",
        transition: "border-color 0.2s",
      }}
      onFocus={e => e.target.style.borderColor = C.blue}
      onBlur={e => e.target.style.borderColor = C.border}
    />
  );
}

// ── Progress Dots ─────────────────────────────────────────────────────────────
function ProgressDots({ total, current }) {
  return (
    <div style={{ display: "flex", gap: 6, justifyContent: "center", marginBottom: 8 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{
          width: i === current ? 20 : 8, height: 8,
          borderRadius: 4,
          background: i === current ? C.blue : i < current ? C.blueLight : C.border,
          transition: "all 0.3s ease",
        }} />
      ))}
    </div>
  );
}

// ── Screen: Welcome ───────────────────────────────────────────────────────────
function WelcomeScreen({ onNext }) {
  const [name, setName] = useState("");
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setStep(1), 200);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, flex: 1 }}>
      <div style={{ textAlign: "center", paddingTop: 8 }}>
        <div style={{ fontSize: 42, marginBottom: 4 }}>🌟</div>
        <div style={{ fontSize: 24, fontWeight: 800, color: C.blue, letterSpacing: -0.5, fontFamily: "'Georgia', serif" }}>
          Companion
        </div>
        <div style={{ fontSize: 13, color: C.textSoft, marginTop: 2 }}>powered by Arlo</div>
      </div>

      {step >= 1 && (
        <div style={{ animation: "fadeUp 0.5s ease" }}>
          <ArloBubble text="Hi there. I'm Arlo. I'm here to help you stay on top of things — your mail, your appointments, your medications, and whatever else you need." />
        </div>
      )}

      {step >= 1 && (
        <div style={{ animation: "fadeUp 0.5s ease 0.2s both" }}>
          <ArloBubble text="Before we get started, can I ask your name?" speaking={false} />
        </div>
      )}

      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
        <TextIn placeholder="Your name…" value={name} onChange={setName} />
        <PrimaryBtn label="That's me →" onClick={() => onNext(name)} disabled={name.trim().length < 1} />
      </div>
    </div>
  );
}

// ── Screen: Voice ─────────────────────────────────────────────────────────────
const VOICES = [
  { id: "warm", label: "Warm", desc: "Friendly and gentle. Feels like a good friend.", emoji: "☀️" },
  { id: "calm", label: "Calm", desc: "Steady and relaxed. Easy to listen to.", emoji: "🌊" },
  { id: "bright", label: "Bright", desc: "Upbeat and cheerful. Always sounds positive.", emoji: "✨" },
  { id: "clear", label: "Clear", desc: "Simple and direct. Easy to understand.", emoji: "🔔" },
];

function VoiceScreen({ name, onNext }) {
  const [selected, setSelected] = useState(null);
  const [playing, setPlaying] = useState(null);

  const preview = (id) => {
    setPlaying(id);
    setTimeout(() => setPlaying(null), 1800);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18, flex: 1 }}>
      <ArloBubble text={`Great to meet you, ${name}! First — I want to make sure I sound right to you. Tap a voice to hear it.`} />

      <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
        {VOICES.map(v => (
          <div key={v.id} style={{ position: "relative" }}>
            <BigBtn
              label={`${v.emoji}  ${v.label}`} sub={v.desc}
              light active={selected === v.id}
              onClick={() => { setSelected(v.id); preview(v.id); }}
            />
            {playing === v.id && (
              <div style={{
                position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)",
                display: "flex", gap: 3, alignItems: "center",
              }}>
                {[0, 1, 2, 3].map(i => (
                  <div key={i} style={{
                    width: 3, height: 6 + i * 4,
                    background: selected === v.id ? "rgba(255,255,255,0.8)" : C.blue,
                    borderRadius: 2,
                    animation: `wave 0.6s ease-in-out ${i * 0.1}s infinite alternate`,
                  }} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div>
        {selected && (
          <p style={{ textAlign: "center", fontSize: 14, color: C.textMid, marginBottom: 10, fontStyle: "italic" }}>
            You can change this anytime — just ask me.
          </p>
        )}
        <PrimaryBtn label="This is my Arlo →" onClick={() => onNext(selected)} disabled={!selected} />
      </div>
    </div>
  );
}

// ── Screen: The Question ──────────────────────────────────────────────────────
const PRIORITIES = [
  { id: "bills", label: "Bills and mail", desc: "Confusing letters, due dates, what to pay", emoji: "📬" },
  { id: "appointments", label: "Doctor appointments", desc: "Keeping track, knowing when to leave", emoji: "🏥" },
  { id: "medications", label: "Medications", desc: "Remembering to take them, refills", emoji: "💊" },
  { id: "todos", label: "Things to do", desc: "Tasks, errands, shopping", emoji: "✅" },
  { id: "email", label: "Understanding what's important", desc: "Connect Gmail — I'll find what matters", emoji: "📧" },
];

function QuestionScreen({ name, onNext }) {
  const [selected, setSelected] = useState(null);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
      <ArloBubble text={`${name}, what's the one thing you find hardest to keep track of?`} />

      <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
        {PRIORITIES.map(p => (
          <BigBtn
            key={p.id} label={p.label} sub={p.desc} emoji={p.emoji}
            light active={selected === p.id}
            onClick={() => setSelected(p.id)}
          />
        ))}
      </div>

      <PrimaryBtn label="Let's start there →" onClick={() => onNext(selected)} disabled={!selected} />
    </div>
  );
}

// ── Screen: First Win ─────────────────────────────────────────────────────────
const WIN_FLOWS = {
  bills: {
    prompt: "What's one bill you pay every month? I'll add it and remind you before it's due.",
    placeholder: "e.g. Electric bill",
    action: "Add this bill",
    confirm: (v) => `Done. I've added your ${v} and I'll remind you 5 days before it's due. That's in My Money now.`,
    emoji: "📬",
  },
  appointments: {
    prompt: "Do you have a doctor's appointment coming up? Tell me who it's with and I'll add it.",
    placeholder: "e.g. Dr. Johnson, Tuesday at 2pm",
    action: "Add this appointment",
    confirm: (v) => `Done. I've added your appointment with ${v} to My Health. I'll remind you the day before and help you plan your trip.`,
    emoji: "🏥",
  },
  medications: {
    prompt: "What's one medication you take every day? I'll set up a reminder for you.",
    placeholder: "e.g. Metformin, morning",
    action: "Set up reminder",
    confirm: (v) => `Done. I've set a morning reminder for ${v}. I'll ask you each day if you took it. We can add more medications anytime.`,
    emoji: "💊",
  },
  todos: {
    prompt: "What's one thing you need to do this week? I'll add it to your list.",
    placeholder: "e.g. Call the pharmacy",
    action: "Add to my list",
    confirm: (v) => `Done. I've added "${v}" to your plans. I'll check in with you about it tomorrow morning.`,
    emoji: "✅",
  },
  email: {
    prompt: "I'd like to connect to your Gmail so I can find what's important and explain it to you. Is that okay?",
    placeholder: null,
    action: "Connect Gmail",
    confirm: () => `Connected. I found something in your email — your electric bill arrived. It's $74 and due in 11 days. Want me to add a reminder?`,
    emoji: "📧",
  },
};

function FirstWinScreen({ name, priority, onNext }) {
  const flow = WIN_FLOWS[priority] || WIN_FLOWS.todos;
  const [value, setValue] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const handleAction = () => {
    const text = flow.confirm(value || "that");
    setConfirmText(text);
    setConfirmed(true);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
      <div style={{
        background: C.tealLight, border: `1.5px solid ${C.teal}22`,
        borderRadius: 16, padding: "12px 16px",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <span style={{ fontSize: 24 }}>{flow.emoji}</span>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.teal, textTransform: "uppercase", letterSpacing: 1 }}>First Win</div>
          <div style={{ fontSize: 13, color: C.textMid }}>Let's do something useful right now</div>
        </div>
      </div>

      {!confirmed ? (
        <>
          <ArloBubble text={flow.prompt} />

          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: "auto" }}>
            {flow.placeholder && (
              <TextIn placeholder={flow.placeholder} value={value} onChange={setValue} />
            )}
            {!flow.placeholder && (
              <div style={{
                background: C.softBlue, borderRadius: 16, padding: "16px",
                textAlign: "center", fontSize: 14, color: C.textMid,
              }}>
                🔒 Your email is read-only. Arlo cannot send email on your behalf.
              </div>
            )}
            <PrimaryBtn
              label={`${flow.action} →`}
              onClick={handleAction}
              disabled={flow.placeholder && value.trim().length < 1}
            />
          </div>
        </>
      ) : (
        <>
          <ArloBubble text={confirmText} />
          <div style={{
            background: C.sageLight, border: `1.5px solid ${C.sage}33`,
            borderRadius: 16, padding: "16px",
            display: "flex", alignItems: "center", gap: 12,
          }}>
            <span style={{ fontSize: 28 }}>✓</span>
            <div style={{ fontSize: 15, color: C.sage, fontWeight: 600 }}>
              That's your first thing handled.
            </div>
          </div>
          <div style={{ marginTop: "auto" }}>
            <PrimaryBtn label="Keep going →" onClick={onNext} />
          </div>
        </>
      )}
    </div>
  );
}

// ── Screen: Demarcation ───────────────────────────────────────────────────────
function DemarcScreen({ name, onContinue, onDone }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, flex: 1 }}>
      <div style={{
        background: `linear-gradient(135deg, ${C.blue} 0%, ${C.teal} 100%)`,
        borderRadius: 20, padding: "24px 20px", textAlign: "center",
        color: "#fff",
      }}>
        <div style={{ fontSize: 36, marginBottom: 8 }}>🌅</div>
        <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 4, fontFamily: "'Georgia', serif" }}>
          You're all set, {name}.
        </div>
        <div style={{ fontSize: 14, opacity: 0.85, lineHeight: 1.5 }}>
          I'll check in with you tomorrow morning. If you need anything before then, just tap the button and I'm here.
        </div>
      </div>

      <ArloBubble text="We can also set up a few more things right now — like connecting your email or adding a trusted contact. Or we can do that later, whenever you're ready." speaking={false} />

      <div style={{ background: C.softBlue, borderRadius: 16, padding: "14px 16px" }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: C.blue, marginBottom: 8 }}>What's next (optional):</div>
        {["Connect Gmail or email", "Add a trusted contact", "Set up more medications", "Choose what your support worker can see"].map((item, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.blueLight }} />
            <span style={{ fontSize: 13, color: C.textMid }}>{item}</span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
        <PrimaryBtn label="Keep going — set up more →" onClick={onContinue} />
        <button
          onClick={onDone}
          style={{
            width: "100%", padding: "14px",
            background: "transparent", border: `2px solid ${C.border}`,
            borderRadius: 16, cursor: "pointer",
            fontSize: 16, color: C.textMid, fontWeight: 600,
          }}>
          I'm done for now
        </button>
      </div>
    </div>
  );
}

// ── Screen: Home ──────────────────────────────────────────────────────────────
function HomeScreen({ name }) {
  const tabs = [
    { id: "home", label: "Home", emoji: "🏠" },
    { id: "health", label: "My Health", emoji: "❤️" },
    { id: "money", label: "My Money", emoji: "💵" },
    { id: "plans", label: "My Plans", emoji: "📋" },
  ];
  const [activeTab, setActiveTab] = useState("home");

  const cards = {
    home: [
      { emoji: "📬", title: "Electric bill arrived", sub: "$74 due in 11 days", color: C.amberLight, accent: C.amber, tag: "My Money" },
      { emoji: "💊", title: "Morning medications", sub: "Tap when you've taken them", color: C.tealLight, accent: C.teal, tag: "Reminder" },
      { emoji: "🏥", title: "Dr. Johnson — Tuesday", sub: "2:00 PM · Leave by 1:15", color: C.softBlue, accent: C.blue, tag: "My Health" },
    ],
    health: [
      { emoji: "💊", title: "Metformin", sub: "Daily · 8:00 AM · ✓ Taken today", color: C.tealLight, accent: C.teal, tag: "Medication" },
      { emoji: "🏥", title: "Dr. Johnson", sub: "Tuesday at 2pm · Primary Care", color: C.softBlue, accent: C.blue, tag: "Appointment" },
      { emoji: "🔄", title: "Metformin refill", sub: "Due in 8 days · CVS Pharmacy", color: C.amberLight, accent: C.amber, tag: "Pharmacy" },
    ],
    money: [
      { emoji: "⚡", title: "Electric bill", sub: "$74 · Due in 11 days", color: C.amberLight, accent: C.amber, tag: "Needs Attention" },
      { emoji: "🏠", title: "Rent", sub: "$850 · Due in 18 days", color: C.sageLight, accent: C.sage, tag: "Upcoming" },
      { emoji: "📱", title: "Phone bill", sub: "$45 · Paid ✓", color: C.softBlue, accent: C.blue, tag: "Handled" },
    ],
    plans: [
      { emoji: "📞", title: "Call the pharmacy", sub: "Added today", color: C.softBlue, accent: C.blue, tag: "To Do" },
      { emoji: "🛒", title: "Grocery trip", sub: "Paper towels, milk, bread", color: C.sageLight, accent: C.sage, tag: "Errand" },
      { emoji: "🚌", title: "Bus route to Dr. Johnson", sub: "34 bus · Leave 1:15 PM Tuesday", color: C.tealLight, accent: C.teal, tag: "Travel" },
    ],
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{
        background: `linear-gradient(135deg, ${C.blue} 0%, ${C.teal} 100%)`,
        padding: "16px 20px 20px", color: "#fff",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 13, opacity: 0.8 }}>Good morning</div>
            <div style={{ fontSize: 22, fontWeight: 800, fontFamily: "'Georgia', serif" }}>{name} 👋</div>
          </div>
          <ArloAvatar size={44} color="#fff" />
        </div>
        <div style={{
          background: "rgba(255,255,255,0.15)", borderRadius: 12,
          padding: "10px 14px", fontSize: 14, opacity: 0.95,
        }}>
          🗓 It's Tuesday. You have 2 things that need attention today.
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex", background: C.warmWhite,
        borderBottom: `1.5px solid ${C.border}`,
        padding: "0 4px",
      }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            flex: 1, padding: "10px 4px",
            background: "transparent",
            border: "none", cursor: "pointer",
            borderBottom: activeTab === t.id ? `3px solid ${C.blue}` : "3px solid transparent",
            fontSize: 11, fontWeight: 700,
            color: activeTab === t.id ? C.blue : C.textSoft,
            display: "flex", flexDirection: "column", alignItems: "center", gap: 2,
            transition: "all 0.2s",
          }}>
            <span style={{ fontSize: 18 }}>{t.emoji}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Cards */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 12 }}>
        {cards[activeTab].map((card, i) => (
          <div key={i} style={{
            background: card.color,
            border: `1.5px solid ${card.accent}33`,
            borderRadius: 16, padding: "14px 16px",
            display: "flex", alignItems: "center", gap: 14,
            boxShadow: `0 2px 8px ${C.shadow}`,
            cursor: "pointer",
          }}>
            <span style={{ fontSize: 28 }}>{card.emoji}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: C.text }}>{card.title}</div>
              <div style={{ fontSize: 13, color: C.textMid, marginTop: 2 }}>{card.sub}</div>
            </div>
            <div style={{
              background: `${card.accent}22`, color: card.accent,
              fontSize: 11, fontWeight: 700, padding: "3px 8px",
              borderRadius: 8, whiteSpace: "nowrap",
            }}>{card.tag}</div>
          </div>
        ))}

        {/* Arlo Floating Button */}
        <div style={{ textAlign: "center", marginTop: 8 }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 10,
            background: C.blue, color: "#fff",
            borderRadius: 50, padding: "12px 24px",
            fontSize: 15, fontWeight: 700,
            boxShadow: `0 4px 16px ${C.shadow}`,
            cursor: "pointer",
          }}>
            <span style={{ fontSize: 20 }}>🌟</span>
            Ask Arlo anything
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState("welcome");
  const [userData, setUserData] = useState({ name: "", voice: null, priority: null });

  const go = (s, updates = {}) => {
    setUserData(prev => ({ ...prev, ...updates }));
    setScreen(s);
  };

  const screens = {
    welcome: <WelcomeScreen onNext={name => go("voice", { name })} />,
    voice: <VoiceScreen name={userData.name} onNext={voice => go("question", { voice })} />,
    question: <QuestionScreen name={userData.name} onNext={priority => go("firstwin", { priority })} />,
    firstwin: <FirstWinScreen name={userData.name} priority={userData.priority} onNext={() => go("demarc")} />,
    demarc: <DemarcScreen name={userData.name} onContinue={() => go("home")} onDone={() => go("home")} />,
    home: <HomeScreen name={userData.name || "Sam"} />,
  };

  const stepMap = { welcome: 0, voice: 1, question: 2, firstwin: 3, demarc: 4, home: 5 };
  const step = stepMap[screen] ?? 0;
  const isHome = screen === "home";

  const screenLabels = {
    welcome: "Meeting Arlo",
    voice: "Choose your voice",
    question: "What matters most",
    firstwin: "Your first win",
    demarc: "Session 1 complete",
    home: "Home",
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: `linear-gradient(135deg, ${C.softBlue} 0%, ${C.cream} 60%, #F0EDE8 100%)`,
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "20px",
      fontFamily: "'Helvetica Neue', 'Arial', sans-serif",
    }}>
      <style>{`
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px) } to { opacity:1; transform:none } }
        @keyframes pulse { 0%,100% { transform:scale(1); opacity:0.5 } 50% { transform:scale(1.15); opacity:0.2 } }
        @keyframes blink { 0%,100% { opacity:1 } 50% { opacity:0 } }
        @keyframes wave { from { transform:scaleY(0.4) } to { transform:scaleY(1.2) } }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px }
        ::-webkit-scrollbar-track { background: transparent }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 2px }
      `}</style>

      {/* Desktop label */}
      <div style={{ maxWidth: 480, width: "100%" }}>
        <div style={{
          textAlign: "center", marginBottom: 16,
          fontSize: 13, color: C.textSoft, letterSpacing: 0.5,
          textTransform: "uppercase", fontWeight: 600,
        }}>
          🌟 Companion — Interactive Mockup
        </div>

        {/* Phone frame */}
        <div style={{
          background: "#1A1A2E",
          borderRadius: 44, padding: "12px",
          boxShadow: "0 24px 80px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.05)",
          maxWidth: 390, margin: "0 auto",
        }}>
          {/* Status bar */}
          <div style={{
            background: C.warmWhite, borderRadius: 34,
            overflow: "hidden",
          }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 20px 6px", fontSize: 12, fontWeight: 600, color: C.textMid,
            }}>
              <span>9:41</span>
              <div style={{
                width: 80, height: 20, background: "#1A1A2E",
                borderRadius: 10, margin: "-2px auto 0",
              }} />
              <span>●●●</span>
            </div>

            {/* Screen header */}
            {!isHome && (
              <div style={{
                padding: "8px 20px 12px",
                borderBottom: `1px solid ${C.border}`,
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <div style={{ fontSize: 13, color: C.textSoft, fontWeight: 600 }}>
                  {screenLabels[screen]}
                </div>
                <ProgressDots total={5} current={Math.min(step, 4)} />
              </div>
            )}

            {/* Screen content */}
            <div style={{
              padding: isHome ? 0 : "16px 20px 24px",
              minHeight: isHome ? 580 : 520,
              display: "flex", flexDirection: "column",
              background: isHome ? C.cream : C.cream,
              borderRadius: "0 0 34px 34px",
            }}>
              <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                {screens[screen]}
              </div>
            </div>
          </div>
        </div>

        {/* Navigation hint */}
        <div style={{
          textAlign: "center", marginTop: 16,
          fontSize: 12, color: C.textSoft,
        }}>
          {screen !== "welcome" && (
            <button
              onClick={() => {
                const prev = { voice: "welcome", question: "voice", firstwin: "question", demarc: "firstwin", home: "demarc" };
                if (prev[screen]) setScreen(prev[screen]);
              }}
              style={{
                background: "none", border: `1px solid ${C.border}`,
                borderRadius: 8, padding: "6px 14px",
                fontSize: 12, color: C.textSoft, cursor: "pointer",
                marginRight: 8,
              }}>
              ← Back
            </button>
          )}
          <span>Step {step + 1} of 5 — {screenLabels[screen]}</span>
        </div>
      </div>
    </div>
  );
}
