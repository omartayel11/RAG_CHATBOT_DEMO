import React from "react";
import { Link } from "react-router-dom";
import "./Home.css";
import { Utensils, MessageCircle, Clock, Bookmark, HeartHandshake } from 'lucide-react';

function Home() {
  return (
    <div className="homepage-wrapper">
      <div className="homepage-content">
        <h1>Recipe Assistant</h1>
        <p className="subtitle">
          The flavors you love, the meals you crave, the conversations you miss. All in one place!
        </p>

        <ul className="feature-list">
  <li><Utensils size={18} /> Personalized recipe suggestions based on your preferences</li>
  <li><MessageCircle size={18} /> Converses with you in Egyptian Arabic</li>
  <li><Clock size={18} /> Recommends meals based on time of day</li>
  <li><Bookmark size={18} /> Save your favorites & access them anytime</li>
  <li><HeartHandshake size={18} /> Optimized experience for elderly users</li>
</ul>

        <div className="button-group">
          <Link to="/signup">
            <button className="btn primary-btn">Join The Table - Register Now</button>
          </Link>
          <Link to="/login">
            <button className="btn secondary-btn">Sign In</button>
          </Link>
        </div>

        
      </div>
    </div>
  );
}

export default Home;
