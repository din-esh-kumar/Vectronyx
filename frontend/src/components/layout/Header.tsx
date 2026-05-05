import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabase";
import { FiMenu } from "react-icons/fi";

export default function Header({ setMobileOpen }: any) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("User");

  const handleLogout = async () => {
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  useEffect(() => {
    const getUser = async () => {
      const { data } = await supabase.auth.getUser();
      const user = data.user;
      if (user) {
        setName(user.user_metadata.full_name || "User");
      }
    };
    getUser();

    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        const user = session?.user;
        if (user) {
          setName(user.user_metadata?.full_name || "User");
        }
      },
    );

    return () => listener.subscription.unsubscribe();
  }, []);

  return (
    <header className="fixed top-0 left-0 w-full h-16 bg-white z-50 flex items-center justify-between px-4 md:px-6 
                      background-color: rgb(255 255 255 / 0.8) backdrop-blur-md border-b border-gray-200/50 shadow-[0_4px_20px_rgba(0,0,0,0.05)]">
      {/* LEFT */}
      <div className="flex items-center gap-3">
        {/* 🔥 MOBILE MENU */}
        <button 
            onClick={() => setMobileOpen(true)}
            className="md:hidden text-xl"
            >
          <FiMenu />
            </button>

          <h1 className="text-3xl font-bold text-purple-500 tracking-wide">
             Vectronyx
          </h1>
      </div>


      {/* 🔥 Dynamic name */}
      <div className="flex items-center gap-4 relative">
        <span className="text-sm text-gray-600 hidden md:block">
          Hi, {name}
        </span>

        {/* Profile */}
        <div className="relative">
          <div
            onClick={() => setOpen(!open)}
            className="w-9 h-9 rounded-full bg-purple-500 text-white flex items-center justify-center font-semibold cursor-pointer"
          >
            {name.charAt(0).toUpperCase() || "U"}
          </div>

          {open && (
            <div className="absolute right-0 mt-2 w-40 bg-white rounded-xl shadow-lg">
              <button className="w-full text-left px-4 py-2 hover:bg-gray-100">
                Profile
              </button>
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-red-500 hover:bg-gray-100"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

