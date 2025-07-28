let params = new URLSearchParams(document.location.search);
let results_container = document.querySelector(".serp__web");
let search_Bar = document.querySelector(".serp__query");
let base_query = "";

const highlightMatches = (text, query) => {
  // Split query into individual words
  const queryWords = query.toLowerCase().split(/\s+/);
  let highlighted = text;
  
  // Highlight each word that matches
  queryWords.forEach(word => {
    const regex = new RegExp(`(${word})`, 'gi');
    highlighted = highlighted.replace(regex, '<span class="serp__match">$1</span>');
  });
  
  return highlighted;
};

const Display = (results) => {
  Object.keys(results).forEach((key) => {
    let new_result = document.createElement("div");
    results_container.appendChild(new_result);
    new_result.outerHTML = `<div class="serp__result">
                <a href="${key}" target="_blank">
                  <div class="serp__title">${results[key].title}</div>
                  <div class="serp__url">${key}</div>
                </a>
                <span class="serp__description">
                  ${highlightMatches(results[key]["description"], base_query)}
                </span>
              </div>`;
  });
};

const emptyDisplay = () => {
  let new_result = document.createElement("div");
  results_container.appendChild(new_result);
  new_result.outerHTML = `<div class="serp__no-results">
            <p>
              <strong>No search results were found for &raquo;${base_query}&laquo;</strong>
            </p>
            <p>Suggestions:</p>
            <ul>
              <li>Check that all words are spelled correctly.</li>
              <li>Try different search terms.</li>
              <li>Try a more general search.</li>
              <li>Try fewer search terms.</li>
            </ul>
          </div>`;
}

search_Bar.value = params.get("query"); // Update search bar with cleaned query

const set_Base_word = (word) => {
  base_query = word.replaceAll(`"`,'');
  console.log(`base word is: ${base_query}`);
}

// Get query from URL and clean it
const initialQuery = params.get("query") || "";
search_Bar.value = initialQuery;

// First fetch NLP processed query
fetch(`/nlp?query=${encodeURIComponent(initialQuery)}`, {
  method: "POST",
}).then(x => {
  x.text().then(x => {
    set_Base_word(x);
    // Then fetch search results with the processed query
    fetch(`/search?query=${encodeURIComponent(base_query)}`, {
      method: "POST",
    })
    .then((x) => {
      if(x.status == 200) x.json().then((x) => Display(JSON.parse(x)));
      else if (x.status == 418) emptyDisplay();
      else window.location.pathname = '/';
    })
    .catch(error => {
      console.error('Search fetch error:', error);
      emptyDisplay();
    });
  });
})
.catch(error => {
  console.error('NLP fetch error:', error);
  // Fallback to original query if NLP fails
  set_Base_word(initialQuery);
  fetch(`/search?query=${encodeURIComponent(base_query)}`, {
    method: "POST",
  })
  .then((x) => {
    if(x.status == 200) x.json().then((x) => Display(JSON.parse(x)));
    else if (x.status == 418) emptyDisplay();
    else window.location.pathname = '/';
  });
});