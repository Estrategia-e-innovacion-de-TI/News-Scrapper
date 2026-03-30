import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import dynamic from 'next/dynamic';
import type {
  Data,
  Layout,
  Config,
  PlotMouseEvent,
  PlotSelectionEvent,
  PlotRelayoutEvent,
} from 'plotly.js';

/* ---------- Lazy-load react-plotly.js (SSR-safe) ---------- */
const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <p style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
      Cargando gráfica…
    </p>
  ),
});

/* ---------- Error boundary for Plotly load failures ---------- */
interface ErrorBoundaryProps {
  children: ReactNode;
}
interface ErrorBoundaryState {
  hasError: boolean;
}

class PlotlyErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('PlotlyWrapper: failed to load visualization', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            textAlign: 'center',
            padding: '2rem',
            color: '#ef4444',
            background: '#fef2f2',
            borderRadius: '0.5rem',
          }}
        >
          Visualización no disponible
        </div>
      );
    }
    return this.props.children;
  }
}

/* ---------- PlotlyWrapper props ---------- */
export interface PlotlyWrapperProps {
  data: Data[];
  layout?: Partial<Layout>;
  config?: Partial<Config>;
  style?: React.CSSProperties;
  className?: string;
  useResizeHandler?: boolean;
  revision?: number;
  onClick?: (event: PlotMouseEvent) => void;
  onHover?: (event: PlotMouseEvent) => void;
  onUnhover?: (event: PlotMouseEvent) => void;
  onSelected?: (event: PlotSelectionEvent) => void;
  onRelayout?: (event: PlotRelayoutEvent) => void;
}

/* ---------- PlotlyWrapper component ---------- */
export default function PlotlyWrapper({
  data,
  layout,
  config,
  style,
  className,
  useResizeHandler = true,
  ...rest
}: PlotlyWrapperProps) {
  return (
    <PlotlyErrorBoundary>
      <Plot
        data={data}
        layout={{ autosize: true, ...layout }}
        config={{ responsive: true, displayModeBar: false, ...config }}
        style={{ width: '100%', ...style }}
        className={className}
        useResizeHandler={useResizeHandler}
        {...rest}
      />
    </PlotlyErrorBoundary>
  );
}
