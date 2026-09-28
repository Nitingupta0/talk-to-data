import { useEffect, useState } from "react";

export type ThemePref = "light" | "dark" | "system";
export type Theme = "light" | "dark";

// Validated categorical palette (fixed order — never cycled past 8; see the dataviz reference palette).
export const SERIES: Record<Theme, string[]> = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
};

export const CHART_INK: Record<Theme, { grid: string; axis: string; text: string; surface: string }> = {
  light: { grid: "#e8e7e3", axis: "#8a8984", text: "#52514e", surface: "#ffffff" },
  dark: { grid: "#2e2e2b", axis: "#77766f", text: "#c3c2b7", surface: "#1c1c1a" },
};

function systemTheme(): Theme {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function readPref(): ThemePref {
  try {
    const v = localStorage.getItem("ttd-theme");
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    /* storage unavailable */
  }
  return "system";
}

export function useTheme() {
  const [pref, setPref] = useState<ThemePref>(readPref);
  const [system, setSystem] = useState<Theme>(systemTheme);

  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const onChange = () => setSystem(mq.matches ? "dark" : "light");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const theme: Theme = pref === "system" ? system : pref;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("ttd-theme", pref);
    } catch {
      /* ignore */
    }
  }, [theme, pref]);

  const toggle = () => setPref(theme === "dark" ? "light" : "dark");
  return { theme, toggle };
}
