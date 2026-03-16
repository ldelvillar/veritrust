import Form from '@/components/Form';
import Hero from '@/components/Hero';

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <Hero />
      <Form />
    </div>
  );
}
