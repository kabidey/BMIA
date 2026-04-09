import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid } from 'recharts';

export default function RSIChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="h-[200px] flex items-center justify-center text-[hsl(var(--muted-foreground))] text-sm">No RSI data</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="time"
          tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }}
          tickFormatter={(t) => t.slice(5)}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }}
          width={35}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(222, 18%, 10%)',
            border: '1px solid hsl(222, 14%, 18%)',
            borderRadius: '8px',
            fontSize: '12px',
          }}
          labelStyle={{ color: 'hsl(210, 20%, 98%)' }}
        />
        <ReferenceLine y={70} stroke="hsl(0, 72%, 52%)" strokeDasharray="3 3" strokeOpacity={0.5} />
        <ReferenceLine y={30} stroke="hsl(142, 70%, 45%)" strokeDasharray="3 3" strokeOpacity={0.5} />
        <Line
          type="monotone"
          dataKey="value"
          stroke="hsl(186, 92%, 42%)"
          strokeWidth={2}
          dot={false}
          name="RSI"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
