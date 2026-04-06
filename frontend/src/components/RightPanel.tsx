'use client';

import React from 'react';
import dynamic from 'next/dynamic';

// Step 2: Use ClientTime for any dynamic timestamp rendering to avoid hydration mismatch
const ClientTime = dynamic(() => import('./ClientTime'), { ssr: false });

interface Alert {
  hex: string;
  callsign: string;
  message: string;
  severity: string;
  timestamp: number;
}

interface RightPanelProps {
  alerts: Alert[];
  onAlertClick?: (hex: string) => void;
}

const RightPanel: React.FC<RightPanelProps> = ({ alerts, onAlertClick }) => {
  return (
    <div className="flex-1 p-4 space-y-4 overflow-y-auto">
      {/* System Status Section */}
      <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
        <p className="text-xs text-slate-500 uppercase font-bold mb-1">System Status</p>
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-300 font-mono italic">ADSB-Stream</span>
          <span className="text-xs text-green-400 font-mono">CONNECTED</span>
        </div>
        <div className="flex justify-between items-center mt-1">
          <span className="text-sm text-slate-300 font-mono italic">Detection Engine</span>
          <span className="text-xs text-green-400 font-mono">ACTIVE</span>
        </div>
        <div className="flex justify-between items-center mt-1">
          <span className="text-sm text-slate-300 font-mono italic">Spatial DB</span>
          <span className="text-xs text-green-400 font-mono">SYNCED</span>
        </div>
      </div>

      {/* Priority Alerts Section */}
      <div className="space-y-2">
        <h3 className="text-xs font-bold text-slate-500 uppercase mb-2 tracking-widest">Global Watchlist</h3>
        
        <div className="flex flex-col gap-2">
          {Array.isArray(alerts) && alerts.length > 0 ? (
            alerts.map((alert, i) => (
              <div 
                key={`${alert.hex}-${i}`} 
                onClick={() => onAlertClick?.(alert.hex)}
                className="p-3 bg-slate-900/90 border-l-4 border-red-500 text-white rounded shadow-xl cursor-pointer hover:bg-slate-800 transition-all group"
              >
                <div className="flex justify-between items-center mb-1">
                  <b className="text-sm font-bold text-red-100 group-hover:text-red-400">
                    {alert.callsign || alert.hex}
                  </b>
                  <span className="text-[10px] text-red-300 uppercase font-bold tracking-widest bg-red-900/30 px-1.5 py-0.5 rounded">
                    {alert.severity}
                  </span>
                </div>
                <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">{alert.message}</p>
                <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-800">
                    <span className="text-[9px] text-slate-500 font-mono tracking-tighter uppercase opacity-60">ICAO: {alert.hex}</span>
                    <span className="text-[9px] text-slate-500 font-mono">
                        {/* Step 2 Fix: Replacing new Date().toLocaleTimeString() with ClientTime */}
                        <ClientTime ts={alert.timestamp} />
                    </span>
                </div>
              </div>
            ))
          ) : (
            <div className="p-4 bg-slate-900/40 border border-slate-800/50 border-l-4 border-emerald-500/60 text-slate-500 rounded text-xs italic leading-tight">
                Deep-Scanning regional sectors... No active threat signatures detected in current snapshot.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RightPanel;
