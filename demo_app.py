import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlparse, urlunparse

# -----------------------------------------------------------------------------
# CONFIGURATION & PAGE SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="CPA LinkedIn Finder", layout="wide")

st.title("🔍 LinkedIn Profile Finder (CPA Demo)")
st.markdown("""
This tool automates the discovery of personal LinkedIn profiles. 
**Instructions:** Enter names and states below, and the system will fetch verified profiles via Google Search.
""")

# -----------------------------------------------------------------------------
# SIDEBAR - API CONFIG
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    # In a real app, use st.secrets. For a demo, inputting it is fine.
    api_key = st.text_input("Enter Serper.dev API Key", type="password")
    st.info("Get a free key at serper.dev")

# -----------------------------------------------------------------------------
# CORE LOGIC (Reuse of your script)
# -----------------------------------------------------------------------------
def search_profiles(names_list, api_key):
    url = "https://google.serper.dev/search"
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(names_list)
    
    for i, person in enumerate(names_list):
        # Update UI
        status_text.text(f"Searching for: {person['name']} in {person['state']}...")
        progress_bar.progress((i + 1) / total)
        
        query = f'"{person["name"]}" "CPA" "{person["state"]}" "United States" LinkedIn'
        
        try:
            payload = {"q": query, "num": 10}
            headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            organic = data.get("organic", [])
            
            # Filter Logic
            found_for_person = False
            for rank, item in enumerate(organic, 1):
                link = item.get('link', '')
                # Filter: Must be linkedin.com/in/ AND NOT company/job/etc
                if "linkedin.com/in/" in link and not any(x in link for x in ["/company/", "/jobs/", "/posts/"]):
                    
                    # Normalize
                    parsed = urlparse(link)
                    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
                    
                    results.append({
                        "Input Name": person['name'],
                        "Input State": person['state'],
                        "Google Rank": rank,
                        "Title": item.get('title'),
                        "LinkedIn URL": clean_url
                    })
                    found_for_person = True
                    # Limit to top 1 valid profile per person for the demo (cleaner UI)
                    break 
            
            if not found_for_person:
                results.append({
                    "Input Name": person['name'],
                    "Input State": person['state'],
                    "Google Rank": "-",
                    "Title": "Not Found",
                    "LinkedIn URL": "-"
                })
                
        except Exception as e:
            st.error(f"Error searching {person['name']}: {e}")
            
    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# MAIN INTERFACE
# -----------------------------------------------------------------------------

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Input Data")
    # Default example data
    default_input = "John Doe, Maine\nJane Smith, Texas\nRobert Johnson, Florida"
    text_input = st.text_area("Enter Name, State (one per line)", value=default_input, height=200)

with col2:
    st.subheader("2. Results")
    if st.button("Run Search", type="primary"):
        if not api_key:
            st.warning("Please enter an API Key in the sidebar.")
        else:
            # Parse the text area
            input_list = []
            for line in text_input.split('\n'):
                if ',' in line:
                    parts = line.split(',')
                    input_list.append({"name": parts[0].strip(), "state": parts[1].strip()})
            
            if input_list:
                df = search_profiles(input_list, api_key)
                st.dataframe(df, use_container_width=True)
                
                # CSV Download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name="linkedin_demo_results.csv",
                    mime="text/csv",
                )
            else:
                st.error("Please enter valid data in 'Name, State' format.")
