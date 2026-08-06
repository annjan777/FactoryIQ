"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>("admin@garmentcorp.com");
  const [password, setPassword] = useState<string>("password123");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const params = new URLSearchParams();
      params.append("username", email);
      params.append("password", password);

      const res = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Invalid email or password.");
      }

      const data = await res.json();
      // Store auth session
      localStorage.setItem("factoryiq_token", data.access_token);
      localStorage.setItem("factoryiq_user", JSON.stringify(data.user));

      // Redirect to tenant workspace
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 font-sans flex items-center justify-center p-6 relative overflow-hidden">
      {/* Dynamic background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-600/15 blur-[120px] rounded-full pointer-events-none" />

      <div className="bg-[#131B2E] border border-gray-800 rounded-2xl p-8 max-w-md w-full shadow-2xl relative z-10">
        
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-4 group">
            <span className="bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-black text-sm px-2.5 py-1 rounded-lg shadow-md">
              FIQ
            </span>
            <span className="font-extrabold text-xl tracking-tight text-white group-hover:text-blue-400 transition">
              FactoryIQ
            </span>
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">Welcome Back</h1>
          <p className="text-xs text-gray-400 mt-1">Access your factory tenant cell & smart ERP workspace</p>
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 p-3 rounded-xl text-xs mb-6 text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1.5 uppercase">
              Work Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="name@factory.com"
              className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2.5 px-3.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="block text-xs font-mono text-gray-400 uppercase">
                Password
              </label>
            </div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2.5 px-3.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-sm py-3 px-4 rounded-xl transition shadow-lg disabled:opacity-50 mt-2"
          >
            {loading ? "Authenticating..." : "Sign In to Factory Cell →"}
          </button>
        </form>

        {/* Footer Link */}
        <div className="mt-8 pt-6 border-t border-gray-800 text-center text-xs text-gray-400">
          Don't have a factory cell registered yet?{" "}
          <Link href="/register" className="text-blue-400 font-semibold hover:underline">
            Register Factory Free
          </Link>
        </div>
      </div>
    </div>
  );
}
