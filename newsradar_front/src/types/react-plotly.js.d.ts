/* Minimal type declarations for react-plotly.js and plotly.js */

declare module 'plotly.js' {
  export interface Data {
    type?: string;
    x?: unknown[];
    y?: unknown[];
    z?: unknown[];
    text?: string | string[];
    name?: string;
    mode?: string;
    marker?: Partial<PlotMarker>;
    line?: Partial<PlotLine>;
    fill?: string;
    fillcolor?: string;
    hoverinfo?: string;
    hovertext?: string | string[];
    hovertemplate?: string | string[];
    orientation?: 'v' | 'h';
    showlegend?: boolean;
    opacity?: number;
    customdata?: unknown[];
    [key: string]: unknown;
  }

  export interface PlotMarker {
    color?: string | string[] | number[];
    size?: number | number[];
    symbol?: string | string[];
    opacity?: number | number[];
    line?: Partial<PlotLine>;
    colorscale?: unknown;
    [key: string]: unknown;
  }

  export interface PlotLine {
    color?: string;
    width?: number;
    dash?: string;
    [key: string]: unknown;
  }

  export interface Layout {
    title?: string | Partial<{ text: string; font: unknown }>;
    autosize?: boolean;
    width?: number;
    height?: number;
    xaxis?: Partial<LayoutAxis>;
    yaxis?: Partial<LayoutAxis>;
    margin?: Partial<Margin>;
    showlegend?: boolean;
    legend?: Partial<Legend>;
    annotations?: Partial<Annotation>[];
    shapes?: Partial<Shape>[];
    paper_bgcolor?: string;
    plot_bgcolor?: string;
    font?: Partial<Font>;
    barmode?: string;
    hovermode?: string | false;
    [key: string]: unknown;
  }

  export interface LayoutAxis {
    title?: string | Partial<{ text: string; font: unknown }>;
    range?: [number, number];
    type?: string;
    showgrid?: boolean;
    zeroline?: boolean;
    tickvals?: unknown[];
    ticktext?: string[];
    tickangle?: number;
    dtick?: number;
    [key: string]: unknown;
  }

  export interface Margin {
    l: number;
    r: number;
    t: number;
    b: number;
    pad?: number;
  }

  export interface Legend {
    x?: number;
    y?: number;
    orientation?: 'v' | 'h';
    [key: string]: unknown;
  }

  export interface Annotation {
    x?: number;
    y?: number;
    text?: string;
    showarrow?: boolean;
    font?: Partial<Font>;
    xref?: string;
    yref?: string;
    [key: string]: unknown;
  }

  export interface Shape {
    type?: string;
    x0?: number;
    y0?: number;
    x1?: number;
    y1?: number;
    line?: Partial<PlotLine>;
    fillcolor?: string;
    opacity?: number;
    [key: string]: unknown;
  }

  export interface Font {
    family?: string;
    size?: number;
    color?: string;
  }

  export interface Config {
    responsive?: boolean;
    displayModeBar?: boolean;
    displaylogo?: boolean;
    scrollZoom?: boolean;
    staticPlot?: boolean;
    [key: string]: unknown;
  }

  export interface Frame {
    name?: string;
    data?: Data[];
    layout?: Partial<Layout>;
    [key: string]: unknown;
  }

  export interface PlotMouseEvent {
    points: Array<{
      pointIndex: number;
      pointNumber: number;
      curveNumber: number;
      data: Data;
      x: unknown;
      y: unknown;
      [key: string]: unknown;
    }>;
    event: MouseEvent;
  }

  export interface PlotSelectionEvent {
    points: Array<{
      pointIndex: number;
      pointNumber: number;
      curveNumber: number;
      data: Data;
      x: unknown;
      y: unknown;
      [key: string]: unknown;
    }>;
  }

  export interface PlotRelayoutEvent {
    [key: string]: unknown;
  }
}

declare module 'react-plotly.js' {
  import { Component } from 'react';
  import type { Data, Layout, Config, Frame, PlotMouseEvent, PlotSelectionEvent, PlotRelayoutEvent } from 'plotly.js';

  export interface PlotParams {
    data: Data[];
    layout?: Partial<Layout>;
    config?: Partial<Config>;
    frames?: Frame[];
    style?: React.CSSProperties;
    className?: string;
    useResizeHandler?: boolean;
    revision?: number;
    onInitialized?: (figure: { data: Data[]; layout: Partial<Layout> }, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: { data: Data[]; layout: Partial<Layout> }, graphDiv: HTMLElement) => void;
    onPurge?: (figure: { data: Data[]; layout: Partial<Layout> }, graphDiv: HTMLElement) => void;
    onError?: (err: Error) => void;
    onClick?: (event: PlotMouseEvent) => void;
    onHover?: (event: PlotMouseEvent) => void;
    onUnhover?: (event: PlotMouseEvent) => void;
    onSelected?: (event: PlotSelectionEvent) => void;
    onRelayout?: (event: PlotRelayoutEvent) => void;
  }

  class Plot extends Component<PlotParams> {}
  export default Plot;
}
