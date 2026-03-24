import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st


st.set_page_config(page_title="Kaufen vs. Mieten", layout="wide")
st.title("Kaufen vs. Mieten – interaktive Simulation")

def simulate(
    home_price=400_000,
    equity=80_000,
    interest_rate=0.04,
    years=30,
    appreciation=0.02,
    rent=1200,
    rent_growth=0.02,
    maint_rate=0.01,
    investment_return=0.05,
    initial_investment=0
):
    # -----------------------------
    # Grundparameter
    # -----------------------------
    months = years * 12
    closing_cost_rate = 0.08
    closing_cost = home_price * closing_cost_rate

    loan_amount = max(home_price - equity, 0)
    monthly_interest = interest_rate / 12
    monthly_return = investment_return / 12

    # -----------------------------
    # Annuität (Monatsrate)
    # -----------------------------
    if loan_amount == 0:
        annuity = 0.0
    else:
        annuity = loan_amount * (
            monthly_interest * (1 + monthly_interest) ** months
        ) / ((1 + monthly_interest) ** months - 1)

    mortgage_payment = np.full(months, annuity)

    # -----------------------------
    # Instandhaltung (monatlich)
    # -----------------------------
    monthly_maint = home_price * maint_rate / 12
    buy_cashflow = mortgage_payment + monthly_maint

    # -----------------------------
    # Miete (jährlich wachsend: pro Jahr Sprung)
    # -----------------------------
    rents = np.array([
        rent * (1 + rent_growth) ** (m // 12)
        for m in range(months)
    ])

    # -----------------------------
    # Investment beim Mieten: Differenz investieren
    # -----------------------------
    invest_per_month = buy_cashflow - rents
    invest_per_month = np.where(invest_per_month < 0, 0, invest_per_month)

    investment_value = float(initial_investment)
    investment_history = np.empty(months)

    for m in range(months):
        investment_value = investment_value * (1 + monthly_return) + invest_per_month[m]
        investment_history[m] = investment_value

    # -----------------------------
    # Kreditverlauf: Zins & Tilgung
    # -----------------------------
    remaining = float(loan_amount)
    remaining_history = np.empty(months)
    interest_history = np.empty(months)
    principal_history = np.empty(months)

    for m in range(months):
        interest = remaining * monthly_interest
        principal = annuity - interest
        remaining = max(remaining - principal, 0)

        interest_history[m] = interest
        principal_history[m] = principal
        remaining_history[m] = remaining

    # Kumuliert
    interest_cum = np.cumsum(interest_history)
    principal_cum = np.cumsum(principal_history)
    maint_cum = np.cumsum(np.full(months, monthly_maint))
    rent_cum = np.cumsum(rents)
    mortgage_paid_cum = np.cumsum(mortgage_payment)
    invest_contrib_cum = np.cumsum(invest_per_month)

    # -----------------------------
    # Immobilienwert
    # -----------------------------
    property_value_history = home_price * (1 + appreciation) ** (np.arange(months) / 12)

    # -----------------------------
    # Eigenkapital im Haus (Vermögen aus Kauf)
    # -----------------------------
    equity_home = property_value_history - remaining_history - closing_cost
    equity_home = np.maximum(equity_home, 0)

    # -----------------------------
    # Tabellen (Snapshot + kumuliert)
    # -----------------------------
    years_view = np.array([1, 5, 10, 20, years])
    months_idx = (years_view * 12 - 1).clip(0, months - 1)

    df_equity = pd.DataFrame({
        "Jahr": years_view,
        "Eigenkapital im Haus (€)": equity_home[months_idx],
        "Depotwert (€)": investment_history[months_idx],
    })

    df_monthly = pd.DataFrame({
        "Jahr": years_view,

        # Kaufen: Monats-Aufschlüsselung
        "Rate p.M. (€)": mortgage_payment[months_idx],
        "Zins p.M. (€)": interest_history[months_idx],
        "Tilgung p.M. (€)": principal_history[months_idx],
        "Instandhaltung p.M. (€)": np.full(len(years_view), monthly_maint),
        "Kauf-Cashflow p.M. (€)": buy_cashflow[months_idx],

        # Mieten: Monatswerte
        "Miete p.M. (€)": rents[months_idx],
        "Invest (Diff) p.M. (€)": invest_per_month[months_idx],
    })

    df_cum = pd.DataFrame({
        "Jahr": years_view,

        # Kaufen: kumuliert
        "Kaufnebenkosten (einmalig) (€)": np.full(len(years_view), closing_cost),
        "Kumulierte Zinsen (€)": interest_cum[months_idx],
        "Kumulierte Tilgung (€)": principal_cum[months_idx],
        "Kumulierte Instandhaltung (€)": maint_cum[months_idx],
        "Kumulierte Rate (Bank) (€)": mortgage_paid_cum[months_idx],
        "Eigenkapital im Haus (€)": equity_home[months_idx],

        # Bestände am Jahresende
        "Restschuld (€)": remaining_history[months_idx],
        "Immobilienwert (€)": property_value_history[months_idx],

        # Mieten: kumuliert
        "Depotwert (€)": investment_history[months_idx],
        "Kumulierte Miete (€)": rent_cum[months_idx],
        "Kumuliert investiert (Beiträge) (€)": invest_contrib_cum[months_idx],
    })

    # Plot-Daten zurückgeben
    series = {
        "x_years": np.arange(months) / 12,
        "investment_history": investment_history,
        "equity_home": equity_home,
        "property_value_history": property_value_history,
        "interest_cum": interest_cum,
        "principal_cum": principal_cum,
        "maint_cum": maint_cum,
        "rent_cum": rent_cum,
    }

    return df_equity, df_monthly, df_cum, series


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Kaufen vs. Mieten", layout="wide")
st.title("Kaufen vs. Mieten – interaktive Simulation (Streamlit)")

with st.sidebar:
    st.header("Parameter")

    home_price = st.slider("Kaufpreis (€)", 150_000, 1_000_000, 400_000, step=10_000)
    equity = st.slider("Eigenkapital (€)", 0, 500_000, 80_000, step=5_000)

    interest_rate = st.slider("Zins p.a. (%)", 1.0, 8.0, 4.0, step=0.1) / 100
    years = st.slider("Laufzeit (Jahre)", 10, 40, 30, step=1)

    appreciation = st.slider("Preissteigerung p.a. (%)", -2.0, 5.0, 2.0, step=0.1) / 100

    rent = st.slider("Miete Start (€/Monat)", 500, 4000, 1200, step=50)
    rent_growth = st.slider("Mietsteigerung p.a. (%)", 0.0, 5.0, 2.0, step=0.1) / 100

    maint_rate = st.slider("Instandhaltung p.a. (% vom Kaufpreis)", 0.5, 3.0, 1.0, step=0.1) / 100
    investment_return = st.slider("Investmentrendite p.a. (%)", 1.0, 10.0, 5.0, step=0.1) / 100

    initial_investment = st.slider("Start-Investment (€)", 0, 500_000, 0, step=5_000)

# Simulation
df_equity, df_monthly, df_cum, s = simulate(
    home_price=home_price,
    equity=equity,
    interest_rate=interest_rate,
    years=years,
    appreciation=appreciation,
    rent=rent,
    rent_growth=rent_growth,
    maint_rate=maint_rate,
    investment_return=investment_return,
    initial_investment=initial_investment,
)

# -----------------------------
# Plots
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Vermögen / Wohlstand (entscheidungsrelevant)")
    fig1, ax1 = plt.subplots(figsize=(10, 4.8))
    ax1.plot(s["x_years"], s["investment_history"], label="Mieten: Depotwert")
    ax1.plot(s["x_years"], s["equity_home"], label="Kaufen: Eigenkapital im Haus")
    ax1.plot(s["x_years"], s["property_value_history"], "--", alpha=0.35, label="Immobilienwert (brutto)")
    ax1.set_xlabel("Jahre")
    ax1.set_ylabel("€")
    ax1.grid(True)
    ax1.legend(loc="upper left")
    st.pyplot(fig1)

with col2:
    st.subheader("Kumulierte Größen (Erklärung)")
    fig2, ax2 = plt.subplots(figsize=(10, 4.8))
    ax2.plot(s["x_years"], s["interest_cum"], label="Kumulierte Zinsen")
    ax2.plot(s["x_years"], s["principal_cum"], label="Kumulierte Tilgung")
    ax2.plot(s["x_years"], s["maint_cum"], label="Kumulierte Instandhaltung")
    ax2.plot(s["x_years"], s["rent_cum"], label="Kumulierte Miete")
    ax2.set_xlabel("Jahre")
    ax2.set_ylabel("€")
    ax2.grid(True)
    ax2.legend(loc="upper left")
    st.pyplot(fig2)

# -----------------------------
# Tabellen (wie bei dir)
# -----------------------------
st.divider()
tab0, tab1, tab2 = st.tabs(["Vergleich Vermögensentwicklung", "Monatliche Werte", "Kumulierte Werte"])

with tab0:
    st.dataframe(df_equity.style.format("{:,.0f}", subset=df_equity.columns[1:]), use_container_width=True)
    st.download_button(
        "CSV herunterladen (Vergleich)",
        df_equity.to_csv(index=False).encode("utf-8"),
        file_name="vergleich_vermoegen.csv",
        mime="text/csv",
    )

with tab1:
    st.dataframe(df_monthly.style.format("{:,.0f}", subset=df_monthly.columns[1:]), use_container_width=True)
    st.download_button(
        "CSV herunterladen (Monatlich)",
        df_monthly.to_csv(index=False).encode("utf-8"),
        file_name="monatliche_werte.csv",
        mime="text/csv",
    )

with tab2:
    st.dataframe(df_cum.style.format("{:,.0f}", subset=df_cum.columns[1:]), use_container_width=True)
    st.download_button(
        "CSV herunterladen (Kumuliert)",
        df_cum.to_csv(index=False).encode("utf-8"),
        file_name="kumulierte_werte.csv",
        mime="text/csv",
    )