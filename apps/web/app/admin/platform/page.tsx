"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

export default function SuperadminPlatformPortal() {
  const [adminToken, setAdminToken] = useState<string>("");
  const [loginEmail, setLoginEmail] = useState<string>("admin@factoryiq.io");
  const [loginPassword, setLoginPassword] = useState<string>("password123");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");

  const [stats, setStats] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoadingId, setActionLoadingId] = useState<string>("");

  // Handle Superadmin Authentication Login
  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    try {
      const params = new URLSearchParams();
      params.append("username", loginEmail);
      params.append("password", loginPassword);

      const res = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params,
      });

      if (!res.ok) throw new Error("Invalid superadmin credentials.");

      const data = await res.json();
      setAdminToken(data.access_token);
      setIsAuthenticated(true);
      fetchAdminData(data.access_token);
    } catch (err: any) {
      setErrorMsg(err.message || "Superadmin login failed.");
    }
  };

  // Fetch System Stats & Tenant Registry
  const fetchAdminData = async (token: string) => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const statsRes = await fetch("http://localhost:8000/api/v1/admin/stats", { headers });
      if (statsRes.ok) setStats(await statsRes.json());

      const tenantsRes = await fetch("http://localhost:8000/api/v1/admin/tenants", { headers });
      if (tenantsRes.ok) setTenants(await tenantsRes.json());
    } catch (err: any) {
      setErrorMsg("Failed loading platform data.");
    } finally {
      setLoading(false);
    }
  };

  // Trigger Kill-Switch (Instant Lockout / Reactivation)
  const handleToggleKillSwitch = async (tenantId: string) => {
    setActionLoadingId(tenantId);
    try {
      const headers = { Authorization: `Bearer ${adminToken}` };
      const res = await fetch(`http://localhost:8000/api/v1/admin/tenants/${tenantId}/kill-switch`, {
        method: "POST",
        headers,
      });
      if (!res.ok) throw new Error("Kill-switch trigger failed.");
      await fetchAdminData(adminToken);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoadingId("");
    }
  };

  // Update Tenant Subscription Settings
  const handleUpdateSubscription = async (
    tenantId: string,
    subStatus: string,
    industry: string,
    productLimit: number
  ) => {
    setActionLoadingId(tenantId);
    try {
      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${adminToken}`,
      };
      const res = await fetch(`http://localhost:8000/api/v1/admin/tenants/${tenantId}/subscription`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          subscription_status: subStatus,
          industry_type: industry,
          max_products_limit: productLimit,
        }),
      });
      if (!res.ok) throw new Error("Subscription update failed.");
      await fetchAdminData(adminToken);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoadingId("");
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex items-center justify-center p-6">
        <div className="bg-[#131B2E] border border-purple-500/30 rounded-2xl p-8 max-w-md w-full shadow-2xl">
          <div className="text-center mb-6">
            <span className="text-4xl inline-block mb-2">🛡️</span>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">FactoryIQ Operator Portal</h1>
            <p className="text-xs text-gray-400 mt-1">Platform Superadmin Authentication</p>
          </div>

          {errorMsg && (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 p-3 rounded-lg text-xs mb-4 text-center font-medium">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleAdminLogin} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1">SUPERADMIN EMAIL</label>
              <input
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
                className="w-full bg-[#0B0F19] border border-gray-800 rounded-lg py-2 px-3 text-sm text-white focus:outline-none focus:border-purple-500"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1">PASSWORD</label>
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                required
                className="w-full bg-[#0B0F19] border border-gray-800 rounded-lg py-2 px-3 text-sm text-white focus:outline-none focus:border-purple-500"
              />
            </div>
            <button
              type="submit"
              className="bg-purple-600 hover:bg-purple-500 text-white font-bold text-sm py-2.5 px-4 rounded-lg transition shadow-lg mt-2"
            >
              Authenticate & Access Platform Controls
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-gray-800 text-center">
            <Link href="/" className="text-xs text-gray-500 hover:text-gray-400 transition">
              ← Return to Client Workspace Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 font-sans p-6">
      
      {/* Platform Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 mb-6 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <span className="bg-purple-500/20 text-purple-400 p-1.5 rounded-lg border border-purple-500/30 text-lg">🛡️</span>
            FactoryIQ Superadmin Operations Console
          </h1>
          <p className="text-xs text-gray-400 mt-1">Cross-Tenant Isolation Control, Subscription Kill-Switch & Industry Configurator</p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="bg-gray-800/80 hover:bg-gray-700 text-gray-300 text-xs font-semibold py-1.5 px-4 rounded-lg border border-gray-700 transition"
          >
            ← Client Dashboard
          </Link>
          <button
            onClick={() => fetchAdminData(adminToken)}
            disabled={loading}
            className="bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs py-1.5 px-4 rounded-lg transition shadow"
          >
            {loading ? "Refreshing..." : "Refresh Platform Controls"}
          </button>
        </div>
      </header>

      {/* Global System Metrics */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
            <span className="text-[10px] font-mono text-gray-500 uppercase block">Platform Tenants</span>
            <span className="text-3xl font-extrabold text-white mt-1 block">{stats.total_tenants}</span>
            <span className="text-xs text-emerald-400 mt-1 block">{stats.active_tenants} Active / {stats.suspended_tenants} Suspended</span>
          </div>
          <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
            <span className="text-[10px] font-mono text-gray-500 uppercase block">Registered Users</span>
            <span className="text-3xl font-extrabold text-blue-400 mt-1 block">{stats.total_users}</span>
            <span className="text-xs text-gray-500 mt-1 block">Cross-tenant aggregate</span>
          </div>
          <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
            <span className="text-[10px] font-mono text-gray-500 uppercase block">Active Production Runs</span>
            <span className="text-3xl font-extrabold text-emerald-400 mt-1 block">{stats.total_production_orders}</span>
            <span className="text-xs text-gray-500 mt-1 block">Factory jobs running</span>
          </div>
          <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
            <span className="text-[10px] font-mono text-gray-500 uppercase block">Material Supply Orders</span>
            <span className="text-3xl font-extrabold text-amber-400 mt-1 block">{stats.total_purchase_orders}</span>
            <span className="text-xs text-gray-500 mt-1 block">PO transactions logged</span>
          </div>
        </div>
      )}

      {/* Tenant Registry & Kill-Switch Control Center */}
      <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-6 shadow-xl">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          </svg>
          Tenant Account Governance & Subscription Kill-Switch
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 font-mono uppercase">
                <th className="py-3 px-3">Tenant / Subdomain</th>
                <th className="py-3 px-3">Industry Type</th>
                <th className="py-3 px-3">Isolation</th>
                <th className="py-3 px-3">Sub Status</th>
                <th className="py-3 px-3">Product Limit</th>
                <th className="py-3 px-3">Users</th>
                <th className="py-3 px-3 text-center">Kill-Switch</th>
                <th className="py-3 px-3 text-right">Update Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {tenants.map((t) => {
                const isLoading = actionLoadingId === t.id;
                const isKilled = t.status === "suspended" || t.subscription_status === "suspended";

                return (
                  <tr key={t.id} className="hover:bg-[#0B0F19]/60">
                    <td className="py-3.5 px-3">
                      <span className="font-bold text-white block">{t.name}</span>
                      <span className="text-[10px] text-blue-400 font-mono block mt-0.5">{t.subdomain}</span>
                    </td>

                    <td className="py-3.5 px-3">
                      <select
                        defaultValue={t.industry_type}
                        onChange={(e) => handleUpdateSubscription(t.id, t.subscription_status, e.target.value, t.max_products_limit)}
                        className="bg-[#0B0F19] border border-gray-800 rounded py-1 px-2 text-xs text-gray-200 capitalize"
                      >
                        <option value="garment">Garment</option>
                        <option value="furniture">Furniture</option>
                        <option value="electronics">Electronics</option>
                        <option value="custom">Custom</option>
                      </select>
                    </td>

                    <td className="py-3.5 px-3">
                      <span className={`px-2 py-0.5 rounded font-mono text-[9px] uppercase ${
                        t.isolation_mode === "schema" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      }`}>
                        {t.isolation_mode}
                      </span>
                    </td>

                    <td className="py-3.5 px-3">
                      <select
                        defaultValue={t.subscription_status}
                        onChange={(e) => handleUpdateSubscription(t.id, e.target.value, t.industry_type, t.max_products_limit)}
                        className={`bg-[#0B0F19] border border-gray-800 rounded py-1 px-2 text-xs font-semibold capitalize ${
                          t.subscription_status === "active" ? "text-emerald-400" :
                          t.subscription_status === "trial" ? "text-yellow-400" : "text-rose-400"
                        }`}
                      >
                        <option value="active">Active</option>
                        <option value="trial">Trial</option>
                        <option value="grace_period">Grace Period</option>
                        <option value="expired">Expired</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </td>

                    <td className="py-3.5 px-3 font-mono">{t.max_products_limit} SKUs</td>
                    <td className="py-3.5 px-3 font-bold">{t.user_count}</td>

                    {/* Kill Switch Toggle */}
                    <td className="py-3.5 px-3 text-center">
                      <button
                        onClick={() => handleToggleKillSwitch(t.id)}
                        disabled={isLoading}
                        className={`py-1.5 px-3 rounded-full text-[10px] font-extrabold uppercase transition shadow-lg ${
                          isKilled
                            ? "bg-rose-600 hover:bg-rose-500 text-white animate-pulse"
                            : "bg-emerald-600 hover:bg-emerald-500 text-white"
                        }`}
                      >
                        {isLoading ? "Updating..." : isKilled ? "⚡ KILL-SWITCH ACTIVE" : "✓ ACCESS ONLINE"}
                      </button>
                    </td>

                    <td className="py-3.5 px-3 text-right">
                      <span className="text-[10px] font-mono text-gray-500">
                        {new Date(t.created_at).toLocaleDateString()}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
