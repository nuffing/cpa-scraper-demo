import os
import requests
import pandas as pd
from urllib.parse import urlparse, urlunparse

# -----------------------------------------------------------------------------
# SCRIPT: LinkedIn Profile Finder (CPA Focused)
# -----------------------------------------------------------------------------
# DESCRIPTION:
# This bot automates the process of finding personal LinkedIn profiles for specific 
# individuals (CPAs) using the Serper.dev Google Search API. It takes a list of 
# names and US states, constructs precise Google search queries, filters the 
# results to exclude company pages/job postings, normalizes the URLs, and exports
# the clean data to a CSV file.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# ALGORITHM DESCRIPTION:
# 1. Start with a list of target individuals (Name + State).
# 2. For each target, generate a specific Google query: "Name" "CPA" "State" "United States" LinkedIn.
# 3. Send this query to the Serper.dev API to fetch the top 10 organic Google results.
# 4. Iterate through the search results and apply filtering rules:
#    a. Check if the URL is a valid LinkedIn profile (contains "/in/").
#    b. Discard non-profile URLs (e.g., /company/, /jobs/, /posts/).
# 5. Normalize valid URLs by removing any tracking parameters (everything after '?').
# 6. Deduplicate the results ensuring only unique profiles are kept per person.
# 7. Extract the Meta Title and Meta Description (Snippet) for each valid profile.
#    a. If metadata is missing, store empty strings but keep the URL.
# 8. Compile the extracted data into a structured list.
# 9. Once all targets are processed, convert the list into a DataFrame.
# 10. Save the final dataset to a CSV file.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# MERMAID DIAGRAM (Workflow Visualization):
# Copy the code inside the block below and paste it into https://mermaid.live
# to visualize the logic flow.
#
# ```mermaid
# graph TD
#     A["Start: Input Name #40;e.g. 'John Doe'#41; and State"] --> B["Generate Google Search Query"]
#     B --> C["Execute Google Search #40;Fetch top 10 results#41;"]
#     C --> D{"Loop through each result"}
#     D -- "Result 1-10" --> E{"Is it a LinkedIn '/in/' URL?"}
#     E -- "No" --> F["Discard Result"]
#     E -- "Yes" --> G["Normalize URL #40;Remove '?' params#41;"]
#     G --> H["Check for Duplicates"]
#     H -- "New Profile" --> I["Extract Meta Title #38; Description"]
#     H -- "Already Found" --> F
#     I --> J["Add to Results List"]
#     J --> K{"More Results?"}
#     K -- "Yes" --> D
#     K -- "No" --> L["Format Data into CSV/Excel"]
#     F --> K
#     L --> M["End: Output Saved"]
# ```
# -----------------------------------------------------------------------------

def search_cpa_profiles(input_data):
    """
    Main function to search and extract LinkedIn profiles.
    
    Args:
        input_data (list of dicts): [{'name': 'John Doe', 'state': 'Maine'}, ...]
    
    Returns:
        pd.DataFrame: A dataframe containing the cleaned scraping results.
    """
    
    # Make sure that we can access the api from an environment variable for safety.
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY not found in environment variables.")

    url = "https://google.serper.dev/search"
    all_results = []

    # 1. Start with a list of target individuals (Name + State).
    for person in input_data:
        name = person.get('name')
        state = person.get('state')
        
        # 2. For each target, generate a specific Google query: "Name" "CPA" "State" "United States" LinkedIn.
        query = f'"{name}" "CPA" "{state}" "United States" LinkedIn'
        
        payload = {
            "q": query,
            "num": 10  # Parse top 10 Google results per query
        }
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        try:
            # 3. Send this query to the Serper.dev API to fetch the top 10 organic Google results.
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            organic_results = data.get("organic", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {name}: {e}")
            continue

        seen_urls = set()
        
        # 4. Iterate through the search results and apply filtering rules:
        for index, result in enumerate(organic_results, start=1):
            raw_url = result.get('link', '')
            
            # a. Check if the URL is a valid LinkedIn profile (contains "/in/").
            # b. Discard non-profile URLs (e.g., /company/, /jobs/, /posts/).
            if "linkedin.com/in/" in raw_url and not any(x in raw_url for x in ["/company/", "/jobs/", "/posts/", "/school/", "/pulse/"]):
                
                # 5. Normalize valid URLs by removing any tracking parameters (everything after '?').
                parsed_url = urlparse(raw_url)
                clean_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", ""))
                
                # 6. Deduplicate the results ensuring only unique profiles are kept per person.
                if clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    
                    # 7. Extract the Meta Title and Meta Description (Snippet) for each valid profile.
                    # a. If metadata is missing, store empty strings but keep the URL.
                    meta_title = result.get('title', '')
                    meta_description = result.get('snippet', '')
                    
                    # 8. Compile the extracted data into a structured list.
                    all_results.append({
                        "input_name": name,
                        "input_state": state,
                        "google_rank": index,
                        "linkedin_url": clean_url,
                        "meta_title": meta_title,
                        "meta_description": meta_description
                    })

    # 9. Once all targets are processed, convert the list into a DataFrame.
    df = pd.DataFrame(all_results)
    
    return df

if __name__ == "__main__":
    # Example Usage
    # You would typically load this input_data from a source CSV file
    sample_input = [
        {"name": "Jane Smith", "state": "Texas"},
        {"name": "John Doe", "state": "Maine"}
    ]
    
    # 10. Save the final dataset to a CSV file.
    try:
        df_results = search_cpa_profiles(sample_input)
        if not df_results.empty:
            print("Extraction complete. Saving to 'linkedin_results.csv'...")
            df_results.to_csv("linkedin_results.csv", index=False)
            print(df_results.head())
        else:
            print("No profiles found.")
    except Exception as e:
        print(f"Script failed: {e}")
