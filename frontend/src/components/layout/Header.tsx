import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabase";
import { useNavigate } from "react-router-dom";

export default function Header({ setSidebarOpen }: any) {
  const navigate = useNavigate();
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const getUser = async () => {
      const { data } = await supabase.auth.getSession();
      setUserEmail(data.session?.user.email || null);
    };

    getUser();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setUserEmail(null);
    navigate("/login");
  };

  return (
    <div className="h-16 bg-gray-900 flex items-center justify-between px-6 border-b border-gray-800">

      {/* ☰ Mobile Menu */}
      <button
        className="md:hidden text-xl"
        onClick={() => setSidebarOpen(true)}
      >
        ☰
      </button>

      <h1 className="text-lg font-semibold">Dashboard</h1>

      {/* Auth */}
      <div className="flex items-center gap-4">
        {userEmail ? (
          <>
            <span className="text-sm text-gray-400 hidden md:block">
              {userEmail}
            </span>

            <button
              onClick={handleLogout}
              className="bg-red-500 px-3 py-1 rounded-md hover:bg-red-600 text-sm"
            >
              Logout
            </button>
          </>
        ) : (
          <button
            onClick={() => navigate("/login")}
            className="bg-teal-500 px-3 py-1 rounded-md hover:bg-teal-600 text-sm"
          >
            Sign In
          </button>
        )}
      </div>
    </div>
  );
}