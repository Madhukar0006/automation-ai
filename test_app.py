import streamlit as st

st.set_page_config(
    page_title="Log Parser Test",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Log Parser Test")
st.write("If you can see this, Streamlit is working!")

# Test log_analyzer import
try:
    from log_analyzer import identify_log_type
    st.success("✅ log_analyzer imported successfully")
    
    # Test with sample log
    sample_log = '{"properties":{"category":"AzureFirewallNatRuleLog"}}'
    log_type = identify_log_type(sample_log)
    st.write(f"Sample log type: {log_type}")
    
except Exception as e:
    st.error(f"❌ Error importing log_analyzer: {e}")

# Test lc_bridge import
try:
    from lc_bridge import classify_log_lc
    st.success("✅ lc_bridge imported successfully")
except Exception as e:
    st.error(f"❌ Error importing lc_bridge: {e}")

st.write("Test completed!")
