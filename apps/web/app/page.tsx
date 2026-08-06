"use client";

import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 font-sans selection:bg-blue-500 selection:text-white relative overflow-hidden">
      
      {/* Dynamic Background Glow Effect */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-gradient-to-b from-blue-600/20 via-cyan-500/10 to-transparent blur-[140px] pointer-events-none rounded-full" />
      <div className="absolute top-[800px] right-0 w-[600px] h-[600px] bg-purple-600/10 blur-[160px] pointer-events-none rounded-full" />

      {/* Navigation Bar */}
      <nav className="max-w-7xl mx-auto px-6 py-6 flex justify-between items-center relative z-20 border-b border-gray-800/60">
        <div className="flex items-center gap-3">
          <span className="bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-black text-sm px-3 py-1.5 rounded-xl shadow-lg shadow-blue-500/20">
            FIQ
          </span>
          <span className="font-extrabold text-2xl tracking-tight text-white">
            Factory<span className="text-blue-400">IQ</span>
          </span>
        </div>

        <div className="hidden md:flex items-center gap-8 text-xs font-semibold text-gray-400">
          <a href="#features" className="hover:text-white transition">Features</a>
          <a href="#industries" className="hover:text-white transition">Industries</a>
          <a href="#pricing" className="hover:text-white transition">Pricing</a>
          <a href="#architecture" className="hover:text-white transition">Cell Architecture</a>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-xs font-semibold text-gray-300 hover:text-white transition px-4 py-2"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-bold py-2.5 px-5 rounded-xl transition shadow-lg shadow-blue-500/25"
          >
            Register Factory Free →
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center relative z-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-6">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          Autonomous AI-Driven Smart Manufacturing ERP
        </div>

        <h1 className="text-4xl md:text-6xl font-black text-white tracking-tight leading-[1.15] mb-6">
          The Intelligent Operating System for <br />
          <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-teal-300 bg-clip-text text-transparent">
            Modern Smart Factories
          </span>
        </h1>

        <p className="text-base md:text-lg text-gray-400 max-w-3xl mx-auto mb-10 leading-relaxed">
          FactoryIQ powers manufacturing cells with real-time multi-product BOM explosions, automated Material Requirements Planning (MRP), dynamic job scheduling, quality inspection gates, and AI-driven operational insights.
        </p>

        <div className="flex flex-col sm:flex-row justify-center gap-4 max-w-md mx-auto">
          <Link
            href="/register"
            className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-extrabold text-sm py-3.5 px-8 rounded-xl transition shadow-xl shadow-blue-500/25 text-center"
          >
            Register Free Factory Cell
          </Link>
          <Link
            href="/login"
            className="bg-gray-800/80 hover:bg-gray-700 text-gray-200 font-bold text-sm py-3.5 px-8 rounded-xl border border-gray-700 transition text-center"
          >
            Sign In to Existing Workspace
          </Link>
        </div>
      </section>

      {/* Feature Grid Section */}
      <section id="features" className="max-w-7xl mx-auto px-6 py-20 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight">
            Engineered for Precision & Production Velocity
          </h2>
          <p className="text-xs md:text-sm text-gray-400 mt-2">
            Every core ERP engine built natively to handle complex manufacturing workflows
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-[#131B2E] border border-gray-800 p-6 rounded-2xl hover:border-blue-500/40 transition group">
            <span className="text-3xl mb-4 block">⚙️</span>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition">MRP & Gantt Timelines</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Explode multi-level BOMs against live stock balances. Auto-generate purchase draft POs for inventory shortfalls and visualize stage lead-time Gantt bars.
            </p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-6 rounded-2xl hover:border-blue-500/40 transition group">
            <span className="text-3xl mb-4 block">🎯</span>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition">Dynamic Order Feasibility</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Evaluate commercial sales order fulfillment feasibility in real-time. Calculate exact max shippable units based on component availability.
            </p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-6 rounded-2xl hover:border-blue-500/40 transition group">
            <span className="text-3xl mb-4 block">🤖</span>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition">FactoryIQ AI Assistant</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Natural language ERP command interface backed by tool calling and a deterministic Hallucination Gate to guarantee 100% grounded operational responses.
            </p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-6 rounded-2xl hover:border-blue-500/40 transition group">
            <span className="text-3xl mb-4 block">🛡️</span>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition">Quality Control Gates</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Define stage-specific inspection gate rules, allowable defect thresholds, and automated scrap disposition logging for rework or vendor returns.
            </p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-6 rounded-2xl hover:border-blue-500/40 transition group">
            <span className="text-3xl mb-4 block">💰</span>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition">Standard vs Actual Job Costing</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Accumulate direct material, labor hours, and factory overhead per job order. Compare actual costs against standard benchmarks with variance analysis.
            </p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-6 rounded-2xl hover:border-blue-500/40 transition group">
            <span className="text-3xl mb-4 block">🔒</span>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition">Isolated Cell Architecture</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Every client operates inside a dedicated single-tenant cell with database Row-Level Security (RLS) policies and private schema isolation options.
            </p>
          </div>
        </div>
      </section>

      {/* Multi-Industry Workflows */}
      <section id="industries" className="max-w-7xl mx-auto px-6 py-16 border-t border-gray-800/60 relative z-10">
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight">
            Tailored Industry Production Templates
          </h2>
          <p className="text-xs md:text-sm text-gray-400 mt-2">
            Configure stage lead times and assembly rules for your specific manufacturing process
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-[#131B2E] border border-gray-800 p-5 rounded-xl">
            <span className="text-xs font-mono text-blue-400 font-bold uppercase block mb-1">Garment Industry</span>
            <h4 className="text-sm font-bold text-white mb-2">Apparel & Textiles</h4>
            <p className="text-xs text-gray-400">Cutting → Stitching → Finishing → Packing</p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-5 rounded-xl">
            <span className="text-xs font-mono text-emerald-400 font-bold uppercase block mb-1">Furniture Industry</span>
            <h4 className="text-sm font-bold text-white mb-2">Woodwork & Furniture</h4>
            <p className="text-xs text-gray-400">Wood Cutting → Sanding → Assembly → Polishing</p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-5 rounded-xl">
            <span className="text-xs font-mono text-amber-400 font-bold uppercase block mb-1">Electronics Industry</span>
            <h4 className="text-sm font-bold text-white mb-2">Hardware & PCB</h4>
            <p className="text-xs text-gray-400">SMT Assembly → Soldering → Testing → Casing</p>
          </div>

          <div className="bg-[#131B2E] border border-gray-800 p-5 rounded-xl">
            <span className="text-xs font-mono text-purple-400 font-bold uppercase block mb-1">Custom Fabrication</span>
            <h4 className="text-sm font-bold text-white mb-2">Industrial Equipment</h4>
            <p className="text-xs text-gray-400">Design → Fabrication → Assembly → QA</p>
          </div>
        </div>
      </section>

      {/* Subscription Pricing Grid Section */}
      <section id="pricing" className="max-w-7xl mx-auto px-6 py-20 border-t border-gray-800/60 relative z-10">
        <div className="text-center mb-16">
          <span className="text-xs font-mono text-blue-400 font-bold uppercase block mb-2">Flexible Subscription Model</span>
          <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight">
            Free Registration & Scalable Tiers
          </h2>
          <p className="text-xs md:text-sm text-gray-400 mt-2">
            Registration is 100% free with an initial trial. Upgrade anytime as your factory scales.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {/* Starter Plan */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-2xl p-6 flex flex-col justify-between hover:border-gray-700 transition">
            <div>
              <span className="text-xs font-mono text-gray-400 uppercase font-bold">Free Registration</span>
              <h3 className="text-xl font-bold text-white mt-1">Starter Trial</h3>
              <div className="my-4">
                <span className="text-3xl font-extrabold text-white">$0</span>
                <span className="text-xs text-gray-400"> / free registration</span>
              </div>
              <ul className="space-y-2.5 text-xs text-gray-300 mb-6">
                <li className="flex items-center gap-2">✓ Full ERP Workspace Access</li>
                <li className="flex items-center gap-2">✓ Multi-Product BOM Explorer</li>
                <li className="flex items-center gap-2">✓ Up to 100 SKU Product Limit</li>
                <li className="flex items-center gap-2">✓ MRP Engine & Gantt Scheduling</li>
              </ul>
            </div>
            <Link
              href="/register"
              className="w-full bg-gray-800 hover:bg-gray-700 text-white font-bold text-xs py-3 rounded-xl transition text-center"
            >
              Start Free Trial →
            </Link>
          </div>

          {/* Growth Plan */}
          <div className="bg-[#131B2E] border-2 border-blue-500 rounded-2xl p-6 flex flex-col justify-between relative shadow-2xl shadow-blue-500/10">
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-[10px] font-extrabold uppercase py-0.5 px-3 rounded-full">
              Most Popular
            </span>
            <div>
              <span className="text-xs font-mono text-blue-400 uppercase font-bold">Growth Cell</span>
              <h3 className="text-xl font-bold text-white mt-1">Professional Factory</h3>
              <div className="my-4">
                <span className="text-4xl font-extrabold text-white">$199</span>
                <span className="text-xs text-gray-400"> / month</span>
              </div>
              <ul className="space-y-2.5 text-xs text-gray-300 mb-6">
                <li className="flex items-center gap-2">✓ Unlimited Product SKUs</li>
                <li className="flex items-center gap-2">✓ Multi-Warehouse Stock Isolation</li>
                <li className="flex items-center gap-2">✓ Quality Inspection Gates</li>
                <li className="flex items-center gap-2">✓ Standard vs Actual Job Costing</li>
                <li className="flex items-center gap-2">✓ FactoryIQ AI Assistant</li>
              </ul>
            </div>
            <Link
              href="/register"
              className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-xs py-3 rounded-xl transition text-center shadow-lg"
            >
              Deploy Growth Cell →
            </Link>
          </div>

          {/* Enterprise Plan */}
          <div className="bg-[#131B2E] border border-gray-800 rounded-2xl p-6 flex flex-col justify-between hover:border-gray-700 transition">
            <div>
              <span className="text-xs font-mono text-purple-400 uppercase font-bold">Enterprise Isolation</span>
              <h3 className="text-xl font-bold text-white mt-1">Custom Dedicated</h3>
              <div className="my-4">
                <span className="text-3xl font-extrabold text-white">Custom</span>
                <span className="text-xs text-gray-400"> / volume pricing</span>
              </div>
              <ul className="space-y-2.5 text-xs text-gray-300 mb-6">
                <li className="flex items-center gap-2">✓ Private Postgres Schema Namespace</li>
                <li className="flex items-center gap-2">✓ Custom Stage Routing Engine</li>
                <li className="flex items-center gap-2">✓ Dedicated SLA & Support</li>
                <li className="flex items-center gap-2">✓ Custom ERP Integrations</li>
              </ul>
            </div>
            <Link
              href="/register"
              className="w-full bg-gray-800 hover:bg-gray-700 text-white font-bold text-xs py-3 rounded-xl transition text-center"
            >
              Contact Enterprise →
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-6 py-10 border-t border-gray-800/60 flex flex-col md:flex-row justify-between items-center gap-4 relative z-10 text-xs text-gray-500">
        <div>
          © {new Date().getFullYear()} FactoryIQ Inc. All rights reserved. Autonomous Smart Manufacturing ERP.
        </div>
        <div className="flex items-center gap-6">
          <Link href="/login" className="hover:text-gray-300 transition">Sign In</Link>
          <Link href="/register" className="hover:text-gray-300 transition">Register Factory</Link>
          <Link href="/admin/platform" className="hover:text-purple-400 transition flex items-center gap-1">
            <span>🛡️</span> Platform Superadmin
          </Link>
        </div>
      </footer>
    </div>
  );
}
