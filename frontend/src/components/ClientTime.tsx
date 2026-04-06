"use client";

import { useEffect, useState } from "react";

/**
 * Step 1: ClientOnlyTime component.
 * Prevents Next.js Hydration Mismatch by ensuring time only renders 
 * after the component has mounted on the client.
 */
export default function ClientTime({ ts }: { ts: number }) {
  const [time, setTime] = useState<string | null>(null);

  useEffect(() => {
    const d = new Date(ts * 1000);
    setTime(
      d.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    );
  }, [ts]);

  // Server phase: Nothing is rendered (Perfect match)
  if (!time) return null;
  
  // Client phase: Time is rendered after mount
  return <>{time}</>;
}
