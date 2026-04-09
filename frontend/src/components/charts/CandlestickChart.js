import React, { useRef, useEffect } from 'react';
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

export default function CandlestickChart({ data }) {
  const chartRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!data || data.length === 0 || !containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: 'hsl(215, 16%, 70%)',
        fontFamily: 'Azeret Mono, monospace',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      localization: {
        locale: 'en-US',
      },
      width: containerRef.current.clientWidth,
      height: 400,
      crosshair: {
        mode: 0,
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.1)',
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.1)',
      },
    });

    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: 'hsl(142, 70%, 45%)',
      downColor: 'hsl(0, 72%, 52%)',
      borderUpColor: 'hsl(142, 70%, 45%)',
      borderDownColor: 'hsl(0, 72%, 52%)',
      wickUpColor: 'hsl(142, 70%, 50%)',
      wickDownColor: 'hsl(0, 72%, 55%)',
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    candleSeries.setData(
      data.map(d => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    volumeSeries.setData(
      data.map(d => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)',
      }))
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  if (!data || data.length === 0) {
    return <div className="h-[400px] flex items-center justify-center text-[hsl(var(--muted-foreground))] text-sm">No chart data available</div>;
  }

  return <div ref={containerRef} data-testid="candlestick-chart" />;
}
