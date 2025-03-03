import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import "./App.css";
import SubtitleVoiceStudio from "./pages/subtitleVoiceStudio/SubtitleVoiceStudio";
import VideoListPage from "./pages/videoList/VideoListPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<SubtitleVoiceStudio />} />
        <Route path="/list" element={<VideoListPage />} />
      </Routes>
    </Router>
  );
}

export default App;
