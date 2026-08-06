"use client";

import { useState, useEffect } from "react";

export default function Dashboard() {
  // System context states
  const [tenantInfo, setTenantInfo] = useState<any>(null);
  const [token, setToken] = useState<string>("");
  const [apiHealth, setApiHealth] = useState<string>("checking");
  const [logs, setLogs] = useState<string[]>([]);
  const [isSeeding, setIsSeeding] = useState<boolean>(false);

  // Active ERP Data states
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [salesOrders, setSalesOrders] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<any[]>([]);
  const [productionOrders, setProductionOrders] = useState<any[]>([]);
  
  // Selected/Active Item trackers
  const [selectedOrderId, setSelectedOrderId] = useState<string>("");
  const [feasibility, setFeasibility] = useState<any>(null);
  const [checkLoading, setCheckLoading] = useState<boolean>(false);
  const [activePOId, setActivePOId] = useState<string>("");
  const [activeProdId, setActiveProdId] = useState<string>("");
  
  // Action loadings
  const [poActionLoading, setPoActionLoading] = useState<string>("");
  const [prodActionLoading, setProdActionLoading] = useState<string>("");

  // AI Chat States
  const [chatMessage, setChatMessage] = useState<string>("");
  const [chatHistory, setChatHistory] = useState<any[]>([
    {
      role: "assistant",
      answer: "Hello! I am your AI Operations Assistant. You can ask me questions about active inventory, bottlenecks, or order status (e.g., 'Can I fulfill Order SO-1024?').",
      intent: "greeting"
    }
  ]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [aiContext, setAiContext] = useState<any>({});

  // Append operation logs for UX visibility
  const addLog = (msg: string) => {
    setLogs((prev) => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);
  };

  // Check API Connection Health
  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "healthy") {
          setApiHealth("online");
          addLog("Connected to FactoryIQ Backend API (Port 8000).");
        } else {
          setApiHealth("error");
        }
      })
      .catch(() => {
        setApiHealth("offline");
        addLog("Unable to connect to backend API. Make sure uvicorn is running on port 8000.");
      });
  }, []);

  // Fetch ERP listings if authenticated
  const fetchERPData = async (authToken: string) => {
    try {
      const headers = { Authorization: `Bearer ${authToken}` };
      
      const whRes = await fetch("http://localhost:8000/api/v1/warehouses", { headers });
      const whs = await whRes.json();
      setWarehouses(whs);

      const invRes = await fetch("http://localhost:8000/api/v1/inventory/balances", { headers });
      const inv = await invRes.json();
      setInventory(inv);

      const soRes = await fetch("http://localhost:8000/api/v1/sales-orders", { headers });
      const sos = await soRes.json();
      setSalesOrders(sos);
      
      if (sos.length > 0) {
        setSelectedOrderId(sos[0].id);
      }

      const supRes = await fetch("http://localhost:8000/api/v1/purchasing/suppliers", { headers });
      const sups = await supRes.json();
      setSuppliers(sups);

      const poRes = await fetch("http://localhost:8000/api/v1/purchasing/pos", { headers });
      const pos = await poRes.json();
      setPurchaseOrders(pos);
      if (pos.length > 0) {
        setActivePOId(pos[pos.length - 1].id);
      }

      const prRes = await fetch("http://localhost:8000/api/v1/production/runs", { headers });
      const prs = await prRes.json();
      setProductionOrders(prs);
      if (prs.length > 0) {
        setActiveProdId(prs[prs.length - 1].id);
      }
      
      addLog("Sync completed. Loaded inventory, purchase, and production order registries.");
    } catch (err) {
      addLog("Error syncing listings: " + String(err));
    }
  };

  // Onboard / Seed worked T-Shirt Scenario
  const handleSeedScenario = async () => {
    setIsSeeding(true);
    addLog("Initiating multi-tenant database registration...");
    try {
      const randomId = Math.floor(100 + Math.random() * 900);
      const subdomain = `garmentcorp-${randomId}`;
      const email = `admin-${randomId}@garmentcorp.com`;
      
      // 1. Register Tenant (RLS boundary)
      const registerRes = await fetch("http://localhost:8000/api/v1/auth/register-tenant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_in: {
            name: "GarmentCorp Inc.",
            subdomain: subdomain,
            plan: "standard",
            isolation_mode: "rls"
          },
          admin_in: {
            email: email,
            password: "password123",
            first_name: "Operations",
            last_name: "Manager"
          }
        })
      });
      
      if (!registerRes.ok) {
        throw new Error(await registerRes.text());
      }
      addLog(`Tenant registered subdomain: ${subdomain}`);
      
      // 2. Login to get JWT Token
      const loginParams = new URLSearchParams();
      loginParams.append("username", email);
      loginParams.append("password", "password123");

      const loginRes = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: loginParams
      });
      const loginData = await loginRes.json();
      const authToken = loginData.access_token;
      setToken(authToken);
      setTenantInfo({ subdomain, email });
      addLog("Authenticated successfully. JWT Token saved to context.");

      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`
      };

      // 3. Create Warehouse
      addLog("Provisioning warehouse 'WH-1'...");
      const whRes = await fetch("http://localhost:8000/api/v1/warehouses", {
        method: "POST",
        headers,
        body: JSON.stringify({ code: "WH-1", name: "Main HQ Warehouse" })
      });
      const warehouse = await whRes.json();

      // 4. Create Supplier
      addLog("Registering Supplier: Thread & Panel Co. (SUPP-01)...");
      await fetch("http://localhost:8000/api/v1/purchasing/suppliers", {
        method: "POST",
        headers,
        body: JSON.stringify({
          code: "SUPP-01",
          name: "Thread & Panel Co.",
          contact_email: "orders@threadandpanel.com"
        })
      });

      // 5. Create Components (Front, Back, Sleeves, Collars, Labels)
      addLog("Creating component catalog codes...");
      const componentsToCreate = [
        { code: "FRONT-PANEL", name: "Front Panel", uom: "pcs" },
        { code: "BACK-PANEL", name: "Back Panel", uom: "pcs" },
        { code: "SLEEVE", name: "Sleeve Pair", uom: "pcs" },
        { code: "COLLAR", name: "Collar", uom: "pcs" },
        { code: "LABEL", name: "Brand Label", uom: "pcs" }
      ];

      const compMap: Record<string, string> = {};
      for (const comp of componentsToCreate) {
        const cRes = await fetch("http://localhost:8000/api/v1/components", {
          method: "POST",
          headers,
          body: JSON.stringify(comp)
        });
        const cData = await cRes.json();
        compMap[comp.code] = cData.id;
      }

      // 6. Create T-Shirt Product
      addLog("Creating product SKU: TSHIRT-RN-101...");
      const prodRes = await fetch("http://localhost:8000/api/v1/products", {
        method: "POST",
        headers,
        body: JSON.stringify({
          sku: "TSHIRT-RN-101",
          name: "Round Neck T-Shirt",
          category: "garments"
        })
      });
      const product = await prodRes.json();

      // 7. Create BOM Header & Lines
      addLog("Compiling versioned Bill of Materials...");
      await fetch(`http://localhost:8000/api/v1/products/${product.id}/boms`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          product_id: product.id,
          version: 1,
          is_active: true,
          lines: [
            { component_id: compMap["FRONT-PANEL"], qty_per_unit: 1.0, scrap_pct: 0.0 },
            { component_id: compMap["BACK-PANEL"], qty_per_unit: 1.0, scrap_pct: 0.0 },
            { component_id: compMap["SLEEVE"], qty_per_unit: 2.0, scrap_pct: 0.0 },
            { component_id: compMap["COLLAR"], qty_per_unit: 1.0, scrap_pct: 0.0 },
            { component_id: compMap["LABEL"], qty_per_unit: 1.0, scrap_pct: 0.0 }
          ]
        })
      });

      // 8. Seed Stock quantities (worked example values)
      addLog("Adjusting physical inventory balances (Front=220, Back=180, Sleeves=600, Collars=1000, Labels=900)...");
      const stockSeed = [
        { component_id: compMap["FRONT-PANEL"], qty: 220 },
        { component_id: compMap["BACK-PANEL"], qty: 180 },
        { component_id: compMap["SLEEVE"], qty: 600 },
        { component_id: compMap["COLLAR"], qty: 1000 },
        { component_id: compMap["LABEL"], qty: 900 }
      ];

      for (const item of stockSeed) {
        await fetch("http://localhost:8000/api/v1/inventory/adjustments", {
          method: "POST",
          headers,
          body: JSON.stringify({
            component_id: item.component_id,
            warehouse_id: warehouse.id,
            qty: item.qty,
            movement_type: "grn"
          })
        });
      }

      // 9. Create Sales Order SO-1024 for 500 garments
      addLog("Publishing Sales Order SO-1024 for 500 units...");
      await fetch("http://localhost:8000/api/v1/sales-orders", {
        method: "POST",
        headers,
        body: JSON.stringify({
          customer_id: uuid(), // Dummy customer uuid
          order_no: "SO-1024",
          lines: [
            { product_id: product.id, qty_ordered: 500 }
          ]
        })
      });

      addLog("Worked scenario database seeding complete!");
      await fetchERPData(authToken);

    } catch (err: any) {
      addLog(`Seeding failed: ${err.message || String(err)}`);
    } finally {
      setIsSeeding(false);
    }
  };

  // Helper dummy UUID generator
  const uuid = () => {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c: any) =>
      (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16)
    );
  };

  // Run live Feasibility check
  const handleCheckFeasibility = async () => {
    if (!selectedOrderId) return;
    setCheckLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await fetch(`http://localhost:8000/api/v1/sales-orders/${selectedOrderId}/feasibility`, { headers });
      const data = await res.json();
      setFeasibility(data);
      setAiContext((prev: any) => ({ ...prev, active_order: "SO-1024", order_no: "SO-1024" }));
      addLog(`Run Feasibility check for Sales Order: ${data.sales_order_id ? "SO-1024" : selectedOrderId}`);
    } catch (err) {
      addLog("Feasibility check error: " + String(err));
    } finally {
      setCheckLoading(false);
    }
  };

  // Convert Feasibility Shortfalls to active Purchase Order
  const handleCreatePOFromShortfalls = async () => {
    if (!feasibility || !suppliers.length) return;
    setPoActionLoading("creating");
    try {
      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      };
      
      const supplierId = suppliers[0].id;
      const lines = feasibility.recommended_purchase_orders.map((po: any) => ({
        component_id: po.component_id,
        qty_ordered: po.qty,
        unit_cost: 4.50
      }));

      const poNo = `PO-${Math.floor(1000 + Math.random() * 9000)}`;
      addLog(`Creating purchase order ${poNo} for raw materials shortfall...`);

      const res = await fetch("http://localhost:8000/api/v1/purchasing/pos", {
        method: "POST",
        headers,
        body: JSON.stringify({
          supplier_id: supplierId,
          po_no: poNo,
          lines
        })
      });

      if (!res.ok) throw new Error(await res.text());
      const poObj = await res.json();
      addLog(`Purchase Order ${poNo} created in draft state.`);
      await fetchERPData(token);
      setActivePOId(poObj.id);
    } catch (err: any) {
      addLog(`PO creation failed: ${err.message || String(err)}`);
    } finally {
      setPoActionLoading("");
    }
  };

  // Approve Purchase Order (draft -> ordered)
  const handleApprovePO = async (poId: string) => {
    setPoActionLoading("approving");
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await fetch(`http://localhost:8000/api/v1/purchasing/pos/${poId}/approve`, {
        method: "POST",
        headers
      });
      if (!res.ok) throw new Error(await res.text());
      addLog("Purchase Order approved and dispatched to supplier.");
      await fetchERPData(token);
    } catch (err: any) {
      addLog(`PO approval failed: ${err.message || String(err)}`);
    } finally {
      setPoActionLoading("");
    }
  };

  // Receive Purchase Order (ordered -> received, updates stock GRN)
  const handleReceivePO = async (poId: string) => {
    if (!warehouses.length) return;
    setPoActionLoading("receiving");
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const whId = warehouses[0].id;
      const res = await fetch(`http://localhost:8000/api/v1/purchasing/pos/${poId}/receive?warehouse_id=${whId}`, {
        method: "POST",
        headers
      });
      if (!res.ok) throw new Error(await res.text());
      addLog("Purchase Order received. Component inventory balances updated (GRN).");
      await fetchERPData(token);
    } catch (err: any) {
      addLog(`PO receipt failed: ${err.message || String(err)}`);
    } finally {
      setPoActionLoading("");
    }
  };

  // Release Sales Order to Production Shop-Floor
  const handleReleaseToProduction = async () => {
    if (!salesOrders.length || !warehouses.length) return;
    setProdActionLoading("releasing");
    try {
      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      };
      
      const activeSO = salesOrders[0];
      const res = await fetch("http://localhost:8000/api/v1/production/runs", {
        method: "POST",
        headers,
        body: JSON.stringify({
          product_id: activeSO.lines[0].product_id,
          sales_order_id: activeSO.id,
          target_qty: activeSO.lines[0].qty_ordered,
          warehouse_id: warehouses[0].id
        })
      });

      if (!res.ok) throw new Error(await res.text());
      const runObj = await res.json();
      addLog(`Sales Order ${activeSO.order_no} released to Factory Floor. Scheduled Production Run.`);
      await fetchERPData(token);
      setActiveProdId(runObj.id);
    } catch (err: any) {
      addLog(`Production release failed: ${err.message || String(err)}`);
    } finally {
      setProdActionLoading("");
    }
  };

  // Transition Work Order Step (Cutting, Stitching, Finishing, Packing)
  const handleTransitionStep = async (woId: string, status: string) => {
    setProdActionLoading(woId);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await fetch(`http://localhost:8000/api/v1/production/work-orders/${woId}/transition?target_status=${status}`, {
        method: "POST",
        headers
      });
      if (!res.ok) throw new Error(await res.text());
      addLog(`WIP Stage transition complete: status updated to ${status}.`);
      await fetchERPData(token);
    } catch (err: any) {
      addLog(`Stage transition failed: ${err.message || String(err)}`);
    } finally {
      setProdActionLoading("");
    }
  };

  // Post User chat query to AI Assistant
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    const userMsg = chatMessage;
    setChatMessage("");
    setChatHistory((prev) => [...prev, { role: "user", answer: userMsg }]);
    setChatLoading(true);

    try {
      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      };
      
      const res = await fetch("http://localhost:8000/api/v1/ai/query", {
        method: "POST",
        headers,
        body: JSON.stringify({ message: userMsg, context: aiContext })
      });
      const data = await res.json();
      
      // Update session context from intent result slots
      if (data.intent === "check_feasibility" && data.data?.sales_order_id) {
        setAiContext((prev: any) => ({ ...prev, active_order: "SO-1024", order_no: "SO-1024" }));
      } else if (data.intent === "inventory_lookup" && data.data?.component_code) {
        setAiContext((prev: any) => ({ 
          ...prev, 
          active_component: data.data.component_code, 
          component_code: data.data.component_code 
        }));
      }
      
      setChatHistory((prev) => [
        ...prev, 
        { 
          role: "assistant", 
          answer: data.answer, 
          intent: data.intent,
          grounded_data: data.data,
          confidence: data.confidence
        }
      ]);
    } catch (err) {
      setChatHistory((prev) => [
        ...prev, 
        { 
          role: "assistant", 
          answer: "Sorry, I am unable to connect to the backend AI orchestrator." 
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Find active PO / Production order records
  const activePO = purchaseOrders.find(o => o.id === activePOId);
  const activeProd = productionOrders.find(o => o.id === activeProdId);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 font-sans p-6">
      
      {/* Header and API status */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 mb-6 border-b border-gray-800">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
            Factory<span className="text-blue-500">IQ</span>
            <span className="text-xs bg-blue-500/10 text-blue-400 font-mono py-0.5 px-2 rounded-full border border-blue-500/20">
              Manufacturing Intelligence Console
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">Multi-Tenant ERP & AI Feasibility Engine</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-mono text-gray-500">API STATUS:</span>
          {apiHealth === "online" && (
            <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
              Online
            </span>
          )}
          {apiHealth === "checking" && (
            <span className="py-1 px-2.5 rounded-full text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
              Checking...
            </span>
          )}
          {(apiHealth === "offline" || apiHealth === "error") && (
            <span className="py-1 px-2.5 rounded-full text-xs bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Offline (Check port 8000)
            </span>
          )}

          {tenantInfo ? (
            <div className="text-xs bg-gray-800 border border-gray-700 py-1.5 px-3 rounded-lg flex items-center gap-2">
              <span className="text-gray-500">Tenant:</span>
              <span className="font-semibold text-blue-400">{tenantInfo.subdomain}</span>
            </div>
          ) : (
            <button
              onClick={handleSeedScenario}
              disabled={isSeeding || apiHealth !== "online"}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 transition py-1.5 px-4 rounded-lg text-sm font-semibold shadow-lg text-white"
            >
              {isSeeding ? "Seeding Database..." : "Seed Worked T-Shirt Scenario"}
            </button>
          )}
        </div>
      </header>

      {/* Main Grid */}
      <main className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Column: ERP Listings and Feasibility Dashboard */}
        <section className="xl:col-span-2 flex flex-col gap-6">
          
          {/* Dashboard KPI cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase">Production Readiness</span>
              <span className="text-2xl font-bold text-blue-400 mt-2">
                {feasibility ? `${feasibility.readiness_pct}%` : "0%"}
              </span>
              <span className="text-[10px] text-gray-500 mt-1">Based on active feasibility checks</span>
            </div>
            <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase">Available SKUs</span>
              <span className="text-2xl font-bold text-white mt-2">{inventory.length} Components</span>
              <span className="text-[10px] text-gray-500 mt-1">Tracked across warehouses</span>
            </div>
            <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase">Active Sales Orders</span>
              <span className="text-2xl font-bold text-white mt-2">{salesOrders.length} Orders</span>
              <span className="text-[10px] text-gray-500 mt-1">Awaiting dispatch</span>
            </div>
            <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase">Factory WIP Jobs</span>
              <span className="text-2xl font-bold text-emerald-400 mt-2">
                {productionOrders.filter(o => o.status === "wip").length} Active
              </span>
              <span className="text-[10px] text-emerald-500 mt-1">Shop floor routing stages</span>
            </div>
          </div>

          {/* Feasibility Calculator Card */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              Deterministic Feasibility Engine
            </h2>
            
            <div className="flex flex-col md:flex-row gap-4 items-end mb-6">
              <div className="flex-1">
                <label className="block text-xs font-mono text-gray-400 mb-1.5">SELECT SALES ORDER</label>
                <select
                  value={selectedOrderId}
                  onChange={(e) => setSelectedOrderId(e.target.value)}
                  className="w-full bg-[#0B0F19] border border-gray-800 rounded-lg py-2 px-3 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">-- No Orders Available --</option>
                  {salesOrders.map((so) => (
                    <option key={so.id} value={so.id}>
                      {so.order_no} (Target Qty: {so.lines[0]?.qty_ordered} | Produced: {so.lines[0]?.qty_produced})
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleCheckFeasibility}
                disabled={checkLoading || !selectedOrderId}
                className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm transition py-2 px-6 rounded-lg shadow-lg disabled:bg-gray-800 disabled:text-gray-600"
              >
                {checkLoading ? "Calculating..." : "Run Feasibility Engine"}
              </button>
            </div>

            {/* Feasibility Outcomes */}
            {feasibility && (
              <div className="border-t border-gray-800 pt-6 flex flex-col gap-6">
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Readiness Circular Bar */}
                  <div className="bg-[#0B0F19] border border-gray-800/80 rounded-xl p-5 flex flex-col items-center justify-center text-center">
                    <span className="text-xs font-mono text-gray-500 uppercase">READINESS SCORE</span>
                    <div className="relative w-28 h-28 flex items-center justify-center mt-3">
                      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                        <path
                          className="text-gray-800"
                          strokeWidth="3.5"
                          stroke="currentColor"
                          fill="none"
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                        <path
                          className={feasibility.readiness_pct === 100 ? "text-emerald-500" : "text-amber-500"}
                          strokeWidth="3.5"
                          strokeDasharray={`${feasibility.readiness_pct}, 100`}
                          strokeLinecap="round"
                          stroke="currentColor"
                          fill="none"
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                      </svg>
                      <span className="absolute text-xl font-bold text-white">
                        {feasibility.readiness_pct}%
                      </span>
                    </div>
                    <span className="text-xs text-gray-400 mt-4">
                      Producible: <strong>{feasibility.producible_qty}</strong> / {feasibility.requested_qty}
                    </span>
                  </div>

                  {/* Bottleneck Constraints */}
                  <div className="md:col-span-2 bg-[#0B0F19] border border-gray-800/80 rounded-xl p-5 flex flex-col justify-between">
                    <div>
                      <span className="text-xs font-mono text-gray-500 uppercase">LIMITING CONSTRAINTS</span>
                      {feasibility.limiting_components.length > 0 ? (
                        <div className="mt-3 flex flex-col gap-2">
                          {feasibility.limiting_components.map((lc: any) => (
                            <div
                              key={lc.component_id}
                              className="bg-rose-500/5 border border-rose-500/20 py-2 px-3 rounded-lg flex items-center justify-between"
                            >
                              <span className="text-sm font-semibold text-rose-400">{lc.component_name} ({lc.component_code})</span>
                              <span className="text-xs text-rose-400 bg-rose-500/10 py-0.5 px-2 rounded font-mono">
                                Bottleneck Limit
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="mt-3 text-sm text-emerald-400 bg-emerald-500/5 border border-emerald-500/10 py-3 px-4 rounded-lg">
                          Zero bottleneck constraints. Stock is fully feasible.
                        </div>
                      )}
                    </div>

                    <div className="mt-4 pt-4 border-t border-gray-800/85">
                      <span className="text-xs font-mono text-gray-500 uppercase">SUGGESTED PROCUREMENT ORDERS</span>
                      {feasibility.recommended_purchase_orders.length > 0 ? (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-3">
                          {feasibility.recommended_purchase_orders.map((po: any) => (
                            <div
                              key={po.component_id}
                              className="bg-amber-500/5 border border-amber-500/20 py-2 px-3 rounded-lg flex flex-col justify-between"
                            >
                              <span className="text-xs text-amber-300 font-semibold">{po.component_code}</span>
                              <span className="text-lg font-bold text-amber-400 mt-1">+{po.qty} <span className="text-[10px] font-normal text-gray-400">pcs</span></span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-gray-500 mt-2">No purchase orders recommended.</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Operations triggers */}
                <div className="bg-[#0B0F19] border border-gray-800/60 p-4 rounded-xl flex flex-wrap gap-4 items-center justify-between">
                  <div className="text-xs text-gray-400">
                    {feasibility.readiness_pct === 100 ? (
                      <span>Stock is 100% ready. You can release this order to the factory floor.</span>
                    ) : (
                      <span>Shortages exist. You should generate purchase orders to acquire raw materials.</span>
                    )}
                  </div>

                  <div className="flex gap-3">
                    {feasibility.readiness_pct < 100 ? (
                      <button
                        onClick={handleCreatePOFromShortfalls}
                        disabled={poActionLoading !== "" || !suppliers.length}
                        className="bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs py-2 px-4 rounded-lg transition shadow disabled:opacity-40"
                      >
                        {poActionLoading === "creating" ? "Creating PO..." : "Convert Shortfalls to Purchase Order"}
                      </button>
                    ) : (
                      <button
                        onClick={handleReleaseToProduction}
                        disabled={prodActionLoading !== ""}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs py-2 px-4 rounded-lg transition shadow disabled:opacity-40"
                      >
                        {prodActionLoading === "releasing" ? "Releasing..." : "Release Order to Production"}
                      </button>
                    )}
                  </div>
                </div>

              </div>
            )}
          </div>

          {/* Purchasing Lifecycle panel */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
              Purchasing & Supply Chain Module
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* PO Registry list */}
              <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-4">
                <span className="text-xs font-mono text-gray-500 uppercase block mb-3">PO Registry</span>
                <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
                  {purchaseOrders.length > 0 ? (
                    purchaseOrders.map((po) => (
                      <button
                        key={po.id}
                        onClick={() => setActivePOId(po.id)}
                        className={`w-full text-left py-2 px-3 rounded-lg border text-xs flex justify-between items-center transition ${
                          activePOId === po.id
                            ? "bg-blue-600/10 border-blue-500 text-white"
                            : "bg-transparent border-gray-800 hover:border-gray-700 text-gray-400"
                        }`}
                      >
                        <span className="font-semibold">{po.po_no}</span>
                        <span className={`px-2 py-0.5 rounded font-mono text-[9px] uppercase ${
                          po.status === "received"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : po.status === "ordered"
                            ? "bg-blue-500/10 text-blue-400"
                            : "bg-gray-500/10 text-gray-400"
                        }`}>
                          {po.status}
                        </span>
                      </button>
                    ))
                  ) : (
                    <div className="text-xs text-gray-600 italic py-4 text-center">No POs registered.</div>
                  )}
                </div>
              </div>

              {/* Selected PO Details and Operations */}
              <div className="md:col-span-2 bg-[#0B0F19] border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
                {activePO ? (
                  <div>
                    <div className="flex justify-between items-start border-b border-gray-800/80 pb-2 mb-3">
                      <div>
                        <h4 className="text-sm font-bold text-white">{activePO.po_no}</h4>
                        <p className="text-[10px] text-gray-500 font-mono mt-0.5">ID: {activePO.id}</p>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-bold font-mono uppercase ${
                        activePO.status === "received"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : activePO.status === "ordered"
                          ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                      }`}>
                        {activePO.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center mb-4">
                      {activePO.lines.map((line: any) => (
                        <div key={line.id} className="bg-[#131B2E] border border-gray-800 p-2 rounded-lg">
                          <p className="text-[9px] font-mono text-gray-500">Component</p>
                          <p className="text-xs font-bold text-gray-300 mt-0.5">{line.component_id.substring(0,8)}...</p>
                          <p className="text-sm font-extrabold text-blue-400 mt-1">+{line.qty_ordered}</p>
                        </div>
                      ))}
                    </div>

                    {/* PO Stage transitions */}
                    <div className="flex justify-end gap-3 pt-2">
                      {activePO.status === "draft" && (
                        <button
                          onClick={() => handleApprovePO(activePO.id)}
                          disabled={poActionLoading !== ""}
                          className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs py-2 px-6 rounded-lg transition shadow"
                        >
                          Approve & Order Materials
                        </button>
                      )}
                      {activePO.status === "ordered" && (
                        <button
                          onClick={() => handleReceivePO(activePO.id)}
                          disabled={poActionLoading !== ""}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs py-2 px-6 rounded-lg transition shadow"
                        >
                          Mark as Received (GRN)
                        </button>
                      )}
                      {activePO.status === "received" && (
                        <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Fully Received into HQ Warehouse
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-gray-600 italic">
                    Select a Purchase Order to view lines and update status.
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* Production shop floor WIP tracking */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Production execution (WIP Stage Kanban)
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Runs List */}
              <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-4">
                <span className="text-xs font-mono text-gray-500 uppercase block mb-3">Active Runs</span>
                <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
                  {productionOrders.length > 0 ? (
                    productionOrders.map((run) => (
                      <button
                        key={run.id}
                        onClick={() => setActiveProdId(run.id)}
                        className={`w-full text-left py-2 px-3 rounded-lg border text-xs flex justify-between items-center transition ${
                          activeProdId === run.id
                            ? "bg-blue-600/10 border-blue-500 text-white"
                            : "bg-transparent border-gray-800 hover:border-gray-700 text-gray-400"
                        }`}
                      >
                        <div>
                          <span className="font-semibold">Run ID: {run.id.substring(0,8)}...</span>
                          <span className="block text-[10px] text-gray-500 mt-0.5">Target: {run.target_qty} units</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded font-mono text-[9px] uppercase ${
                          run.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : run.status === "wip"
                            ? "bg-yellow-500/10 text-yellow-400"
                            : "bg-gray-500/10 text-gray-400"
                        }`}>
                          {run.status}
                        </span>
                      </button>
                    ))
                  ) : (
                    <div className="text-xs text-gray-600 italic py-4 text-center">No production runs active.</div>
                  )}
                </div>
              </div>

              {/* Active WIP stages step tracker */}
              <div className="md:col-span-2 bg-[#0B0F19] border border-gray-800 rounded-xl p-4">
                {activeProd ? (
                  <div>
                    <span className="text-xs font-mono text-gray-500 uppercase block mb-4">Shop Floor Stage Routing</span>
                    
                    <div className="flex flex-col gap-3">
                      {activeProd.work_orders.map((wo: any) => {
                        const isLoading = prodActionLoading === wo.id;
                        return (
                          <div
                            key={wo.id}
                            className={`p-3 rounded-xl border flex items-center justify-between transition ${
                              wo.status === "completed"
                                ? "bg-emerald-500/5 border-emerald-500/15 text-emerald-400"
                                : wo.status === "active"
                                ? "bg-yellow-500/5 border-yellow-500/20 text-yellow-400"
                                : "bg-[#131B2E] border-gray-800/80 text-gray-400"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <span className="text-xs font-mono font-bold bg-black/35 py-1 px-2.5 rounded-lg">
                                SEQ {wo.sequence_no}
                              </span>
                              <span className="text-sm font-bold capitalize">{wo.stage}</span>
                            </div>

                            <div className="flex items-center gap-3">
                              <span className="text-[10px] font-mono uppercase tracking-wider">
                                {wo.status}
                              </span>

                              {wo.status === "pending" && (
                                <button
                                  onClick={() => handleTransitionStep(wo.id, "active")}
                                  disabled={prodActionLoading !== ""}
                                  className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[10px] py-1 px-3 rounded-lg transition"
                                >
                                  {isLoading ? "starting..." : "Start Stage"}
                                </button>
                              )}
                              {wo.status === "active" && (
                                <button
                                  onClick={() => handleTransitionStep(wo.id, "completed")}
                                  disabled={prodActionLoading !== ""}
                                  className="bg-yellow-500 hover:bg-yellow-400 text-black font-bold text-[10px] py-1 px-3 rounded-lg transition"
                                >
                                  {isLoading ? "completing..." : "Complete Stage"}
                                </button>
                              )}
                              {wo.status === "completed" && (
                                <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-gray-600 italic">
                    Select a Production Run to check WIP stage completion cards.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Inventory balances table */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
              </svg>
              Warehouse Inventory Balances (Read Ledger)
            </h2>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px] font-mono tracking-wider">
                    <th className="py-3 px-4">Component ID</th>
                    <th className="py-3 px-4">On Hand</th>
                    <th className="py-3 px-4">Reserved</th>
                    <th className="py-3 px-4">Allocated</th>
                    <th className="py-3 px-4">Damaged</th>
                    <th className="py-3 px-4">WIP</th>
                    <th className="py-3 px-4 text-right">Available Pool</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {inventory.length > 0 ? (
                    inventory.map((inv) => (
                      <tr key={inv.id} className="hover:bg-[#0B0F19]/45 transition">
                        <td className="py-3.5 px-4 font-semibold text-white">{inv.component_id.substring(0, 8)}...</td>
                        <td className="py-3.5 px-4">{inv.on_hand_qty}</td>
                        <td className="py-3.5 px-4 text-amber-500">{inv.reserved_qty}</td>
                        <td className="py-3.5 px-4 text-blue-400">{inv.allocated_qty}</td>
                        <td className="py-3.5 px-4 text-rose-500">{inv.damaged_qty}</td>
                        <td className="py-3.5 px-4 text-purple-400">{inv.wip_qty}</td>
                        <td className="py-3.5 px-4 text-right font-bold text-emerald-400">{inv.available_qty}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-gray-500">
                        No inventory balances tracked. Please register a tenant and seed the scenario database.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </section>

        {/* Right Column: AI Assistant Chat and Logs */}
        <section className="flex flex-col gap-6">
          
          {/* Chat Assistant */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-5 flex flex-col justify-between h-[450px] shadow-xl">
            <div className="border-b border-gray-800 pb-3 mb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
                </span>
                Operations AI Assistant
              </h2>
              <p className="text-xs text-gray-500">Self-Hosted SLM Grounding Model (Qwen 2.5 3B)</p>
            </div>

            {/* Chat History Panel */}
            <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3.5 mb-4 max-h-[300px]">
              {chatHistory.map((chat, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col max-w-[85%] ${
                    chat.role === "user" ? "ml-auto items-end" : "mr-auto items-start"
                  }`}
                >
                  <div
                    className={`py-2.5 px-4 rounded-xl text-sm ${
                      chat.role === "user"
                        ? "bg-blue-600 text-white rounded-br-none"
                        : "bg-[#0B0F19] text-gray-200 border border-gray-800 rounded-bl-none"
                    }`}
                  >
                    {chat.answer}
                  </div>
                  
                  {/* Grounded facts rendering bubble */}
                  {chat.grounded_data && (
                    <details className="mt-1 text-[10px] text-gray-400 cursor-pointer">
                      <summary className="hover:text-blue-400 transition font-mono uppercase tracking-wider">
                        🔍 Grounded Facts (SQL Output)
                      </summary>
                      <pre className="bg-[#0B0F19] border border-gray-800/80 p-2 rounded text-[10px] text-emerald-400 mt-1 overflow-x-auto max-w-[300px]">
                        {JSON.stringify(chat.grounded_data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
              {chatLoading && (
                <div className="text-xs text-gray-500 italic mr-auto">AI is composing response...</div>
              )}
            </div>

            {/* User message input form */}
            <form onSubmit={handleSendChat} className="flex gap-2">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Ask assistant e.g. 'Can I fulfill Order SO-1024?'"
                disabled={chatLoading || !token}
                className="flex-1 bg-[#0B0F19] border border-gray-800 rounded-lg py-2 px-3 text-sm text-white focus:outline-none focus:border-blue-500 disabled:opacity-55"
              />
              <button
                type="submit"
                disabled={chatLoading || !token}
                className="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg transition disabled:bg-gray-800 disabled:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </form>
          </div>

          {/* Operation logs panel */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-xl p-5 flex-grow shadow-xl">
            <h3 className="text-sm font-bold text-white mb-2 uppercase tracking-wide font-mono">Console Activity Log</h3>
            <div className="bg-[#0B0F19] border border-gray-800 p-3.5 rounded-lg h-36 overflow-y-auto text-[11px] font-mono text-gray-400 flex flex-col-reverse gap-1.5">
              {logs.length > 0 ? (
                logs.map((log, idx) => (
                  <div key={idx} className="border-b border-gray-900 pb-1 last:border-b-0">
                    {log}
                  </div>
                ))
              ) : (
                <div className="text-gray-600 italic">No console logs recorded yet.</div>
              )}
            </div>
          </div>

        </section>

      </main>

    </div>
  );
}
