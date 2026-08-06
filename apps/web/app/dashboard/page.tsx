"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function TenantDashboard() {
  const router = useRouter();

  // Auth Context
  const [token, setToken] = useState<string>("");
  const [user, setUser] = useState<any>(null);
  const [subscriptionLocked, setSubscriptionLocked] = useState<boolean>(false);

  // System Context
  const [apiHealth, setApiHealth] = useState<"checking" | "online" | "offline">("checking");
  const [tenantInfo, setTenantInfo] = useState<any>(null);

  // Data States
  const [components, setComponents] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [inventoryBalances, setInventoryBalances] = useState<any[]>([]);
  const [salesOrders, setSalesOrders] = useState<any[]>([]);
  const [productionRuns, setProductionRuns] = useState<any[]>([]);
  const [qualityGates, setQualityGates] = useState<any[]>([]);
  const [standardCosts, setStandardCosts] = useState<any[]>([]);

  // Logs & UI States
  const [logs, setLogs] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "products" | "inventory" | "orders" | "mrp" | "quality" | "costing" | "ai">("overview");

  // Load Auth Session
  useEffect(() => {
    const storedToken = localStorage.getItem("factoryiq_token");
    const storedUser = localStorage.getItem("factoryiq_user");

    if (!storedToken) {
      router.push("/login");
      return;
    }

    setToken(storedToken);
    if (storedUser) setUser(JSON.parse(storedUser));

    fetchInitialData(storedToken);
  }, []);

  const addLog = (msg: str) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${timestamp}] ${msg}`, ...prev.slice(0, 49)]);
  };

  // Helper fetch with 402 Kill-Switch catch
  const apiFetch = async (url: str, options: RequestInit = {}, customToken?: str) => {
    const authToken = customToken || token;
    const headers = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
      ...(options.headers || {}),
    };

    const res = await fetch(url, { ...options, headers });

    if (res.status === 402) {
      setSubscriptionLocked(true);
      addLog("⚡ Subscription Kill-Switch activated. Access restricted.");
      throw new Error("Subscription expired or trial period ended.");
    }

    return res;
  };

  const fetchInitialData = async (activeToken: str) => {
    try {
      const healthRes = await fetch("http://localhost:8000/health").catch(() => null);
      if (healthRes && healthRes.ok) setApiHealth("online");
      else setApiHealth("offline");

      const meRes = await apiFetch("http://localhost:8000/api/v1/auth/me", {}, activeToken);
      if (meRes.ok) {
        const userData = await meRes.json();
        setUser(userData);
        setTenantInfo(userData.tenant);
      }

      await refreshAllData(activeToken);
    } catch (err: any) {
      addLog(`Initialization notice: ${err.message}`);
    }
  };

  const refreshAllData = async (activeToken?: str) => {
    const tok = activeToken || token;
    if (!tok) return;

    try {
      const [compRes, prodRes, whRes, invRes, soRes, prodRunRes, qualRes, costRes] = await Promise.all([
        apiFetch("http://localhost:8000/api/v1/components", {}, tok),
        apiFetch("http://localhost:8000/api/v1/products", {}, tok),
        apiFetch("http://localhost:8000/api/v1/warehouses", {}, tok),
        apiFetch("http://localhost:8000/api/v1/inventory/balances", {}, tok),
        apiFetch("http://localhost:8000/api/v1/sales-orders", {}, tok),
        apiFetch("http://localhost:8000/api/v1/production/runs", {}, tok),
        apiFetch("http://localhost:8000/api/v1/quality/gates", {}, tok),
        apiFetch("http://localhost:8000/api/v1/costing/standard-costs", {}, tok),
      ]);

      if (compRes.ok) setComponents(await compRes.json());
      if (prodRes.ok) setProducts(await prodRes.json());
      if (whRes.ok) setWarehouses(await whRes.json());
      if (invRes.ok) setInventoryBalances(await invRes.json());
      if (soRes.ok) setSalesOrders(await soRes.json());
      if (prodRunRes.ok) setProductionRuns(await prodRunRes.json());
      if (qualRes.ok) setQualityGates(await qualRes.json());
      if (costRes.ok) setStandardCosts(await costRes.json());

      addLog("Refreshed factory cell state successfully.");
    } catch (err: any) {
      addLog(`Data refresh notice: ${err.message}`);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("factoryiq_token");
    localStorage.removeItem("factoryiq_user");
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 font-sans p-6 relative">
      
      {/* Top Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-gray-800 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <span className="bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-black text-xs px-2.5 py-1 rounded-lg">
              CELL
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              {tenantInfo?.name || "Factory Workspace"}
            </h1>
            <span className="text-xs bg-gray-800 text-blue-400 font-mono py-0.5 px-2 rounded">
              {tenantInfo?.subdomain}.factoryiq
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Single-tenant isolated manufacturing cell & smart ERP console</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshAllData()}
            className="bg-gray-800/80 hover:bg-gray-700 text-gray-300 text-xs font-semibold py-1.5 px-3 rounded-lg border border-gray-700 transition"
          >
            🔄 Refresh Cell State
          </button>
          <button
            onClick={handleLogout}
            className="bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-semibold py-1.5 px-3 rounded-lg border border-rose-500/30 transition"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="flex overflow-x-auto gap-2 border-b border-gray-800 pb-3 mb-6 scrollbar-none">
        {[
          { id: "overview", label: "📊 Overview" },
          { id: "products", label: "📦 Products & BOM" },
          { id: "inventory", label: "🏭 Inventory" },
          { id: "orders", label: "🛒 Sales Orders" },
          { id: "mrp", label: "⚙️ MRP & Gantt" },
          { id: "quality", label: "🛡️ Quality Control" },
          { id: "costing", label: "💰 Job Costing" },
          { id: "ai", label: "🤖 AI Assistant" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`py-2 px-4 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              activeTab === tab.id
                ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                : "bg-gray-800/40 text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Metric Cards Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
          <span className="text-[10px] font-mono text-gray-500 uppercase block">Registered SKUs</span>
          <span className="text-2xl font-bold text-white mt-1 block">{products.length} Products</span>
          <span className="text-[10px] text-blue-400 mt-1 block">{components.length} Raw Materials</span>
        </div>
        <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
          <span className="text-[10px] font-mono text-gray-500 uppercase block">Stocked Warehouses</span>
          <span className="text-2xl font-bold text-emerald-400 mt-1 block">{inventoryBalances.length} Balances</span>
          <span className="text-[10px] text-gray-400 mt-1 block">{warehouses.length} Active Locations</span>
        </div>
        <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
          <span className="text-[10px] font-mono text-gray-500 uppercase block">Sales Orders</span>
          <span className="text-2xl font-bold text-amber-400 mt-1 block">{salesOrders.length} Orders</span>
          <span className="text-[10px] text-gray-400 mt-1 block">Commercial pipeline</span>
        </div>
        <div className="bg-[#131B2E] border border-gray-800 p-4 rounded-xl">
          <span className="text-[10px] font-mono text-gray-500 uppercase block">Production Runs</span>
          <span className="text-2xl font-bold text-purple-400 mt-1 block">{productionRuns.length} Scheduled</span>
          <span className="text-[10px] text-gray-400 mt-1 block">Work orders active</span>
        </div>
      </div>

      {/* Activity Audit Log */}
      <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-4 shadow-xl">
        <h3 className="text-xs font-mono text-gray-400 uppercase mb-2">Live Factory Cell Console Logs</h3>
        <div className="bg-[#0B0F19] rounded-lg p-3 h-32 overflow-y-auto font-mono text-[11px] text-gray-300 space-y-1">
          {logs.length > 0 ? (
            logs.map((log, i) => <div key={i}>{log}</div>)
          ) : (
            <div className="text-gray-600 italic">Cell activity initialized cleanly.</div>
          )}
        </div>
      </div>

      {/* Subscription Upgrade Modal Overlay (Kill-Switch Active) */}
      {subscriptionLocked && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-6 z-50 animate-fade-in">
          <div className="bg-[#131B2E] border border-rose-500/40 rounded-2xl p-8 max-w-lg w-full text-center shadow-2xl">
            <span className="text-4xl inline-block mb-3">⚡</span>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">Subscription Plan Required</h2>
            <p className="text-xs text-gray-400 mt-2">
              Your free trial period has ended or your subscription status is currently restricted by platform governance.
            </p>

            <div className="my-6 bg-[#0B0F19] border border-gray-800 rounded-xl p-4 text-left space-y-2 text-xs">
              <div className="flex justify-between text-gray-300">
                <span>Tenant Cell:</span>
                <span className="font-mono text-blue-400 font-bold">{tenantInfo?.subdomain}</span>
              </div>
              <div className="flex justify-between text-gray-300">
                <span>Status:</span>
                <span className="font-mono text-rose-400 font-bold uppercase">{tenantInfo?.subscription_status || "Expired"}</span>
              </div>
            </div>

            <button
              onClick={() => alert("Redirecting to subscription payment checkout...")}
              className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-sm py-3 px-4 rounded-xl transition shadow-lg"
            >
              Upgrade Subscription Plan →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
