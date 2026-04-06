'use client';

import dynamic from 'next/dynamic';
import React, { useState, useEffect, useRef } from 'react';

// Maps and Panels
const AviationMap = dynamic(() => import('@/components/AviationMap'), { 
  ssr: false, 
  loading: () => <div className="w-full h-full bg-slate-900 flex items-center justify-center font-mono italic text-slate-500 uppercase tracking-widest animate-pulse">Establishing Regional ADSB Feed...</div>
});

const RightPanel = dynamic(() => import('@/components/RightPanel'), { 
  ssr: false 
});

interface Alert {
  hex: string;
  callsign: string;
  message: string;
  severity: string;
  timestamp: number;
  created_at: number;
}

export default function Home() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedHex, setSelectedHex] = useState<string | null>(null);
  
  // Requirement 4: lastSeenRef manages time, but not rendered in server JSX anymore
  const [lastFetch, setLastFetch] = useState<number>(0);
  const lastSeenRef = useRef<number>(Date.now() / 1000);

  useEffect(() => {
    const fetchAlerts = () => {
      fetch(`http://localhost:8000/aircraft/alerts/live?since=${lastSeenRef.current}`)
        .then(res => res.json())
        .then(data => {
            const newAlerts: Alert[] = Array.isArray(data) ? data : [];
            
            if (newAlerts.length > 0) {
              const latestTs = newAlerts[newAlerts.length - 1].created_at;
              lastSeenRef.current = latestTs;
              setLastFetch(latestTs);
              
              setAlerts(prev => {
                const existingHexes = new Set(prev.map(a => `${a.hex}-${a.created_at}`));
                const uniqueNew = newAlerts.filter(a => !existingHexes.has(`${a.hex}-${a.created_at}`));
                return [...uniqueNew, ...prev].slice(0, 50); 
              });
            }
        })
        .catch(err => console.error("Cursor Polling Error:", err));
    };

    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="flex min-h-screen flex-col bg-slate-950 overflow-hidden font-sans text-slate-200">
      <div className="flex-1 relative flex">
        {/* Main Tracking Area */}
        <div className="flex-1 relative border-r border-slate-800 shadow-inner">
           <AviationMap onSelect={setSelectedHex} selectedHex={selectedHex} />
        </div>

        {/* Intelligence Side Panel */}
        <div className="w-96 bg-slate-900/50 backdrop-blur-xl flex flex-col border-l border-slate-800 shadow-2xl overflow-y-auto">
           <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-900/80">
              <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Active Intelligence</h2>
              <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 text-[10px] font-bold uppercase animate-pulse border border-sky-500/40">Live Feed</span>
           </div>
           
           <RightPanel alerts={alerts} onAlertClick={(hex) => setSelectedHex(hex)} />

           <div className="p-6 border-t border-slate-800 bg-slate-900/80">
              <div className="flex items-center gap-2 mb-2">
                 <div className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-ping"></div>
                 <span className="text-[10px] text-slate-400 font-medium uppercase tracking-tighter italic">Sector-Matched Anomaly Stream</span>
              </div>
              {/* Step 3 Fix: Replacing dynamic time string with static text to avoid hydration killers */}
              <p className="text-[9px] text-slate-600 leading-tight">
                 Incremental cursor-polling activated. Monitoring regional sky patterns with high-fidelity ADS-B correlating nodes. 
              </p>
           </div>
        </div>
      </div>
    </main>
  );
}
