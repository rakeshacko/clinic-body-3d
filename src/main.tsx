import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { App } from "./App";
import { AuraLab } from "./AuraLab";
import { Remote } from "./Remote";
import "./styles/tokens.css";
import "./styles/app.css";

const router = createBrowserRouter([
  { path: "/", element: <App /> },
  { path: "/anny-aura", element: <AuraLab /> },
  { path: "/remote", element: <Remote /> },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
