import { Link as RouterLink, type LinkProps } from "react-router";
import { Link } from "@cloudflare/kumo/components/link";
import type { AnchorHTMLAttributes } from "react";

type Props = (LinkProps | (AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; to?: never })) & { inline?: boolean };
export function SiteLink({ inline = false, ...props }: Props) {
  const variant = inline ? "inline" : "plain";
  if ("href" in props && props.href) return <Link {...props as AnchorHTMLAttributes<HTMLAnchorElement>} variant={variant} />;
  const { to, state, replace, preventScrollReset, ...rest } = props as LinkProps;
  return <Link {...rest} variant={variant} render={<RouterLink to={to} state={state} replace={replace} preventScrollReset={preventScrollReset} />} />;
}
