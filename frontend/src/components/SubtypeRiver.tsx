'use client';

import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';

const SUBTYPE_COLORS: Record<string, string> = {
  LumA: '#3b82f6',
  LumB: '#6366f1',
  Her2: '#ec4899',
  Basal: '#ef4444',
  Normal: '#10b981',
};

const SUBTYPES = ['Normal', 'LumA', 'LumB', 'Her2', 'Basal'];

interface SubtypeDistribution {
  timepoint: string;
  proportions: Record<string, number>;
}

interface SubtypeRiverProps {
  data?: SubtypeDistribution[];
  width?: number;
  height?: number;
}

function generateDemoData(): SubtypeDistribution[] {
  const timepoints = [
    'Normal',
    'Early ADH',
    'Late ADH',
    'Early DCIS',
    'Late DCIS',
    'Early IDC',
    'Advanced IDC',
    'Metastatic',
  ];

  return timepoints.map((tp, i) => {
    const progress = i / (timepoints.length - 1);
    return {
      timepoint: tp,
      proportions: {
        Normal: Math.max(0, 0.6 - progress * 0.8),
        LumA: 0.15 + Math.sin(progress * Math.PI) * 0.2,
        LumB: 0.1 + progress * 0.15,
        Her2: progress > 0.3 ? (progress - 0.3) * 0.3 : 0,
        Basal: progress > 0.5 ? (progress - 0.5) * 0.4 : 0,
      },
    };
  });
}

export default function SubtypeRiver({
  data,
  width = 800,
  height = 400,
}: SubtypeRiverProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const chartData = useMemo(() => data || generateDemoData(), [data]);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 30, right: 120, bottom: 50, left: 60 };
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Prepare stacked data
    const stackData = chartData.map((d, i) => ({
      index: i,
      timepoint: d.timepoint,
      ...d.proportions,
    }));

    const stack = d3
      .stack<(typeof stackData)[0]>()
      .keys(SUBTYPES)
      .offset(d3.stackOffsetWiggle)
      .order(d3.stackOrderInsideOut);

    const series = stack(stackData);

    // Scales
    const x = d3
      .scaleLinear()
      .domain([0, chartData.length - 1])
      .range([0, w]);

    const yMin = d3.min(series, (s) => d3.min(s, (d) => d[0])) || 0;
    const yMax = d3.max(series, (s) => d3.max(s, (d) => d[1])) || 1;
    const y = d3.scaleLinear().domain([yMin, yMax]).range([h, 0]);

    // Area generator
    const area = d3
      .area<d3.SeriesPoint<(typeof stackData)[0]>>()
      .x((d) => x(d.data.index))
      .y0((d) => y(d[0]))
      .y1((d) => y(d[1]))
      .curve(d3.curveBasis);

    // Draw streams
    g.selectAll('path')
      .data(series)
      .join('path')
      .attr('d', area)
      .attr('fill', (d) => SUBTYPE_COLORS[d.key] || '#888')
      .attr('opacity', 0.85)
      .attr('stroke', 'rgba(0,0,0,0.3)')
      .attr('stroke-width', 0.5)
      .on('mouseover', function () {
        d3.select(this).attr('opacity', 1).attr('stroke-width', 2);
      })
      .on('mouseout', function () {
        d3.select(this).attr('opacity', 0.85).attr('stroke-width', 0.5);
      });

    // X axis
    g.append('g')
      .attr('transform', `translate(0,${h})`)
      .call(
        d3
          .axisBottom(x)
          .ticks(chartData.length)
          .tickFormat((d) => chartData[d as number]?.timepoint || '')
      )
      .selectAll('text')
      .attr('fill', '#8888aa')
      .attr('font-size', '10px')
      .attr('transform', 'rotate(-30)')
      .style('text-anchor', 'end');

    g.selectAll('.domain, .tick line').attr('stroke', '#333');

    // Title
    svg
      .append('text')
      .attr('x', width / 2)
      .attr('y', 20)
      .attr('text-anchor', 'middle')
      .attr('fill', '#e8e8f0')
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text('Subtype Emergence River — Progression Timeline');

    // Legend
    const legend = svg
      .append('g')
      .attr(
        'transform',
        `translate(${width - margin.right + 10}, ${margin.top})`
      );

    SUBTYPES.forEach((subtype, i) => {
      const row = legend.append('g').attr('transform', `translate(0, ${i * 22})`);
      row
        .append('rect')
        .attr('width', 14)
        .attr('height', 14)
        .attr('rx', 3)
        .attr('fill', SUBTYPE_COLORS[subtype]);
      row
        .append('text')
        .attr('x', 20)
        .attr('y', 11)
        .attr('fill', '#8888aa')
        .attr('font-size', '12px')
        .text(subtype);
    });
  }, [chartData, width, height]);

  return (
    <div className="glass-card p-4">
      <svg ref={svgRef} width={width} height={height} />
    </div>
  );
}
