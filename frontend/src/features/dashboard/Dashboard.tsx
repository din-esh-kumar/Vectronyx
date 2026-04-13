import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabase";
import { useNavigate } from "react-router-dom";
import Layout from "../../components/layout/Layout";

export default function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const { data } = await supabase.auth.getSession();

      if (data.session) {
        setUserEmail(data.session.user.email || null);
      }

      setLoading(false);
    };

    checkAuth();
  }, []);

  // 🔄 Loading
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950 text-white">
        <p className="text-lg animate-pulse">Loading...</p>
      </div>
    );
  }

  // 🚪 Logout
  const handleLogout = async () => {
    await supabase.auth.signOut();
    setUserEmail(null);
  };

  return (
    <Layout>
      <div className="space-y-8">

        {/* 🔝 Top Bar */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-teal-400">
              Vectronyx
            </h1>
            <p className="text-gray-400 text-sm">
              AI Workbench Dashboard
            </p>
          </div>

          {/* 🔐 Auth Button */}
          {!userEmail ? (
            <button
              onClick={() => navigate("/login")}
              className="bg-teal-500 px-4 py-2 rounded-md hover:bg-teal-600"
            >
              Sign In / Sign Up
            </button>
          ) : (
            <button
              onClick={handleLogout}
              className="bg-red-500 px-4 py-2 rounded-md hover:bg-red-600"
            >
              Logout
            </button>
          )}
        </div>

        {/*  IF NOT LOGGED IN → LANDING */}
        {!userEmail ? (
          <div className="flex flex-col items-center justify-center text-center mt-20">

            <h2 className="text-4xl font-bold text-teal-400 mb-4">
              Welcome to Vectronyx 
            </h2>

            <p className="text-gray-400 mb-6 max-w-md">
              AI-powered system combining memory, research, and data analysis.
              Sign up to unlock full features.
            </p>

            <button
              onClick={() => navigate("/login")}
              className="bg-teal-500 px-6 py-3 rounded-lg hover:bg-teal-600"
            >
              Get Started
            </button>

          </div>
        ) : (
          /*  LOGGED IN → DASHBOARD */
          <div className="space-y-6">

            {/*  Grid */}
            <div className="grid md:grid-cols-3 gap-6">

              {/*  User */}
              <div className="bg-gray-900 p-5 rounded-xl shadow">
                <h2 className="text-lg font-semibold mb-2">User</h2>
                <p className="text-teal-400">{userEmail}</p>
              </div>

              {/*  Memory */}
              <div className="bg-gray-900 p-5 rounded-xl shadow">
                <h2 className="text-lg font-semibold mb-2">Memory</h2>
                <p className="text-gray-400 text-sm">
                  Recent stored context will appear here
                </p>
              </div>

              {/*  Activity */}
              <div className="bg-gray-900 p-5 rounded-xl shadow">
                <h2 className="text-lg font-semibold mb-2">Activity</h2>
                <p className="text-gray-400 text-sm">
                  Recent queries & outputs
                </p>
              </div>

            </div>

            {/*  Quick Actions */}
            <div className="bg-gray-900 p-5 rounded-xl shadow">
              <h2 className="text-lg font-semibold mb-4">
                Quick Actions
              </h2>

              <div className="flex flex-wrap gap-4">
                <button
                  onClick={() => navigate("/memory")}
                  className="bg-teal-500 px-4 py-2 rounded-md hover:bg-teal-600"
                >
                  Memory
                </button>

                <button
                  onClick={() => navigate("/research")}
                  className="bg-blue-500 px-4 py-2 rounded-md hover:bg-blue-600"
                >
                  Research
                </button>

                <button
                  onClick={() => navigate("/data-analyst")}
                  className="bg-purple-500 px-4 py-2 rounded-md hover:bg-purple-600"
                >
                  Data Analyst
                </button>
              </div>
            </div>

          </div>
        )}

      </div>
    </Layout>
  );
}