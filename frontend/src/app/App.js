import React, { useState } from "react";
import { BrowserRouter as Router, Route, Routes, Link } from "react-router-dom";
import "./App.css";
import ImportText from "./pages/importText/ImportText";
import TextToSpeech from "./pages/textToSpeech/TextToSpeech";

const routes = [
  {
    path: "/",
    element: TextToSpeech,
    label: "Text to Speech",
    showInNav: false
  },
  {
    path: "/text-to-speech", 
    element: TextToSpeech,
    label: "Text to Speech",
    showInNav: true
  },
  {
    path: "/subtitle",
    element: ImportText,
    label: "Subtitle Editor", 
    showInNav: true
  }
];

function App() {
  const [isProcessing, setIsProcessing] = useState(false);

  return (
    <Router>
      <div className="App">
        <nav className="navigation">
          {routes.filter(route => route.showInNav).map(route => (
            <Link
              key={route.path}
              to={route.path}
              className={route.path === '/subtitle' && isProcessing ? "disabled-link" : ""}
              onClick={(e) => {
                if (route.path === '/subtitle' && isProcessing) {
                  e.preventDefault();
                }
              }}
            >
              {route.label}
            </Link>
          ))}
        </nav>

        <Routes>
          {routes.map(route => (
            <Route
              key={route.path}
              path={route.path}
              element={
                <route.element 
                  setIsProcessing={route.path.includes('text-to-speech') || route.path.includes('') ? setIsProcessing : undefined}
                />
              }
            />
          ))}
        </Routes>
      </div>
    </Router>
  );
}

export default App;
