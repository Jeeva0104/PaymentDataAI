import React from 'react';

const ExamplesSection = ({ onExampleClick }) => {
  const examples = [
    {
      id: 1,
      text: "Highest payment amount processed till date",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      category: "Payment Records"
    },
    {
      id: 2,
      text: "What is success rate",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      category: "Success Metrics"
    },
    {
      id: 3,
      text: "What is error rate",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      category: "Error Metrics"
    },
    {
      id: 4,
      text: "List payment failed using currency USD",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      ),
      category: "Failed Payments"
    }
  ];

  const handleExampleClick = (example) => {
    if (onExampleClick) {
      onExampleClick(example.text);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {examples.map((example, index) => (
          <div
            key={example.id}
            className="card card-hover cursor-pointer p-6 transition-all duration-200 hover:scale-[1.02] animate-fade-in-up"
            style={{ animationDelay: `${index * 0.1}s` }}
            onClick={() => handleExampleClick(example)}
          >
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-primary-100 text-primary-600 rounded-lg flex items-center justify-center">
                  {example.icon}
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="mb-2">
                  <span className="inline-block px-2 py-1 text-xs font-medium text-primary-600 bg-primary-50 rounded-full">
                    {example.category}
                  </span>
                </div>
                <p className="text-gray-800 font-medium leading-relaxed">
                  {example.text}
                </p>
              </div>
              <div className="flex-shrink-0">
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Additional helpful text */}
      <div className="mt-8 text-center">
        <p className="text-gray-500 text-sm">
          You can also ask custom questions about payments, refunds, transaction volumes, success rates, and more
        </p>
      </div>
    </div>
  );
};

export default ExamplesSection;
