import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  CornerDownLeft,
  Download,
  List,
  type LucideIcon,
  Maximize,
  MessageSquare,
  Mic,
  MoreHorizontal,
  Network,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Search,
  Send,
  Settings as SettingsIcon,
  Sparkles,
  Square,
  Upload,
  Users,
  Video,
  Wand2,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';

const REGISTRY = {
  search: Search,
  x: X,
  plus: Plus,
  'arrow-up-right': ArrowUpRight,
  'arrow-down': ArrowDown,
  'arrow-right': ArrowRight,
  check: Check,
  'chevron-down': ChevronDown,
  'chevron-right': ChevronRight,
  more: MoreHorizontal,
  mic: Mic,
  square: Square,
  'zoom-in': ZoomIn,
  'zoom-out': ZoomOut,
  fit: Maximize,
  reset: RotateCcw,
  'corner-down-left': CornerDownLeft,
  send: Send,
  upload: Upload,
  download: Download,
  copy: Copy,
  sparkles: Sparkles,
  list: List,
  graph: Network,
  people: Users,
  message: MessageSquare,
  meeting: Video,
  settings: SettingsIcon,
  play: Play,
  pause: Pause,
  tidy: Wand2,
} as const satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof REGISTRY;

interface IconProps {
  name: IconName;
  size?: number;
  stroke?: number;
  color?: string;
  className?: string;
}

export const Icon = ({ name, size = 14, stroke = 1.5, color, className }: IconProps) => {
  const Cmp = REGISTRY[name];
  return <Cmp size={size} strokeWidth={stroke} color={color} className={className} />;
};
