import type { ComponentType, SVGProps } from 'react';

import Document from '@/assets/Document';
import LockIcon from '@/assets/Lock';
import SettingsIcon from '@/assets/Settings';
import ShieldIcon from '@/assets/Shield';
import StarIcon from '@/assets/Star';
import WarningIcon from '@/assets/Warning';

import type { HelpCategoryIconName } from '../helpContent';

interface HelpCategoryIconProps {
  name: HelpCategoryIconName;
  size?: number;
}

const CATEGORY_ICONS: Record<
  HelpCategoryIconName,
  ComponentType<SVGProps<SVGSVGElement>>
> = {
  star: StarIcon,
  report: Document,
  shield: ShieldIcon,
  settings: SettingsIcon,
  lock: LockIcon,
  warning: WarningIcon,
};

export default function HelpCategoryIcon({
  name,
  size = 22,
}: HelpCategoryIconProps) {
  const Icon = CATEGORY_ICONS[name];

  return <Icon width={size} height={size} />;
}
