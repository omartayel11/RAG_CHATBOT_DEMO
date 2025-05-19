// Signup.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Signup.css";

const categories = {
  likes: [
  "فول مدمس", "طعمية", "كشري", "محشي", "ملوخية", "شاورما", "كباب", "كفتة",
  "حمام محشي", "فسيخ", "كبدة إسكندراني", "مكرونة بشاميل", "فتة", "حواوشي",
  "دجاج مشوي", "صدور دجاج", "لحم ضاني", "بانيه", "سمك بلطي", "جمبري",
  "بطاطس محمرة", "بامية", "كوسة", "سبانخ", "بسلة بالجزر", "ورق عنب"
],
  dislikes: [
  "فسيخ", "كوارع", "ممبار", "كبدة", "كوارع", "محشي ورق عنب", "بامية", "كوسة",
  "بصل", "ثوم", "فلفل حار", "كزبرة", "كراوية", "يانسون", "قرفة", "زنجبيل"
],
  allergies: [
  "لبن", "بيض", "فول سوداني", "قمح", "سمك", "جمبري", "كابوريا", "فراولة",
  "طماطم", "فلفل", "سمسم", "موز", "مانجو", "مكسرات"
]
,
  professions: ["طالب", "طبيب", "مهندس", "مدرس", "فنان", "أخرى"]
};

function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    gender: "male",
    profession: "",
    otherProfession: "",
    likes: [],
    otherLike: "",
    dislikes: [],
    otherDislike: "",
    allergies: [],
    otherAllergy: ""
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const [showLikes, setShowLikes] = useState(false);
const [showDislikes, setShowDislikes] = useState(false);
const [showAllergies, setShowAllergies] = useState(false);


  const handleCheckboxChange = (e, field) => {
    const value = e.target.value;
    const isChecked = e.target.checked;
    setForm((prev) => {
      const updated = isChecked
        ? [...prev[field], value]
        : prev[field].filter((item) => item !== value);
      return { ...prev, [field]: updated };
    });
  };

  const handleSignup = async () => {
    const payload = {
      ...form,
      likes: [...new Set([...form.likes, ...form.otherLike.split(",").map((v) => v.trim())])].filter(Boolean),
      dislikes: [...new Set([...form.dislikes, ...form.otherDislike.split(",").map((v) => v.trim())])].filter(Boolean),
      allergies: [...new Set([...form.allergies, ...form.otherAllergy.split(",").map((v) => v.trim())])].filter(Boolean),
      profession: form.profession === "أخرى" ? form.otherProfession.trim() : form.profession
    };

    const res = await fetch("http://localhost:8001/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert("تم التسجيل بنجاح!");
      navigate("/login");
    } else {
      const err = await res.json();
      alert("فشل التسجيل: " + err.detail);
    }
  };

  return (
  <div className="signup-wrapper">
    <div className="signup-form">
      <h2>Create Account</h2>
      <input name="email" type="email" placeholder="Email" onChange={handleChange} />
      <input name="password" type="password" placeholder="Password" onChange={handleChange} />
      <input name="name" placeholder="First name" onChange={handleChange} />

      <select name="gender" value={form.gender} placeholder="Gender" onChange={handleChange}>
        <option value="male">ذكر</option>
        <option value="female">أنثى</option>
      </select>

      <select name="profession" value={form.profession} onChange={handleChange}>
        <option value="">Profession</option>
        {categories.professions.map((p, i) => (
          <option key={i} value={p}>{p}</option>
        ))}
      </select>
      {form.profession === "أخرى" && (
        <input name="otherProfession" placeholder="Other" onChange={handleChange} />
      )}

      {/* Likes Section */}
      <div className="toggle-checkbox-block">
        <div className="toggle-header" onClick={() => setShowLikes(!showLikes)}>
          <span>Your food faves go here... don't hold back!</span>
          <span className="plus-icon">{showLikes ? "×" : "+"}</span>
        </div>
        {showLikes && (
          <>
            <div className="checkbox-group">
              {categories.likes.map((item, i) => (
                <label key={i} className="custom-checkbox">
  <input
    type="checkbox"
    value={item}
    onChange={(e) => handleCheckboxChange(e, "likes")}
  />
  <div className="checkbox-box">{item}</div>
</label>

              ))}
            </div>
            <input name="otherLike" placeholder="Other" onChange={handleChange} />
          </>
        )}
      </div>

      {/* Dislikes Section */}
      <div className="toggle-checkbox-block">
        <div className="toggle-header" onClick={() => setShowDislikes(!showDislikes)}>
          <span>Anything that ruins your appetite?</span>
          <span className="plus-icon">{showDislikes ? "×" : "+"}</span>
        </div>
        {showDislikes && (
          <>
            <div className="checkbox-group">
              {categories.dislikes.map((item, i) => (
                <label key={i} className="custom-checkbox">
                  <input type="checkbox" value={item} onChange={(e) => handleCheckboxChange(e, "dislikes")} />
                  <div className="checkbox-box">{item}</div>
                </label>
              ))}
            </div>
            <input name="otherDislike" placeholder="Other" onChange={handleChange} />
          </>
        )}
      </div>

      {/* Allergies Section */}
      <div className="toggle-checkbox-block">
        <div className="toggle-header" onClick={() => setShowAllergies(!showAllergies)}>
          <span>Allergic to something? Drop it here - safety first.</span>
          <span className="plus-icon">{showAllergies ? "×" : "+"}</span>
        </div>
        {showAllergies && (
          <>
            <div className="checkbox-group">
              {categories.allergies.map((item, i) => (
                <label key={i} className="custom-checkbox">
                  <input type="checkbox" value={item} onChange={(e) => handleCheckboxChange(e, "allergies")} />
                  <div className="checkbox-box">{item}</div>
                </label>
              ))}
            </div>
            <input name="otherAllergy" placeholder="Other" onChange={handleChange} />
          </>
        )}
      </div>

      <button onClick={handleSignup}>Register</button>
    </div>
  </div>
);

}

export default Signup;
