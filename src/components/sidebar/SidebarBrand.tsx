import logoPng from '../../assets/figma/logo.png';

export function SidebarBrand() {
  return (
    <div className="flex items-center gap-3 px-4 py-5">
      <img alt="" src={logoPng} className="h-8 w-10 rounded-md" draggable={false} />
      <div className="leading-tight">
        <div className="text-lg font-semibold text-slate-900">IntelliTriage</div>
        <div className="text-xs text-slate-500">Emergency triage workspace</div>
      </div>
    </div>
  );
}

