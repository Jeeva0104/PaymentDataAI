// Utility functions for markdown processing and HTML conversion

/**
 * Capitalizes the first letter of a word
 * @param {string} word - The word to capitalize
 * @returns {string} The capitalized word
 */
export const capitalizeWord = (word) => {
  if (!word || typeof word !== 'string') return '';
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
};

/**
 * Converts snake_case text to Title Case
 * @param {string} text - The snake_case text to convert
 * @returns {string} The converted Title Case text
 */
export const convertSnakeCaseToTitle = (text) => {
  if (!text || typeof text !== 'string') return text;
  
  // Check if text contains underscores and looks like snake_case
  if (!text.includes('_')) return text;
  
  // Handle edge cases: remove leading/trailing underscores and handle multiple consecutive underscores
  const cleaned = text.replace(/^_+|_+$/g, '').replace(/_+/g, '_');
  
  // Split by underscores, capitalize each word, and join with spaces
  return cleaned
    .split('_')
    .filter(word => word.length > 0)
    .map(word => capitalizeWord(word))
    .join(' ');
};

export const escapeHtml = (text) => {
  if (typeof text !== 'string') return '';
  
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

export const convertMarkdownToTable = (markdown) => {
  if (!markdown || typeof markdown !== 'string') {
    return '<p class="text-gray-500 text-sm">No table data available</p>';
  }
  
  try {
    const lines = markdown.trim().split('\n');
    if (lines.length < 2) {
      return `<pre class="bg-gray-100 p-3 rounded text-sm overflow-x-auto">${escapeHtml(markdown)}</pre>`;
    }
    
    // Extract headers (first line) and convert snake_case to Title Case
    const headerLine = lines[0];
    const headers = headerLine.split('|')
      .map(h => h.trim())
      .filter(h => h)
      .map(h => convertSnakeCaseToTitle(h));
    
    // Skip separator line (second line with ---)
    const dataLines = lines.slice(2);
    
    if (headers.length === 0) {
      return `<pre class="bg-gray-100 p-3 rounded text-sm overflow-x-auto">${escapeHtml(markdown)}</pre>`;
    }
    
    let html = '<div class="overflow-x-auto"><table class="response-table">';
    
    // Create header
    html += '<thead><tr>';
    headers.forEach(header => {
      html += `<th class="bg-gray-50 text-left font-semibold text-gray-900 px-4 py-3 border-b border-gray-200">${escapeHtml(header)}</th>`;
    });
    html += '</tr></thead>';
    
    // Create body
    html += '<tbody>';
    dataLines.forEach((line, index) => {
      if (line.trim()) {
        const cells = line.split('|').map(c => c.trim()).filter(c => c);
        if (cells.length > 0) {
          const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';
          html += `<tr class="${rowClass} hover:bg-gray-100">`;
          
          // Ensure we have the right number of cells
          for (let i = 0; i < headers.length; i++) {
            const cellValue = cells[i] || '';
            html += `<td class="px-4 py-3 border-b border-gray-200 text-gray-700">${escapeHtml(cellValue)}</td>`;
          }
          html += '</tr>';
        }
      }
    });
    html += '</tbody></table></div>';
    
    return html;
    
  } catch (e) {
    console.error('Error converting markdown to table:', e);
    return `<pre class="bg-gray-100 p-3 rounded text-sm overflow-x-auto">${escapeHtml(markdown)}</pre>`;
  }
};

export const formatProcessingTime = (timeMs) => {
  if (typeof timeMs !== 'number') return '';
  
  if (timeMs < 1000) {
    return `${timeMs.toFixed(1)}ms`;
  } else {
    return `${(timeMs / 1000).toFixed(2)}s`;
  }
};

export const formatTokenCount = (tokens) => {
  if (typeof tokens !== 'number') return '';
  
  if (tokens < 1000) {
    return tokens.toString();
  } else if (tokens < 1000000) {
    return `${(tokens / 1000).toFixed(1)}k`;
  } else {
    return `${(tokens / 1000000).toFixed(1)}M`;
  }
};

export const sanitizeHtml = (html) => {
  if (!html || typeof html !== 'string') return '';
  
  // Create a temporary div to parse HTML
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = html;
  
  // Remove potentially dangerous elements and attributes
  const dangerousElements = ['script', 'iframe', 'object', 'embed', 'link', 'style'];
  const dangerousAttributes = ['onload', 'onerror', 'onclick', 'onmouseover', 'onfocus', 'onblur'];
  
  dangerousElements.forEach(tag => {
    const elements = tempDiv.querySelectorAll(tag);
    elements.forEach(el => el.remove());
  });
  
  // Remove dangerous attributes from all elements
  const allElements = tempDiv.querySelectorAll('*');
  allElements.forEach(el => {
    dangerousAttributes.forEach(attr => {
      if (el.hasAttribute(attr)) {
        el.removeAttribute(attr);
      }
    });
    
    // Remove javascript: links
    if (el.hasAttribute('href') && el.getAttribute('href').startsWith('javascript:')) {
      el.removeAttribute('href');
    }
    
    if (el.hasAttribute('src') && el.getAttribute('src').startsWith('javascript:')) {
      el.removeAttribute('src');
    }
  });
  
  return tempDiv.innerHTML;
};

export const parseInsights = (insights) => {
  if (!Array.isArray(insights)) return [];
  
  return insights.map((insight, index) => ({
    id: index,
    text: typeof insight === 'string' ? insight : String(insight)
  }));
};
