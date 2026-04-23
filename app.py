import streamlit as st
import requests
import pandas as pd
import math

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="News Dose", layout="wide")
st.title("News Dose")
st.markdown(
    "Your daily dose of news, ready for you to explore and digest!\n\n"
    "Use the filters on the left to find stories by category or source.\n"
    "Dive into the clusters of related news.\n"
    "Click the Summarize button on any article to get a quick summary.\n\n"
    "Happy reading!"
)
def call_api(endpoint: str, params: dict = {}) -> list | dict | None:
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def render_article_card(article: dict, key_prefix: str, idx: int) -> None:
    headline = article.get("headline") or "No headline"
    description = article.get("description") or ""
    category_text = article.get("category") or "Unknown"
    source_text = article.get("source") or "Unknown"
    url = article.get("url") or article.get("link") or ""

    link_html = (
        f"<a href='{url}' target='_blank' style='color:#1f77b4;'>Read full article</a>"
        if url else ""
    )

    st.markdown(
        f"""
        <div style="
            border:1px solid #ccc;
            padding:15px;
            margin-bottom:10px;
            border-radius:10px;
            background-color:#f9f9f9;
            color:#000000;
        ">
            <h3 style="margin:0; color:#1a1a1a;">{headline}</h3>
            <p style="margin:5px 0; color:#333333;">{description}</p>
            <p style="margin:0; font-size:12px; color:gray;">
                Category: {category_text} | Source: {source_text}
            </p>
            <p style="margin:5px 0 0 0; font-size:12px;">{link_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if url:
        btn_key = f"{key_prefix}_{idx}_{url}"
        if st.button("Summarize", key=btn_key):
            with st.spinner("Generating summary..."):
                result = call_api("/summarize", {"url": url})
                if result:
                    st.info(result.get("summary", "No summary returned."))
                else:
                    st.error("Summarization failed.")


def render_cluster_card(cluster: list, cluster_idx: int) -> None:
    if not cluster:
        return

    main = cluster[0]
    headline = main.get("headline") or "No headline"
    description = main.get("description") or ""
    category_text = main.get("category") or "Unknown"
    source_text = main.get("source") or "Unknown"
    url = main.get("url") or main.get("link") or ""

    link_html = (
        f"<a href='{url}' target='_blank' style='color:#1f77b4;'>Read full article</a>"
        if url else ""
    )

    st.markdown(
        f"""
        <div style="
            border:2px solid #ff7f0e;
            padding:15px;
            margin-bottom:10px;
            border-radius:10px;
            background-color:#fff7ec;
            color:#000000;
        ">
            <h3 style="margin:0; color:#1a1a1a;">{headline}</h3>
            <p style="margin:5px 0; color:#333333;">{description}</p>
            <p style="margin:0; font-size:12px; color:gray;">
                Category: {category_text} | Source: {source_text}
            </p>
            <p style="margin:5px 0 0 0; font-size:12px;">{link_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if url:
        if st.button(" Summarize", key=f"cluster_main_{cluster_idx}_{url}"):
            with st.spinner("Generating summary..."):
                result = call_api("/summarize", {"url": url})
                if result:
                    st.info(result.get("summary", "No summary returned."))
                else:
                    st.error("Summarization failed.")

    if len(cluster) > 1:
        with st.expander(f" {len(cluster) - 1} more source(s) covering this story"):
            for other in cluster[1:]:
                other_headline = other.get("headline") or "No headline"
                other_source = other.get("source") or "Unknown"
                other_url = other.get("url") or other.get("link") or ""
                read_link = (
                    f"<a href='{other_url}' target='_blank' style='color:#1f77b4;'>Read</a>"
                    if other_url else ""
                )
                st.markdown(
                    f"<p style='margin:4px 0; font-size:13px;'>"
                    f"<strong>{other_source}</strong>: {other_headline} {read_link}</p>",
                    unsafe_allow_html=True,
                )


@st.cache_data(ttl=300)
def get_filter_options() -> tuple[list, list]:
    data = call_api("/filter", {"limit": 10000})
    if not data:
        return [], []
    df = pd.DataFrame(data)
    if df.empty:
        return [], []
    categories = sorted(df["category"].dropna().unique().tolist())
    sources = sorted(df["source"].dropna().unique().tolist())
    return categories, sources


st.sidebar.header("Filters")
categories, sources = get_filter_options()

selected_category = st.sidebar.selectbox("Category:", ["All"] + categories)
selected_source = st.sidebar.selectbox("Source:", ["All"] + sources)
view_mode = st.sidebar.radio("View mode:", ["Normal", "Clustered"], index=0)

category = None if selected_category == "All" else selected_category
source = None if selected_source == "All" else selected_source


st.markdown("---")
st.header("Search")

semantic_query = st.text_input(
    "Search news semantically:",
    placeholder="e.g. AI regulation, climate policy, stock market crash",
)

if semantic_query:
    search_params = {"query": semantic_query}
    if category:
        search_params["category"] = category
    if source:
        search_params["source"] = source

    results = call_api("/semantic_search", search_params)
    if results is None:
        st.error("Semantic search failed.")
    elif not results:
        st.info("No matches found for the current filters.")
    else:
        for idx, item in enumerate(results):
            render_article_card(item, "sem", idx)
    st.stop()

if view_mode == "Clustered":
    st.markdown("---")
    st.header("Top Stories (Clustered)")

    params = {"limit": 50}
    if category:
        params["category"] = category
    if source:
        params["source"] = source

    clusters = call_api("/clustered", params)

    if not clusters:
        st.info("No clustered stories available.")
    else:
        total_clusters = len(clusters)
        if total_clusters <= 1:
            clusters_per_page = 1
        else:
            clusters_per_page = st.sidebar.slider(
                "Clusters per page:",
                min_value=1,
                max_value=total_clusters,
                value=min(10, total_clusters),
            )

        if "cluster_page" not in st.session_state:
            st.session_state.cluster_page = 1

        total_pages = max(1, math.ceil(total_clusters / clusters_per_page))
        st.session_state.cluster_page = min(st.session_state.cluster_page, total_pages)

        col1, col2, col3 = st.sidebar.columns([1, 2, 1])
        with col1:
            if st.button("◀", key="cluster_prev") and st.session_state.cluster_page > 1:
                st.session_state.cluster_page -= 1
        with col2:
            st.markdown(f"<center>{st.session_state.cluster_page}/{total_pages}</center>", unsafe_allow_html=True)
        with col3:
            if st.button("▶", key="cluster_next") and st.session_state.cluster_page < total_pages:
                st.session_state.cluster_page += 1

        start = (st.session_state.cluster_page - 1) * clusters_per_page
        end = start + clusters_per_page

        for c_idx, cluster in enumerate(clusters[start:end], start=start):
            render_cluster_card(cluster, c_idx)

        st.sidebar.caption(f"Showing {start+1}–{min(end, total_clusters)} of {total_clusters} clusters")

else:
    params = {"limit": 10000}
    if category:
        params["category"] = category
    if source:
        params["source"] = source

    data = call_api("/filter", params)

    if not data:
        st.warning("No articles found for this filter combination.")
        st.stop()

    df = pd.DataFrame(data)
    total_articles = len(df)

    articles_per_page = st.sidebar.slider("Articles per page:", 1, max(10, total_articles), min(10, total_articles))

    if "article_page" not in st.session_state:
        st.session_state.article_page = 1

    total_pages = max(1, math.ceil(total_articles / articles_per_page))
    st.session_state.article_page = min(st.session_state.article_page, total_pages)

    col1, col2, col3 = st.sidebar.columns([1, 2, 1])
    with col1:
        if st.button("◀", key="art_prev") and st.session_state.article_page > 1:
            st.session_state.article_page -= 1
    with col2:
        st.markdown(f"<center>{st.session_state.article_page}/{total_pages}</center>", unsafe_allow_html=True)
    with col3:
        if st.button("▶", key="art_next") and st.session_state.article_page < total_pages:
            st.session_state.article_page += 1

    start = (st.session_state.article_page - 1) * articles_per_page
    end = start + articles_per_page

    for idx, row in df.iloc[start:end].iterrows():
        render_article_card(row.to_dict(), "main", idx)

    st.sidebar.caption(f"Showing {start+1}–{min(end, total_articles)} of {total_articles} articles")
