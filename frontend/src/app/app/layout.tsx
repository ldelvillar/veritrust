import Sidebar from '@/components/layout/Sidebar';

export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-screen flex-col bg-white md:flex-row">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col bg-[linear-gradient(180deg,#f4f3fb,#eeedf8_360px)]">
        {children}
      </main>
    </div>
  );
}
