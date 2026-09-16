import { HealthPanel } from "@/components/health-panel";

const workflowSteps = [
  {
    number: "01",
    title: "Create a setup",
    copy: "Define the model, tools, and instructions for your agent.",
  },
  {
    number: "02",
    title: "Run experiments",
    copy: "Compare variants against a repeatable evaluation set.",
  },
  {
    number: "03",
    title: "Inspect results",
    copy: "Trace behavior, latency, and quality from one workspace.",
  },
] as const;

export default function Home() {
  return (
    <div className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Developer workspace</p>
          <h1>
            Build agents with
            <br />a tighter feedback loop.
          </h1>
          <p className="hero-copy">
            Configure, test, and understand agent behavior without losing the thread between
            iterations.
          </p>
        </div>
        <div className="hero-art" aria-hidden="true">
          <span className="orbit orbit-one" />
          <span className="orbit orbit-two" />
          <span className="core">A</span>
        </div>
      </section>

      <HealthPanel />

      <section className="workflow" aria-labelledby="workflow-title">
        <div className="section-heading">
          <p className="eyebrow">Workflow</p>
          <h2 id="workflow-title">From prompt to evidence</h2>
        </div>
        <div className="workflow-grid">
          {workflowSteps.map((step) => (
            <article className="workflow-card" key={step.number}>
              <span>{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.copy}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
