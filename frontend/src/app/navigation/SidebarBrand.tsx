import logoPng from '../../assets/figma/logo.png';

type SidebarBrandProps = {
  collapsed?: boolean;
};

// Renders the sidebar brand.
export function SidebarBrand({ collapsed = false }: SidebarBrandProps) {
  return (
    <div className={collapsed ? 'flex justify-center px-1 py-2' : 'flex items-center gap-3 px-1 py-2'}>
      <img alt="" src={logoPng} className="h-8 w-10 rounded-md" draggable={false} />
      {!collapsed ? (
        <div className="leading-tight">
          <div className="text-lg font-semibold text-slate-900">IntelliTriage</div>
          <div className="text-xs text-slate-500">Emergency triage workspace</div>
        </div>
      ) : null}
    </div>
  );
}
