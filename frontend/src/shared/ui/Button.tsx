import type { ButtonHTMLAttributes } from "react";
import { Link, type LinkProps } from "react-router-dom";

type Variant = "primary" | "ghost" | "lime" | "danger";
type Size = "md" | "sm" | "icon";

const kelas = (v: Variant, s: Size, blok?: boolean, extra?: string) =>
  ["btn", `btn--${v}`, s === "sm" ? "btn--sm" : s === "icon" ? "btn--icon btn--sm" : "", blok ? "btn--block" : "", extra ?? ""].filter(Boolean).join(" ");

export function Button({
  variant = "primary",
  size = "md",
  blok,
  className,
  type = "button",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; blok?: boolean }) {
  return <button type={type} className={kelas(variant, size, blok, className)} {...rest} />;
}

export function LinkButton({ variant = "ghost", size = "md", className, ...rest }: LinkProps & { variant?: Variant; size?: Size; className?: string }) {
  return <Link className={kelas(variant, size, false, className)} {...rest} />;
}
