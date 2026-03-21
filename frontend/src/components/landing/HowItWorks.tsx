const steps = [
  {
    number: "1",
    title: "註冊帳號",
    description: "30 秒完成註冊，免費使用",
  },
  {
    number: "2",
    title: "搜尋股票",
    description: "輸入代號或名稱，即時查看行情",
  },
  {
    number: "3",
    title: "開始分析",
    description: "籌碼、回測、提醒，全方位掌握",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold tracking-tight text-center mb-12">
          三步驟開始
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl mx-auto">
          {steps.map((step) => (
            <div key={step.number} className="text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <span className="text-2xl font-bold text-primary">{step.number}</span>
              </div>
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
