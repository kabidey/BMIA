import { useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { TrendingUp, TrendingDown } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function SignalAlerts() {
  const seenAlerts = useRef(new Set());
  const lastCheck = useRef(new Date().toISOString());

  useEffect(() => {
    const checkAlerts = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/signals/alerts?since=${lastCheck.current}`);
        if (!res.ok) return;
        const data = await res.json();
        const alerts = data.alerts || [];

        for (const alert of alerts) {
          const key = `${alert.symbol}-${alert.status}-${alert.evaluated_at}`;
          if (seenAlerts.current.has(key)) continue;
          seenAlerts.current.add(key);

          if (alert.status === 'TARGET_HIT') {
            toast.success(
              `${alert.symbol} Target Hit! +${alert.return_pct?.toFixed(2)}%`,
              {
                description: `${alert.action} signal closed at ${alert.current_price?.toFixed(2)}`,
                duration: 8000,
                icon: <TrendingUp className="w-4 h-4" />,
              }
            );
          } else if (alert.status === 'STOP_LOSS_HIT') {
            toast.error(
              `${alert.symbol} Stop Loss Hit! ${alert.return_pct?.toFixed(2)}%`,
              {
                description: `${alert.action} signal closed at ${alert.current_price?.toFixed(2)}`,
                duration: 8000,
                icon: <TrendingDown className="w-4 h-4" />,
              }
            );
          }
        }

        lastCheck.current = new Date().toISOString();
      } catch (e) {
        // Silent fail for polling
      }
    };

    // Initial check
    checkAlerts();

    // Poll every 60 seconds
    const interval = setInterval(checkAlerts, 60000);
    return () => clearInterval(interval);
  }, []);

  return null; // This component only produces toasts
}
