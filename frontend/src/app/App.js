import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import "./App.css";
import { VideoProvider } from "./context/VideoContext";
import SubtitleVoiceStudio from "./pages/subtitleVoiceStudio/SubtitleVoiceStudio";
import VideoListPage from "./pages/videoList/VideoListPage";
import ImportText from './pages/importText/ImportText';
import ApiConfig from './components/common/ApiConfig/ApiConfig';


function App() {
  return (
    <VideoProvider>
      <Router>
        <div className="App">
          <nav className="navigation">
            <a href="/">Studio</a>
            <a href="/import-text">Import Text</a>
            <a href="/video-list">Videos</a>
          </nav>
          
          <Routes>
            <Route path="/" element={<SubtitleVoiceStudio />} />
            <Route path="/video-list" element={<VideoListPage />} />
            <Route path="/import-text" element={<ImportText />} />
          </Routes>
          
          {/* API Configuration Component */}
          <ApiConfig />
        </div>
      </Router>
    </VideoProvider>
  );
}

export default App;