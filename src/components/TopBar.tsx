type TopBarProps = {
  title: string;
};

export function TopBar({ title }: TopBarProps) {
  return (
    <header className="flex h-16 items-center border-b border-neutral-200 bg-neutral-100 px-6">
      <h1 className="text-2xl font-medium">{title}</h1>
    </header>
  );
}
