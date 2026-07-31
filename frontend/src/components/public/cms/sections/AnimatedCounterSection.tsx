"use client";

import React, { useEffect, useRef, useState } from "react";
import { CmsSection } from "@/types/cms-v2";

interface CounterItemProps {
  label?: string;
  value?: number | string;
  suffix?: string;
  prefix?: string;
  duration_ms?: number;
  isVisible: boolean;
}

function CounterItem({ label, value, suffix = "", prefix = "", duration_ms = 2000, isVisible }: CounterItemProps) {
  const targetValue = typeof value === "number" ? value : parseFloat(String(value || "0")) || 0;
  const [currentValue, setCurrentValue] = useState(0);
  const animatedRef = useRef(false);

  useEffect(() => {
    if (!isVisible || animatedRef.current) return;
    animatedRef.current = true;

    const startTime = performance.now();
    const duration = duration_ms > 0 ? duration_ms : 2000;

    let animationFrameId: number;

    const updateCounter = (currentTime: number) => {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1);
      // Ease out cubic
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      const val = Math.floor(targetValue * easedProgress);

      setCurrentValue(val);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(updateCounter);
      } else {
        setCurrentValue(targetValue);
      }
    };

    animationFrameId = requestAnimationFrame(updateCounter);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [isVisible, targetValue, duration_ms]);

  return (
    <div className="flex flex-col items-center justify-center p-6 bg-white dark:bg-zinc-900/50 rounded-xl border border-gray-100 dark:border-zinc-800 shadow-sm text-center">
      <div className="text-4xl md:text-5xl font-extrabold text-[hsl(var(--primary))] tracking-tight">
        {prefix}{currentValue.toLocaleString()}{suffix}
      </div>
      {label && (
        <div className="mt-2 text-sm font-medium text-gray-600 dark:text-gray-400">
          {label}
        </div>
      )}
    </div>
  );
}

export function AnimatedCounterSection({ section }: { section: Partial<CmsSection<"animated_counter">> }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return;
    }

    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry && entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2 }
    );

    observer.observe(node);

    return () => {
      observer.disconnect();
    };
  }, []);

  const title = section.props_json?.title;
  const rawItems = section.props_json?.items;
  const items = Array.isArray(rawItems) ? rawItems : [];

  return (
    <section ref={containerRef} className="py-12 md:py-16 px-4 max-w-7xl mx-auto">
      {title && (
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-8 md:mb-12 text-gray-900 dark:text-white">
          {title}
        </h2>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 md:gap-8">
        {items.map((item, idx) => (
          <CounterItem
            key={idx}
            label={item.label}
            value={item.value}
            suffix={item.suffix}
            prefix={item.prefix}
            duration_ms={item.duration_ms}
            isVisible={isVisible}
          />
        ))}
      </div>
    </section>
  );
}
