import { SectionLabel } from '@/components/ui/section-label';

const PeoplePage = () => {
  return (
    <div style={{ padding: '24px 32px', maxWidth: 900, position: 'relative' }}>
      <SectionLabel>PEOPLE</SectionLabel>
      <div style={{ marginTop: 12, color: 'var(--color-ink-tertiary)', fontSize: 14 }}>
        No people yet.
      </div>
    </div>
  );
};

export default PeoplePage;
