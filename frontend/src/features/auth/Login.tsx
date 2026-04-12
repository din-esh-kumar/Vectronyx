import { useState, useEffect } from "react";
import { FcGoogle } from "react-icons/fc";
import { FaGithub } from "react-icons/fa";
import { supabase } from "../../lib/supabase";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { BiSolidShow, BiSolidHide } from "react-icons/bi";

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange(
      (event, session) => {
        console.log("EVENT:", event);

        if (event === "SIGNED_IN" && session) {
          toast.success("Login successful!");

          // redirect after login
          navigate("/"); // dashboard as home
        }
      },
    );

    return () => {
      listener.subscription.unsubscribe();
    };
  }, [navigate]);

  const handleGoogleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
    });
  };

  const handleGithubLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "github",
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isLogin) {
      // 🔐 LOGIN
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        toast.error(error.message);
        return;
      }

      if (data.session) {
        toast.success("Login successful!");
        navigate("/"); // redirect to dashboard
      }
    } else {
      // 📝 SIGNUP
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            name,
          },
        },
      });

      if (error) {
        toast.error(error.message);
        return;
      }

      toast.success("Signup successful! Please login.");
      setIsLogin(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-md bg-white rounded-xl shadow-md p-8">
        {/* Logo */}
        <div className="flex flex-col items-center mb-6">
          <h1 className="text-3xl font-bold text-violet-500">Vectronyx</h1>
          <h2 className="text-xl font-semibold mt-3">
            {isLogin ? "Sign in" : "Create account"}
          </h2>
          <p className="text-sm text-gray-500 text-center mt-2">
            {isLogin
              ? "Using Vectronyx for work? Sign in with your email."
              : "Create your account to continue."}
          </p>
        </div>

        {/* Form */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          {/* Full Name (only for signup) */}
          {!isLogin && (
            <div className="relative w-full">
              <input
                type="text"
                placeholder=" "
                onChange={(e) => setName(e.target.value)}
                className="peer w-full px-4 pt-5 pb-2 border border-gray-300 rounded-md 
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300"
              />
              <label
                className="absolute left-3 -top-2 px-1 text-sm bg-white text-gray-500 transition-all duration-200
        peer-placeholder-shown:top-3
        peer-placeholder-shown:text-base
        peer-placeholder-shown:text-gray-400
        peer-placeholder-shown:bg-transparent
        peer-focus:-top-2
        peer-focus:text-sm
        peer-focus:text-blue-600
        peer-focus:bg-white"
              >
                Full Name
              </label>
            </div>
          )}

          {/* Email */}
          <div className="relative w-full">
            <input
              type="email"
              placeholder=" "
              onChange={(e) => setEmail(e.target.value)}
              className="peer w-full px-4 pt-5 pb-2 border border-gray-300 rounded-md 
      focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300"
            />
            <label
              className="absolute left-3 -top-2 px-1 text-sm bg-white text-gray-500 transition-all duration-200
      peer-placeholder-shown:top-3
      peer-placeholder-shown:text-base
      peer-placeholder-shown:text-gray-400
      peer-placeholder-shown:bg-transparent
      peer-focus:-top-2
      peer-focus:text-sm
      peer-focus:text-blue-600
      peer-focus:bg-white"
            >
              email address
            </label>
          </div>

          {/* Password */}
          <div className="relative w-full">
            <input
              type={showPassword ? "text" : "password"}
              placeholder=" "
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="peer w-full px-4 pt-5 pb-2 pr-10 border border-gray-300 rounded-md 
                 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300"
            />
            <label
              className="absolute left-3 -top-2 px-1 text-sm bg-white text-gray-500 transition-all duration-200
                  peer-placeholder-shown:top-3
                  peer-placeholder-shown:text-base
                  peer-placeholder-shown:text-gray-400
                  peer-placeholder-shown:bg-transparent
                  peer-focus:-top-2
                  peer-focus:text-sm
                  peer-focus:text-blue-600
                  peer-focus:bg-white"
            >
              Password
            </label>
            {/* 👁️ Toggle Button */}
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-violet-600 text-violet-600 "
            >
              {showPassword ? <BiSolidShow /> : <BiSolidHide />}
            </button>
          </div>

          {/* Button */}
          <button
            type="submit"
            className="w-full bg-violet-500 text-white py-2 rounded-md hover:bg-violet-600 transition cursor-pointer"
          >
            {isLogin ? "Continue" : "Sign Up"}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center my-4">
          <hr className="grow border-gray-300" />
          <span className="px-2 text-gray-400 text-sm">OR</span>
          <hr className="grow border-gray-300" />
        </div>

        {/* Social Login */}
        <div className="space-y-3">
          <button
            className="w-full border py-2 rounded-md flex items-center justify-center gap-2 hover:bg-gray-50 cursor-pointer border-gray-300"
            onClick={handleGoogleLogin}
          >
            <span>
              {" "}
              <FcGoogle />{" "}
            </span>{" "}
            Continue with Google
          </button>

          <button
            className="w-full border py-2 rounded-md flex items-center justify-center gap-2 hover:bg-gray-50 cursor-pointer border-gray-300"
            onClick={handleGithubLogin}
          >
            <span>
              {" "}
              <FaGithub />{" "}
            </span>{" "}
            Continue with GitHub
          </button>

          {/* <button className="w-full border py-2 rounded-md flex items-center justify-center gap-2 hover:bg-gray-50 cursor-pointer">
            <span>🔑</span> Continue with SSO
          </button> */}
        </div>

        {/* Toggle */}
        <p className="text-center text-sm mt-6">
          {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
          <span
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-600 cursor-pointer hover:underline"
          >
            {isLogin ? "Sign Up" : "Sign In"}
          </span>
        </p>
      </div>
    </div>
  );
}
