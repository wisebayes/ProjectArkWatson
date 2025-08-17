"use client";
import React from "react";

export function Tabs({ tabs, current, onChange }: { tabs: string[]; current: string; onChange: (t: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map(t => {
        const active = current === t;
        return (
          <button
            key={t}
            onClick={() => onChange(t)}
            className={`px-3 py-2 rounded-lg text-sm font-semibold transition border ${
              active
                ? "bg-white/10 border-white/20"
                : "bg-white/[.03] border-white/10 hover:bg-white/[.06]"
            }`}
          >
            {t}
          </button>
        );
      })}
    </div>
  );
}


