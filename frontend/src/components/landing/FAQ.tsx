"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "Stock Tracer 是免費的嗎？",
    answer: "是的，目前所有功能完全免費。",
  },
  {
    question: "資料多久更新一次？",
    answer: "每個交易日收盤後自動更新（約 14:00-18:00）。",
  },
  {
    question: "支援哪些股票？",
    answer: "涵蓋台灣上市（TWSE）及上櫃（TPEX）所有股票。",
  },
  {
    question: "回測系統支援哪些策略？",
    answer: "內建均線、法人、大戶持股、融資融券四種策略，可自訂參數。",
  },
];

export default function FAQ() {
  return (
    <section id="faq" className="py-20">
      <div className="container mx-auto px-4 max-w-2xl">
        <h2 className="text-3xl font-bold tracking-tight text-center mb-12">
          常見問題
        </h2>
        <Accordion>
          {faqs.map((faq, i) => (
            <AccordionItem key={i} value={`item-${i}`}>
              <AccordionTrigger className="text-left">
                {faq.question}
              </AccordionTrigger>
              <AccordionContent>{faq.answer}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
