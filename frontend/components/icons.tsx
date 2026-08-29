import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const baseProps = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function SparkIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="m12 3 1.15 3.85L17 8l-3.85 1.15L12 13l-1.15-3.85L7 8l3.85-1.15L12 3Z"/><path d="m18 14 .65 2.35L21 17l-2.35.65L18 20l-.65-2.35L15 17l2.35-.65L18 14Z"/><path d="m5 13 .55 1.95L7.5 15.5l-1.95.55L5 18l-.55-1.95-1.95-.55 1.95-.55L5 13Z"/></svg>;
}

export function PlusIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M12 5v14M5 12h14"/></svg>;
}

export function SendIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="m21 3-7.4 18-3.8-7.8L2 9.4 21 3Z"/><path d="M9.8 13.2 15 8"/></svg>;
}

export function StopIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><rect x="7" y="7" width="10" height="10" rx="1"/></svg>;
}

export function UserIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><circle cx="12" cy="8" r="4"/><path d="M4.8 21a7.2 7.2 0 0 1 14.4 0"/></svg>;
}

export function MenuIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M4 7h16M4 12h16M4 17h16"/></svg>;
}

export function CloseIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="m6 6 12 12M18 6 6 18"/></svg>;
}

export function MoreIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><circle cx="5" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1" fill="currentColor" stroke="none"/></svg>;
}
