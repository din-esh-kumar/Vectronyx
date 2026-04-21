import Header from "./Header";
import Sidebar from "./Sidebar";
import { Outlet } from "react-router-dom";
import { useState } from "react";

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="h-screen bg-gray-50">
      {/*  HEADER (FIXED) */}
      <Header setMobileOpen={setMobileOpen} />

      <div className="flex pt-16">
        {/*  SIDEBAR (FIXED) */}
        <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen}/>

        {/*  MAIN CONTENT */}
        <main className="flex-1 ml-0 md:ml-16 p-4 md:p-6">
          <Outlet/>
        </main>
      </div>
    </div>
  );
}