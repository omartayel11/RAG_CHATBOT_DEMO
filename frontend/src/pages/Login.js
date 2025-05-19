import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Signup.css";

function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async () => {
    const res = await fetch("http://localhost:8001/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (res.ok) {
      localStorage.setItem("userEmail", email);
      navigate("/chat");
    } else {
      const err = await res.json();
      alert("Unable to login: " + err.detail);
    }
  };

  return (
    <div className="signup-wrapper">
      <div className="signup-form">
        <h2>Sign In</h2>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="form-switch-text">
  Don't Have an Account Yet?   {" "}
  <span className="form-link" onClick={() => navigate("/signup")}>
    Register Now
  </span>
</p>

        <button onClick={handleLogin}>Let's Go!</button>
      </div>
    </div>
  );
}

export default Login;
