/**
 * SafeResponsiveContainer — workaround for the recharts 3.x "0 width on first
 * paint" bug that manifests on narrow viewports (mobile) and inside flex/grid
 * parents whose width isn't yet resolved when recharts runs its initial
 * ResizeObserver measurement.
 *
 * Strategy:
 *   1) Measure the real parent width with useRef + useLayoutEffect.
 *   2) Only render the chart once width > 0 so recharts never sees 0.
 *   3) Keep re-measuring on window resize so the chart stays responsive.
 *
 * Drop-in replacement for recharts' `ResponsiveContainer`:
 *     import { ResponsiveContainer } from '../components/layout/SafeResponsiveContainer';
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ResponsiveContainer as RCResponsiveContainer } from 'recharts';

export function ResponsiveContainer({
  width = '100%',
  height = 300,
  minHeight,
  minWidth = 0,
  aspect,
  debounce = 50,
  children,
  className,
  style: userStyle,
  ...rest
}) {
  const ref = useRef(null);
  const [w, setW] = useState(0);

  // Measure parent width synchronously after layout commits.
  // Tabs / accordions may mount this while hidden (display:none) which yields
  // width=0. We retry for ~1s and also subscribe to ResizeObserver so we pick
  // up the tab becoming visible.
  useLayoutEffect(() => {
    if (!ref.current) return;
    const measure = () => {
      const rect = ref.current?.getBoundingClientRect();
      if (rect && rect.width > 0) setW(rect.width);
    };
    measure();
    let ro;
    try {
      ro = new ResizeObserver(measure);
      ro.observe(ref.current);
    } catch { /* older browsers */ }
    window.addEventListener('resize', measure);

    // Retry loop: covers the hidden-tab case where ResizeObserver fails to
    // fire when display changes from none → block.
    const retry = setInterval(() => {
      const rect = ref.current?.getBoundingClientRect();
      if (rect && rect.width > 0) { setW(rect.width); clearInterval(retry); }
    }, 80);
    const stopRetry = setTimeout(() => clearInterval(retry), 3000);

    return () => {
      if (ro) ro.disconnect();
      window.removeEventListener('resize', measure);
      clearInterval(retry);
      clearTimeout(stopRetry);
    };
  }, []);

  const hPx = typeof height === 'number' ? `${height}px` : height;
  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: hPx,
    minHeight,
    minWidth,
    ...userStyle,
  };

  return (
    <div ref={ref} className={className} style={style}>
      {w > 0 ? (
        <RCResponsiveContainer
          width={w}
          height="100%"
          minWidth={minWidth}
          aspect={aspect}
          debounce={debounce}
          {...rest}
        >
          {children}
        </RCResponsiveContainer>
      ) : null}
    </div>
  );
}
