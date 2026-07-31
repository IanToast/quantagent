import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="QuantAgent",
    layout="wide"
)

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True
    
    st.title("QuantAgent")
    st.subheader("Autonomous Stock Research")

    password = st.text_input("Password", type="password")
    if st.button("Login"):
        correct = os.getenv("APP_PASSWORD")
        if password == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

from agent.graph import build_graph

st.title("QuantAgent")
st.caption("Autonomous quantitative research powered by LangGraph + Claude")

@st.cache_resource
def get_graph():
    return build_graph()

graph = get_graph()

col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
with col1:
    tickers_input = st.text_input("Enter ticker symbol", placeholder="e.g. NVDA, AAPL, JPM").upper().strip()
with col2:
    run = st.button("Generate Report", type="primary", use_container_width=True)

if run and tickers_input:

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    if not tickers:
        st.error("Please enter at least one ticker.")
        st.stop()

    results = {}
    for ticker in tickers:
        with st.spinner(f"Researching {ticker}... this takes about 30-60 seconds"):
            result = graph.invoke({"ticker": ticker, "errors": []})
            results[ticker] = result

    tabs = st.tabs(tickers)
    for tab, ticker in zip(tabs, tickers):
        with tab:
            result = results[ticker]
            
            if not result.get("research_report"):
                errors = result.get("errors", [])
                if any("no data returned" in e for e in errors):
                    st.error(f"**{ticker}** could not be found. Please check the ticker symbol and try again.")
                else:
                    st.error(f"Failed to generate report for **{ticker}**. Please try again.")
                continue
    
            report = result["research_report"]
            sentiment = report.sentiment
            quant = report.quant_signals
            price = report.price_summary

            st.header(f"{report.company_name} ({report.ticker})")
            st.caption(f"Generated {report.generated_at.strftime('%Y-%m-%d %H:%M')}")

            st.subheader(f"{report.overall_signal.upper()} · {report.time_horizon.title()}")
            st.info(report.one_line_summary.replace("$", "\\$").replace("_", "\\_"))
            st.write(report.signal_rationale.replace("$", "\\$").replace("_", "\\_"))

            with st.expander("Risks & Catalysts", expanded=True):
                col_risk, col_cat = st.columns(2)
                with col_risk:
                    st.subheader("Risks")
                    for risk in report.risks:
                        st.write("- " + risk.replace("$", "\\$").replace("_", "\\_"))
                with col_cat:
                    st.subheader("Catalysts")
                    for catalyst in report.catalysts:
                        st.write("- " + catalyst.replace("$", "\\$").replace("_", "\\_"))

            with st.expander("Price Summary", expanded=False):
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Current Price", f"${price.current_price:,.2f}", f"{price.price_change_1d_pct:+.2f}% today")
                c2.metric("1 Month", f"{price.price_change_1m_pct:+.2f}%")
                c3.metric("1 Year", f"{price.price_change_1y_pct:+.2f}%")
                c4.metric("52W High", f"${price.week_52_high:,.2f}")
                c5.metric("52W Low", f"${price.week_52_low:,.2f}")

            with st.expander("Analyst Targets", expanded=False):
                if report.analyst_target_mean:
                    upside = ((report.analyst_target_mean - price.current_price) / price.current_price) * 100
                    a1, a2, a3 = st.columns(3)
                    a1.metric("Mean Target", f"${report.analyst_target_mean:,.2f}", f"{upside:+.1f}% upside")
                    a2.metric("High Target", f"${report.analyst_target_high:,.2f}")
                    a3.metric("Low Target", f"${report.analyst_target_low:,.2f}")
                else:
                    st.write("No analyst targets available.")

            with st.expander("Quantitative Signals", expanded=False):
                q1, q2, q3, q4 = st.columns(4)
                q1.metric("RSI (14)", f"{quant.rsi_14}" if quant.rsi_14 else "N/A",
                        "Overbought" if quant.rsi_14 and quant.rsi_14 > 70 else "Oversold" if quant.rsi_14 and quant.rsi_14 < 30 else "Neutral")
                q2.metric("Beta (60d)", f"{quant.beta_60d}" if quant.beta_60d else "N/A")
                q3.metric("Sharpe (1Y)", f"{quant.sharpe_ratio_1y}" if quant.sharpe_ratio_1y else "N/A")
                q4.metric("Max Drawdown", f"{quant.max_drawdown_1y}%")

                t1, t2, t3, t4 = st.columns(4)
                t1.metric("SMA 20", f"${quant.sma20:,.2f}")
                t2.metric("SMA 50", f"${quant.sma50:,.2f}")
                t3.metric("SMA 200", f"${quant.sma200:,.2f}")
                t4.metric("Golden Cross", "Yes" if quant.golden_cross else "No")

                m1, m2, m3 = st.columns(3)
                m1.metric("MACD Line", f"{quant.macd_line}" if quant.macd_line else "N/A")
                m2.metric("MACD Signal", f"{quant.macd_signal}" if quant.macd_signal else "N/A")
                m3.metric("MACD Histogram", f"{quant.macd_histogram}" if quant.macd_histogram else "N/A")

            with st.expander("Sentiment Analysis", expanded=False):
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Overall", f"{sentiment.overall.title()}")
                s2.metric("Score", f"{sentiment.score:+.2f}")
                s3.metric("Confidence", sentiment.confidence.title())
                s4.metric("Trend", sentiment.sentiment_trend.title())

                if sentiment.themes:
                    st.markdown("**Themes:**")
                    for theme in sentiment.themes:
                        st.write(f"- **{theme.trajectory.title()}**: " + theme.description.replace("$", "\\$").replace("_", "\\_"))

                if sentiment.inflections:
                    st.markdown("**Narrative Inflections:**")
                    for inflection in sentiment.inflections:
                        st.write("- " + inflection.replace("$", "\\$").replace("_", "\\_"))

                if sentiment.latent_risks:
                    st.markdown("**Latent Risks:**")
                    for risk in sentiment.latent_risks:
                        st.write("- " + risk.replace("$", "\\$").replace("_", "\\_"))

            with st.expander("Key Metrics", expanded=False):
                for metric in report.key_metrics:
                    st.write("- " + metric.replace("$", "\\$").replace("_", "\\_"))

            if result.get("errors"):
                with st.expander("Pipeline warnings", expanded=False):
                    for error in result["errors"]:
                        st.warning(error)

