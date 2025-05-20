import React, { useState, useEffect, useRef } from "react";
import "./Chat.css";
import { Bot, User } from "lucide-react";
import { Heart, ThumbsDown, AlertTriangle, Trash2, Plus, Edit3, UserCircle2 } from "lucide-react"; // Add at the top



function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [expectingChoice, setExpectingChoice] = useState(false);
  const [ws, setWs] = useState(null);
  const [currentRecipeTitle, setCurrentRecipeTitle] = useState(null);
  const [favourites, setFavourites] = useState([]);
  const [fullRecipeContent, setFullRecipeContent] = useState({});
  const [isRecording, setIsRecording] = useState(false);
  const [mode, setMode] = useState(null); // 'text' or 'voice'
  const [botSpeaking, setBotSpeaking] = useState(false);
  const [showThinking, setShowThinking] = useState(false);
  const [typingText, setTypingText] = useState(null);
  const [selectedFavourite, setSelectedFavourite] = useState(null);
  const [chatLogs, setChatLogs] = useState([]);
  const [selectedChatLog, setSelectedChatLog] = useState(null);
  const [userPrefs, setUserPrefs] = useState({ name: "", likes: [], dislikes: [], allergies: [] });
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [showStarters, setShowStarters] = useState(true);
  const [isHistoryCollapsed, setIsHistoryCollapsed] = useState(false);
  const [awaitingResponse, setAwaitingResponse] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);




  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const messageListRef = useRef(null);

  useEffect(() => {
    if (mode) connectWebSocket();
  }, [mode]);

  useEffect(() => {
  const email = localStorage.getItem("userEmail");
  if (!email) return;

  fetchFavourites();
  fetchChatLogs();
  fetchUserProfile();
}, []);

  const connectWebSocket = () => {
  const socket = new WebSocket("ws://localhost:8001/ws/chat");

  socket.onopen = () => {
    const email = localStorage.getItem("userEmail");
    socket.send(JSON.stringify({ email, mode }));
    setWsConnected(true);
    // fetchFavourites();
    // fetchChatLogs();
    // fetchUserProfile();
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === "suggestions") {
        setSuggestions(data.suggestions);
        setExpectingChoice(true);
        setShowThinking(true);
        setMessages((prev) => [...prev, { sender: "bot", text: data.message || "اختر وصفة من الخيارات التالية:" }]);
      } else if (data.type === "response") {
        setShowThinking(false);
        animateTyping(data.message);
        setAwaitingResponse(false); // just in case there's no TTS
        if (mode === "voice") {
          setBotSpeaking(true);
          playBotSpeech(data.message);
        }
        setExpectingChoice(false);
        setSuggestions([]);
        if (data.selected_title && data.full_recipe) {
          setCurrentRecipeTitle(data.selected_title);
          setFullRecipeContent(prev => ({ ...prev, [data.selected_title]: data.full_recipe }));
        }
      }
    } catch (e) {
      console.error("WebSocket message parsing error:", e);
      handleCriticalError("An unexpected error occurred. You will be redirected to the homepage.");
    }
  };

  socket.onclose = () => {
    console.warn("WebSocket connection closed.");
    setWsConnected(false);
    handleCriticalError("The connection was lost. You will be redirected to the homepage.");
  };

  setWs(socket);
};


  useEffect(() => {
    messageListRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, suggestions, typingText]);

  const handleCriticalError = (message = "You're out of chats for today, please come back later! You will be logged out and returned to the homepage.") => {
  alert(message);
  localStorage.removeItem("userEmail");
  window.location.href = "/";
};


  const sendMessage = (messageText = input) => {
    setShowStarters(false);
    if (!messageText.trim() || !ws) return;
    setMessages((prev) => [...prev, { sender: "user", text: messageText }]);
    setShowThinking(true);
    ws.send(messageText);
    setInput("");
  };

  const handleAddToFavourites = async () => {
  if (!currentRecipeTitle || !ws) return;

  const email = localStorage.getItem("userEmail");
  if (!email) {
    setMessages((prev) => [
      ...prev,
      { sender: "bot", text: "❗ You must be logged in to add to favourites." },
    ]);
    return;
  }

  try {
    const response = await fetch("http://localhost:8001/add-favourite", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        title: currentRecipeTitle,
        recipe: fullRecipeContent[currentRecipeTitle] || "",
      }),
    });

    const result = await response.json();

    if (result.status === "success") {
      setFavourites((prev) => [...prev, currentRecipeTitle]);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: `✅ "${currentRecipeTitle}" has been added to your favourites.` },
      ]);
    } else if (result.status === "exists") {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: `🔔 "${currentRecipeTitle}" is already in your favourites.` },
      ]);
    } else {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: `❗ Failed to add to favourites.` },
      ]);
    }
  } catch (error) {
    console.error("Error adding to favourites:", error);
    setMessages((prev) => [
      ...prev,
      { sender: "bot", text: `❗ Server error while adding to favourites.` },
    ]);
  }

  setCurrentRecipeTitle(null); // clear after saving
};

const updatePreference = async (field, updatedList) => {
  const email = localStorage.getItem("userEmail");
  if (!email) return;

  try {
    await fetch(`http://localhost:8001/update-profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, field, updatedList })
    });

    setUserPrefs(prev => ({ ...prev, [field]: updatedList }));
  } catch (err) {
    console.error("Error updating preference:", err);
  }
};


  const fetchChatLogs = async () => {
  const email = localStorage.getItem("userEmail");
  if (!email) return;

  try {
    const response = await fetch(`http://localhost:8001/get-chat-logs?email=${email}`);
    const data = await response.json();
    if (Array.isArray(data.chats)) {
      setChatLogs(data.chats);
    }
  } catch (err) {
    console.error("Error fetching chats:", err);
  }
};

const fetchUserProfile = async () => {
  const email = localStorage.getItem("userEmail");
  if (!email) return;

  try {
    const response = await fetch(`http://localhost:8001/get-profile?email=${email}`);
    const data = await response.json();
    setUserPrefs({
      name: data.name || "",
      likes: data.likes || [],
      dislikes: data.dislikes || [],
      allergies: data.allergies || []
    });
    setProfileLoaded(true);
  } catch (err) {
    console.error("Error fetching user profile:", err);
  }
};


  const fetchFavourites = async () => {
  const email = localStorage.getItem("userEmail");
  if (!email) return;

  try {
    const response = await fetch(`http://localhost:8001/get-favourites?email=${email}`);
    const data = await response.json();
    if (Array.isArray(data.favourites)) {
      setFavourites(data.favourites.map(f => f.title)); // get titles
      const fullContent = {};
      data.favourites.forEach(f => {
        fullContent[f.title] = f.recipe;
      });
      setFullRecipeContent(fullContent); // store full recipes
    }
  } catch (err) {
    console.error("Error fetching favourites:", err);
  }
};


  const animateTyping = (fullText) => {
  let index = 0;
  setTypingText(""); // start fresh

  const interval = setInterval(() => {
    setTypingText((prev) => {
      const next = fullText.slice(0, index + 1);
      index++;
      if (index === fullText.length) {
        clearInterval(interval);
        setTypingText(null);
        setMessages((prev) => [...prev, { sender: "bot", text: fullText }]);
      }
      return next;
    });
  }, 30); // adjust typing speed (ms per character)
};


  const playBotSpeech = async (text) => {
    try {
      const response = await fetch("http://localhost:8001/speak-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) throw new Error("TTS failed");
      const arrayBuffer = await response.arrayBuffer();
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.onended = () => {
  setBotSpeaking(false);
  setAwaitingResponse(false);
}; 
      setBotSpeaking(true);
      source.start(0);
    } catch (e) {
      console.error("TTS Error", e);
      setBotSpeaking(false);
      handleCriticalError("Failed to play the bot's voice. You will be redirected to the homepage.");
    }
  };

  const toggleRecording = async () => {
  if (!navigator.mediaDevices || !window.MediaRecorder) return alert("🎙️ غير مدعوم");

  if (!isRecording) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    recordedChunksRef.current = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) recordedChunksRef.current.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      setIsRecording(false); // ✅ Move this here

      const blob = new Blob(recordedChunksRef.current, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("file", blob, "voice.webm");

      try {
        const res = await fetch("http://localhost:8001/transcribe-audio", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        if (data.text) {
          setAwaitingResponse(true); // ✅ Set waiting immediately after send
          sendMessage(data.text);
        }
      } catch (err) {
  console.error("Transcription failed", err);
  handleCriticalError("Failed to convert your voice to text. You will be redirected to the homepage.");
}
    };

    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.start();
    setIsRecording(true);
  } else {
    mediaRecorderRef.current?.stop(); // ⚠️ async stop — don't reset state here
  }
};


  const DropdownSection = ({ title, items }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="dropdown-section">
      <div className="dropdown-header" onClick={() => setOpen(!open)}>
        <span>{title}</span>
        <span className="dropdown-arrow">{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <ul className="dropdown-list">
          {items.length === 0 ? (
            <li className="empty-item">None</li>
          ) : (
            items.map((item, i) => <li key={`${title}-${i}`}>{item}</li>)
          )}
        </ul>
      )}
    </div>
  );
};

const EditableListSection = ({ title, items, icon: Icon, onAdd, onDelete }) => {
  const [open, setOpen] = useState(false);
  const [newItem, setNewItem] = useState("");

  return (
    <div className="editable-section">
      <div className="section-header" onClick={() => setOpen(!open)}>
        <div className="section-title">
          <Icon size={18} style={{ marginRight: "8px" }} />
          {title}
        </div>
        <span className="dropdown-arrow">{open ? "▲" : "▼"}</span>
      </div>

      {open && (
        <div className="section-body">
          <ul>
            {items.map((item, i) => (
              <li key={`${title}-${i}`}>
                {item}
                <Trash2 size={16} className="delete-icon" onClick={() => onDelete(i)} />
              </li>
            ))}
          </ul>
          <div className="add-input">
            <input
              type="text"
              placeholder={`Add to ${title}`}
              value={newItem}
              onChange={(e) => setNewItem(e.target.value)}
            />
            <button onClick={() => {
              if (newItem.trim()) {
                onAdd(newItem.trim());
                setNewItem("");
              }
            }}>
              <Plus size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};


  const handleModeSelect = (selectedMode) => setMode(selectedMode);

  return (
    <div className="chat-page">
      <div className={`chat-history-bar ${isHistoryCollapsed ? "collapsed" : ""}`}>
    <div className="chat-history-header">
  <h3>Past Chats</h3>
  <button className="collapse-btn" onClick={() => setIsHistoryCollapsed(prev => !prev)}>
    {isHistoryCollapsed ? "»" : "«"}
  </button>
</div>

    {chatLogs.map((log, i) => (
      <div key={i} className="chat-log-item" onClick={() => setSelectedChatLog(log.chat)}>
        Chat #{i + 1}
      </div>
    ))}
  </div>
      {!mode ? (
        <div className="chat-window">
          <div className="mode-selection">
            <h2>How would you like to chat?</h2>
            <button onClick={() => handleModeSelect("text")}>Text - Type your questions and get instant responses</button>
            <button onClick={() => handleModeSelect("voice")}>Voice - Speak naturally and have a voice-driven conversation</button>
          </div>
        </div>
      ) : mode === "text" ? (
        <div className="chat-window">
          <div className="chat-header">
            <h2>Recipe Assistant</h2>
            <button className="new-chat-btn" onClick={() => window.location.reload()}><span className="plus-icon">+</span> New Chat</button>
          </div>
          {showStarters && (
  <div className="starter-options">
    <p className="starter-title">Need help getting started?</p>
    <div className="starter-buttons">
      {[
  "السلام عليكم",
  "أزيك؟ عامل إيه؟",
  "مساء الفل ",
  "صباح الخير ",
  "أنا زهقان شوية ",
  "احكيلي حاجة حلوة",
  "إيه الأخبار؟"
]
.map((text, i) => (
        <button
          key={i}
          onClick={() => {
            sendMessage(text);
            setShowStarters(false);
          }}
        >
          {text}
        </button>
      ))}
    </div>
  </div>
)}

          <div className="chat-messages">
           {messages.map((msg, idx) => (
  <div key={idx} className={`message-row ${msg.sender}`}>
    <div className={`avatar ${msg.sender === "bot" ? "bot-avatar" : "user-avatar"}`}>
  {msg.sender === "bot" ? <Bot size={22} strokeWidth={2} /> : <User size={22} strokeWidth={2} />}
</div>

    <div className={`message ${msg.sender}`} style={{ whiteSpace: "pre-wrap",
    direction: "rtl",
    textAlign: "right",
    fontFamily: "Tahoma, Arial, sans-serif" }}>
  {msg.text}
</div>

  </div>
))}

{typingText && (
  <div className="message-row bot" style={{ whiteSpace: "pre-wrap",
    direction: "rtl",
    textAlign: "right",
    fontFamily: "Tahoma, Arial, sans-serif" }}>
    <div className="avatar bot-avatar">
  <Bot size={22} strokeWidth={2} />
</div>

    <div className="message bot">{typingText}</div>
  </div>
)}


{showThinking && (
  <div className="message-row bot">
     <div className="avatar bot-avatar">
  <Bot size={22} strokeWidth={2} />
</div>
    <div className="message bot typing-indicator">
      <span className="dot"></span>
      <span className="dot"></span>
      <span className="dot"></span>
    </div>
  </div>
)}


            {expectingChoice && (
              <>
                <div className="choice-hint">Choose from the following suggestions ⬇</div>
                <div className="suggestions">
                  {suggestions.map((s, i) => (
  <button
    className="suggestion-button"
    key={i}
    onClick={() => {
      const selectedTitle = s;
      setMessages((prev) => [...prev, { sender: "user", text: selectedTitle }]);
      sendMessage(`${i + 1}`);
      setExpectingChoice(false);
      setSuggestions([]);
    }}
    // style={{
    //   fontWeight: i === suggestions.length - 1 ? "bold" : "normal",
    //   backgroundColor: i === suggestions.length - 1 ? "#ffdddd" : undefined,
    //   color: i === suggestions.length - 1 ? "#b20000" : undefined,
    // }}
  >
    {s}
  </button>
))}

                </div>
              </>
            )}
            <div ref={messageListRef}></div>
          </div>
          <div className="input-container">
  <input
  type="text"
  placeholder={
    !wsConnected
      ? "Connecting..."
      : showThinking
      ? "Please wait..."
      : expectingChoice
      ? "Waiting for your choice..."
      : "Type here..."
  }
  value={input}
  onChange={(e) => setInput(e.target.value)}
  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
  disabled={!wsConnected || expectingChoice || showThinking}
/>


  <button
    onClick={() => {
      if (!expectingChoice) sendMessage();
    }}
    disabled={!wsConnected || expectingChoice || showThinking ||input.trim() === ""}
  >
    send
  </button>

  {expectingChoice && (
    <div className="suggestion-hint">Choose from suggestions</div>
  )}
</div>

        </div>
      ) : (
        <div className="chat-window">
          <div className="chat-header">
            <h2>Recipe Assistant</h2>
            <button className="new-chat-btn" onClick={() => window.location.reload()}><span className="plus-icon">+</span> New Chat</button>
          </div>
          <div
  className={`voice-circle ${
    isRecording ? "listening" : botSpeaking ? "speaking" : awaitingResponse ? "thinking" : ""
  }`}
  onClick={() => {
    // Allow toggleRecording during recording, but block during thinking/speaking
    if (!botSpeaking && !awaitingResponse) toggleRecording();
  }}
>

  {isRecording
    ? "Listening..."
    : botSpeaking
    ? "Speaking..."
    : awaitingResponse
    ? "Thinking..."
    : "Click to Speak"}
</div>

          {expectingChoice && (
            <>
              <div className="choice-hint">Choose from the following suggestions⬇</div>
              <div className="suggestions">
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => sendMessage(`${i + 1}`)}>{i + 1}. {s}</button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      <div className="info-panel">
        <h2 className="info-panel-title">My Companion</h2>

{currentRecipeTitle && (
          <div className="current-recipe-box">
            <h3>Current Recipe</h3>
            <h4 style={{
    direction: "rtl",
    textAlign: "right",
    whiteSpace: "pre-wrap",
    fontFamily: "Tahoma, Arial, sans-serif",
  }}>{currentRecipeTitle}</h4>
            <p
  style={{
    direction: "rtl",
    textAlign: "right",
    whiteSpace: "pre-wrap",
    fontFamily: "Tahoma, Arial, sans-serif",
  }}
>
  {fullRecipeContent[currentRecipeTitle]}
</p>

            <div style={{ display: "flex", justifyContent: "center", marginTop: "1rem" }}>
  <button className="new-chat-btn" onClick={handleAddToFavourites}>
    <span className="plus-icon">+</span>Add to favorites
  </button>
</div>


          </div>
        )}

      <div className="user-profile-box">
  <div className="profile-header">
    <UserCircle2 size={48} className="profile-avatar" />
    <h3>{userPrefs.name || "Guest"}</h3>
  </div>

  {profileLoaded && (
  <div className="profile-sections">
    <EditableListSection
      title="Likes"
      items={userPrefs.likes}
      icon={Heart}
      onAdd={(item) => updatePreference("likes", [...userPrefs.likes, item])}
      onDelete={(index) => {
        const updated = [...userPrefs.likes];
        updated.splice(index, 1);
        updatePreference("likes", updated);
      }}
    />

    <EditableListSection
      title="Dislikes"
      items={userPrefs.dislikes}
      icon={ThumbsDown}
      onAdd={(item) => updatePreference("dislikes", [...userPrefs.dislikes, item])}
      onDelete={(index) => {
        const updated = [...userPrefs.dislikes];
        updated.splice(index, 1);
        updatePreference("dislikes", updated);
      }}
    />

    <EditableListSection
      title="Allergies"
      items={userPrefs.allergies}
      icon={AlertTriangle}
      onAdd={(item) => updatePreference("allergies", [...userPrefs.allergies, item])}
      onDelete={(index) => {
        const updated = [...userPrefs.allergies];
        updated.splice(index, 1);
        updatePreference("allergies", updated);
      }}
    />
  </div>
)}

</div>


        <div className="favourites-box">
  <h3>My Favorites</h3>
  {favourites.length === 0 ? (
    <p className="empty-message">You haven’t added any favorite recipes yet.</p>
  ) : (
    <ul>
      {favourites.map((fav, i) => (
        <li key={i} onClick={() => setSelectedFavourite(fav)}>
          {fav}
        </li>
      ))}
    </ul>
  )}
</div>

<div style={{ marginTop: "2rem", display: "flex", justifyContent: "center" }}>
  <button
    className="new-chat-btn"
    onClick={() => {
      localStorage.removeItem("userEmail");
      window.location.href = "/";
    }}
  >
    Log Out
  </button>
</div>



      </div>
      {selectedFavourite && (
  <div className="recipe-modal-overlay" onClick={() => setSelectedFavourite(null)}>
    <div className="recipe-modal" onClick={(e) => e.stopPropagation()}>
      <h2>{selectedFavourite}</h2>
      <p  style={{
    direction: "rtl",
    textAlign: "right",
    whiteSpace: "pre-wrap",
    fontFamily: "Tahoma, Arial, sans-serif",
  }}>{fullRecipeContent[selectedFavourite]}</p>
      <button className="close-modal-btn" onClick={() => setSelectedFavourite(null)}>Close ✖</button>
    </div>
  </div>
)}

{selectedChatLog && (
  <div className="recipe-modal-overlay" onClick={() => setSelectedChatLog(null)}>
    <div className="recipe-modal" onClick={(e) => e.stopPropagation()}>
      <h2>Previous Chat</h2>
      {selectedChatLog.map((msg, i) => (
        <div key={i} className={`message ${msg.sender}`}>
          <strong>{msg.sender === "bot" ? "🤖" : "🧑"}</strong> {msg.text}
        </div>
      ))}
      <button className="close-modal-btn" onClick={() => setSelectedChatLog(null)}>Close ✖</button>
    </div>
  </div>
)}

    </div>
  );
}

export default Chat;
