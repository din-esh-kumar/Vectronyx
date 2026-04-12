// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

import { Toaster } from 'react-hot-toast'
import { BrowserRouter } from "react-router-dom";
import AppRouter from "./app/router";


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* <App /> */}
     <BrowserRouter>
       <Toaster position="top-center" />
       <AppRouter />
    </BrowserRouter>
  </StrictMode>,
)