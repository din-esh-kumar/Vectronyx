import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabase";

export default function Dashboard() {

  const [name, setName] = useState("User");

  useEffect(() => {
    const getUser = async () => {
      const { data } = await supabase.auth.getUser();
      const user = data.user;

      if (user) {
        setName(user.user_metadata?.full_name || "User");
      }
    };

    getUser();
  }, []);

  return (
      <div className="space-y-8">

        {/* Welcome */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-purple-600">
              Welcome back, {name} 👋
            </h1>
            <p className="text-gray-500 mt-1">
                Your AI Workbench is running at ⚡ 98% efficiency. <br />
                Last activity: Research query on “AI agents” (5 mins ago). <br />
                Continue where you left off or start a new analysis.
            </p>
          </div>

          {/* System Status */}
          <div className="bg-white p-4 rounded-xl shadow w-64 animate-pulse">
            <p className="text-sm text-gray-500">System Status</p>
            <p className="text-green-500 font-semibold mt-2">Live</p>
            <p className="text-sm mt-1">Latency: 12ms</p>
          </div>
        </div>

        {/* Cards */}
        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-white p-5 rounded-xl shadow">
            <h2 className="font-semibold">Memory System</h2>
            <p className="text-sm text-gray-500 mt-2">
              Contextual AI memory tracking
            </p>
          </div>

          <div className="bg-white p-5 rounded-xl shadow">
            <h2 className="font-semibold">Research Agent</h2>
            <p className="text-sm text-gray-500 mt-2">
              Deep reasoning engine
            </p>
          </div>

          <div className="bg-white p-5 rounded-xl shadow">
            <h2 className="font-semibold">Data Analyst</h2>
            <p className="text-sm text-gray-500 mt-2">
              CSV & analytics engine
            </p>
          </div>
        </div>

        {/* User Context */}
        <div className="bg-white p-6 rounded-xl shadow">
          <h2 className="font-semibold mb-3">User Context</h2>
          <p className="text-gray-500 text-sm">
            Name: Edwin Samuel <br />
            Role: Developer <br />
            Plan: Pro
          </p>
        </div>

        {/* Graph */}
        <div className="bg-white p-6 rounded-xl shadow">
          <h2 className="font-semibold mb-4">Activity Graph</h2>

          <div className="h-40 flex items-end gap-2">
            {[40, 60, 30, 80, 50, 90, 70].map((h, i) => (
              <div
                key={i}
                className="w-6 bg-purple-500 rounded"
                style={{ height: `${h}%` }}
              />
            ))}
          </div>
        </div>

      </div>
  );
}