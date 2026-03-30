"use client"

import Link from "next/link"
import Image from "next/image"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#fdfdfd] text-[#1c1c1c] selection:bg-black selection:text-white flex flex-col overflow-hidden relative">
      
      {/* Decorative Blur Orbs for purely 3D soft lighting effect */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-100/40 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-gray-100/60 rounded-full blur-[150px] pointer-events-none" />

      {/* Minimalism Header */}
      <header className="w-full px-8 py-10 md:px-16 flex items-center justify-between z-10">
        <div className="flex items-baseline tracking-tighter cursor-default">
          <span className="text-4xl font-extrabold lowercase">screenvault</span>
          <span className="text-4xl font-extrabold text-blue-500">.</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-[1600px] mx-auto flex flex-col lg:flex-row items-center justify-between px-8 md:px-16 lg:px-24 z-10">
        
        {/* Left Typography Block */}
        <div className="w-full lg:w-1/2 flex flex-col justify-center gap-10 lg:pr-12 pt-12 lg:pt-0">
          <h1 className="text-6xl md:text-8xl font-black lowercase tracking-tighter leading-[0.9] text-black">
            visual<br />
            memory,<br />
            <span className="text-gray-300">perfected.</span>
          </h1>

          <p className="text-xl md:text-2xl font-light text-gray-500 max-w-md leading-relaxed">
            The intelligent storage for your screenshots. Search by text, concept, or context in milliseconds.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center gap-6">
            <Link 
              href="/vault"
              className="group relative inline-flex items-center justify-center px-10 py-5 font-bold text-white bg-black rounded-full overflow-hidden transition-all hover:scale-105 active:scale-95 shadow-2xl hover:shadow-black/20"
            >
              <span className="absolute inset-0 w-full h-full bg-gradient-to-tr from-transparent via-white/20 to-transparent translate-x-[-150%] skew-x-[-45deg] group-hover:translate-x-[150%] transition-transform duration-700 pointer-events-none" />
              <span className="text-[16px] tracking-wide">Enter Vault</span>
              <svg className="w-5 h-5 ml-3 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Link>

            <span className="text-sm font-medium text-gray-400">
              Free forever. Local-first.
            </span>
          </div>
        </div>

        {/* Right 3D Visual Block */}
        <div className="w-full lg:w-1/2 flex justify-center items-center mt-20 lg:mt-0 relative">
          <div className="relative w-full max-w-[700px] aspect-square animate-float flex items-center justify-center">
            {/* Soft shadow underneath the floating object */}
            <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-[60%] h-8 bg-black/5 rounded-[100%] blur-xl animate-pulse-shadow pointer-events-none" />
            
            <Image
              src="/3d-vault.png"
              alt="3D Minimal Vault"
              fill
              className="object-contain drop-shadow-2xl scale-110 lg:scale-125 select-none pointer-events-none"
              priority
            />
          </div>
        </div>

      </main>

    </div>
  )
}
