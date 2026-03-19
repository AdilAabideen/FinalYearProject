import { SectionHeader } from '../../../components/layout/SectionHeader';

export function HomePage() {
  return (
    <section aria-label="Home">
      <div className="max-w-xl space-y-6 p-6 gap-4">
        <SectionHeader
          title="Home"
          description="This is a placeholder page. We can wire it up to backend metadata endpoints next."
        />
       
      </div>
    </section>
  );
}
