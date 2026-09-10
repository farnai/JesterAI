/* ==========================================================================
   JESTER Chat Client Controller
   ========================================================================== */

(() => {
  // State
  let conversationId = getOrCreateSessionId();
  let isThinking = false;

  // DOM Elements
  const messagesContainer = document.getElementById("messages-container");
  const messagesViewport = document.getElementById("messages-viewport");
  const welcomeBanner = document.getElementById("welcome-banner");
  const typingIndicator = document.getElementById("typing-indicator");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const btnNewChat = document.getElementById("btn-new-chat");
  const sessionIdDisplay = document.getElementById("session-id-display");
  const engineModel = document.getElementById("engine-model");
  const engineStatus = document.getElementById("engine-status");
  const engineStatusText = document.getElementById("engine-status-text");
  const headerConnPill = document.getElementById("header-conn-pill");
  const headerConnText = document.getElementById("header-conn-text");
  const toggleSidebarBtn = document.getElementById("toggle-sidebar");
  const sidebar = document.getElementById("sidebar");
  const presetButtons = document.querySelectorAll(".preset-btn");

  // Init
  function init() {
    updateSessionDisplay();
    checkHealth();
    bindEvents();
    autoResizeTextarea();
  }

  function getOrCreateSessionId() {
    let id = sessionStorage.getItem("jester_conversation_id");
    if (!id) {
      id = "aud-" + Math.random().toString(36).substring(2, 10);
      sessionStorage.setItem("jester_conversation_id", id);
    }
    return id;
  }

  function updateSessionDisplay() {
    if (sessionIdDisplay) {
      sessionIdDisplay.textContent = conversationId;
    }
  }

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        if (engineModel && data.model) {
          engineModel.textContent = data.model;
        }
        if (data.status === "healthy") {
          setHealthStatus(true, `${data.model} Ready`);
        } else {
          setHealthStatus(false, data.ollama?.error || "Degraded");
        }
      } else {
        setHealthStatus(false, "API Offline");
      }
    } catch (e) {
      setHealthStatus(false, "Unreachable");
    }
  }

  function setHealthStatus(healthy, text) {
    if (engineStatusText) engineStatusText.textContent = text;
    if (headerConnText) headerConnText.textContent = text;
    if (headerConnPill) {
      headerConnPill.style.borderColor = healthy ? "rgba(46, 213, 115, 0.3)" : "rgba(214, 48, 49, 0.3)";
      headerConnPill.style.color = healthy ? "#2ed573" : "#ff4757";
    }
  }

  function bindEvents() {
    // Form Submit
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      sendMessage();
    });

    // Enter to submit (Shift+Enter for new line)
    userInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-expand textarea
    userInput.addEventListener("input", () => {
      autoResizeTextarea();
      sendBtn.disabled = !userInput.value.trim() || isThinking;
    });

    // New Chat
    btnNewChat.addEventListener("click", () => {
      startNewAudience();
    });

    // Sidebar toggle (mobile/compact)
    if (toggleSidebarBtn && sidebar) {
      toggleSidebarBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
      });
    }

    // Preset buttons
    presetButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const prompt = btn.getAttribute("data-prompt");
        if (prompt && !isThinking) {
          userInput.value = prompt;
          autoResizeTextarea();
          sendBtn.disabled = false;
          sendMessage();
        }
      });
    });
  }

  function autoResizeTextarea() {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 160) + "px";
  }

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isThinking) return;

    // Hide welcome banner
    if (welcomeBanner) {
      welcomeBanner.style.display = "none";
    }

    // Append user message to UI
    appendMessage("user", text);
    userInput.value = "";
    autoResizeTextarea();
    setThinkingState(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: text,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData.detail || `Server error (${response.status})`;
        appendMessage("assistant", `The court bells ring with alarm: ${errMsg}`);
        return;
      }

      const data = await response.json();
      if (data.conversation_id) {
        conversationId = data.conversation_id;
        sessionStorage.setItem("jester_conversation_id", conversationId);
        updateSessionDisplay();
      }

      appendMessage("assistant", data.response);
    } catch (err) {
      appendMessage("assistant", `Even a jester cannot speak through severed cords: ${err.message}`);
    } finally {
      setThinkingState(false);
      userInput.focus();
    }
  }

  function appendMessage(role, content) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = `avatar ${role === "user" ? "user-avatar" : "jester-avatar"}`;
    avatar.textContent = role === "user" ? "👑" : "🃏";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const sender = document.createElement("span");
    sender.className = "bubble-sender";
    sender.textContent = role === "user" ? "Sovereign Decree" : "JESTER";

    const contentDiv = document.createElement("div");
    contentDiv.className = "bubble-content";
    contentDiv.innerHTML = formatMarkdown(content);

    bubble.appendChild(sender);
    bubble.appendChild(contentDiv);
    row.appendChild(avatar);
    row.appendChild(bubble);

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function formatMarkdown(text) {
    // Basic safe markdown parser for bold, italics, inline code, and paragraphs
    let escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks ```code```
    escaped = escaped.replace(/```([\s\S]*?)```/g, (match, p1) => {
      return `<pre><code>${p1.trim()}</code></pre>`;
    });

    // Inline code `code`
    escaped = escaped.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Paragraphs
    const paragraphs = escaped.split(/\n\n+/);
    return paragraphs
      .map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`)
      .join("");
  }

  function setThinkingState(thinking) {
    isThinking = thinking;
    sendBtn.disabled = thinking || !userInput.value.trim();
    if (typingIndicator) {
      typingIndicator.style.display = thinking ? "flex" : "none";
    }
    if (thinking) {
      scrollToBottom();
    }
  }

  function scrollToBottom() {
    setTimeout(() => {
      messagesViewport.scrollTop = messagesViewport.scrollHeight;
    }, 20);
  }

  function startNewAudience() {
    conversationId = "aud-" + Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem("jester_conversation_id", conversationId);
    updateSessionDisplay();
    messagesContainer.innerHTML = "";
    if (welcomeBanner) {
      welcomeBanner.style.display = "block";
    }
    userInput.value = "";
    autoResizeTextarea();
    userInput.focus();
  }

  // Start
  document.addEventListener("DOMContentLoaded", init);
})();
