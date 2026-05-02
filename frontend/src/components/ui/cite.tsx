interface CiteProps {
  time: string;
  onClick?: (time: string) => void;
}

export const Cite = ({ time, onClick }: CiteProps) => (
  <button
    type="button"
    className="cite-chip"
    onClick={(e) => {
      e.stopPropagation();
      onClick?.(time);
    }}
  >
    <span className="cite-arrow">→</span>
    {time}
  </button>
);
