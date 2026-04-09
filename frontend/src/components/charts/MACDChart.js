import React from 'react';
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts';

export default function MACDChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="h-[200px] flex items-center justify-center text-[hsl(var(--muted-foreground))] text-sm">No MACD data</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="time"
          tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }}
          tickFormatter={(t) => t.slice(5)}
          interval="preserveStartEnd"
        />
        <YAxis tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }} width={45} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(222, 18%, 10%)',
            border: '1px solid hsl(222, 14%, 18%)',
            borderRadius: '8px',
            fontSize: '12px',
          }}
          labelStyle={{ color: 'hsl(210, 20%, 98%)' }}
        />
        <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
        <Bar
          dataKey="histogram"
          name="Histogram"
          fill="hsl(186, 92%, 42%)"
          opacity={0.6}
        />
        <Line type="monotone" dataKey="macd" name="MACD" stroke="hsl(186, 92%, 42%)" strokeWidth={1.5} dot={false} />
        <Line type="monotone" dataKey="signal" name="Signal" stroke="hsl(38, 92%, 55%)" strokeWidth={1.5} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
