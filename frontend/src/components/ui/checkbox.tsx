import { cn } from '@/lib/utils';
import { Icon } from './icon';

interface CheckboxProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  id?: string;
}

export const Checkbox = ({ checked, onChange, id }: CheckboxProps) => (
  <button
    type="button"
    className={cn('checkbox', checked && 'checked')}
    onClick={() => onChange(!checked)}
    aria-pressed={checked}
    id={id}
  >
    {checked && <Icon name="check" size={11} stroke={2.5} />}
  </button>
);
