export function pageMeta(title: string, description: string, path: string) {
  return [
    { title: title },
    { name: "description", content: description },
    { name: "robots", content: "index, follow" },
    { property: "og:title", content: title },
    { property: "og:description", content: description },
    {
      property: "og:type",
      content: path.startsWith("/articles/") ? "article" : "website",
    },
    { property: "og:url", content: `https://weihuasongguo.com${path}` },
    {
      tagName: "link",
      rel: "canonical",
      href: `https://weihuasongguo.com${path}`,
    },
  ];
}
