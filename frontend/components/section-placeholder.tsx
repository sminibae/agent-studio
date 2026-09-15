interface SectionPlaceholderProps {
  readonly eyebrow: string;
  readonly title: string;
  readonly description: string;
}

export function SectionPlaceholder({ eyebrow, title, description }: SectionPlaceholderProps) {
  return (
    <div className="page section-page">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className="empty-state">
        <strong>This workspace is ready for its first feature.</strong>
        <span>The project skeleton intentionally leaves product data empty.</span>
      </div>
    </div>
  );
}
