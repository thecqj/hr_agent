import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "sonner";

import AppProviders from "@/app/providers/AppProviders";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <App />
      <Toaster richColors position="top-right" />
    </AppProviders>
  </React.StrictMode>
);
