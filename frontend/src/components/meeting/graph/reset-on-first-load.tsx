import { select } from 'd3-selection';
import { type ZoomBehavior, zoomIdentity } from 'd3-zoom';
import { useEffect, useRef } from 'react';

interface ResetOnFirstLoadProps {
  svgRef: React.RefObject<SVGSVGElement | null>;
  zoomRef: React.RefObject<ZoomBehavior<SVGSVGElement, unknown> | null>;
}

export const ResetOnFirstLoad = ({ svgRef, zoomRef }: ResetOnFirstLoadProps) => {
  const armed = useRef(false);
  useEffect(() => {
    if (armed.current) return;
    armed.current = true;
    if (svgRef.current && zoomRef.current)
      select(svgRef.current).call(zoomRef.current.transform, zoomIdentity);
  }, [svgRef, zoomRef]);
  return null;
};
