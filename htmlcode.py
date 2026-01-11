import base64
import os
import html # Import the html module for escaping
import re
import pandas as pd
import json # Import json for embedding dictionary as JSON string

#def build_html_content(ticker_map, sector_desc,all_industries_results):
# Convert ticker_map to a JSON string for embedding
json_ticker_map = json.dumps(ticker_map).replace('`', '\\`') # Escape backticks for template literal
# Define new JavaScript parsing functions
js_parsing_functions = f"""
        // Embed the raw processed dilution ranges string
        const rawProcessedDilutionRanges = {json.dumps(processed_output_string_from_github)};

        // Lookup object for custom dilution ranges
        let customDilutionRangesLookup = {{}};

        // Function to parse a single range string like "88.0/93.0"
        function parseSlashRange(rangeStr) {{
            if (!rangeStr || typeof rangeStr !== 'string') return {{ min: NaN, max: NaN }};
            const parts = rangeStr.split('/');
            if (parts.length === 2) {{
                const num1 = parseFloat(parts[0]);
                const num2 = parseFloat(parts[1]);
                if (!isNaN(num1) && !isNaN(num2)) {{
                    return {{ min: Math.min(num1, num2), max: Math.max(num1, num2) }};
                }}
            }} else if (parts.length === 1) {{
                const num = parseFloat(parts[0]);
                if (!isNaN(num)) {{
                    return {{ min: num, max: num }};
                }}
            }}
            return {{ min: NaN, max: NaN }};
        }}

        // Function to parse the rawProcessedDilutionRanges string into customDilutionRangesLookup
        function parseCustomDilutionRanges() {{
            if (!rawProcessedDilutionRanges) {{
                console.warn("rawProcessedDilutionRanges is empty. Skipping custom dilution range parsing.");
                return;
            }}
            const tickerRanges = rawProcessedDilutionRanges.split(';');
            tickerRanges.forEach(entry => {{
                const parts = entry.split(':');
                if (parts.length === 2) {{
                    const ticker = parts[0].toUpperCase();
                    const ranges = parts[1].split(','); // Expecting "floor/ceiling"
                    if (ranges.length === 2) {{
                        const floorRangeStr = ranges[0];
                        const ceilingRangeStr = ranges[1];
                        customDilutionRangesLookup[ticker] = {{
                            floor: parseSlashRange(floorRangeStr),
                            ceiling: parseSlashRange(ceilingRangeStr)
                        }};
                    }}
                }}
            }});
            console.log("Custom dilution ranges parsed successfully:", Object.keys(customDilutionRangesLookup).length, "tickers.");
        }}
"""


html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>NASDAQ S&P Growth Stoks AI generated fundamentals technicals and Latest updates</title>
    <script src="https://cdn.jsdelivr.net/npm/marked@4.0.10/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
    <script>
        // Register the datalabels plugin globally, immediately after loading it
        Chart.register(ChartDataLabels);
        // Embed Python variables as JavaScript variables
        const csvExportUrl = '{csv_export_url}';
        const tickerMap = JSON.parse(`{json_ticker_map}`); // Use backticks for template literal
        const fundamentalsData = JSON.parse(`{json_fundamentals_data}`); // Embedded fundamentals data
        const optionsRangesMap = JSON.parse(`{options_ranges_map}`); // Parse it into an array of objects
        {js_parsing_functions}
        // Create a global lookup for fundamentals data
        const fundamentalsLookup = {{}};
        fundamentalsData.forEach(item => {{
            fundamentalsLookup[item.ticker.toUpperCase()] = item;
        }});

        // Create a global lookup for options data
        const optionsLookup = {{}};
        optionsRangesMap.forEach(item => {{
            optionsLookup[item.ticker.toUpperCase()] = item;
        }});

        // Dynamically fetched dilution data
        let tickerDilutionMap = {{}};
        const GITHUB_RAW_URL_BASE = "https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/";
        const DILUTION_DATA_FILENAME = "all_industries_detailed_dilution_results.json";
        const DATA_URL = GITHUB_RAW_URL_BASE + DILUTION_DATA_FILENAME;

        async function fetchDilutionData() {{
            try {{
                const response = await fetch(DATA_URL);
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                const rawData = await response.json();
                // Assuming rawData is already in the {{ "TICKER": "dilution_string" }} format
                // Convert all keys to uppercase for consistent lookup
                tickerDilutionMap = Object.fromEntries(
                    Object.entries(rawData).map(([key, value]) => [key.toUpperCase(), value])
                );
                console.log("Dilution data fetched successfully:", Object.keys(tickerDilutionMap).length, "tickers.");
            }} catch (error) {{
                console.error('Error fetching dilution data:', error);
            }}
        }}
        // Function to parse price ranges like "$185.00 – $205.00" or single values "$93.00"
        function parsePriceRange(rangeStr) {{
            if (!rangeStr || typeof rangeStr !== 'string') return {{ min: NaN, max: NaN }};

            // Clean the string by removing dollar signs and commas first
            const cleanStr = rangeStr.replace(/[$,]/g, '').trim();

            // Attempt to match a range pattern: e.g., "X.XX - Y.YY" or "X.YY – Y.YY"
            const rangeMatch = cleanStr.match(/(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)/);

            if (rangeMatch && rangeMatch.length >= 3) {{ // group 0 is full match, 1 is first number, 2 is second number
                const num1 = parseFloat(rangeMatch[1]);
                const num2 = parseFloat(rangeMatch[2]); // Corrected from rangeMatch[3]
                if (!isNaN(num1) && !isNaN(num2)) {{
                    return {{ min: Math.min(num1, num2), max: Math.max(num1, num2) }};
                }}
            }}

            // If no range pattern is found, try to extract a single number
            const singleNumberMatch = cleanStr.match(/(\d+(?:\.\d+)?)/); // Use capturing group here
            if (singleNumberMatch && singleNumberMatch.length >= 2) {{ // group 0 is full match, 1 is the number
                const num = parseFloat(singleNumberMatch[1]); // Corrected to singleNumberMatch[1]
                if (!isNaN(num)) {{
                    return {{ min: num, max: num }};
                }}
            }}
            return {{ min: NaN, max: NaN }};
        }}

        // Helper to convert hex to RGB
        function hexToRgb(hex) {{
            const bigint = parseInt(hex.slice(1), 16);
            const r = (bigint >> 16) & 255;
            const g = (bigint >> 8) & 255;
            const b = bigint & 255;
            return [r, g, b];
        }}

        // Linear interpolation for colors
        function lerpColor(color1, color2, ratio) {{
            const r = Math.round(color1[0] + (color2[0] - color1[0]) * ratio);
            const g = Math.round(color1[1] + (color2[1] - color1[1]) * ratio);
            const b = Math.round(color1[2] + (color2[2] - color1[2]) * ratio);
            return `rgb(${{r}}, ${{g}}, ${{b}})`;
        }}

        // Function to get color at a specific percentage on the gradient
        function getColorAtGradientPosition(position) {{
            const green = hexToRgb('#4CAF50'); // 0%
            const yellow = hexToRgb('#FFEB3B'); // 50%
            const red = hexToRgb('#F44336'); // 100%
            if (position <= 50) {{
                const ratio = position / 50; // Normalize to 0-1 range for green to yellow segment
                return lerpColor(green, yellow, ratio);
            }} else {{
                const ratio = (position - 50) / 50; // Normalize to 0-1 range for yellow to red segment
                return lerpColor(yellow, red, ratio);
            }}
        }}



        // JavaScript function for conditional coloring of 'price%' column
        function colorPricePercent(val) {{
            try {{
                val = parseFloat(val);
            }} catch (e) {{
                return ''; // No coloring for non-numeric values
            }}

            if (isNaN(val)) return '';

            if (val <= -10) {{
                return 'background-color: #8B0000; color: white;'; // Dark Red
            }} else if (val >= 10) {{
                return 'background-color: #006400; color: white;'; // Dark Green
            }} else if (val < 0) {{ // Between -10 and 0, scale from white to dark red
                let ratio = Math.abs(val) / 10.0;
                let r = parseInt(255 - (255 - 139) * ratio);
                let g = parseInt(255 - (255 - 0) * ratio);
                let b = parseInt(255 - (255 - 0) * ratio);
                return `background-color: rgb(${{r}}, ${{g}}, ${{b}});`;
            }} else if (val > 0) {{ // Between 0 and 10, scale from white to dark green
                let ratio = val / 10.0;
                let r = parseInt(255 - (255 - 0) * ratio);
                let g = parseInt(255 - (255 - 100) * ratio);
                let b = parseInt(255 - (255 - 0) * ratio);
                return `background-color: rgb(${{r}}, ${{g}}, ${{b}});`;
            }} else {{ // val == 0
                return 'background-color: white;';
            }}
        }}
        // Functions for inline dilution window
        function toggleDilutionInline(element, ticker, event, currentPrice) {{
            event.stopPropagation(); // Prevent default button action or parent click
            const popup = document.getElementById('dilution-inline-popup');
            const backdrop = document.getElementById('dilution-backdrop');

            if (popup.classList.contains('active') && popup.dataset.currentTicker === ticker) {{
                // If it's already active and for the same ticker, close it
                closeDilutionInline();
                return;
            }}

            // Check if dilution data is loaded before proceeding
            if (Object.keys(tickerDilutionMap).length === 0) {{
                console.warn("Dilution data not yet loaded. Please wait and try again.");
                // Optionally show a message to the user
                // alert("Dilution data is still loading. Please try again in a moment.");
                return;
            }}

            if (tickerDilutionMap[ticker]) {{
                // Set content
                popup.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0;">Dilution Details for ${{ticker}}(Price: $${{currentPrice}})</h3>
                        <button onclick="closeDilutionInline()" style="background: none; border: none; font-size: 1.5em; cursor: pointer;">&times;</button>
                    </div>
                    <div class="popup-content-scroll">${{marked.parse(tickerDilutionMap[ticker])}}</div>
                `;
                popup.dataset.currentTicker = ticker; // Store current ticker
                popup.classList.add('active');
                backdrop.classList.add('active');
            }} else {{
                console.log(`No dilution data found for ticker: ${{ticker}}`);
                // Optionally show a message to the user
                // alert(`No detailed dilution data available for ${{ticker}}.`);
            }}
        }}

        function closeDilutionInline() {{
            document.getElementById('dilution-inline-popup').classList.remove('active');
            document.getElementById('dilution-backdrop').classList.remove('active');
            document.getElementById('dilution-inline-popup').dataset.currentTicker = ''; // Clear current ticker
        }}


        // Generic toggle function for sections
        function toggleSection(contentId, headerElement) {{
            const content = document.getElementById(contentId);
            const icon = headerElement.querySelector('.toggle-icon');
            if (content.classList.contains('hidden')) {{
                content.classList.remove('hidden');
                icon.innerHTML = '&uarr;'; // Up arrow
            }} else {{
                content.classList.add('hidden');
                icon.innerHTML = '&darr;'; // Down arrow
            }}
        }}

        // Helper to parse CSV data into an array of objects
        function parseCsv(csvText) {{
            const lines = csvText.split('\\n').map(line => line.trim()).filter(line => line !== '');
            if (lines.length === 0) return [];

            const headers = lines[0].split(',').map(h => h.trim());
            const data = [];

            for (let i = 1; i < lines.length; i++) {{
                if (lines[i].trim() === '') continue; // Skip empty lines

                const currentLine = lines[i].split(',');
                let row = {{}};
                for (let j = 0; j < headers.length; j++) {{
                    row[headers[j]] = (currentLine[j] || '').trim();
                }}
                data.push(row);
            }}
            return data;
        }}
        // Function to load actual image sources for lazy loading
        function loadChartsImages() {{
            console.log('loadChartsImages function called.');
            document.querySelectorAll('.chart-image').forEach(img => {{
                console.log('Processing image:', img.alt);
                console.log('Current img.src:', img.src);
                console.log('Current img.dataset.src:', img.dataset.src);
                //if (!img.src) {{ // Only load if not already loaded
                    img.src = img.dataset.src;
                    //console.log('Image src set to:', img.src);
                //}}
            }});
        }}
        // Function to render charts from provided data
        async function renderCharts(allCsvData) {{
            try {{
                const chartingData = allCsvData;
                console.log('Charting data received:', chartingData);


                for (const industryKey in tickerMap) {{
                    const industryTickers = tickerMap[industryKey].map(t => t.toUpperCase()); // Ensure ticker case matches
                    const filteredChartingData = chartingData.filter(row => industryTickers.includes(row['Ticker'].toUpperCase()));

                    const chartCanvas = document.getElementById(`chart_${{industryKey}}`);
                    if (!chartCanvas) {{
                        console.warn(`Chart canvas not found for industry: ${{industryKey}}`);
                        continue;
                    }}

                    if (filteredChartingData.length > 0) {{
                        const labels = filteredChartingData.map(row => row['Ticker']);
                        const debtMcapRatios = filteredChartingData.map(row => {{
                            const mcap = parseFloat(row['mcap']);
                            const debt_m = parseFloat(row['Debt_M']); // Use Debt_M from sheets_df
                            return mcap > 0 ? (debt_m / mcap * 100).toFixed(2) : 0;
                        }});
                        const cashMcapRatios = filteredChartingData.map(row => {{
                            const mcap = parseFloat(row['mcap']);
                            const cash_m = parseFloat(row['Cash_M']); // Use Cash_M from sheets_df
                            return mcap > 0 ? (cash_m / mcap * 100).toFixed(2) : 0;
                        }});
                        const siPercents = filteredChartingData.map(row => parseFloat(row['SI%']) || 0);
                        const institutesPercents = filteredChartingData.map(row => parseFloat(row['institutes%']) || 0);

                        // Calculate Burn/Market Cap (%)
                        const burnMcapRatios = filteredChartingData.map(row => {{
                            const mcap = parseFloat(row['mcap']);
                            const tickerUpper = row['Ticker'].toUpperCase();
                            const fundData = fundamentalsLookup[tickerUpper];
                            if (fundData && mcap > 0) {{
                                const burn = parseFloat(fundData['burn']);
                                return (burn / mcap * 100).toFixed(2);
                            }}
                            return 0; // Default to 0 if data is missing or mcap is zero
                        }});
                        new Chart(chartCanvas, {{
                            type: 'bar',
                            data: {{
                                labels: labels,
                                datasets: [
                                    {{
                                        label: 'Debt%',
                                        data: debtMcapRatios,
                                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                                        borderColor: 'rgba(255, 99, 132, 1)',
                                        borderWidth: 1
                                    }},
                                    {{
                                        label: 'Cash%',
                                        data: cashMcapRatios,
                                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                                        borderColor: 'rgba(54, 162, 235, 1)',
                                        borderWidth: 1
                                    }},
                                    {{
                                        label: 'SI%',
                                        data: siPercents,
                                        backgroundColor: 'rgba(255, 206, 86, 0.6)',
                                        borderColor: 'rgba(255, 206, 86, 1)',
                                        borderWidth: 1
                                    }},
                                    {{
                                        label: 'tutes%',
                                        data: institutesPercents,
                                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                                        borderColor: 'rgba(75, 192, 192, 1)',
                                        borderWidth: 1
                                    }},
                                    {{
                                        label: 'Burn%',
                                        data: burnMcapRatios,
                                        backgroundColor: 'rgba(153, 102, 255, 0.6)', // A new color
                                        borderColor: 'rgba(153, 102, 255, 1)',
                                        borderWidth: 1
                                    }}
                                    ]
                            }},
                            options: {{
                                responsive: true,
                                animation: false,
                                events: [],
                                aspectRatio: 4,
                                maintainAspectRatio: true,
                                scales: {{
                                    x: {{
                                        stacked: false,
                                        title: {{
                                            display: false,
                                            text: 'Ticker'
                                        }}
                                    }},
                                    y: {{
                                        beginAtZero: true,
                                        title: {{
                                            display: false,
                                            text: 'Percentage (%)'
                                        }}
                                    }}
                                }},
                                plugins: {{
                                      datalabels: {{
                                        anchor: 'end',
                                        align: 'top',
                                        formatter: (value) => {{
                                            return parseFloat(value).toFixed(1);
                                        }},
                                        color: '#333',
                                        font: {{
                                            weight: 'bold',
                                            size: 10
                                        }}
                                    }},
                                    title: {{
                                        display: false,
                                        text: `Peer Comparison for ${{industryKey.replace('_', ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}}`
                                    }},
                                    legend: {{
                                        display: true,
                                        position: 'top'
                                    }}
                                }}
                            }}
                        }});

                    }} else {{
                        chartCanvas.parentElement.innerHTML = '<p>No charting data available for this industry.</p>';
                    }}
                }}
            }} catch (error) {{
                console.error('Error rendering charts:', error); // Changed log message
                for (const industryKey in tickerMap) {{
                    const chartCanvas = document.getElementById(`chart_${{industryKey}}`);
                    if (chartCanvas) {{
                        chartCanvas.parentElement.innerHTML = `<p>Error loading charting data: ${{error.message}}</p>`;
                    }}
                }}
            }}
        }}
        // Function to fetch CSV data and render tables (fundamentals)
        async function fetchAndRenderTables() {{
            try {{
                const response = await fetch(csvExportUrl);
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                const csvText = await response.text();
                const lines = csvText.split('\\n').map(line => line.endsWith('\\r') ? line.slice(0, -1) : line);
                console.log('Parsed CSV lines:', lines);

                if (lines.length < 2 || lines.every(line => line.trim() === '')) {{
                    console.warn('CSV data is empty or contains only headers.');
                    for (const industryKey in tickerMap) {{
                        const placeholderDiv = document.getElementById(`fundamentals-table-${{industryKey}}`);
                        if (placeholderDiv) {{
                            placeholderDiv.innerHTML = '<p>No CSV data loaded or only headers found.</p>';
                        }}
                    }}
                    return;
                }}

                const headers = lines[0].split(',').map(h => h.trim());
                const data = [];

                for (let i = 1; i < lines.length; i++) {{
                    if (lines[i].trim() === '') continue; // Skip empty lines

                    const currentLine = lines[i].split(',');
                    let row = {{}};
                    for (let j = 0; j < headers.length; j++) {{
                        row[headers[j]] = (currentLine[j] || '').trim();
                    }}
                    data.push(row);
                }}

                // Call renderCharts with the parsed data
                renderCharts(data);

                // Columns to display (must match Python list in sheets_df)
                const columnsToDisplay = [
                    'Ticker', 'price%', 'Price', 'mcap',
                    'Debt_M', 'Cash_M', 'QRevenue_M', 'QPL_M', 'OrderBook_M'
                ];

                for (const industryKey in tickerMap) {{
                    const industryTickers = tickerMap[industryKey];
                    const industryData = data.filter(row => industryTickers.includes(row['Ticker'].toLowerCase()));

                    industryData.sort((a, b) => {{
                        const mcapA = parseFloat(a['mcap']) || 0;
                        const mcapB = parseFloat(b['mcap']) || 0;
                        return mcapB - mcapA; // Decreasing order
                    }});

                    const placeholderDiv = document.getElementById(`fundamentals-table-${{industryKey}}`);
                    if (!placeholderDiv) {{
                        console.warn(`Placeholder div not found for industry: ${{industryKey}}`);
                        continue;
                    }}

                    if (industryData.length > 0) {{
                        let tableHtml = '<table class="\dataframe\"><thead><tr>';
                        const actualHeaders = headers.filter(h => columnsToDisplay.includes(h) && industryData[0].hasOwnProperty(h));

                        actualHeaders.forEach(header => {{
                            tableHtml += `<th>${{header}}</th>`;
                        }});
                        tableHtml += '</tr></thead><tbody>';

                        industryData.forEach(row => {{
                            tableHtml += '<tr>';
                            actualHeaders.forEach(header => {{
                                let cellValue = row[header] || '';
                                // Try to override with fundamentalsData if available and applicable
                                const tickerUpper = row['Ticker'].toUpperCase();
                                const fundData = fundamentalsLookup[tickerUpper];

                                if (fundData) {{
                                    if (header === 'Debt_M') {{
                                        cellValue = fundData['debt'] !== undefined ? fundData['debt'] : cellValue;
                                    }} else if (header === 'Cash_M') {{
                                        cellValue = fundData['cash'] !== undefined ? fundData['cash'] : cellValue;
                                    }} else if (header === 'QRevenue_M') {{
                                        cellValue = fundData['rev'] !== undefined ? fundData['rev'] : cellValue;
                                    }} else if (header === 'QPL_M') {{ // Assuming QPL_M from sheets_df maps to 'burn' from fundamentalsData
                                        cellValue = fundData['burn'] !== undefined ? fundData['burn'] : cellValue;
                                    }}
                                    // OrderBook_M is not in fundamentalsData, so it remains row[header]
                                }}

                                let style = '';
                                //if (header === 'price%') {{
                                //    style = colorPricePercent(cellValue);
                                //}}
                                if (!isNaN(parseFloat(cellValue)) && isFinite(cellValue)) {{
                                    cellValue = parseFloat(cellValue).toString();
                                }}
                                let displayValue = cellValue;
                                if (header === 'Ticker') {{
                                    const ticker = cellValue.toUpperCase();
                                    const price = row['Price'] || 'N/A'; // Get the price
                                    if (tickerDilutionMap[ticker]) {{
                                        displayValue = `
                                            <button class="ticker-button" onclick="toggleDilutionInline(this, '${{ticker}}', event, '${{price}}')">
                                                ${{cellValue}}
                                            </button>
                                        `;
                                    }}
                                }}
                                tableHtml += `<td style="${{style}}">${{displayValue}}</td>`;
                            }});
                            tableHtml += '</tr>';
                            const currentPrice = parseFloat(row['Price']) || NaN;
                            let ceilingRange = {{min: NaN, max: NaN}};
                            let floorRange = {{min: NaN, max: NaN}};

                            const tickerUpper = row['Ticker'].toUpperCase();
                            if (customDilutionRangesLookup[tickerUpper]) {{
                                const customRanges = customDilutionRangesLookup[tickerUpper];
                                ceilingRange = customRanges.ceiling;
                                floorRange = customRanges.floor;
                            }}
                            const optionsData = optionsLookup[tickerUpper];
                            let overallMin = currentPrice;
                            let overallMax = currentPrice;

                            if (!isNaN(ceilingRange.min)) overallMax = Math.max(overallMax, ceilingRange.min);
                            if (!isNaN(ceilingRange.max)) overallMax = Math.max(overallMax, ceilingRange.max);
                            if (!isNaN(floorRange.min)) overallMin = Math.min(overallMin, floorRange.min);
                            if (!isNaN(floorRange.max)) overallMin = Math.min(overallMin, floorRange.max);

                            let putwall = NaN;
                            let callwall = NaN;
                            let gammaflip = NaN;
                            let maxpain = NaN;

                            if (optionsData) {{
                                putwall = parseFloat(optionsData['putwall']);
                                callwall = parseFloat(optionsData['callwall']);
                                gammaflip = parseFloat(optionsData['gammaflip']);
                                maxpain = parseFloat(optionsData['maxpain']);

                                if (!isNaN(putwall)) overallMin = Math.min(overallMin, putwall);
                                if (!isNaN(callwall)) overallMax = Math.max(overallMax, callwall);
                            }}

                            let lineHtml = ''; // For dilution line
                            let optionsLineHtml = ''; // For options line

                            if (!isNaN(overallMin) && !isNaN(overallMax) && overallMin < overallMax) {{
                                const range = overallMax - overallMin;
                                // Helper to clamp positions between 0 and 100%
                                const clampPosition = (value) => Math.max(0, Math.min(100, (value - overallMin) / range * 100));
                                const pricePosition = clampPosition(currentPrice);
                                rowBackgroundColor = getColorAtGradientPosition(pricePosition);
                                // Calculate positions for floor/ceiling range arrows
                                const floorMinPos = clampPosition(floorRange.min);
                                const floorMaxPos = clampPosition(floorRange.max);
                                const ceilMinPos = clampPosition(ceilingRange.min);
                                const ceilMaxPos = clampPosition(ceilingRange.max);

                                lineHtml = `
                                    <tr class="price-line-row">
                                        <td colspan="${{actualHeaders.length}}" style="padding: 0px;">
                                            <div style="position: relative; width: 100%; height: 4px; border-radius: 5px; background-color: #ddd;"> <!-- Base grey line -->
                                                ${{
                                                    !isNaN(floorRange.min) && !isNaN(ceilingRange.max) && floorRange.min <= ceilingRange.max ?
                                                    `<div style="position: absolute; top:2px; left: ${{clampPosition(floorRange.min)}}%; width: ${{Math.max(0, clampPosition(ceilingRange.max) - clampPosition(floorRange.min))}}%; height: 100%; background-color: ${{rowBackgroundColor}}; border-radius: 5px;"></div>`
                                                    : ''
                                                }}
                                                <!--div style="position: absolute; left: ${{pricePosition}}%; top: -3px; width: 10px; height: 10px; background-color: #333; border-radius: 50%; transform: translateX(-50%); box-shadow: 0 0 5px rgba(0,0,0,0.5);" title="${{currentPrice.toFixed(2)}}"></div-->
                                                <span style="position: absolute; left: ${{pricePosition}}%; top: -12px; transform: translateX(-50%); font-weight: bold; font-size: 1.5em; color: black;">$&nbsp;</span>

                                                ${{!isNaN(floorRange.min) ? `<span class="arrow-right-green" style="left: ${{floorMinPos}}%;" title="${{floorRange.min.toFixed(2)}}"></span>` : ''}}
                                                ${{!isNaN(floorRange.max) ? `<span class="arrow-right-green" style="left: ${{floorMaxPos}}%;" title="${{floorRange.max.toFixed(2)}}"></span>` : ''}}
                                                ${{!isNaN(ceilingRange.min) ? `<span class="arrow-left-red" style="left: ${{ceilMinPos}}%;" title="${{ceilingRange.min.toFixed(2)}}"></span>` : ''}}
                                                ${{!isNaN(ceilingRange.max) ? `<span class="arrow-left-red" style="left: ${{ceilMaxPos}}%;" title="${{ceilingRange.max.toFixed(2)}}"></span>` : ''}}
                                            </div>
                                        </td>
                                    </tr>
                                `;
                            }}


                            if (optionsData) {{
                                // Check if values are valid and a meaningful range exists
                                if (!isNaN(putwall) && !isNaN(callwall) && !isNaN(gammaflip) && !isNaN(maxpain) && putwall < callwall) {{
                                    const range = overallMax - overallMin;
                                    const clampPosition = (value) => Math.max(0, Math.min(100, (value - overallMin) / range * 100));
                                    const optionsRange = callwall - putwall;
                                    const optionsClampPosition = (value) => Math.max(0, Math.min(100, (value - putwall) / optionsRange * 100));

                                    const optionsPricePosition = optionsClampPosition(currentPrice);
                                    const optionsRowBacPkgroundColor = getColorAtGradientPosition(optionsPricePosition);
                                    const putwallPos = clampPosition(putwall);
                                    const callwallPos = clampPosition(callwall);
                                    const gammaflipPos = clampPosition(gammaflip);
                                    const maxpainPos = clampPosition(maxpain);

                                    // Calculate background color for options line
                                    const pricePosition = clampPosition(currentPrice);

                                    optionsLineHtml = `
                                        <tr class="options-price-line-row">
                                            <td colspan="${{actualHeaders.length}}" style="padding: 0px;">
                                                <div style="position: relative; width: 100%; height: 4px; border-radius: 5px; background-color: #ddd;"> <!-- Base grey line -->
                                                    ${{
                                                        !isNaN(putwall) && !isNaN(callwall) && putwall <= callwall ?
                                                        `<div style="position: absolute; top:-2px; left: ${{clampPosition(putwall)}}%; width: ${{Math.max(0, clampPosition(callwall) - clampPosition(putwall))}}%; height: 100%; background-color: ${{optionsRowBacPkgroundColor}}; border-radius: 5px;"></div>`
                                                        : ''
                                                    }}
                                                    <!-- Put Wall Text -->
                                                    <span style="position: absolute; left: ${{putwallPos}}%; top: -12px; width: auto; height: auto; padding: 0 3px; background-color: green; color: white; border-radius: 3px; transform: translateX(-50%); font-weight: bold; font-size: 0.8em;" title="$${{putwall.toFixed(2)}}">W</span>
                                                    <!-- Call Wall Text -->
                                                    <span style="position: absolute; left: ${{callwallPos}}%; top: -12px; width: auto; height: auto; padding: 0 3px; background-color: red; color: white; border-radius: 3px; transform: translateX(-50%); font-weight: bold; font-size: 0.8em;" title="$${{callwall.toFixed(2)}}">W</span>

                                                    <!-- Current Price Dot (black) -->
                                                    <!--div style="position: absolute; left: ${{pricePosition}}%; top: -3px; width: 10px; height: 10px; background-color: black; border-radius: 50%; transform: translateX(-50%); box-shadow: 0 0 5px rgba(0,0,0,0.5);title=""></div-->
                                                   <!-- Gamma Flip Character (blue) -->
                                                    <span style="position: absolute; left: ${{gammaflipPos}}%; top: -12px; width: auto; height: auto; padding: 0 3px; background-color: blue; color: white; border-radius: 3px; transform: translateX(-50%); font-weight: bold; font-size: 0.8em;" title="$${{gammaflip.toFixed(2)}}">F</span>
                                                    <!-- Max Pain Character (green) -->
                                                    <span style="position: absolute; left: ${{maxpainPos}}%; top: -12px; width: auto; height: auto; padding: 0 3px; background-color: green; color: white; border-radius: 3px; transform: translateX(-50%); font-weight: bold; font-size: 0.8em;" title="$${{maxpain.toFixed(2)}}">P</span>
                                                </div>
                                            </td>
                                        </tr>
                                    `;
                                }}
                            }}
                            tableHtml += optionsLineHtml;
                            tableHtml += lineHtml;
                        }});
                        tableHtml += '</tbody></table>';
                        placeholderDiv.innerHTML = tableHtml;
                    }} else {{
                        placeholderDiv.innerHTML = '<p>No fundamentals data available for this industry.</p>';
                    }}
                }}
            }} catch (error) {{
                console.error('Error fetching or processing CSV:', error);
                for (const industryKey in tickerMap) {{
                    const placeholderDiv = document.getElementById(`fundamentals-table-${{industryKey}}`);
                    if (placeholderDiv) {{
                        placeholderDiv.innerHTML = `<p>Error loading fundamentals data: ${{error.message}}</p>`;
                    }}
                }}
            }}
        }}


    </script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }}
        h1 {{ color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }}
        h2 {{ color: #004085; margin-top: 25px; }}
        h3 {{ color: #002d6b; margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background-color: #f4f4f4; box-shadow: none; border: none; }} /* Modified table styling */
        th, td {{ border: none; padding: 8px; text-align: left; }} /* Modified table cell styling */
        th {{ display: none; }} /* Hide table headers */
        td {{ color: #f4f4f4; }} /* Make text color same as page background */
        .news-item {{ background-color: #e9f7ef; border-left: 5px solid #28a745; margin-bottom: 10px; padding: 10px; border-radius: 4px; }} /* Added news item styling */
        .news-date {{ font-weight: bold; color: #28a745; }} /* Added news date styling */
        .ticker-header {{ background-color: #d1ecf1; padding: 8px; margin-top: 15px; margin-bottom: 5px; border-radius: 4px; border-left: 5px solid #17a2b8; }} /* Added ticker header styling */
        /* Style for markdown content */
        .markdown-output {{
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            background-color: #f9f9f9;
            margin-top: 15px;
        }}
        .markdown-output h1, .markdown-output h2, .markdown-output h3, .markdown-output h4, .markdown-output h5, .markdown-output h6 {{
            border-bottom: 1px solid #eee;
            padding-bottom: 0.3em;
            margin-top: 1em;
            margin-bottom: 0.5em;
            line-height: 1.25;
        }}
        .markdown-output ul, .markdown-output ol {{
            padding-left: 2em;
        }}
        .markdown-output blockquote {{
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
            padding: 0 1em;
            margin-left: 0;
        }}
        .markdown-output pre {{
            background-color: #f6f8fa;
            border-radius: 3px;
            padding: 1em;
            overflow: auto;
        }}
        .markdown-output code {{
            background-color: rgba(27,31,35,.05);
            border-radius: 3px;
            padding: 0.2em 0.4em;
            font-family: SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace;
        }}
        .statement {{
            /* Treat each statement as a block to force a new line */
            display: block;
            /* Optional: Add some spacing between lines */
            margin: 6px 0;
            /* Inherit the small/italic formatting from the original input */
            font-style: italic;
            font-size: small;
        }}
        .scroll-to-top-button {{
            float: right;
            margin-left: 10px;
            text-decoration: none;
            font-size: 1.5em;
            color: #0056b3;
        }}
        .hidden {{ display: none; }}

        /* New CSS for inline dilution popup */
        .dilution-inline-popup {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: #fff;
            border: 1px solid #ccc;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            padding: 20px;
            z-index: 1001; /* Higher than backdrop */
            max-width: 80%;
            max-height: 80%;
            overflow: hidden; /* Manage content scroll separately */
            border-radius: 8px;
            display: none; /* Hidden by default */
            flex-direction: column; /* To manage header and scrollable content */
        }}
        .dilution-inline-popup.active {{
            display: flex; /* Show when active */
        }}
        .dilution-backdrop {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5); /* Semi-transparent black overlay */
            z-index: 1000; /* Behind popup */
            display: none; /* Hidden by default */
        }}
        .dilution-backdrop.active {{
            display: block; /* Show when active */
        }}
        .popup-content-scroll {{
            flex-grow: 1; /* Allow content to take available space */
            overflow-y: auto; /* Enable vertical scrolling for content */
            padding-right: 10px; /* Space for scrollbar */
        }}
        .ticker-button {{
            background: none;
            border: none;
            padding: 0;
            margin: 0;
            font: inherit;
            cursor: pointer;
            text-decoration: underline;
            color: #0056b3; /* Or your preferred link color */
            display: inline-block; /* To allow padding/margins if needed */
        }}
        .ticker-button:hover {{
            color: #003366;
            text-decoration: none;
        }}

        .toggle-header {{ cursor: pointer; }}
        .toggle-icon {{ margin-left: 10px; }}

        /* CSS for arrowheads */
        .arrow-right-green,
        .arrow-left-red {{
            position: absolute;
            top: -2px; /* Adjust to align with the line */
            width: 0; /* No width for the base of the arrow */
            height: 0; /* No height for the base of the arrow */
            border-top: 6px solid transparent;
            border-bottom: 6px solid transparent;
            transform: translateX(-50%); /* Center the arrow horizontally */
            z-index: 2; /* Ensure arrows are above the colored line */
        }}

        .arrow-right-green {{
            border-left: 8px solid green; /* Right-pointing arrow */
        }}

        .arrow-left-red {{
            border-right: 8px solid red; /* Left-pointing arrow */
        }}
    </style>
</head>
<body id="top">
    <div id="dilution-backdrop" class="dilution-backdrop"></div>
    <div id="dilution-inline-popup" class="dilution-inline-popup"></div>
    <h1>NASDAQ S&P Growth Stoks AI generated fundamentals technicals and Latest updates</h1>
    <div id="industry-index-placeholder"></div>
'''

# Ensure output_dir exists as it was created in cell 265e7129
output_dir = 'html_output'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- Generate Clickable Index (from cell 0aa3ba89) ---
navigation_html = '<h2>Industry Index</h2><nav><ul>\n'
index_counter = 1 # Initialize counter for industry index
for key, tickervalues in ticker_map.items():
    formatted_industry_name = key.replace('_', ' ').title()
    tickers_str = ', '.join(tickervalues)
    navigation_html += f'<li><a href="#{key}">{index_counter}. {formatted_industry_name} ({tickers_str})</a></li>\n'
    index_counter += 1
navigation_html += '</ul></nav><hr/>\n'

# The h2 is clickable to toggle the content below it.
govt_news_section_html = '''
<h2 class="toggle-header" onclick="toggleSection('govt-news-content', this)">
    Government and Prominent Investor News <span class="toggle-icon">&darr;</span>
</h2>

<div id="govt-news-content" class="hidden">
'''

if all_orgs_news_results:
    escaped_govt_news = html.escape(all_orgs_news_results)
    # The markdown-raw-content class should be on the div that contains the actual markdown text
    govt_news_section_html += f'<div class="markdown-raw-content govt-news-section">{escaped_govt_news}</div>\n'
else:
    govt_news_section_html += '<div class="govt-news-section"><p>No government and prominent investor news available.</p></div>\n'
govt_news_section_html += '</div>\n' # Close govt-news-content div




# Inject the government news section and then the navigation HTML into the html_content
# The placeholder is replaced first by the govt news section, and then the original placeholder content is added back.
html_content = html_content.replace('<div id="industry-index-placeholder"></div>', govt_news_section_html + '<div id="industry-index-placeholder"></div>')

# Inject the navigation HTML into the html_content at the placeholder
html_content = html_content.replace('<div id="industry-index-placeholder"></div>', navigation_html)


# Add filter checkboxes
html_content += '''
<div style="margin-top: 20px; margin-bottom: 20px;">
    <label><input type="checkbox" id="toggleNews" checked> News</label>
    <label><input type="checkbox" id="toggleTables" checked> Fundamentals</label>
    <label><input type="checkbox" id="toggleCharts"> Charts</label>
    <!-- <label><input type="checkbox" id="toggleNotes" checked> Notes</label> -->
</div>
'''

# Iterate through each entry in the all_industries_news_results list to build the HTML report.
# (from cell 0aa3ba89)
industry_counter = 1 # Initialize counter
for results_entry in all_industries_results:
    industry_key = results_entry['Industry']
    news_data = results_entry['Results']

    # 3a. Add an <h2> heading to html_content for the industry with an ID for linking.
    formatted_industry_name = industry_key.replace('_', ' ').title()
    html_content += f'<div class="industry-section" id="{industry_key}"><h2>{industry_counter}. {formatted_industry_name} <a href="#top" class="scroll-to-top-button">&uarr;</a></h2>\n'

    # Add industry description
    description = sector_desc.get(industry_key, "No description available.")
    html_content += f'<p><i>{html.escape(description)}</i></p>\n'

    # 3e. Format the collected news data as raw markdown for marked.js (moved above fundamentals)
    html_content += '<h3 class="news-section">Recent News </h3>\n'
    if news_data == ['0']:
        html_content += '<div class="markdown-raw-content news-section"><p>No news available for this industry.</p></div>\n'
    else:
        full_news_text = "".join(news_data)
        # Attempt to fix common fragmentation patterns from the original split(',')
        full_news_text = re.sub(r'(\\w+),\\s*(\\d{4})', r'\\1, \\2', full_news_text)
        full_news_text = re.sub(r',\\s*,', ',', full_news_text) # Remove multiple consecutive commas
        full_news_text = full_news_text.replace(':,', ':') # Fix "date:, news" pattern if any

        # Wrap the raw markdown content in a div for marked.js to process
        # Escape HTML entities in the markdown content to ensure it's treated as raw text until marked.js processes it
        escaped_full_news_text = html.escape(full_news_text)
        html_content += f'<div class="markdown-raw-content news-section">{escaped_full_news_text}</div>\n'

    # 3b. Filter the sheets_df DataFrame to get rows where the 'Industry' column matches
    # the current industry_key.
    industry_df = sheets_df[sheets_df['Industry'] == industry_key]

    # 3c. Select the specified columns, ensuring only columns present in the filtered DataFrame
    # are included.
    columns_to_display = [
        'Ticker', 'price%', 'Price', 'mcap',
        'Debt_M', 'Cash_M', 'QRevenue_M', 'QPL_M', 'OrderBook_M'
    ]
    available_columns = [col for col in columns_to_display if col in industry_df.columns]
    selected_df = industry_df[available_columns]

    # 3d. Convert this filtered and selected DataFrame into an HTML table.
    # Append this HTML table to html_content after an <h3> heading for 'Company Data'.
    html_content += '<h3 class="fundamentals-section">Fundamentals</h3>\n'

    # Replace static table generation with a placeholder div
    html_content += f'<div id="fundamentals-table-{industry_key}" class="fundamentals-section">Loading Fundamentals...</div>\n'

    #notes class set to hidden.
    notes_df = industry_df.dropna(subset=['Notes'])
    if not notes_df.empty and 'Ticker' in notes_df.columns:
        html_content += '<h3 class="notes-section hidden">Notes </h3>\n'
        # Create a list of formatted notes: "Ticker: Note"
        # It's safer to ensure both columns are converted to string for concatenation
        notes_list = [
            f"{row['Ticker']}:> {str(row['Notes'])}"
            for index, row in notes_df.iterrows()
        ]

        # Combine all notes into a single markdown string, separated by two newlines for distinct paragraphs
        all_notes_markdown = '\n\n'.join(notes_list)

        # Escape HTML entities and wrap the raw markdown content in a div for marked.js
        escaped_all_notes = html.escape(all_notes_markdown)
        html_content += f'<div class="markdown-notes-block notes-section hidden">{escaped_all_notes}</div>\n'

    # Retrieve the last modified date for the current industry's image
    chart_update_date = image_update_dates.get(industry_key, 'N/A')
    # Format the date to show only day and date, removing time and GMT
    if chart_update_date != 'N/A':
        chart_update_date = chart_update_date.rsplit(' ', 1)[0]


    # Generate the ticker hyperlinks HTML string
    ticker_hyperlinks_html = '<div class="ticker-hyperlinks-row" style="margin-top: 10px;">\n'
    ticker_hyperlinks_html += '   <strong>Buy/Sell Zone details:</strong>'
    for ticker_symbol in ticker_map[industry_key]:
        # Find the price for the current ticker from sheets_df
        ticker_row = sheets_df[sheets_df['Ticker'].str.lower() == ticker_symbol.lower()]
        current_price = ticker_row['Price'].iloc[0] if not ticker_row.empty else 'N/A'
        if current_price != 'N/A':
            try:
                current_price = float(current_price) # Ensure it's a number for formatting
                current_price_str = f"{current_price:.2f}"
            except ValueError:
                current_price_str = 'N/A'
        else:
            current_price_str = 'N/A'

        # Only create hyperlink if dilution data exists for the ticker
        if ticker_symbol.upper() in ticker_dilution_map:
            # Corrected string escaping for onclick arguments and changed <a> to <button>
            ticker_hyperlinks_html += f"<button class=\"ticker-button\" onclick=\"toggleDilutionInline(this, '{ticker_symbol.upper()}', event, '{current_price_str}'); return false;\" style=\"margin-right: 10px;\">{ticker_symbol.upper()}</button>"
        else:
            ticker_hyperlinks_html += f'<span style="margin-right: 10px; color: #666;">{ticker_symbol.upper()} (${current_price_str})</span>' # Display as plain text if no dilution data
    ticker_hyperlinks_html += '</div>\n' # Close ticker-hyperlinks-row

    # Add the Chart.js canvas and the ticker hyperlinks row within the fundamentals section
    html_content += f'''
<div id="fundamentals-charts-{industry_key}" class="fundamentals-section">
    <canvas id="chart_{industry_key}" style="max-width:100%; display:block; margin-bottom:20px;"></canvas>
    {ticker_hyperlinks_html}
</div>
'''

    # The static image and its title remain in the charts-section
    html_content += f'''
<div class="charts-section hidden">
    <h3 class="charts-section">Technicals & charts <small><i>({chart_update_date})</i></small></h3>
<img src="" data-src="screenshots/{industry_key}.png" alt="{formatted_industry_name} Industry Image" class="chart-image" style="max-width:100%; height:auto; display:block; margin-bottom:20px;"></div>
'''

    html_content += '</div>\n' # Close the industry-section div
    industry_counter += 1 # Increment counter
# Add the script to render markdown content using marked.js and to handle toggle functionality
html_content += '''
<script>
    document.addEventListener('DOMContentLoaded', async function() {{
        // Fetch dilution data first
        await fetchDilutionData();
        // Parse custom dilution ranges from the embedded string
        parseCustomDilutionRanges();
        // Then call the function to fetch and render fundamentals tables, which will then call renderCharts
        fetchAndRenderTables();
        // Configure marked.js if needed (e.g., to sanitize HTML)
        // marked.setOptions({{ sanitize: true }});

        const markdownBlocks = document.querySelectorAll('.markdown-raw-content');
        markdownBlocks.forEach(block => {{
            // Decode HTML entities before passing to marked.js, as we escaped them earlier
            const rawMarkdown = block.innerHTML;
            const decodedMarkdown = new DOMParser().parseFromString(rawMarkdown, 'text/html').documentElement.textContent;
            block.innerHTML = marked.parse(decodedMarkdown);
            block.classList.remove('markdown-raw-content'); // Remove the raw class
            block.classList.add('markdown-output'); // Add a class for styled output
        }});

        // Toggle functionality
        const toggleVisibility = (selector, isChecked) => {{
            document.querySelectorAll(selector).forEach(element => {{
                if (isChecked) {{
                    element.classList.remove('hidden');
                }}
                 else {{
                    element.classList.add('hidden');
                }}
            }});
        }};

        document.getElementById('toggleTables').addEventListener('change', function() {{
            toggleVisibility('.fundamentals-section', this.checked);
        }});

        document.getElementById('toggleNews').addEventListener('change', function() {{
            toggleVisibility('.news-section', this.checked);
            toggleVisibility('.markdown-output', this.checked); // Also toggle the rendered markdown news
        }});

        document.getElementById('toggleCharts').addEventListener('change', function() {{
            const isChecked = this.checked;
            toggleVisibility('.charts-section', isChecked);
            if (isChecked) {
                loadChartsImages(); // Load images when charts are shown
            }
        }});

        //document.getElementById('toggleNotes').addEventListener('change', function() {{
        //    toggleVisibility('.notes-section', this.checked);
        //    toggleVisibility('.markdown-notes-block', this.checked);
        //}});

        // Close dilution popup when clicking outside
        document.getElementById('dilution-backdrop').addEventListener('click', closeDilutionInline);

    }});
</script>
'''

# Add a horizontal line before the disclaimer
html_content += '<hr/>\n'

# Add the disclaimer at the very end of the HTML file
html_content += '''
<p><small><i>This is not a financial advice and all the material and content provided is for study and research purposes only. The financials table and technical charts are not updated regularly. Errors in data is expected</i></small></p>
<div class="container">
        <span class="statement">Form 4 within 2 days after insider selling/buying</span>
        <span class="statement">Form 144 at the time of sell order with broker by affiliate/insider</span>
        <span class="statement">Form 10k Anual audited stmnt</span>
        <span class="statement">Form S3 for shelf registration dilutive</span>
        <span class="statement">schedule 13D/13G(/A Amendment) control/passive invest report within 10 days of >5% acquisition of total stock</span>
        <span class="statement">Form 10Q Quarterly unaudited stmnt</span>
        <span class="statement">Form 8k/6k(foreigner) within 4 days of unscheduled events that has stock price implications</span>
        <span class="statement">Def 14A board updates shareholder voting</span>
        <span class="statement">A resale filing for shares tied to warrant exercises means allowing the holders to resell the shares after warrant excercise in the market</span>
        <span class="statement">completion of redemption of warrants generating cash, typically means company redeemed outstanding warrants, and investors exercised those warrants to buy shares(added to outstanding shares), providing the company with cash</span>
        <span class="statement">Form S8 offer RSU/stock options incentives to employees, directors, or consultants.</span>
        <span class="statement">After shelf/ATM filing, subsequent prospectus supplement Form 424B5 filing to find the exact amount, if any, that was sold or exchanged.</span>
    </div>
'''

# Close the HTML body and document
html_content += '''</body>\n</html>'''
