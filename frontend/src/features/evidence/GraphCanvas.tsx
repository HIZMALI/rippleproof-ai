import { useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
import type {
  EvidenceNode,
  EvidencePath,
  EvidenceRelationship,
} from "../../api/contracts";

export default function GraphCanvas({
  path,
  selectedId,
  onSelect,
  fitVersion,
  orderStatus,
}: {
  path: EvidencePath;
  selectedId?: string;
  fitVersion: number;
  orderStatus?: string;
  onSelect: (fact: EvidenceNode | EvidenceRelationship) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const graph = useRef<Core | null>(null);
  const callback = useRef(onSelect);
  useEffect(() => {
    callback.current = onSelect;
  }, [onSelect]);
  useEffect(() => {
    if (!container.current) return;
    const facts = new Map(
      [...path.nodes, ...path.relationships].map((f) => [f.id, f]),
    );
    const horizontal = [
      { x: 70, y: 105 },
      { x: 240, y: 105 },
      { x: 410, y: 105 },
      { x: 580, y: 105 },
    ];
    const vertical = path.nodes.map((_, index) => ({
      x: 150,
      y: 60 + index * 105,
    }));
    const positions = window.matchMedia("(max-width: 767px)").matches
      ? vertical
      : horizontal;
    const cy = cytoscape({
      container: container.current,
      elements: [
        ...path.nodes.map((node, index) => ({
          data: {
            id: node.id,
            label: `${node.id}\n${node.label}`,
            kind: node.label,
            status: node.label === "Order" ? (orderStatus ?? "dependency") : "",
          },
          position: positions[index] ?? { x: index * 170, y: 105 },
        })),
        ...path.relationships.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source_id,
            target: edge.target_id,
            label: edge.type,
            kind: edge.type,
          },
        })),
      ],
      layout: { name: "preset", fit: true, padding: 35 },
      minZoom: 0.35,
      maxZoom: 2.5,
      wheelSensitivity: 0.2,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#182936",
            "border-color": "#79a6c7",
            "border-width": 1.5,
            width: 78,
            height: 64,
            shape: "round-rectangle",
            label: "data(label)",
            color: "#edf2f6",
            "font-family": "system-ui, sans-serif",
            "font-size": 13,
            "font-weight": 500,
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "90px",
            "line-height": 1.6,
          },
        },
        {
          selector: 'node[kind = "Supplier"]',
          style: { "border-color": "#d6a16b", "background-color": "#33291f" },
        },
        {
          selector: 'node[kind = "Product"]',
          style: { "border-color": "#91a0b0", "background-color": "#222b35" },
        },
        {
          selector: 'node[status = "on_time"]',
          style: { "border-color": "#71b29a", "background-color": "#1b302a" },
        },
        {
          selector: 'node[status = "at_risk"]',
          style: { "border-color": "#d6a16b", "background-color": "#33291f" },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#71879a",
            "target-arrow-color": "#71879a",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.8,
            "curve-style": "bezier",
            label: "data(label)",
            color: "#a5b4c1",
            "font-family": "system-ui, sans-serif",
            "font-size": 10,
            "text-rotation": "none",
            "text-margin-y": -12,
            "text-background-color": "#10171f",
            "text-background-opacity": 1,
            "text-background-padding": "4px",
          },
        },
        {
          selector: 'edge[kind = "SUPPLIES"]',
          style: { "line-color": "#79a6c7", "target-arrow-color": "#79a6c7" },
        },
        {
          selector: 'edge[kind = "CONTAINS"]',
          style: { "line-color": "#71b29a", "target-arrow-color": "#71b29a" },
        },
        {
          selector: ".inspected",
          style: {
            "border-width": 3,
            "border-color": "#edf2f6",
            "line-color": "#edf2f6",
            "target-arrow-color": "#edf2f6",
          },
        },
        { selector: "edge.inspected", style: { width: 2.5 } },
      ],
    });
    graph.current = cy;
    cy.on("tap", "node, edge", (event) => {
      const fact = facts.get(event.target.id());
      if (fact) callback.current(fact);
    });
    const observer = new ResizeObserver(() => {
      const coordinates = window.matchMedia("(max-width: 767px)").matches
        ? vertical
        : horizontal;
      cy.nodes().forEach((node, index) => {
        const point = coordinates[index];
        if (point) node.position(point);
      });
      cy.resize();
      cy.fit(undefined, 35);
    });
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      cy.destroy();
      graph.current = null;
    };
  }, [path, orderStatus]);
  useEffect(() => {
    graph.current?.fit(undefined, 35);
  }, [fitVersion]);
  useEffect(() => {
    graph.current?.elements().removeClass("inspected");
    if (selectedId)
      graph.current?.getElementById(selectedId).addClass("inspected");
  }, [selectedId, path]);
  return (
    <div
      className="graph-canvas"
      ref={container}
      role="img"
      aria-label={`Graph evidence: ${path.human_readable}. Use the source reference buttons below for keyboard access.`}
    />
  );
}
