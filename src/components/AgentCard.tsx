import arrowRightIcon from '../assets/figma/icon-arrow-right.png';
import { Badge } from './ui/Badge';
import { IconButton } from './ui/IconButton';
import { StatChip } from './ui/StatChip';

type AgentCardProps = {
  title: string;
  toolsCount: number;
  testCasesCount: number;
};

export function AgentCard({ title, toolsCount, testCasesCount }: AgentCardProps) {
  return (
    <div className="group flex w-full max-w-sm flex-col rounded-2xl border border-slate-200 border-t-4 border-t-PrimaryBlue bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
        <Badge>Ready</Badge>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <StatChip value={toolsCount} label="Tools" />
        <StatChip value={testCasesCount} label="Test Cases" />
      </div>

      <IconButton className="ml-auto mt-6" aria-label={`Open ${title}`}>
        <img
          alt=""
          src={arrowRightIcon}
          className="h-5 w-5 object-contain invert transition-transform group-hover:translate-x-0.5"
          draggable={false}
        />
      </IconButton>
    </div>
  );
}
