import React from 'react';

const WelcomeSection = () => {
  return (
    <div className="text-center py-12 px-4 max-w-4xl mx-auto animate-fade-in-up">
      <div className="mb-8">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 text-balance">
          Welcome to Payment Data AI
        </h1>
        <p className="text-lg md:text-xl text-gray-600 leading-relaxed max-w-3xl mx-auto text-balance">
          Ask questions about your payments, refunds, and analytics. Get instant insights without writing 
          any SQL queries.
        </p>
      </div>
      
      <div className="mb-12">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">
          Try these examples
        </h2>
        <p className="text-gray-600">
          Click on any question below to get started
        </p>
      </div>
    </div>
  );
};

export default WelcomeSection;
