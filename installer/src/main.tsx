import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./style.css";
import { initializeTheme } from "./ThemeControl";
import { initializeZoom } from "./ZoomControl";
initializeTheme();
initializeZoom();
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
