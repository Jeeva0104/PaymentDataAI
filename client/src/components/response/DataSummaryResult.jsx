import React from 'react';
import { 
  convertMarkdownToTable, 
  sanitizeHtml, 
  parseInsights, 
  formatProcessingTime, 
  formatTokenCount 
} from '../../utils/markdownUtils';

const DataSummaryResult = ({ data }) => {
  if (!data) {
    return (
      <div className="text-gray-500 text-sm">
        No response data available
      </div>
    );
  }

  const {
    success,
    html_summary,
    key_insights,
    markdown_data,
    summary_time_ms,
    prompt_tokens,
    completion_tokens,
    data_points_analyzed,
    error,
    summary
  } = data;

  const getStatusIcon = () => {
    return success ? (
      <svg className="w-5 h-5 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ) : (
      <svg className="w-5 h-5 text-error-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    );
  };

  const getHeaderStyle = () => {
    return success 
      ? 'bg-success-50 border-success-200 text-success-800'
      : 'bg-error-50 border-error-200 text-error-800';
  };

  const formatTimestamp = () => {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const buildProcessingStats = () => {
    const stats = [];
    
    if (summary_time_ms) {
      stats.push(`⚡ ${formatProcessingTime(summary_time_ms)}`);
    }
    
    if (data_points_analyzed) {
      stats.push(`📊 ${data_points_analyzed} records`);
    }
    
    if (prompt_tokens) {
      stats.push(`📝 ${formatTokenCount(prompt_tokens)} prompt tokens`);
    }
    
    if (completion_tokens) {
      stats.push(`🤖 ${formatTokenCount(completion_tokens)} completion tokens`);
    }
    
    return stats;
  };

  return (
    <div className="data-summary-response border border-gray-200 rounded-lg overflow-hidden">
      {/* Response Header */}
      <div className={`px-4 py-3 border-b ${getHeaderStyle()} flex items-center justify-between`}>
        <div className="flex items-center space-x-2">
          {getStatusIcon()}
          <span className="font-semibold">
            {success ? 'Query Result' : 'Query Error'}
          </span>
        </div>
        <div className="text-sm opacity-75">
          {formatTimestamp()}
        </div>
      </div>

      {/* Response Body */}
      <div className="p-4 bg-white">
        {success ? (
          <div className="space-y-4">
            {/* HTML Summary Section */}
            {html_summary && (
              <div className="html-summary border-l-4 border-primary-400 bg-primary-50 p-4 rounded-r-lg">
                <div 
                  className="prose prose-sm max-w-none text-gray-800"
                  dangerouslySetInnerHTML={{ 
                    __html: sanitizeHtml(html_summary) 
                  }}
                />
              </div>
            )}

            {/* Key Insights Section */}
            {key_insights && key_insights.length > 0 && (
              <div className="key-insights">
                <div className="flex items-center space-x-2 mb-3">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <h3 className="font-semibold text-gray-900">Key Insights</h3>
                </div>
                <div className="bg-primary-50 rounded-lg p-4">
                  <ul className="space-y-2">
                    {parseInsights(key_insights).map((insight) => (
                      <li key={insight.id} className="flex items-start space-x-2">
                        <div className="w-1.5 h-1.5 bg-primary-600 rounded-full mt-2 flex-shrink-0" />
                        <span className="text-gray-700">{insight.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Data Table Section */}
            {markdown_data && markdown_data !== "No data table available for non-analytics queries" && (
              <div className="markdown-data">
                <div className="flex items-center space-x-2 mb-3">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  <h3 className="font-semibold text-gray-900">Data Table</h3>
                </div>
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <div 
                    className="max-h-96 overflow-y-auto"
                    dangerouslySetInnerHTML={{ 
                      __html: convertMarkdownToTable(markdown_data) 
                    }}
                  />
                </div>
              </div>
            )}

            {/* Fallback to plain summary if no HTML summary */}
            {!html_summary && summary && (
              <div className="html-summary border-l-4 border-gray-400 bg-gray-50 p-4 rounded-r-lg">
                <p className="text-gray-800 whitespace-pre-wrap">{summary}</p>
              </div>
            )}
          </div>
        ) : (
          /* Error Display */
          <div className="error-message border-l-4 border-error-400 bg-error-50 p-4 rounded-r-lg">
            <div className="flex items-center space-x-2 mb-2">
              <svg className="w-5 h-5 text-error-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-semibold text-error-800">Error</span>
            </div>
            <p className="text-error-700">
              {error || summary || 'An unknown error occurred while processing your request.'}
            </p>
          </div>
        )}

        {/* Processing Statistics */}
        {buildProcessingStats().length > 0 && (
          <div className="processing-stats mt-4 pt-3 border-t border-gray-200">
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
              {buildProcessingStats().map((stat, index) => (
                <span key={index} className="flex items-center space-x-1">
                  <span>{stat}</span>
                  {index < buildProcessingStats().length - 1 && (
                    <span className="text-gray-300 ml-3">|</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DataSummaryResult;
