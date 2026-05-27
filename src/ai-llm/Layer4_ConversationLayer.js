// Layer 4 - LLM Conversation Layer
// Nhận output từ Layer 3, đưa cho LLM diễn giải thành câu chữ tự nhiên với người dùng

export const generateAIResponse = async (userMessage, messageHistory, groqKey, systemData) => {
  if (!groqKey) {
    return "Tôi là WanderBot. Hệ thống đang chạy ở chế độ Mock (Vui lòng điền Groq API Key trong cài đặt).";
  }

  const systemPrompt = `You are the AI Conversation Layer for WanderHUB — an AI-powered smart travel assistant.

YOUR ROLE (Layer 4 — AI Conversation Layer):
- explain recommendations naturally
- answer conversationally
- personalize tone
- summarize itineraries
- provide travel coaching
- ask follow-up questions when information is missing

You MUST:
- only use data provided by the system
- never hallucinate prices, opening hours, or routes
- never invent promotions or locations
- never override backend business logic
- keep answers concise, helpful, friendly, and modern
- Reply in Vietnamese.

EXAMPLE SYSTEM DATA FROM LAYER 3 (For your context):
${JSON.stringify(systemData, null, 2)}`;

  const msgs = [
    { role: "system", content: systemPrompt },
    ...messageHistory.map(m => ({ role: m.from === "ai" ? "assistant" : "user", content: m.text })),
    { role: "user", content: userMessage }
  ];

  try {
    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${groqKey}`
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: msgs,
        temperature: 0.6,
      })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData?.error?.message || `HTTP ${res.status}`);
    }
    const data = await res.json();
    return data.choices[0].message.content;
  } catch (err) {
    return `Lỗi kết nối Groq API: ${err.message}`;
  }
};
