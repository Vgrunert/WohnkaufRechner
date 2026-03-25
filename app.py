import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

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
        "Differenz investiert (€)": equity_home[months_idx] - investment_history[months_idx],
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
# Ergebnis-Kennzahlen (Ende der Laufzeit)
# -----------------------------
final_year = years
final_equity_buy = df_equity["Eigenkapital im Haus (€)"].iloc[-1]
final_equity_rent = df_equity["Depotwert (€)"].iloc[-1]

delta = final_equity_buy - final_equity_rent

better_option = "Kaufen" if delta > 0 else "Mieten"
abs_delta = abs(delta)

# Zusatzinfos für Erklärung
total_interest = df_cum["Kumulierte Zinsen (€)"].iloc[-1]
total_rent = df_cum["Kumulierte Miete (€)"].iloc[-1]
total_principal = df_cum["Kumulierte Tilgung (€)"].iloc[-1]



# -----------------------------
# Plots
# -----------------------------
col1 = st.columns(1)

# ✅ EINE gemeinsame Figure mit zwei Axes
fig, (ax1, ax2) = plt.subplots(
    1, 2,
    figsize=(14, 4.8),
    layout="constrained"
)

# --- Plot links: Vermögen ---
ax1.plot(s["x_years"], s["investment_history"], label="Mieten: Depotwert")
ax1.plot(s["x_years"], s["equity_home"], label="Kaufen: Eigenkapital im Haus")
ax1.plot(s["x_years"], s["property_value_history"], "--", alpha=0.35, label="Immobilienwert (brutto)")
ax1.set_xlabel("Jahre")
ax1.set_ylabel("€")
ax1.grid(True)
ax1.legend(loc="upper left")
ax1.set_title("Vermögen / Wohlstand")

# --- Plot rechts: Kumulierte Größen ---
ax2.plot(s["x_years"], s["interest_cum"], label="Kumulierte Zinsen")
ax2.plot(s["x_years"], s["principal_cum"], label="Kumulierte Tilgung")
ax2.plot(s["x_years"], s["maint_cum"], label="Kumulierte Instandhaltung")
ax2.plot(s["x_years"], s["rent_cum"], label="Kumulierte Miete")
ax2.set_xlabel("Jahre")
ax2.set_ylabel("€")
ax2.grid(True)
ax2.legend(loc="upper left")
ax2.set_title("Kumulierte Größen")

# ✅ dieselbe Figure in beide Columns "schneiden"
# with col1:
st.pyplot(fig, use_container_width=True)



# -----------------------------
# Erklärungstext (Markdown)
# -----------------------------
st.divider()
st.subheader("Bedeutung der Plots & Interpretation")

st.markdown("""
## Wie ist dieser Vergleich zu lesen?

Diese Simulation vergleicht **Kaufen vs. Mieten** unter der Annahme,  
dass beim Mieten die **monatliche Differenz** zwischen Kauf‑Cashflow  
(Kreditrate + Instandhaltung) und Miete **konsequent investiert** wird.

### Linker Plot – Vermögen / Wohlstand (entscheidungsrelevant)
Dieser Plot zeigt die **relevanten Vermögensstände über die Zeit**:

- **Kaufen:**  
  *Eigenkapital im Haus* = Immobilienwert − Restschuld − Kaufnebenkosten  
  → Tilgung wirkt hier als Vermögensaufbau, Zinsen nicht.

- **Mieten:**  
  *Depotwert* aus dem Investieren der monatlichen Differenz  
  → Miete reduziert den Sparbetrag automatisch.

- **Immobilienwert (brutto):**  
  Nur zur Einordnung – kein direkt vergleichbarer Wohlstand.

👉 **Dieser Plot beantwortet die Kernfrage:**  
**Mit welcher Alternative baue ich mehr Vermögen auf?**

---

### Rechter Plot – Kumulierte Größen (Erklärungsebene)
Dieser Plot zeigt **aufsummierte Zahlungsströme**:

- Kumulierte Zinsen  
- Kumulierte Tilgung (Vermögensaufbau, kein Kostenblock)  
- Kumulierte Instandhaltung  
- Kumulierte Miete  

👉 **Dieser Plot erklärt das „Warum“**,  
ist aber **nicht** direkt für die Entscheidungsfrage gedacht.

---

### Wichtige Annahmen & Hinweise
- Tilgung wird **nicht als Kosten** behandelt, sondern als Sparen.
- Kaufnebenkosten werden **einmalig** beim Kauf berücksichtigt.
- Steuern, Förderungen, Verkaufskosten und Leerstand sind **nicht** modelliert.
- Das Modell vergleicht **reine Zahlungsströme und Vermögensbildung**,  
  nicht persönliche Präferenzen (Flexibilität, Risiko, Lebensstil).

➡️ **Interpretation:**  
Der Vergleich ist dann fair, wenn beide Alternativen  
denselben monatlichen finanziellen Spielraum beanspruchen.
""")


st.divider()
st.subheader("Zusammenfassung & Interpretation")

st.markdown(f"""
### Ergebnis nach {final_year} Jahren

Bei einem **Kaufpreis von {home_price:,.0f} €**,  
einem **Zinssatz von {interest_rate*100:.1f} %**  
und einer **Laufzeit von {final_year} Jahren** ergibt sich folgendes Bild:

- **Alternative Kaufen**  
  - Eigenkapital im Haus: **{final_equity_buy:,.0f} €**  
  - Davon wurden **{total_principal:,.0f} €** durch Tilgung aufgebaut  
  - Die gesamten Zinskosten betragen **{total_interest:,.0f} €**

- **Alternative Mieten + Investieren der Differenz**  
  - Depotwert am Ende: **{final_equity_rent:,.0f} €**  
  - Insgesamt gezahlte Miete: **{total_rent:,.0f} €**

### Fazit
In diesem Szenario ist **{better_option}** die finanziell vorteilhaftere Alternative.

Der Unterschied beträgt **{abs_delta:,.0f} €** zugunsten von **{better_option}**.

### Warum?
""")

if better_option == "Kaufen":
    st.markdown("""
- Ein großer Teil der monatlichen Kreditrate fließt in **Tilgung** und erhöht direkt das Eigenkapital.
- Trotz der Zinskosten wirkt der **Hebel der Immobilie** (Fremdkapital + Wertsteigerung).
- Die eingesparte Miete kompensiert langfristig die laufenden Kosten.
""")
else:
    st.markdown("""
- Die **Miete ist niedriger** als der Kauf‑Cashflow, wodurch regelmäßig investiert werden kann.
- Das **Depot profitiert vom Zinseszinseffekt** über viele Jahre.
- Die Zinskosten des Kredits übersteigen den Vorteil der Immobilien‑Tilgung.
""")

st.caption("""
Hinweis:  
Diese Bewertung berücksichtigt ausschließlich Zahlungsströme und Vermögensaufbau.  
Persönliche Faktoren wie Flexibilität, Risiko, Steuern, Förderungen oder ein späterer Verkauf
sind nicht enthalten.
""")

# with col2:
#     st.pyplot(fig, use_container_width=True)




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