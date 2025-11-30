// WARNING: Placing the API key directly in client-side code exposes it to the public.
// REPLACE 'YOUR_EXPOSED_GEMINI_API_KEY_HERE' with your actual key.
const API_KEY = 'AIzaSyAWKScV20zljs8ceb7NeXQYed3rDPrk38M'; 
const API_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent';

// --- Ticker Group Definitions ---
const TICKET_GROUPS = {
    'quantum': ['ionq','qbts','rgti','qubt','laes','arqq'],
    'power_management_chips': ['nvts', 'on', 'aosl', 'mpwr', 'powi', 'wolf'],
    'uas_defense_robotics': ['dpro', 'rcat', 'zena', 'onds', 'avav', 'ktos', 'umac', 'spai'],
    'lidar_sensing': ['aeva', 'lazr', 'mvis', 'lidr', 'oust', 'indi', 'arbe', 'cohr'],
    'service_robotics': ['rr', 'serv', 'prct', 'zbra', 'irbt'],
    'autonomous_driving': ['mbly', 'aur', 'tsla', 'xpev', 'kdk'],
    'space_launch_systems': ['rklb', 'fly', 'mnts', 'spce','lunr', 'rdw'],
    'earth_observation': ['pl', 'bksy', 'spir', 'satl'],
    'satellite_communications': ['asts', 'irdm', 'sats', 'vsat'],
    'ev_charging_infrastructure': ['evgo', 'blnk', 'chpt', 'beem', 'adse'],
    'evtol_air_mobility': ['achr', 'joby', 'evex', 'evtl', 'eh'],
    'hydrogen_fuel_cells': ['fcel', 'be', 'plug', 'hyln', 'bw'],
    'cybersecurity': ['ftnt', 'zs', 'crwd','panw'],
    'new_nuclear_energy': ['nne', 'ccj', 'smr', 'bwxt', 'oklo', 'ceg'],
    'batteries_storage_tech': ['qs', 'envx', 'ses', 'mvst', 'ampx', 'sldp'],
    'batteries_storage_sw': ['enph', 'stem', 'flnc', 'eose', 'gwh','kulr'],
    'battery_materials_mining': ['atlx', 'abat', 'alb', 'sqm', 'sgml', 'elvr', 'lac','nb'],
    'Hyperscalers': ['crwv', 'nbis', 'alab', 'cifr', 'apld', 'corz','wulf']
};

// --- Query Definitions ---
// Note: Titles are kept short as they will become table column headers.
const queryActions = [
    { action: 'queryGemini1', title: '1. Overview/News', builder: (ticker) => `What business is USA NYSE/NASDAQ stock ${ticker} into, focusing on business focus areas in two sentences highlighting keywords, latest as of today dated news(not interested in stock price changes as standalone news item) bullted and highlighted dates, any announcement of strategic alternatives in two sentences highligting key phrases. Exclude disclaimer.` },
    { action: 'queryGemini2', title: '2. Institutions Prcnt', builder: (ticker) => `present busines pivots highligting keywords since inception by USA NYSE/NASDAQ stock ${ticker} in bulleted style in less than 100 words, and total percentage of institutional ownership from 13f filings as of today, highlight percentage. Exclude disclaimer.` },
    { action: 'queryGemini3', title: '3. Orders', builder: (ticker) => `As of today, List Recent large orders dated for ${ticker} with value, highlight institutes/organizations/companies. No extra information in list items. Exclude disclaimer.` },
    { action: 'queryGemini4', title: '4. Dilution/Peers', builder: (ticker) => `For USA NYSE/NASDAQ stock ${ticker} what is current debt load, cash position and quarterly burn rate, highlight keywords. What is potential fully diluted share count and total outstanding share count based on stock dilution and warrants from recent forms 8k and 10q SEC filings considering footnotes as of today, highlight key phrases and numbers in millions, present in two short bulleted points. What is the market cap of the company including class A class B etc shares, highlighting the value in millions or billions. List all peer listed company tickers in single sentence. Exclude disclaimer.` },
    { action: 'queryGemini5', title: '5. Short Interest', builder: (ticker) => `what is the total open interest for ${ticker} across all future expiry dates and strike prices in single sentence along with put call ratio and short interest percentage as of today. present in bulleted output. Exclude disclaimer.` },
];

// --- DOM References ---
const startButton = document.getElementById('startButton');
const tickerSelect = document.getElementById('ticker-group-select');
const tickerInput = document.getElementById('tickerInput');
const snapshotUrlInput = document.getElementById('snapshotUrl');
const spinnerElement = document.getElementById('loading-spinner');
const currentActionElement = document.getElementById('current-action');

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    // Dropdown Change Handler: Populates the input box with tickers from TICKET_GROUPS
    tickerSelect.addEventListener('change', function() {
        const selectedGroupKey = this.value;
        const tickerList = TICKET_GROUPS[selectedGroupKey];
        
        if (tickerList) {
            // Join the array elements with a comma and space
            tickerInput.value = tickerList.join(', ');
        } else {
            tickerInput.value = '';
        }
    });

    // Full Analysis Button
    startButton.addEventListener('click', runFullAnalysis);
    

});

// --- Core API Fetch Function ---

/**
 * Executes a single query against the Gemini API.
 */
async function sendQueryDirectlyToGemini(query) {
 
    try {
        const response = await fetch(`${API_ENDPOINT}?key=${API_KEY}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: query }] }],
                tools: [{ googleSearch: {} }] 
                
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error ${response.status}: ${errorData.error?.message || response.statusText}`);
        }
        
        const data = await response.json();
        const resultText = data.candidates?.[0]?.content?.parts?.[0]?.text;
        
        return { result: resultText || 'No result found.' };

    } catch (error) {
        console.error('CRITICAL API Request Failed:', error);
        return { error: `API Request Failed: ${error.message}` };
    }
}

// --- Main Analysis & Display Logic ---

/**
 * Main function to run all 5 queries for all tickers and collect data.
 */
async function runFullAnalysis() {
    const rawTickerInput = tickerInput.value.trim();
    // Normalize and filter tickers
    const tickerList = rawTickerInput
        .toUpperCase()
        .split(',')
        .map(t => t.trim())
        .filter(t => t.length > 0);
        
    const imageUrl = snapshotUrlInput.value.trim();
    
    if (tickerList.length === 0) {
        alert('Please enter at least one ticker symbol.');
        return;
    }
    
    // Array to store ALL results for the final table
    const allResultsData = {}; 

    // UI Setup
    spinnerElement.style.display = 'block';
    startButton.disabled = true;
    
    const clearButton = document.getElementById('clear-results-button');
    if (clearButton) clearButton.disabled = true;


    for (const ticker of tickerList) {
        // Initialize object for the current ticker row
        const tickerData = {};

        for (const { action, title, builder } of queryActions) {
            currentActionElement.textContent = `Running ${title} for ${ticker}...`;
            
            const query = builder(ticker);
            const response = await sendQueryDirectlyToGemini(query);
            
            if (response.error) {
                tickerData[action] = `<span style="color:red;">Error: ${response.error}</span>`;
            } else {
                // Apply basic text cleaning and formatting for table cell display
                let cleanText = marked.parse(response.result);
                cleanText = cleanText.replace(/#/g, ''); 
                cleanText = cleanText.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>'); 
                cleanText = cleanText.replace(/\*(.*?)\*/g, '<i>$1</i>');     
                cleanText = cleanText.replace(/^- /gm, '• ');               
                cleanText = cleanText.replace(/\n/g, '<br>');               
                
                tickerData[action] = cleanText;
            }
        }
        allResultsData[ticker] = tickerData;
    }

    // UI Cleanup
    currentActionElement.textContent = 'Complete! Generating Table...';
    spinnerElement.style.display = 'none';
    startButton.disabled = false;
    
    
    // Display results in a new table window
    displayResultsInTable(allResultsData);
}

function displayResultsInTable(resultsDict) {
    const tickers = Object.keys(resultsDict);

    if (tickers.length === 0) {
        alertMessage('No data to display.', 'danger');
        return;
    }
    let tableHTML = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stock Analysis Results Table</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f9; }
                h1 { color: #333; }
                p { color: #666; font-size: 0.9em; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); table-layout: fixed; }
                th, td { 
                    padding: 12px 15px; 
                    border: 1px solid #ddd; 
                    text-align: left; 
                    vertical-align: top; 
                    font-size: 14px; 
                    word-wrap: break-word; 
                }
                th { background-color: #007bff; color: white; font-weight: bold; position: sticky; top: 0; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                tr:hover { background-color: #f1f1f1; }
                td:first-child { font-weight: bold; width: 80px; } 
                td:nth-child(2) { width: 100px; }
            </style>
        </head>
        <body>
            <h1>Full Analysis Results (${new Date().toLocaleDateString()})</h1>
            <p>Note: Results are direct API responses with basic formatting applied.</p>
            <table>
                <thead><tr>`;

    
    tickers.forEach(ticker => {
        tableHTML += `<th>${ticker}</th>`;
    });
    
    tableHTML += '</tr></thead><tbody>';

    const queryTitles = queryActions.map(qa => qa.action);
    // Iterate over rows (Queries)
    queryTitles.forEach(title => {
        tableHTML += '<tr>';
        
        
        // Remaining Cells (Ticker Results)
        tickers.forEach(ticker => {
            const resultData = resultsDict[ticker][title] || '[N/A: Data Missing]';
            
            let cellContent;
            let errorStyle = '';
            
            if (resultData.includes('Error:')) {
                // Error handling (inline style for quick identification)
                cellContent = `<span style="color:red; font-weight:bold;">${resultData}</span>`;
                errorStyle = 'style="background-color: #301010;"';
            } else if (typeof marked !== 'undefined') {
                // Use marked.parse for Markdown rendering (marked.min.js must be loaded in HTML)
                // Note: The 'marked' library is assumed to be globally available from the HTML file.
                cellContent = marked.parse(resultData, { sanitize: true });
            } else {
                // Fallback rendering
                cellContent = resultData.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
            }

            tableHTML += `<td class="analysis-result-cell" ${errorStyle}>${cellContent}</td>`;
        });

        tableHTML += '</tr>';
    });
    tableHTML += `</tbody>
          </table>
        </body>
        </html>
    `;


    const newWindow = window.open('', '_blank');
    if (newWindow) {
        newWindow.document.write(tableHTML);
        newWindow.document.close();
    } else {
        alert('Could not open new window. Please check your browser pop-up blocker settings.');
    }
}

