import React, { useState, useEffect, useRef } from "react";

export default function PersonalAssistant({ user }) {
  const [isOpen, setIsOpen] = useState(false);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("gemini_api_key") || "");
  const [showSettings, setShowSettings] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Initial greeting tailored to logged-in user
  useEffect(() => {
    const candidateName = user?.name || "there";
    const userSkills = user?.profile?.skills?.join(", ") || "various technologies";

    setMessages([
      {
        role: "assistant",
        text: `Hi ${candidateName}! 👋 I'm your SkillLock personal assistant. I have access to your profile data and skills (${userSkills}).\n\nAsk me anything about your skill readiness, recommendations for assessments, or career tips!`,
      },
    ]);
  }, [user]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  function handleSaveKey(newKey) {
    const trimmed = newKey.trim();
    setApiKey(trimmed);
    localStorage.setItem("gemini_api_key", trimmed);
  }

  async function handleSendMessage(textToSend) {
    const query = (textToSend || input).trim();
    if (!query) return;

    if (!apiKey) {
      setShowSettings(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", text: query },
        {
          role: "assistant",
          text: "⚠️ Please enter your Gemini API key in the settings above so I can answer your questions!",
        },
      ]);
      setInput("");
      return;
    }

    const newMessages = [...messages, { role: "user", text: query }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    // Build context from user profile
    const profile = user?.profile || {};
    const contextPrompt = `
You are the SkillLock Personal AI Career Coach.
User Profile Details:
- Name: ${user?.name || "Candidate"}
- Email: ${user?.email || "N/A"}
- Bio: ${profile.bio || "N/A"}
- Skills: ${(profile.skills || []).join(", ") || "None"}
- Projects: ${JSON.stringify(profile.projects || [])}
- Experience: ${JSON.stringify(profile.experience || [])}
- Education: ${JSON.stringify(profile.education || [])}
- Certifications: ${JSON.stringify(profile.certifications || [])}

Instructions:
Answer user questions concisely, warmly, and helpfully. Keep answers to 2-4 sentences or bullet points unless detailed explanation is asked.
`;

    try {
      const contents = [
        {
          role: "user",
          parts: [{ text: `${contextPrompt}\n\nUser Question: ${query}` }],
        },
      ];

      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents,
            generationConfig: {
              temperature: 0.7,
              maxOutputTokens: 1024,
            },
          }),
        }
      );

      const data = await res.json();
      if (data.error) {
        throw new Error(data.error.message || "Failed to reach Gemini API");
      }

      const reply =
        data.candidates?.[0]?.content?.parts?.[0]?.text ||
        "I could not generate an answer. Please try again.";

      setMessages((prev) => [...prev, { role: "assistant", text: reply.trim() }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `⚠️ Error: ${err.message || "Could not connect to Gemini."}. Check your API key.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const suggestions = [
    "What are my top skills?",
    "Which assessment should I take?",
    "How can I improve my profile?",
  ];

  return (
    <>
      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: "fixed",
          bottom: "26px",
          right: "26px",
          zIndex: 9999,
          background: "#1c4936",
          color: "#ffffff",
          border: "none",
          borderRadius: "50px",
          padding: "12px 20px",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "13px",
          fontWeight: 600,
          boxShadow: "0 8px 24px rgba(28, 73, 54, 0.35)",
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = "translateY(-2px)";
          e.currentTarget.style.boxShadow = "0 12px 28px rgba(28, 73, 54, 0.45)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = "translateY(0)";
          e.currentTarget.style.boxShadow = "0 8px 24px rgba(28, 73, 54, 0.35)";
        }}
        aria-label="Open Personal Assistant"
      >
        <span style={{ fontSize: "16px" }}>✨</span>
        <span>{isOpen ? "Close Assistant" : "SkillLock Assistant"}</span>
      </button>

      {/* Floating Chat Window */}
      {isOpen && (
        <div
          style={{
            position: "fixed",
            bottom: "84px",
            right: "26px",
            width: "380px",
            maxWidth: "calc(100vw - 40px)",
            height: "530px",
            maxHeight: "calc(100vh - 120px)",
            background: "#ffffff",
            border: "1px solid #e1e7e2",
            borderRadius: "16px",
            boxShadow: "0 18px 45px rgba(26, 48, 38, 0.16)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            zIndex: 9999,
            fontFamily: '"DM Sans", -apple-system, sans-serif',
            animation: "fadeIn 0.2s ease-out",
          }}
        >
          {/* Header */}
          <div
            style={{
              background: "#1c4936",
              color: "#ffffff",
              padding: "14px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "50%",
                  background: "rgba(255,255,255,0.18)",
                  display: "grid",
                  placeItems: "center",
                  fontSize: "14px",
                }}
              >
                ✨
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px", letterSpacing: "-0.2px" }}>
                  SkillLock Assistant
                </div>
                <div style={{ fontSize: "11px", opacity: 0.8, display: "flex", alignItems: "center", gap: "5px" }}>
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "50%",
                      background: "#52d294",
                      display: "inline-block",
                    }}
                  />
                  AI Career Coach
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <button
                onClick={() => setShowSettings(!showSettings)}
                title="API Key Settings"
                style={{
                  background: showSettings ? "rgba(255,255,255,0.25)" : "transparent",
                  border: "none",
                  color: "#fff",
                  padding: "5px 8px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                ⚙️
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close"
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#fff",
                  fontSize: "16px",
                  padding: "4px 8px",
                  cursor: "pointer",
                  borderRadius: "6px",
                }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Settings Drawer (API Key) */}
          {(showSettings || !apiKey) && (
            <div
              style={{
                background: "#f4f7f4",
                borderBottom: "1px solid #e1e7e2",
                padding: "10px 14px",
                fontSize: "12px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontWeight: 500 }}>
                <span>Gemini API Key</span>
                {!apiKey && <span style={{ color: "#d25a2b" }}>Required to chat</span>}
              </div>
              <input
                type="password"
                value={apiKey}
                placeholder="Paste Gemini API key..."
                onChange={(e) => handleSaveKey(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 9px",
                  border: "1px solid #d2ded5",
                  borderRadius: "6px",
                  fontSize: "12px",
                  boxSizing: "border-box",
                  background: "#fff",
                }}
              />
              <div style={{ fontSize: "10px", color: "#6a7972", marginTop: "4px" }}>
                Saved locally in your browser.
              </div>
            </div>
          )}

          {/* Chat Messages */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              background: "#fafbfa",
            }}
          >
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "84%",
                  background: m.role === "user" ? "#1c4936" : "#ffffff",
                  color: m.role === "user" ? "#ffffff" : "#1f2a24",
                  padding: "9px 13px",
                  borderRadius: "12px",
                  fontSize: "12.5px",
                  lineHeight: 1.5,
                  border: m.role === "user" ? "none" : "1px solid #e6ece7",
                  boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
                  whiteSpace: "pre-wrap",
                }}
              >
                {m.text}
              </div>
            ))}

            {loading && (
              <div
                style={{
                  alignSelf: "flex-start",
                  background: "#ffffff",
                  border: "1px solid #e6ece7",
                  padding: "9px 14px",
                  borderRadius: "12px",
                  fontSize: "12px",
                  color: "#6b7972",
                }}
              >
                Thinking... ✨
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions Pills */}
          <div
            style={{
              display: "flex",
              gap: "6px",
              overflowX: "auto",
              padding: "8px 14px",
              background: "#ffffff",
              borderTop: "1px solid #edf1ee",
            }}
          >
            {suggestions.map((s, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(s)}
                style={{
                  whiteSpace: "nowrap",
                  background: "#f0f4f1",
                  border: "1px solid #dce5df",
                  color: "#284f3e",
                  borderRadius: "14px",
                  padding: "4px 10px",
                  fontSize: "11px",
                  cursor: "pointer",
                }}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Input Area */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{
              padding: "10px 14px",
              background: "#ffffff",
              borderTop: "1px solid #e6ece7",
              display: "flex",
              gap: "8px",
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything..."
              disabled={loading}
              style={{
                flex: 1,
                border: "1px solid #d4ded7",
                borderRadius: "8px",
                padding: "8px 12px",
                fontSize: "12.5px",
                outline: "none",
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              style={{
                background: "#1c4936",
                color: "#ffffff",
                border: "none",
                borderRadius: "8px",
                padding: "0 14px",
                fontSize: "13px",
                cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                opacity: loading || !input.trim() ? 0.6 : 1,
              }}
            >
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}

