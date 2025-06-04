// You might need to install node-fetch: npm install node-fetch
import fetch from 'node-fetch';

const TAVILY_API_KEY = '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'; // Replace with your actual API key if different
const TAVILY_API_ENDPOINT = 'https://api.tavily.com/search';

async function searchTavily(query, searchDepth = 'basic', maxResults = 5) {
  if (!query) {
    console.error('Error: Search query cannot be empty.');
    return;
  }

  console.log(`Searching Tavily for: "${query}"...`);

  try {
    const response = await fetch(TAVILY_API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${TAVILY_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        api_key: TAVILY_API_KEY, // Some APIs require the key in the body as well
        query: query,
        search_depth: searchDepth, // 'basic' or 'advanced'
        include_answer: false, // Whether to include a short answer summary
        include_raw_content: false, // Whether to include raw content of search results
        max_results: maxResults, // Number of results to return
        // include_domains: [], // Optional: list of domains to focus on
        // exclude_domains: [], // Optional: list of domains to exclude
      }),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Error: API request failed with status ${response.status} - ${response.statusText}`);
      console.error('Error details:', errorBody);
      return null;
    }

    const data = await response.json();
    console.log('Search successful!');
    return data;

  } catch (error) {
    console.error('Error during Tavily search:', error);
    return null;
  }
}

// --- Example Usage ---
async function main() {
  const searchQuery = 'What are the latest advancements in AI?'; // Replace with your desired search query
  const searchResults = await searchTavily(searchQuery, 'basic', 3);

  if (searchResults && searchResults.results) {
    console.log('\nSearch Results:');
    searchResults.results.forEach((result, index) => {
      console.log(`\n${index + 1}. ${result.title}`);
      console.log(`   URL: ${result.url}`);
      console.log(`   Score: ${result.score}`);
      // console.log(`   Content: ${result.content}`); // Content might be long
    });
    if (searchResults.answer) {
        console.log('\nAnswer Summary:', searchResults.answer);
    }
  } else {
    console.log('No results found or an error occurred.');
  }
}

main();
