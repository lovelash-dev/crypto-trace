import json
import re
import os
from datetime import datetime

import streamlit as st

import config
from core.fetcher import BlockchainFetcher
from core.graph import TransactionGraph
from core.accounting import FundReconciler
from core.attribution import EntityAttributor


st.set_page_config(
    page_title="CryptoTrace",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700&display=swap');
:root {
  --ink: #172033;
  --muted: #69758a;
  --line: #e7ebf2;
  --paper: #ffffff;
  --canvas: #f5f7fb;
  --indigo: #4f46e5;
  --indigo-dark: #3730a3;
  --mint: #dff7ec;
  --green: #138a61;
}
html, body, [class*="css"] { font-family: "DM Sans", sans-serif; color: var(--ink); }
.stApp { background: var(--canvas); }
.block-container { max-width: 1480px; padding: 1.25rem 2rem 3rem; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }
[data-testid="stMetric"] {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: 0 4px 16px rgba(32,45,74,.035);
}
[data-testid="stMetricLabel"] { color: var(--muted); }
[data-testid="stMetricValue"] { color: var(--ink); font-family: "Manrope", sans-serif; }
.stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { height: 48px; padding: 0 4px; color: var(--muted); }
.stTabs [aria-selected="true"] { color: var(--indigo); border-bottom-color: var(--indigo); }
.stButton > button {
  border-radius: 9px;
  border: 1px solid var(--line);
  height: 42px;
  font-weight: 600;
}
.stButton > button[kind="primary"] {
  background: var(--indigo);
  border: 1px solid var(--indigo);
  color: white;
  box-shadow: 0 7px 18px rgba(79,70,229,.16);
}
.stButton > button[kind="primary"]:hover { background: var(--indigo-dark); border-color: var(--indigo-dark); }
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  height: 48px; margin-bottom: 18px;
}
.brand { display: flex; align-items: center; gap: 10px; font-family: "Manrope"; font-size: 18px; font-weight: 700; }
.brand-mark {
  display: grid; place-items: center; width: 34px; height: 34px; border-radius: 9px;
  background: #edeafd; color: var(--indigo); font-size: 19px;
}
.network-pill {
  display: inline-flex; align-items: center; gap: 8px; background: white;
  border: 1px solid var(--line); border-radius: 999px; padding: 7px 11px;
  color: #536075; font-size: 12px; font-weight: 600;
}
.network-dot { width: 7px; height: 7px; border-radius: 50%; background: #29b686; box-shadow: 0 0 0 3px #e7f7f1; }
.hero-card {
  background: linear-gradient(135deg, #ffffff 0%, #fdfcff 58%, #f1efff 100%);
  border: 1px solid var(--line); border-radius: 18px; padding: 30px 32px 28px;
  margin-bottom: 18px; box-shadow: 0 10px 30px rgba(31,42,68,.035);
}
.hero-card h1 { margin: 5px 0 8px; font-family: "Manrope"; font-size: 32px; letter-spacing: -.04em; }
.hero-card p { max-width: 650px; margin: 0 0 22px; color: var(--muted); line-height: 1.55; }
.eyebrow { color: var(--indigo); font-size: 11px; font-weight: 700; letter-spacing: .13em; }
.section-title { font-family: "Manrope"; font-size: 16px; font-weight: 700; margin: 22px 0 12px; }
.panel {
  background: white; border: 1px solid var(--line); border-radius: 14px;
  padding: 18px; box-shadow: 0 4px 16px rgba(32,45,74,.025);
}
.status-banner {
  display:flex; align-items:center; justify-content:space-between;
  background:#f0f7ff; border:1px solid #dceafa; border-radius:10px;
  padding:10px 12px; color:#55708d; font-size:12px; margin:8px 0 16px;
}
.status-banner.demo { background:#f3f1ff; border-color:#e3dffd; color:#6258a8; }
.address { font-family: monospace; color:#43516a; }
.small-muted { color: var(--muted); font-size: 12px; }
.graph-scroll { overflow-x:auto; background:#fbfcff; border:1px solid var(--line); border-radius:14px; padding:14px; }
.graph-node { fill:white; stroke:#dfe4ef; stroke-width:1.5; }
.graph-root { fill:#f0efff; stroke:#7166df; stroke-width:2; }
.graph-exchange { fill:#eaf8f1; stroke:#73c9a6; stroke-width:1.7; }
.graph-edge { stroke:#aab4c5; stroke-width:1.5; fill:none; marker-end:url(#arrow); }
.graph-label { font-family:"DM Sans",sans-serif; fill:#26324a; font-size:11px; font-weight:700; }
.graph-sub { font-family:"DM Sans",sans-serif; fill:#78849a; font-size:9px; }
.download-wrap [data-testid="stDownloadButton"] { float:right; }
div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow:hidden; }
</style>
""", unsafe_allow_html=True)


def valid_input(value):
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", value) or
                re.fullmatch(r"0x[0-9a-fA-F]{64}", value))


def short_address(address):
    if not address:
        return "Unknown"
    if len(address) < 16:
        return address
    return f"{address[:8]}…{address[-6:]}"


def collect_nodes(root_node):
    nodes, edges = [], []
    seen = set()

    def walk(node):
        if node.address not in seen:
            seen.add(node.address)
            nodes.append(node)
        for edge in node.edges:
            edges.append(edge)
        for child in node.children:
            walk(child)

    walk(root_node)
    return nodes, edges


def make_graph_svg(root_node, endpoint_info):
    endpoint_map = {item["address"]: item for item in endpoint_info}
    nodes, edges = collect_nodes(root_node)
    by_depth = {}
    for node in nodes:
        by_depth.setdefault(node.depth, []).append(node)

    max_depth = max(by_depth, default=0)
    width = max(820, (max_depth + 1) * 210)
    max_layer = max((len(layer) for layer in by_depth.values()), default=1)
    height = max(260, max_layer * 82 + 60)
    positions = {}

    for depth, layer in by_depth.items():
        x = 105 + depth * 210
        for index, node in enumerate(layer):
            y = 42 + index * (height - 84) / max(len(layer) - 1, 1)
            positions[node.address] = (x, y)

    svg = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L7,3 z" fill="#aab4c5"/></marker></defs>'
    ]

    for edge in edges:
        x1, y1 = positions.get(edge.from_address, (0, 0))
        x2, y2 = positions.get(edge.to_address, (0, 0))
        midx = (x1 + x2) / 2
        svg.append(
            f'<path class="graph-edge" d="M{x1 + 72},{y1} C{midx},{y1} {midx},{y2} {x2 - 72},{y2}"/>'
            f'<text x="{midx}" y="{(y1 + y2) / 2 - 7}" text-anchor="middle" '
            f'class="graph-sub">{edge.amount_eth:.4f} ETH</text>'
        )

    for node in nodes:
        x, y = positions[node.address]
        meta = endpoint_map.get(node.address, {})
        entity = meta.get("entity", "")
        title = entity if entity and entity != "Unknown Wallet" else short_address(node.address)
        if len(title) > 22:
            title = title[:20] + "…"
        if node.address == root_node.address:
            css_class = "graph-root"
        elif "exchange" in meta.get("category", "").lower():
            css_class = "graph-exchange"
        else:
            css_class = "graph-node"
        svg.append(
            f'<rect class="{css_class}" x="{x - 72}" y="{y - 28}" width="144" height="56" rx="10"/>'
            f'<text class="graph-label" x="{x}" y="{y - 5}" text-anchor="middle">{title}</text>'
            f'<text class="graph-sub" x="{x}" y="{y + 12}" text-anchor="middle">'
            f'{node.stolen_flow:.4f} ETH</text>'
        )

    svg.append("</svg>")
    return "".join(svg)


st.markdown("""
<div class="topbar">
  <div class="brand"><span class="brand-mark">◈</span> CryptoTrace</div>
  <div class="network-pill"><span class="network-dot"></span> Ethereum Mainnet</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Investigation")
    demo_mode = st.toggle("Demo mode", value=True, help="Uses deterministic synthetic data and does not call Etherscan.")
    api_key = st.text_input("Etherscan API key", type="password",
                            value=os.getenv("ETHERSCAN_API_KEY", ""),
                            help="Your key is used only for server-side live requests.")
    st.divider()
    st.markdown("### Trace settings")
    depth = st.slider("Trace depth", 1, 7, 3)
    max_transactions = st.slider("Transactions per wallet", 1, 100, 25)
    st.divider()
    st.caption("Asset coverage")
    st.markdown("**Native ETH**")
    st.caption("ERC-20 tokens are not included.")
    st.markdown('<div class="small-muted">Educational analysis only. Verify findings independently.</div>',
                unsafe_allow_html=True)


if "identifier" not in st.session_state:
    st.session_state["identifier"] = ""

st.markdown("""
<div class="hero-card">
  <div class="eyebrow">ON-CHAIN INVESTIGATION WORKSPACE</div>
  <h1>Trace the flow. Understand the destination.</h1>
  <p>Investigate Ethereum wallet balances and transaction paths with transparent fund reconciliation and local entity attribution.</p>
</div>
""", unsafe_allow_html=True)

search_col, action_col = st.columns([5, 1.15], vertical_alignment="bottom")
with search_col:
    identifier = st.text_input(
        "Wallet address or transaction hash",
        key="identifier",
        placeholder="0x…",
        label_visibility="visible",
    )
with action_col:
    run = st.button("Run investigation", type="primary", use_container_width=True)

example_col, spacer = st.columns([4, 1])
with example_col:
    st.caption("Quick demo")
    b1, b2, b3 = st.columns(3)
    if b1.button("Wallet example", use_container_width=True):
        st.session_state["identifier"] = "0x0941dfaa0db804f37df1273e04cf10d55e6ffebffb80"
        st.rerun()
    if b2.button("Binance endpoint", use_container_width=True):
        st.session_state["identifier"] = "0x28c6c06298d514db089934071355e5743bf21d60"
        st.rerun()
    if b3.button("Transaction example", use_container_width=True):
        st.session_state["identifier"] = "0x" + "a" * 64
        st.rerun()


if run:
    value = identifier.strip()
    if not value:
        st.error("Enter a wallet address or transaction hash.")
    elif not demo_mode and not valid_input(value):
        st.error("Enter a valid 42-character wallet address or 66-character transaction hash.")
    else:
        try:
            with st.spinner("Fetching data and tracing transaction paths…"):
                fetcher = BlockchainFetcher(
                    api_key=api_key or os.getenv("ETHERSCAN_API_KEY"),
                    use_mock=demo_mode,
                )
                is_wallet = bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", value))
                origin = (
                    fetcher.get_wallet_start_details(value)
                    if is_wallet
                    else fetcher.get_transaction_details(value)
                )
                graph = TransactionGraph(
                    fetcher=fetcher,
                    max_depth=depth,
                    max_transactions=max_transactions,
                )
                graph.build_from_origin(origin)
                reconciliation = FundReconciler(int(origin["value_wei"])).analyze(graph)
                attributor = EntityAttributor(db_path=config.ATTRIBUTION_DB_PATH)
                endpoints = attributor.label_graph_endpoints(graph.get_endpoints())
                nodes, edges = collect_nodes(graph.root)

                st.session_state["report"] = {
                    "origin": origin,
                    "endpoints": endpoints,
                    "reconciliation": reconciliation.to_dict(),
                }
                st.session_state["root_node"] = graph.root
                st.session_state["nodes"] = nodes
                st.session_state["edges"] = edges
                st.session_state["demo_mode"] = demo_mode
                history = st.session_state.setdefault("history", [])
                history.insert(0, {
                    "time": datetime.now().strftime("%H:%M"),
                    "input": value,
                    "amount": origin["value_eth"],
                    "mode": "Demo" if demo_mode else "Live",
                })
                st.session_state["history"] = history[:8]
        except Exception as exc:
            st.error(f"Investigation failed: {exc}")


if "report" in st.session_state:
    report = st.session_state["report"]
    rec = report["reconciliation"]
    origin = report["origin"]

    st.divider()
    mode_class = "demo" if st.session_state.get("demo_mode") else ""
    mode_text = "Synthetic demo data" if st.session_state.get("demo_mode") else "Live Etherscan data"
    st.markdown(
        f'<div class="status-banner {mode_class}"><span><b>Investigation complete</b>'
        f' · <span class="address">{short_address(origin["to_address"])}</span></span>'
        f'<span>{mode_text}</span></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Starting amount", f'{origin["value_eth"]:.6f} ETH')
    c2.metric("Tracked flow", f'{rec["tracked_stolen_flow"]:.6f} ETH')
    c3.metric("Gas fees", f'{rec["total_gas_fees_eth"]:.6f} ETH')
    c4.metric("Wallet endpoints", rec["total_endpoints"])

    exchange_endpoints = [
        item for item in report["endpoints"]
        if "exchange" in item["category"].lower()
    ]
    if exchange_endpoints:
        exchange_summary = " · ".join(
            f'{item["entity"]} ({item["stolen_flow"]:.4f} ETH)'
            for item in exchange_endpoints
        )
        st.success(f"Known exchange endpoint{'' if len(exchange_endpoints) == 1 else 's'}: {exchange_summary}")

    tab_graph, tab_endpoints, tab_transfers, tab_audit, tab_json = st.tabs(
        ["Transaction flow", "Endpoints", "Transfers", "Reconciliation", "Raw report"]
    )

    with tab_graph:
        st.markdown('<div class="section-title">Wallet-to-wallet flow</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="graph-scroll">{make_graph_svg(st.session_state["root_node"], report["endpoints"])}</div>',
            unsafe_allow_html=True,
        )

    with tab_endpoints:
        st.markdown('<div class="section-title">Terminal wallets and attribution</div>', unsafe_allow_html=True)
        if report["endpoints"]:
            st.dataframe(
                [{
                    "Address": item["address"],
                    "Entity": item["entity"],
                    "Category": item["category"],
                    "Tracked flow": f'{item["stolen_flow"]:.6f} ETH',
                    "Confidence": item["confidence"],
                    "Source": item["source"],
                    "Verified": item["last_verified"],
                } for item in report["endpoints"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No terminal endpoints were found within the selected depth.")
        st.caption("A known-service match is an address-label match, not proof of misconduct.")

    with tab_transfers:
        st.markdown('<div class="section-title">Tracked outgoing transfers</div>', unsafe_allow_html=True)
        edges = st.session_state["edges"]
        if edges:
            st.dataframe(
                [{
                    "From": edge.from_address,
                    "To": edge.to_address,
                    "Transfer": f"{edge.amount_eth:.8f} ETH",
                    "Tracked flow": f"{edge.stolen_flow_wei / 10**18:.8f} ETH",
                    "Gas fee": f"{edge.gas_fee_eth:.8f} ETH",
                    "Block": edge.block_number,
                } for edge in edges],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No outgoing transfers were found within the selected depth.")

    with tab_audit:
        st.markdown('<div class="section-title">Fund reconciliation</div>', unsafe_allow_html=True)
        a, b, c = st.columns(3)
        a.metric("Initial amount", f'{rec["initial_stolen_amount"]:.8f} ETH')
        b.metric("Unaccounted amount", f'{rec["unaccounted_amount"]:.8f} ETH')
        c.metric("Fully accounted", "Yes" if rec["is_fully_accounted"] else "No")
        d, e = st.columns(2)
        d.metric("Nodes analyzed", rec["total_nodes_analyzed"])
        e.metric("Terminal endpoints", rec["total_endpoints"])
        st.warning(
            "Flow allocation is an analytical estimate. It does not prove that specific ETH "
            "units moved to a particular wallet."
        )

    with tab_json:
        st.json(report)

    st.markdown('<div class="download-wrap">', unsafe_allow_html=True)
    st.download_button(
        "Download JSON report",
        data=json.dumps(report, indent=2),
        file_name="cryptotrace-report.json",
        mime="application/json",
        type="secondary",
    )
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("history"):
    st.markdown('<div class="section-title">Recent investigations</div>', unsafe_allow_html=True)
    history_rows = [{
        "Time": item["time"],
        "Input": short_address(item["input"]),
        "Amount": f'{item["amount"]:.6f} ETH',
        "Source": item["mode"],
    } for item in st.session_state["history"]]
    st.dataframe(history_rows, use_container_width=True, hide_index=True)
