import { useState, useRef, useEffect } from "react";

// ── Design tokens ──────────────────────────────────────────────────────────
const C = {
  bg: "#0B0F1A",
  surface: "#111827",
  surfaceAlt: "#1A2235",
  border: "#1E2D45",
  accent: "#3B7EF6",
  accentSoft: "#1E3A6E",
  accentGlow: "rgba(59,126,246,0.15)",
  gold: "#F5A623",
  goldSoft: "rgba(245,166,35,0.12)",
  text: "#E8EDF5",
  textMuted: "#7B8FA8",
  textDim: "#4A5E78",
  success: "#22C55E",
  warning: "#F59E0B",
  danger: "#EF4444",
  green: "#10B981",
};

// ── Agent routing logic (mirrors Python agents) ───────────────────────────
function buildSystemPrompt(agentType) {
  const base = `You are TalentPulse360, an AI HR analytics assistant. You have access to these gold tables:
- gold.talentpulse.gold_employee_360 (cols: employee_id, employee_name, email, department, designation, location, date_of_joining, employment_type, manager_name, tenure_years, primary_skills, attendance_percentage, present_days, leave_days, wfh_days, avg_effective_hours_per_day, total_effective_hours, attendance_trend, last_attendance_date, total_trainings_assigned, trainings_completed, training_completion_percentage, total_training_hours, total_kras, weighted_performance_score, performance_band, avg_self_rating, avg_manager_rating, avg_final_rating, top_performing_areas, improvement_areas, composite_talent_score, attendance_risk_flag, training_risk_flag, performance_risk_flag, employee_health_status, created_at, updated_at)
- gold.talentpulse.gold_employee_attendance_summary (cols: employee_id, current_month, total_days_recorded, present_days, absent_days, leave_days, wfh_days, half_days, avg_effective_hours_per_day, total_effective_hours, avg_break_time_minutes, total_overtime_hours, attendance_percentage, avg_effective_hours_last_3m, present_days_last_3m, attendance_trend, last_attendance_date, last_attendance_status)
- gold.talentpulse.gold_employee_performance_summary (cols: employee_id, total_kras, avg_self_rating, avg_manager_rating, avg_final_rating, weighted_performance_score, excellent_ratings_count, good_ratings_count, average_ratings_count, below_average_ratings_count, performance_band, avg_rating_gap, latest_evaluation_period, latest_final_rating, top_performing_areas, improvement_areas)
- gold.talentpulse.gold_employee_training_summary (cols: employee_id, total_trainings_assigned, trainings_completed, trainings_in_progress, trainings_not_started, trainings_pending, trainings_skipped, training_completion_percentage, total_training_hours, avg_training_hours_per_course, weighted_progress_score, last_training_completed_date, last_training_completed, last_training_assigned_date)
- gold.talentpulse.gold_employee_ranking (cols: employee_id, employee_name, department, designation, composite_talent_score, weighted_performance_score, attendance_percentage, training_completion_percentage, overall_rank, overall_percentile, department_rank, total_in_department, department_percentile, designation_rank, total_in_designation, performance_rank, performance_quartile, attendance_rank, training_rank, ranking_category, performance_tier)
- gold.talentpulse.gold_employee_ai_features (cols: employee_id, employee_name, department, designation, attendance_percentage, avg_effective_hours_per_day, leave_days, wfh_days, avg_break_time_normalized, attendance_trend_numeric, training_completion_percentage, trainings_completed, total_training_hours, weighted_performance_score, avg_self_rating, avg_manager_rating, avg_final_rating, tenure_years, tenure_months, composite_talent_score, predicted_next_month_attendance, predicted_next_quarter_performance, prediction_confidence, department_encoded, employment_type_encoded, attendance_risk, training_risk, performance_risk)
- gold.talentpulse.gold_promotion_readiness (cols: employee_id, employee_name, department, designation, tenure_years, composite_talent_score, tenure_eligible, performance_eligible, attendance_eligible, training_eligible, promotion_readiness_score, promotion_readiness_status, tenure_gap, performance_gap, attendance_gap, training_gap, recommended_next_designation, estimated_months_to_promotion)

You cannot actually run queries, but you must respond as if you have the data. Generate realistic, structured answers based on the schema. Format your responses with emojis and markdown-style bold text. Be concise (3-6 lines max). Always include the employee name and relevant metric values.`;

  const agentInstructions = {
    attendance: `${base}\n\nYou are the ATTENDANCE AGENT. Focus exclusively on: attendance %, present days, absent days, WFH days, leave days, effective hours, attendance trends, and attendance risk flags. Use gold_employee_attendance_summary and gold_employee_360.`,
    performance: `${base}\n\nYou are the PERFORMANCE AGENT. Focus on: KRA scores, self ratings, manager ratings, final ratings, performance band (Meets Expectations/Exceeds/etc), top performing areas, improvement areas, weighted performance scores. Use gold_employee_performance_summary and gold_employee_360.`,
    training: `${base}\n\nYou are the TRAINING AGENT. Focus on: trainings assigned vs completed, in-progress, pending, skipped, training hours, completion %, last training completed. Use gold_employee_training_summary and gold_employee_360.`,
    skills: `${base}\n\nYou are the SKILLS AGENT. Focus on: primary_skills from gold_employee_360, designation-based skill gaps, what skills they have vs what their designation typically requires. Suggest upskilling paths.`,
    employee360: `${base}\n\nYou are the EMPLOYEE 360 AGENT. Provide a comprehensive profile combining all dimensions: attendance, performance, training, skills, tenure, composite talent score, health status, risk flags, and promotion readiness from gold_employee_360 and gold_promotion_readiness.`,
    workforce: `${base}\n\nYou are the WORKFORCE AGENT. Handle aggregate questions: top performers, low attendance lists, employees needing training, promotion-ready employees, department summaries, ranking insights. Use gold_employee_ranking and gold_employee_360.`,
    prediction: `${base}\n\nYou are the PREDICTION AGENT. Focus on AI predictions: predicted_next_month_attendance, predicted_next_quarter_performance, prediction_confidence, composite_talent_score trends, promotion readiness scores and timelines from gold_employee_ai_features and gold_promotion_readiness.`,
    general: base,
  };
  return agentInstructions[agentType] || base;
}

function detectAgent(question) {
  const q = question.toLowerCase();
  if (/attendance|present|absent|wfh|leave|hours|check.?in|trend/.test(q)) return "attendance";
  if (/performance|kra|rating|score|band|manager.?rating|self.?rating|appraisal/.test(q)) return "performance";
  if (/train|course|learning|certif|completion|pending train/.test(q)) return "training";
  if (/skill|technolog|python|java|ml|ai|gap|certif/.test(q)) return "skills";
  if (/360|complete.?profile|overall|composite|health|risk/.test(q)) return "employee360";
  if (/top performer|low attend|rank|workforce|department|all employee|list of/.test(q)) return "workforce";
  if (/predict|forecast|next month|next quarter|promotion.?read|when.*promot/.test(q)) return "prediction";
  if (/360|profile|summary/.test(q)) return "employee360";
  return "general";
}

const AGENT_LABELS = {
  attendance: { label: "Attendance Agent", icon: "📅", color: C.accent },
  performance: { label: "Performance Agent", icon: "🏆", color: C.gold },
  training: { label: "Training Agent", icon: "🎓", color: C.green },
  skills: { label: "Skills Agent", icon: "🧩", color: "#A855F7" },
  employee360: { label: "360° Agent", icon: "🌐", color: "#06B6D4" },
  workforce: { label: "Workforce Agent", icon: "👥", color: "#F97316" },
  prediction: { label: "Prediction Agent", icon: "🤖", color: "#EC4899" },
  general: { label: "TalentPulse AI", icon: "✨", color: C.accent },
};

// ── Quick-action chips ─────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { label: "Attendance summary", icon: "📅", prompt: "Show attendance summary for Bhavani Shaganti" },
  { label: "Performance score", icon: "🏆", prompt: "What is the performance score of Bhavani Shaganti?" },
  { label: "Training status", icon: "🎓", prompt: "Show training completion for Bhavani Shaganti" },
  { label: "Skills profile", icon: "🧩", prompt: "What skills does Bhavani Shaganti have?" },
  { label: "Top performers", icon: "🌟", prompt: "Who are the top performers in AI/ML department?" },
  { label: "360° profile", icon: "🌐", prompt: "Show complete 360 profile for Bhavani Shaganti" },
  { label: "Promotion readiness", icon: "🚀", prompt: "Is Bhavani Shaganti ready for promotion?" },
  { label: "Low attendance", icon: "⚠️", prompt: "Show employees with low attendance" },
];

// ── API call ───────────────────────────────────────────────────────────────
async function callAgent(messages, agentType) {
  const systemPrompt = buildSystemPrompt(agentType);
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1000,
      system: systemPrompt,
      messages: messages.map(m => ({ role: m.role, content: m.content })),
    }),
  });
  const data = await response.json();
  return data.content?.[0]?.text || "No response received.";
}

// ── Markdown renderer (simple) ─────────────────────────────────────────────
function renderMarkdown(text) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    line = line.replace(/\*\*(.+?)\*\*/g, (_, t) => `<strong>${t}</strong>`);
    line = line.replace(/\*(.+?)\*/g, (_, t) => `<em>${t}</em>`);
    const isListItem = /^[\-\*•]\s/.test(line.trim());
    if (isListItem) {
      return <div key={i} style={{ display: "flex", gap: 8, marginBottom: 4 }}>
        <span style={{ color: C.accent, flexShrink: 0, marginTop: 1 }}>▸</span>
        <span dangerouslySetInnerHTML={{ __html: line.replace(/^[\-\*•]\s/, "") }} />
      </div>;
    }
    if (!line.trim()) return <div key={i} style={{ height: 6 }} />;
    return <p key={i} style={{ margin: "2px 0" }} dangerouslySetInnerHTML={{ __html: line }} />;
  });
}

// ── Main App ───────────────────────────────────────────────────────────────
export default function TalentPulse360() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [typingDots, setTypingDots] = useState(0);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading) return;
    const t = setInterval(() => setTypingDots(d => (d + 1) % 4), 400);
    return () => clearInterval(t);
  }, [loading]);

  async function handleSend(text) {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput("");

    const agentType = detectAgent(q);
    const userMsg = { role: "user", content: q, agentType };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setLoading(true);

    try {
      const apiMessages = newMessages.map(m => ({ role: m.role, content: m.content }));
      const answer = await callAgent(apiMessages, agentType);
      setMessages(prev => [...prev, { role: "assistant", content: answer, agentType }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: `❌ Error: ${e.message}`, agentType: "general" }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      background: C.bg,
      color: C.text,
      fontFamily: "'Inter', system-ui, sans-serif",
      overflow: "hidden",
    }}>
      {/* ── Header ── */}
      <header style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "14px 24px",
        borderBottom: `1px solid ${C.border}`,
        background: C.surface,
        position: "relative",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36,
            borderRadius: 10,
            background: `linear-gradient(135deg, ${C.accent}, #7C3AED)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, boxShadow: `0 0 20px ${C.accentGlow}`,
          }}>🧠</div>
          <div>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, letterSpacing: "-0.3px", color: C.text }}>
              TalentPulse<span style={{ color: C.accent }}>360</span>
            </h1>
            <p style={{ margin: 0, fontSize: 11, color: C.textMuted, letterSpacing: "0.3px" }}>
              HR Intelligence Platform
            </p>
          </div>
        </div>

        {/* Agent badges row */}
        <div style={{
          position: "absolute", right: 16,
          display: "flex", gap: 6,
        }}>
          {["attendance","performance","training","skills","employee360","workforce","prediction"].map(a => {
            const ag = AGENT_LABELS[a];
            return (
              <div key={a} title={ag.label} style={{
                width: 28, height: 28, borderRadius: 8,
                background: `${ag.color}18`,
                border: `1px solid ${ag.color}40`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 13, cursor: "default",
              }}>{ag.icon}</div>
            );
          })}
        </div>
      </header>

      {/* ── Chat area ── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0 16px" }}>
        {isEmpty ? (
          <WelcomeScreen onQuickAction={handleSend} />
        ) : (
          <div style={{ maxWidth: 800, margin: "0 auto", paddingTop: 20, paddingBottom: 16 }}>
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {loading && <TypingIndicator dots={typingDots} />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* ── Quick chips (shown only when chat exists) ── */}
      {!isEmpty && (
        <div style={{
          padding: "8px 16px 0",
          overflowX: "auto",
          borderTop: `1px solid ${C.border}20`,
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", gap: 6, maxWidth: 800, margin: "0 auto", paddingBottom: 6 }}>
            {QUICK_ACTIONS.slice(0, 5).map(a => (
              <button key={a.label} onClick={() => handleSend(a.prompt)} style={{
                flexShrink: 0,
                padding: "4px 12px",
                background: C.surfaceAlt,
                border: `1px solid ${C.border}`,
                borderRadius: 20,
                color: C.textMuted,
                fontSize: 12,
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.15s",
              }}
                onMouseEnter={e => { e.target.style.borderColor = C.accent; e.target.style.color = C.text; }}
                onMouseLeave={e => { e.target.style.borderColor = C.border; e.target.style.color = C.textMuted; }}
              >{a.icon} {a.label}</button>
            ))}
          </div>
        </div>
      )}

      {/* ── Input bar ── */}
      <div style={{
        padding: "12px 16px 16px",
        background: C.surface,
        borderTop: `1px solid ${C.border}`,
        flexShrink: 0,
      }}>
        <div style={{
          maxWidth: 800, margin: "0 auto",
          display: "flex", gap: 10, alignItems: "flex-end",
        }}>
          <div style={{
            flex: 1,
            background: C.surfaceAlt,
            border: `1px solid ${C.border}`,
            borderRadius: 14,
            padding: "10px 16px",
            display: "flex", alignItems: "center",
            transition: "border-color 0.2s",
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
              }}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
              }}
              placeholder="Ask about attendance, performance, training, skills..."
              disabled={loading}
              rows={1}
              style={{
                flex: 1, background: "none", border: "none", outline: "none",
                color: C.text, fontSize: 14, resize: "none", lineHeight: 1.5,
                fontFamily: "inherit", overflow: "hidden",
              }}
            />
          </div>
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            style={{
              width: 44, height: 44, borderRadius: 12, flexShrink: 0,
              background: loading || !input.trim() ? C.border : `linear-gradient(135deg, ${C.accent}, #7C3AED)`,
              border: "none", cursor: loading || !input.trim() ? "not-allowed" : "pointer",
              color: "#fff", fontSize: 18, display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s",
              boxShadow: loading || !input.trim() ? "none" : `0 4px 16px ${C.accentGlow}`,
            }}
          >
            {loading ? "⏳" : "↑"}
          </button>
        </div>
      </div>

      <style>{`
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 2px; }
        * { box-sizing: border-box; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:translateY(0) } }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </div>
  );
}

// ── Welcome Screen ─────────────────────────────────────────────────────────
function WelcomeScreen({ onQuickAction }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", minHeight: "calc(100vh - 220px)",
      padding: "24px 16px", animation: "fadeUp 0.4s ease",
    }}>
      <div style={{
        width: 64, height: 64, borderRadius: 18,
        background: `linear-gradient(135deg, ${C.accent}, #7C3AED)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 32, marginBottom: 20,
        boxShadow: `0 0 40px rgba(59,126,246,0.3)`,
      }}>🧠</div>

      <h2 style={{ margin: "0 0 8px", fontSize: 24, fontWeight: 700, textAlign: "center" }}>
        How can I help you today?
      </h2>
      <p style={{ margin: "0 0 32px", color: C.textMuted, textAlign: "center", fontSize: 14, maxWidth: 400 }}>
        Ask me about any employee — attendance, performance, training, skills, or workforce insights.
      </p>

      {/* Agent pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginBottom: 28, maxWidth: 600 }}>
        {Object.entries(AGENT_LABELS).filter(([k]) => k !== "general").map(([key, ag]) => (
          <div key={key} style={{
            padding: "4px 12px",
            borderRadius: 20,
            background: `${ag.color}12`,
            border: `1px solid ${ag.color}30`,
            fontSize: 12, color: ag.color,
            display: "flex", alignItems: "center", gap: 4,
          }}>{ag.icon} {ag.label}</div>
        ))}
      </div>

      {/* Quick action grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: 10,
        width: "100%",
        maxWidth: 560,
      }}>
        {QUICK_ACTIONS.map(a => (
          <button key={a.label} onClick={() => onQuickAction(a.prompt)} style={{
            padding: "14px 16px",
            background: C.surfaceAlt,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            color: C.text, fontSize: 13,
            cursor: "pointer", textAlign: "left",
            display: "flex", alignItems: "center", gap: 10,
            transition: "all 0.15s",
          }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = C.accent;
              e.currentTarget.style.background = C.accentGlow;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = C.border;
              e.currentTarget.style.background = C.surfaceAlt;
            }}
          >
            <span style={{ fontSize: 18 }}>{a.icon}</span>
            <span style={{ color: C.textMuted }}>{a.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Message Bubble ─────────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  const ag = AGENT_LABELS[msg.agentType] || AGENT_LABELS.general;

  return (
    <div style={{
      display: "flex",
      flexDirection: isUser ? "row-reverse" : "row",
      gap: 10, marginBottom: 16,
      animation: "fadeUp 0.25s ease",
    }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: 10, flexShrink: 0,
        background: isUser
          ? `linear-gradient(135deg, #4B5563, #374151)`
          : `linear-gradient(135deg, ${ag.color}, ${ag.color}88)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 14, border: isUser ? `1px solid ${C.border}` : `1px solid ${ag.color}40`,
      }}>
        {isUser ? "👤" : ag.icon}
      </div>

      {/* Bubble */}
      <div style={{ maxWidth: "80%", display: "flex", flexDirection: "column", gap: 4 }}>
        {!isUser && (
          <span style={{ fontSize: 11, color: ag.color, fontWeight: 600, paddingLeft: 2 }}>
            {ag.label}
          </span>
        )}
        <div style={{
          padding: "10px 14px",
          borderRadius: isUser ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
          background: isUser ? C.accentSoft : C.surfaceAlt,
          border: `1px solid ${isUser ? C.accent + "40" : C.border}`,
          fontSize: 13.5, lineHeight: 1.6,
          color: C.text,
        }}>
          {isUser
            ? <span>{msg.content}</span>
            : <div>{renderMarkdown(msg.content)}</div>
          }
        </div>
      </div>
    </div>
  );
}

// ── Typing indicator ───────────────────────────────────────────────────────
function TypingIndicator({ dots }) {
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "flex-start" }}>
      <div style={{
        width: 32, height: 32, borderRadius: 10,
        background: `linear-gradient(135deg, ${C.accent}, #7C3AED)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 14, flexShrink: 0,
      }}>🧠</div>
      <div style={{
        padding: "12px 16px",
        background: C.surfaceAlt,
        border: `1px solid ${C.border}`,
        borderRadius: "4px 16px 16px 16px",
        display: "flex", gap: 6, alignItems: "center",
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 7, height: 7, borderRadius: "50%",
            background: C.accent,
            animation: `blink 1.2s ease ${i * 0.2}s infinite`,
          }} />
        ))}
        <span style={{ fontSize: 11, color: C.textMuted, marginLeft: 6 }}>
          Querying agent...
        </span>
      </div>
    </div>
  );
}
