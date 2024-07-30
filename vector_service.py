from langchain.tools import tool
from alloy import store, store_hs

@tool
def get_hs_code(hs_code: str) -> dict:
    """Get goods description from HS (Harmonized) code"""
    api_response_in = store_hs.search(hs_code, "mmr")
    return api_response_in

@tool
def search_hs_code_info(goods_name: str) -> list:
    """Search the international harmonized code from goods name"""
    api_response_in = store_hs.search(goods_name, "mmr")
    return api_response_in

@tool
def search_faq_info(query: str) -> list:
    """Search common information about customs"""
    api_response_in = store.search(query, "mmr")
    return api_response_in