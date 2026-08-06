"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();

  const [factoryName, setFactoryName] = useState<string>("");
  const [subdomain, setSubdomain] = useState<string>("");
  const [industryType, setIndustryType] = useState<string>("garment");
  const [email, setEmail] = useState<string>("");
  const [firstName, setFirstName] = useState<string>("");
  const [lastName, setLastName] = useState<string>("");
  const [password, setPassword] = useState<string>("");

  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  // Auto-generate subdomain from factory name
  const handleFactoryNameChange = (name: str) => {
    setFactoryName(name);
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
    setSubdomain(slug);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // 1. Register Tenant Cell
      const regRes = await fetch("http://localhost:8000/api/v1/auth/register-tenant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_in: {
            name: factoryName,
            subdomain: subdomain,
            plan: "standard",
            isolation_mode: "rls",
            industry_type: industryType,
          },
          admin_in: {
            email: email,
            password: password,
            first_name: firstName,
            last_name: lastName,
          },
        }),
      });

      if (!regRes.ok) {
        const errData = await regRes.json().catch(() => ({}));
        throw new Error(errData.detail || "Registration failed. Subdomain or email may already be registered.");
      }

      // 2. Auto-login after successful registration
      const params = new URLSearchParams();
      params.append("username", email);
      params.append("password", password);

      const loginRes = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params,
      });

      if (loginRes.ok) {
        const tokenData = await loginRes.json();
        localStorage.setItem("factoryiq_token", tokenData.access_token);
        localStorage.setItem("factoryiq_user", JSON.stringify(tokenData.user));
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 font-sans flex items-center justify-center p-6 relative overflow-hidden">
      {/* Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-600/15 blur-[120px] rounded-full pointer-events-none" />

      <div className="bg-[#131B2E] border border-gray-800 rounded-2xl p-8 max-w-lg w-full shadow-2xl relative z-10">
        
        {/* Header */}
        <div className="text-center mb-6">
          <Link href="/" className="inline-flex items-center gap-2 mb-3 group">
            <span className="bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-black text-sm px-2.5 py-1 rounded-lg shadow-md">
              FIQ
            </span>
            <span className="font-extrabold text-xl tracking-tight text-white group-hover:text-blue-400 transition">
              FactoryIQ
            </span>
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">Register Your Factory Cell</h1>
          <p className="text-xs text-gray-400 mt-1">Deploy an isolated tenant workspace for your factory with free trial</p>
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 p-3 rounded-xl text-xs mb-4 text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1 uppercase">Factory / Company Name</label>
              <input
                type="text"
                value={factoryName}
                onChange={(e) => handleFactoryNameChange(e.target.value)}
                required
                placeholder="e.g. Apex Garments"
                className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2 px-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1 uppercase">Cell Subdomain</label>
              <div className="flex items-center bg-[#0B0F19] border border-gray-800 rounded-xl px-3 py-2 text-sm text-gray-400">
                <input
                  type="text"
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value)}
                  required
                  placeholder="apex-garments"
                  className="bg-transparent w-full text-white focus:outline-none"
                />
                <span className="text-xs text-gray-500 font-mono">.factoryiq</span>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1 uppercase">Manufacturing Industry Workflow</label>
            <select
              value={industryType}
              onChange={(e) => setIndustryType(e.target.value)}
              className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2 px-3 text-sm text-white focus:outline-none focus:border-blue-500 transition capitalize"
            >
              <option value="garment">Garment Manufacturing (Cutting → Stitching → Finishing → Packing)</option>
              <option value="furniture">Furniture / Woodwork (Cutting → Sanding → Assembly → Polishing)</option>
              <option value="electronics">Electronics Assembly (SMT → Soldering → Testing → Casing)</option>
              <option value="custom">Custom Industrial Fabrication (Design → Fabrication → Assembly → QA)</option>
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1 uppercase">First Name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                placeholder="Jane"
                className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2 px-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1 uppercase">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                placeholder="Doe"
                className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2 px-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1 uppercase">Admin Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="admin@factory.com"
              className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2 px-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-400 mb-1 uppercase">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Minimum 8 characters"
              className="w-full bg-[#0B0F19] border border-gray-800 rounded-xl py-2 px-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-sm py-3 px-4 rounded-xl transition shadow-lg disabled:opacity-50 mt-2"
          >
            {loading ? "Provisioning Factory Cell..." : "Provision Free Factory Cell →"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-gray-800 text-center text-xs text-gray-400">
          Already registered your factory cell?{" "}
          <Link href="/login" className="text-blue-400 font-semibold hover:underline">
            Sign In Here
          </Link>
        </div>
      </div>
    </div>
  );
}
